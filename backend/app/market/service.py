"""Market, team and user operations. Routers call these and nothing else.

Functions return None when the thing asked for does not exist; the router turns that into a 404.
Raise MarketError for a request that is understood but not allowed; the router turns that into a 400.

Locking: anything that changes a market's weights first locks that market's positions rows
(_lock_positions), so two changes at once can't read the same price. Take that lock before
locking a users row, always in that order.
"""

import re
import uuid
from datetime import datetime

from psycopg import AsyncConnection

from app import db
from app.config import get_settings
from app.market import pricing
from app.schemas import (
    BetCreate,
    BetFeedItem,
    BetReceipt,
    LeaderboardEntry,
    MarketDetail,
    MarketHistory,
    MarketSummary,
    MarketTeam,
    MarketTotals,
    PricePoint,
    ResolveResult,
    ScoutFeedItem,
    Team,
    TeamCreate,
    TeamSeries,
    User,
    UserBet,
    UserSummary,
)


class MarketError(Exception):
    """A bet or resolution that breaks a market rule, e.g. stake above balance."""


def _as_uuid(value: str) -> uuid.UUID | None:
    """User ids arrive as strings from the browser; a malformed one is simply an unknown user."""
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        return None


async def _fetchone(conn: AsyncConnection, sql: str, params: tuple = ()) -> dict | None:
    return await (await conn.execute(sql, params)).fetchone()


async def _fetchall(conn: AsyncConnection, sql: str, params: tuple = ()) -> list[dict]:
    return await (await conn.execute(sql, params)).fetchall()


async def _lock_positions(conn: AsyncConnection, market_id: str) -> dict[str, dict[str, float]]:
    """Lock a market's positions rows until the transaction ends. Returns team_id -> {seed, staked}."""
    rows = await _fetchall(
        conn,
        "SELECT team_id, seed, staked FROM positions WHERE market_id = %s ORDER BY team_id FOR UPDATE",
        (market_id,),
    )
    return {r["team_id"]: {"seed": float(r["seed"]), "staked": float(r["staked"])} for r in rows}


def _weights(positions: dict[str, dict[str, float]]) -> dict[str, float]:
    return {team_id: p["seed"] + p["staked"] for team_id, p in positions.items()}


async def _clock(conn: AsyncConnection) -> datetime:
    """The time right now, for bets and ticks written under the positions lock.

    Not now(): that is the transaction's start, which can be earlier than a change that got
    the lock first. The clock read after the lock keeps bets and ticks in their true order.
    """
    return (await _fetchone(conn, "SELECT clock_timestamp() AS at"))["at"]


async def _write_ticks(
    conn: AsyncConnection, market_id: str, weights: dict[str, float], source: str, at: datetime
) -> None:
    """Record every team's price in a market after its weights changed. `source` is 'bet' or 'scout'."""
    prices = pricing.prices_from_weights(weights, get_settings().price_floor)
    async with conn.cursor() as cur:
        await cur.executemany(
            "INSERT INTO price_ticks (time, market_id, team_id, price, source) VALUES (%s, %s, %s, %s, %s)",
            [(at, market_id, team_id, price, source) for team_id, price in prices.items()],
        )


# ---- Teams -----------------------------------------------------------------


_TEAM_COLUMNS = "id, name, idea, repo_url, demo_url, color, creator_user_id"


def _team(row: dict) -> Team:
    return Team(
        id=row["id"],
        name=row["name"],
        idea=row["idea"],
        repo_url=row.get("repo_url"),
        demo_url=row.get("demo_url"),
        color=row["color"],
        creator_user_id=str(row["creator_user_id"]) if row.get("creator_user_id") else None,
    )


async def list_teams() -> list[Team]:
    async with db.get_pool().connection() as conn:
        rows = await _fetchall(conn, f"SELECT {_TEAM_COLUMNS} FROM teams ORDER BY created_at, name")
    return [_team(r) for r in rows]


async def get_team(team_id: str) -> Team | None:
    async with db.get_pool().connection() as conn:
        row = await _fetchone(conn, f"SELECT {_TEAM_COLUMNS} FROM teams WHERE id = %s", (team_id,))
    return _team(row) if row else None


# Assigned in sign-up order, then reused. From the build spec's design tokens.
TEAM_COLORS = ["#7DB8FF", "#FFB454", "#D2B8FF", "#4FC9B0", "#F29BB7", "#C9D1D8"]


async def create_team(body: TeamCreate) -> Team:
    """Save a team and enter it in every open market.

    It enters with no seed, so it sits at the price floor until Scout's first report sets its odds.
    """
    base = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-") or "team"
    creator_uid = _as_uuid(body.creator_user_id) if body.creator_user_id else None
    async with db.get_pool().connection() as conn:
        async with conn.transaction():
            if await _fetchone(conn, "SELECT 1 FROM teams WHERE lower(name) = lower(%s)", (body.name,)):
                raise MarketError("A team with this name has already signed up.")
            taken = {r["id"] for r in await _fetchall(conn, "SELECT id FROM teams WHERE id LIKE %s", (base + "%",))}
            slug, n = base, 2
            while slug in taken:
                slug, n = f"{base}-{n}", n + 1
            count = (await _fetchone(conn, "SELECT count(*) AS n FROM teams"))["n"]
            row = await _fetchone(
                conn,
                f"INSERT INTO teams (id, name, idea, repo_url, demo_url, color, creator_user_id) VALUES (%s, %s, %s, %s, %s, %s, %s) "
                f"RETURNING {_TEAM_COLUMNS}",
                (slug, body.name, body.idea, body.repo_url, body.demo_url, TEAM_COLORS[count % len(TEAM_COLORS)], creator_uid),
            )
            open_markets = await _fetchall(conn, "SELECT id FROM markets WHERE status = 'open' ORDER BY id")
            for market in open_markets:
                positions = await _lock_positions(conn, market["id"])
                await conn.execute(
                    "INSERT INTO positions (market_id, team_id, seed, staked) VALUES (%s, %s, 0, 0)", (market["id"], slug)
                )
                positions[slug] = {"seed": 0.0, "staked": 0.0}
                await _write_ticks(conn, market["id"], _weights(positions), "scout", await _clock(conn))
    return _team(row)


# ---- Markets ---------------------------------------------------------------


_MARKET_COLUMNS = "id, title, category, status, winner_team_id"
# The order the category pills appear in. Any other market sorts after these, by id.
_MARKET_ORDER = ["overall", "nimble", "gemini", "tiger_data"]


async def list_markets() -> list[MarketSummary]:
    async with db.get_pool().connection() as conn:
        rows = await _fetchall(
            conn,
            f"SELECT {_MARKET_COLUMNS} FROM markets ORDER BY coalesce(array_position(%s::text[], id), 999), id",
            (_MARKET_ORDER,),
        )
    return [MarketSummary(**r) for r in rows]


async def get_market(market_id: str) -> MarketDetail | None:
    async with db.get_pool().connection() as conn:
        market = await _fetchone(conn, f"SELECT {_MARKET_COLUMNS} FROM markets WHERE id = %s", (market_id,))
        if market is None:
            return None
        rows = await _fetchall(
            conn,
            "SELECT p.team_id, t.name, t.idea, t.color, p.seed, p.staked "
            "FROM positions p JOIN teams t ON t.id = p.team_id WHERE p.market_id = %s",
            (market_id,),
        )
        bets = await _fetchone(
            conn,
            "SELECT coalesce(sum(stake), 0) AS traded, count(DISTINCT user_id) AS forecasters "
            "FROM bets WHERE market_id = %s",
            (market_id,),
        )

    prices = pricing.prices_from_weights(
        {r["team_id"]: float(r["seed"] + r["staked"]) for r in rows}, get_settings().price_floor
    )
    # Scout's odds are its share of the seed: that is exactly how it sets them (see apply_scout_odds).
    seed_total = sum(float(r["seed"]) for r in rows)
    teams = [
        MarketTeam(
            team_id=r["team_id"],
            name=r["name"],
            idea=r["idea"],
            color=r["color"],
            price=prices[r["team_id"]],
            multiple=pricing.multiple_for(prices[r["team_id"]]),
            scout_odds=float(r["seed"]) / seed_total if seed_total > 0 else 1 / len(rows),
            staked=float(r["staked"]),
        )
        for r in rows
    ]
    teams.sort(key=lambda t: (-t.price, t.name))
    return MarketDetail(
        **market,
        totals=MarketTotals(
            team_count=len(teams), hackcoin_traded=float(bets["traded"]), forecaster_count=bets["forecasters"]
        ),
        teams=teams,
    )


async def get_history(market_id: str) -> MarketHistory | None:
    """Per-minute prices for the chart, from the price_ticks_1m continuous aggregate (not raw ticks)."""
    async with db.get_pool().connection() as conn:
        if not await _fetchone(conn, "SELECT 1 FROM markets WHERE id = %s", (market_id,)):
            return None
        teams = await _fetchall(
            conn,
            "SELECT t.id, t.name, t.color FROM positions p JOIN teams t ON t.id = p.team_id "
            "WHERE p.market_id = %s ORDER BY t.created_at, t.name",
            (market_id,),
        )
        points = await _fetchall(
            conn, "SELECT bucket, team_id, price FROM price_ticks_1m WHERE market_id = %s ORDER BY bucket", (market_id,)
        )
    by_team: dict[str, list[PricePoint]] = {t["id"]: [] for t in teams}
    for p in points:
        if p["team_id"] in by_team:
            by_team[p["team_id"]].append(PricePoint(time=p["bucket"], price=p["price"]))
    return MarketHistory(
        market_id=market_id,
        series=[TeamSeries(team_id=t["id"], name=t["name"], color=t["color"], points=by_team[t["id"]]) for t in teams],
    )


# A Scout re-price shows in the feed when it moved a team by about a point or more.
_SCOUT_MOVE_MIN = 0.00999


async def get_feed(market_id: str, limit: int = 20) -> list[BetFeedItem | ScoutFeedItem] | None:
    """The latest bets and Scout moves, newest first. The feed is a query, not a table."""
    async with db.get_pool().connection() as conn:
        if not await _fetchone(conn, "SELECT 1 FROM markets WHERE id = %s", (market_id,)):
            return None
        bets = await _fetchall(
            conn,
            "SELECT b.id, b.created_at AS time, u.display_name, b.team_id, t.name AS team_name, t.color AS team_color, "
            "       b.stake, b.price_at_bet AS price "
            "FROM bets b JOIN users u ON u.id = b.user_id JOIN teams t ON t.id = b.team_id "
            "WHERE b.market_id = %s ORDER BY b.created_at DESC LIMIT %s",
            (market_id, limit),
        )
        # Each scout tick against the price just before it, whoever set that price.
        moves = await _fetchall(
            conn,
            "SELECT x.time, x.team_id, t.name AS team_name, t.color AS team_color, x.prev AS price_from, x.price AS price_to "
            "FROM (SELECT time, team_id, price, source, lag(price) OVER (PARTITION BY team_id ORDER BY time) AS prev "
            "      FROM price_ticks WHERE market_id = %s) x "
            "JOIN teams t ON t.id = x.team_id "
            "WHERE x.source = 'scout' AND x.prev IS NOT NULL AND abs(x.price - x.prev) >= %s "
            "ORDER BY x.time DESC LIMIT %s",
            (market_id, _SCOUT_MOVE_MIN, limit),
        )
    items: list[BetFeedItem | ScoutFeedItem] = [
        BetFeedItem(
            id=str(b["id"]), time=b["time"], user_display_name=b["display_name"], team_id=b["team_id"],
            team_name=b["team_name"], team_color=b["team_color"], stake=float(b["stake"]), price=b["price"],
        )
        for b in bets
    ]
    items += [
        ScoutFeedItem(
            id=f"scout-{m['team_id']}-{m['time'].timestamp()}", time=m["time"], team_id=m["team_id"],
            team_name=m["team_name"], team_color=m["team_color"], price_from=m["price_from"], price_to=m["price_to"],
            note="after its latest report",
        )
        for m in moves
    ]
    items.sort(key=lambda item: item.time, reverse=True)
    return items[:limit]


async def place_bet(body: BetCreate) -> BetReceipt | None:
    """Fill a bet against the house at the current price, in one transaction."""
    user_id = _as_uuid(body.user_id)
    async with db.get_pool().connection() as conn:
        async with conn.transaction():
            # An unknown market has no positions, so this also covers "market not found".
            weights = _weights(await _lock_positions(conn, body.market_id))
            if body.team_id not in weights:
                return None
            # Read the status only once we hold the lock: a resolve may have just finished.
            market = await _fetchone(conn, "SELECT status FROM markets WHERE id = %s", (body.market_id,))
            if market["status"] != "open":
                raise MarketError("Betting is closed: this market has been resolved.")

            user = None
            if user_id is not None:
                user = await _fetchone(conn, "SELECT balance FROM users WHERE id = %s FOR UPDATE", (user_id,))
            if user is None:
                raise MarketError("We don't know this player. Pick a display name and try again.")
            if body.stake > user["balance"]:
                raise MarketError("Stake is more than your balance.")

            price = pricing.prices_from_weights(weights, get_settings().price_floor)[body.team_id]
            multiple = pricing.multiple_for(price)
            at = await _clock(conn)

            bet = await _fetchone(
                conn,
                "INSERT INTO bets (user_id, market_id, team_id, stake, price_at_bet, multiple, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (user_id, body.market_id, body.team_id, body.stake, price, multiple, at),
            )
            balance = await _fetchone(
                conn, "UPDATE users SET balance = balance - %s WHERE id = %s RETURNING balance", (body.stake, user_id)
            )
            await conn.execute(
                "UPDATE positions SET staked = staked + %s WHERE market_id = %s AND team_id = %s",
                (body.stake, body.market_id, body.team_id),
            )
            weights[body.team_id] += body.stake
            await _write_ticks(conn, body.market_id, weights, "bet", at)

    return BetReceipt(
        bet_id=str(bet["id"]),
        market_id=body.market_id,
        team_id=body.team_id,
        stake=body.stake,
        price_at_bet=price,
        multiple=multiple,
        potential_payout=pricing.payout(body.stake, multiple),
        new_balance=float(balance["balance"]),
        created_at=at,
    )


async def resolve_market(market_id: str, winner_team_id: str) -> ResolveResult | None:
    """Close a market and pay every bet on the winner its stake times its locked multiple."""
    async with db.get_pool().connection() as conn:
        async with conn.transaction():
            # The lock stops bets landing mid-payout. An unknown market has no positions.
            if winner_team_id not in await _lock_positions(conn, market_id):
                return None
            market = await _fetchone(conn, "SELECT status FROM markets WHERE id = %s", (market_id,))
            if market["status"] != "open":
                raise MarketError("This market has already been resolved.")
            resolved = await _fetchone(
                conn,
                f"UPDATE markets SET status = 'resolved', winner_team_id = %s WHERE id = %s RETURNING {_MARKET_COLUMNS}",
                (winner_team_id, market_id),
            )
            # The multiple was stored when the bet was placed; it is never recomputed here.
            wins = await _fetchall(
                conn,
                "SELECT user_id, stake, multiple FROM bets WHERE market_id = %s AND team_id = %s",
                (market_id, winner_team_id),
            )
            owed: dict[uuid.UUID, float] = {}
            for w in wins:
                owed[w["user_id"]] = owed.get(w["user_id"], 0) + pricing.payout(float(w["stake"]), w["multiple"])
            async with conn.cursor() as cur:
                await cur.executemany(
                    "UPDATE users SET balance = balance + %s WHERE id = %s",
                    # Sorted so two resolves at once always lock players in the same order.
                    [(round(amount, 2), user_id) for user_id, amount in sorted(owed.items())],
                )
    return ResolveResult(
        market=MarketSummary(**resolved), bets_paid=len(wins), total_paid=round(sum(owed.values()), 2)
    )


async def apply_scout_odds(market_id: str, odds: dict[str, float]) -> None:
    """The one place Scout touches the market. `odds` maps team_id -> a share; they need not sum to 1.

    Scout calls this for each market at the end of a run (scout.pipeline.reprice_markets).
    The market's seed is re-split by these odds, which moves prices; stakes are untouched.
    A team left out of `odds` gets no seed. Unknown team ids are ignored. Resolved and unknown
    markets are left alone.
    """
    async with db.get_pool().connection() as conn:
        async with conn.transaction():
            positions = await _lock_positions(conn, market_id)
            market = await _fetchone(conn, "SELECT status FROM markets WHERE id = %s", (market_id,))
            if not positions or market["status"] != "open":
                return
            seeds = pricing.split_seed(
                {team_id: max(0.0, float(odds.get(team_id, 0))) for team_id in positions},
                get_settings().seed_per_market,
            )
            async with conn.cursor() as cur:
                await cur.executemany(
                    "UPDATE positions SET seed = %s WHERE market_id = %s AND team_id = %s",
                    [(seed, market_id, team_id) for team_id, seed in seeds.items()],
                )
            for team_id, seed in seeds.items():
                positions[team_id]["seed"] = seed
            await _write_ticks(conn, market_id, _weights(positions), "scout", await _clock(conn))


# ---- Users -----------------------------------------------------------------


def _user(row: dict) -> User:
    return User(id=str(row["id"]), display_name=row["display_name"], balance=float(row["balance"]))


async def create_user(display_name: str) -> User:
    async with db.get_pool().connection() as conn:
        row = await _fetchone(
            conn,
            "INSERT INTO users (display_name, balance) VALUES (%s, %s) RETURNING id, display_name, balance",
            (display_name, get_settings().starting_balance),
        )
    return _user(row)


async def get_user(user_id: str) -> User | None:
    uid = _as_uuid(user_id)
    if uid is None:
        return None
    async with db.get_pool().connection() as conn:
        row = await _fetchone(conn, "SELECT id, display_name, balance FROM users WHERE id = %s", (uid,))
    return _user(row) if row else None


async def get_leaderboard(limit: int = 100) -> list[LeaderboardEntry]:
    """Players by balance, richest first. Equal balances share a rank."""
    async with db.get_pool().connection() as conn:
        rows = await _fetchall(
            conn,
            "SELECT id, display_name, balance, rank() OVER (ORDER BY balance DESC) AS rank "
            "FROM users ORDER BY balance DESC, created_at LIMIT %s",
            (limit,),
        )
    return [
        LeaderboardEntry(rank=r["rank"], user_id=str(r["id"]), display_name=r["display_name"], balance=float(r["balance"]))
        for r in rows
    ]


async def get_user_summary(user_id: str) -> UserSummary | None:
    """Detailed summary of a user's activity: rank, balance, bets placed, and teams signed up."""
    uid = _as_uuid(user_id)
    if uid is None:
        return None
    async with db.get_pool().connection() as conn:
        user_row = await _fetchone(conn, "SELECT id, display_name, balance FROM users WHERE id = %s", (uid,))
        if user_row is None:
            return None

        rank_row = await _fetchone(
            conn,
            "SELECT rank FROM (SELECT id, rank() OVER (ORDER BY balance DESC) AS rank FROM users) x WHERE id = %s",
            (uid,),
        )
        rank = rank_row["rank"] if rank_row else None

        bet_rows = await _fetchall(
            conn,
            "SELECT b.id, b.market_id, m.title AS market_title, m.category AS market_category, "
            "       m.status AS market_status, m.winner_team_id, "
            "       b.team_id, t.name AS team_name, t.color AS team_color, "
            "       b.stake, b.price_at_bet, b.multiple, b.created_at "
            "FROM bets b "
            "JOIN markets m ON m.id = b.market_id "
            "JOIN teams t ON t.id = b.team_id "
            "WHERE b.user_id = %s "
            "ORDER BY b.created_at DESC",
            (uid,),
        )

        team_rows = await _fetchall(
            conn,
            f"SELECT {_TEAM_COLUMNS} FROM teams WHERE creator_user_id = %s ORDER BY created_at DESC",
            (uid,),
        )

    bets: list[UserBet] = []
    total_staked = 0.0
    open_bets_count = 0
    won_bets_count = 0
    total_payout = 0.0

    for r in bet_rows:
        stake = float(r["stake"])
        mult = float(r["multiple"])
        potential = pricing.payout(stake, mult)
        total_staked += stake

        if r["market_status"] == "resolved":
            if r["winner_team_id"] == r["team_id"]:
                status = "won"
                payout = potential
                won_bets_count += 1
                total_payout += payout
            else:
                status = "lost"
                payout = 0.0
        else:
            status = "open"
            payout = None
            open_bets_count += 1

        bets.append(
            UserBet(
                id=str(r["id"]),
                market_id=r["market_id"],
                market_title=r["market_title"],
                market_category=r["market_category"],
                market_status=r["market_status"],
                winner_team_id=r["winner_team_id"],
                team_id=r["team_id"],
                team_name=r["team_name"],
                team_color=r["team_color"],
                stake=stake,
                price_at_bet=float(r["price_at_bet"]),
                multiple=mult,
                potential_payout=potential,
                payout=payout,
                status=status,
                created_at=r["created_at"],
            )
        )

    user = _user(user_row)
    net_profit = round(user.balance - get_settings().starting_balance, 2)

    return UserSummary(
        user=user,
        rank=rank,
        total_staked=round(total_staked, 2),
        bet_count=len(bets),
        open_bets_count=open_bets_count,
        won_bets_count=won_bets_count,
        total_payout=round(total_payout, 2),
        net_profit=net_profit,
        bets=bets,
        teams=[_team(tr) for tr in team_rows],
    )


async def get_user_bets(user_id: str) -> list[UserBet] | None:
    summary = await get_user_summary(user_id)
    return summary.bets if summary else None

