"""Market, team and user operations. Routers call these and nothing else.

Every function currently returns sample data. Replace each body with real queries against
Tiger Data (see app/db.py) without changing its signature or return type, and the routers
and the frontend keep working.

Functions return None when the thing asked for does not exist; the router turns that into a 404.
Raise MarketError for a request that is understood but not allowed; the router turns that into a 400.
"""

import re
import uuid
from datetime import datetime, timezone

from app import sample_data
from app.config import get_settings
from app.schemas import (
    BetCreate,
    BetFeedItem,
    BetReceipt,
    LeaderboardEntry,
    MarketDetail,
    MarketHistory,
    MarketSummary,
    ResolveResult,
    ScoutFeedItem,
    Team,
    TeamCreate,
    User,
)


class MarketError(Exception):
    """A bet or resolution that breaks a market rule, e.g. stake above balance."""


# ---- Teams -----------------------------------------------------------------


async def list_teams() -> list[Team]:
    # TODO(market): SELECT from teams ORDER BY created_at.
    return sample_data.TEAMS


async def get_team(team_id: str) -> Team | None:
    # TODO(market): SELECT from teams.
    return sample_data.TEAMS_BY_ID.get(team_id)


async def create_team(body: TeamCreate) -> Team:
    # TODO(market): in one transaction, insert the team (next colour in TEAM_COLORS by sign-up order)
    # and a positions row with seed 0 in every market. Scout's first run then sets the seed.
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-") or uuid.uuid4().hex[:8]
    color = sample_data.TEAM_COLORS[len(sample_data.TEAMS) % len(sample_data.TEAM_COLORS)]
    return Team(id=slug, color=color, **body.model_dump())


# ---- Markets ---------------------------------------------------------------


async def list_markets() -> list[MarketSummary]:
    # TODO(market): SELECT from markets.
    return sample_data.MARKETS


async def get_market(market_id: str) -> MarketDetail | None:
    # TODO(market): join positions and teams, compute prices with pricing.prices_from_weights,
    # take scout_odds from seed / sum(seed).
    if market_id not in sample_data.MARKETS_BY_ID:
        return None
    return sample_data.market_detail(market_id)


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
    # TODO(market): one transaction, with the market's positions rows locked (SELECT ... FOR UPDATE):
    # check the market is open, check balance, read the price, insert the bet, deduct the balance,
    # add to staked, insert a price tick with source 'bet' for every team in the market.
    market = await get_market(body.market_id)
    team = next((t for t in market.teams if t.team_id == body.team_id), None) if market else None
    if team is None:
        return None
    balance = sample_data.USER.balance
    if body.stake > balance:
        raise MarketError("Stake is more than your balance.")
    return BetReceipt(
        bet_id=str(uuid.uuid4()),
        market_id=body.market_id,
        team_id=body.team_id,
        stake=body.stake,
        price_at_bet=team.price,
        multiple=team.multiple,
        potential_payout=round(body.stake * team.multiple, 2),
        new_balance=balance - body.stake,
        created_at=datetime.now(timezone.utc),
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


async def create_user(display_name: str) -> User:
    # TODO(market): INSERT into users with balance = settings.starting_balance.
    return sample_data.USER.model_copy(
        update={"display_name": display_name, "balance": get_settings().starting_balance}
    )


async def get_user(user_id: str) -> User | None:
    # TODO(market): SELECT from users.
    return sample_data.USER


async def get_leaderboard() -> list[LeaderboardEntry]:
    # TODO(market): users ORDER BY balance DESC.
    return sample_data.leaderboard()
