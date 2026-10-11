"""Market, team and user operations. Routers call these and nothing else.

Functions marked TODO(market) still return sample data. Replace each body with real queries
against Tiger Data (see app/db.py) without changing its signature or return type, and the
routers and the frontend keep working.

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

from app import db, sample_data
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
    ResolveResult,
    ScoutFeedItem,
    Team,
    TeamCreate,
    User,
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


async def _lock_positions(conn: AsyncConnection, market_id: str) -> dict[str, float]:
    """Lock a market's positions rows until the transaction ends and return team_id -> weight."""
    rows = await _fetchall(
        conn,
        "SELECT team_id, seed + staked AS weight FROM positions WHERE market_id = %s ORDER BY team_id FOR UPDATE",
        (market_id,),
    )
    return {r["team_id"]: float(r["weight"]) for r in rows}


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


_TEAM_COLUMNS = "id, name, idea, repo_url, demo_url, color"


async def list_teams() -> list[Team]:
    async with db.get_pool().connection() as conn:
        rows = await _fetchall(conn, f"SELECT {_TEAM_COLUMNS} FROM teams ORDER BY created_at, name")
    return [Team(**r) for r in rows]


async def get_team(team_id: str) -> Team | None:
    async with db.get_pool().connection() as conn:
        row = await _fetchone(conn, f"SELECT {_TEAM_COLUMNS} FROM teams WHERE id = %s", (team_id,))
    return Team(**row) if row else None


async def create_team(body: TeamCreate) -> Team:
    # TODO(market): in one transaction, insert the team (next colour in TEAM_COLORS by sign-up order)
    # and a positions row with seed 0 in every market. Scout's first run then sets the seed.
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-") or uuid.uuid4().hex[:8]
    color = sample_data.TEAM_COLORS[len(sample_data.TEAMS) % len(sample_data.TEAM_COLORS)]
    return Team(id=slug, color=color, **body.model_dump())


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
    # TODO(market): read the price_ticks_1m continuous aggregate, not raw price_ticks.
    if market_id not in sample_data.MARKETS_BY_ID:
        return None
    return sample_data.market_history(market_id)


async def get_feed(market_id: str, limit: int = 20) -> list[BetFeedItem | ScoutFeedItem] | None:
    # TODO(market): the feed is a query, not a table. Latest bets UNION scout-sourced ticks that
    # moved a team's price by a point or more, newest first.
    if market_id not in sample_data.MARKETS_BY_ID:
        return None
    return sample_data.market_feed(market_id)[:limit]


async def place_bet(body: BetCreate) -> BetReceipt | None:
    """Fill a bet against the house at the current price, in one transaction."""
    user_id = _as_uuid(body.user_id)
    async with db.get_pool().connection() as conn:
        async with conn.transaction():
            # An unknown market has no positions, so this also covers "market not found".
            weights = await _lock_positions(conn, body.market_id)
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
            # Not now(): that is the transaction's start, which can be earlier than a bet that
            # got the lock first. The clock after the lock keeps bets and ticks in true order.
            at = (await _fetchone(conn, "SELECT clock_timestamp() AS at"))["at"]

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
        potential_payout=round(body.stake * multiple, 2),
        new_balance=float(balance["balance"]),
        created_at=at,
    )


async def resolve_market(market_id: str, winner_team_id: str) -> ResolveResult | None:
    # TODO(market): one transaction: refuse if already resolved, set status and winner, then credit
    # stake * multiple to every bet on the winner. Losing bets pay nothing.
    market = sample_data.MARKETS_BY_ID.get(market_id)
    if market is None or winner_team_id not in sample_data.TEAMS_BY_ID:
        return None
    resolved = market.model_copy(update={"status": "resolved", "winner_team_id": winner_team_id})
    return ResolveResult(market=resolved, bets_paid=0, total_paid=0)


async def apply_scout_odds(market_id: str, odds: dict[str, float]) -> None:
    """The one place Scout touches the market. `odds` maps team_id -> fraction, summing to 1.

    Scout calls this for each market at the end of a run (scout.pipeline.reprice_markets).
    """
    # TODO(market): one transaction, with the same positions lock as place_bet: re-split the seed
    # with pricing.split_seed, UPDATE positions.seed, insert a price tick with source 'scout' for
    # every team in the market.
    return None


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


async def get_leaderboard() -> list[LeaderboardEntry]:
    # TODO(market): users ORDER BY balance DESC.
    return sample_data.leaderboard()
