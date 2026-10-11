"""The API contract.

This file is the single source of truth for request and response shapes. The frontend's
types are generated from it: after any change here, run `make types` and commit the result.

Conventions
- Prices and odds are fractions between 0 and 1 (0.27 = 27%). The UI formats them.
- A payout multiple is 1 / price at the moment of the bet.
- Stakes are whole Hackcoin. Balances can carry cents after a payout.
- Market ids are 'overall', 'nimble', 'gemini', 'tiger_data': the same keys as Scout's scores.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

MarketStatus = Literal["open", "resolved"]

# ---- Teams -----------------------------------------------------------------


class Team(BaseModel):
    id: str
    name: str
    idea: str
    repo_url: str | None = None
    demo_url: str | None = None
    color: str


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    idea: str = Field(min_length=1, max_length=200)
    repo_url: str | None = None
    demo_url: str | None = None


# ---- Users -----------------------------------------------------------------


class User(BaseModel):
    id: str
    display_name: str
    balance: float


class UserCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    display_name: str
    balance: float


# ---- Markets ---------------------------------------------------------------


class MarketSummary(BaseModel):
    id: str
    title: str
    category: str
    status: MarketStatus
    winner_team_id: str | None = None


class MarketTeam(BaseModel):
    team_id: str
    name: str
    idea: str
    color: str
    price: float
    multiple: float
    scout_odds: float
    staked: float


class MarketTotals(BaseModel):
    team_count: int
    hackcoin_traded: float
    forecaster_count: int


class MarketDetail(MarketSummary):
    totals: MarketTotals
    teams: list[MarketTeam]  # sorted by price, highest first


class PricePoint(BaseModel):
    time: datetime
    price: float


class TeamSeries(BaseModel):
    team_id: str
    name: str
    color: str
    points: list[PricePoint]  # oldest first, one per minute


class MarketHistory(BaseModel):
    market_id: str
    series: list[TeamSeries]


class BetFeedItem(BaseModel):
    kind: Literal["bet"] = "bet"
    id: str
    time: datetime
    user_display_name: str
    team_id: str
    team_name: str
    team_color: str
    stake: float
    price: float


class ScoutFeedItem(BaseModel):
    kind: Literal["scout"] = "scout"
    id: str
    time: datetime
    team_id: str
    team_name: str
    team_color: str
    price_from: float
    price_to: float
    note: str


FeedItem = Annotated[BetFeedItem | ScoutFeedItem, Field(discriminator="kind")]


class ResolveRequest(BaseModel):
    winner_team_id: str


class ResolveResult(BaseModel):
    market: MarketSummary
    bets_paid: int
    total_paid: float


# ---- Bets ------------------------------------------------------------------


class BetCreate(BaseModel):
    user_id: str
    market_id: str
    team_id: str
    stake: int = Field(gt=0)


class BetReceipt(BaseModel):
    bet_id: str
    market_id: str
    team_id: str
    stake: float
    price_at_bet: float
    multiple: float
    potential_payout: float
    new_balance: float
    created_at: datetime


# ---- Scout reports ---------------------------------------------------------
# ScoutReport is exactly the JSON Gemini returns (build spec, "Scout pipeline").


class SimilarProject(BaseModel):
    title: str
    url: str


class ReportSection(BaseModel):
    label: str
    finding: str


class OriginalitySection(ReportSection):
    similar: list[SimilarProject] = []


class ScoutScores(BaseModel):
    overall: int = Field(ge=1, le=100)
    nimble: int = Field(ge=1, le=100)
    gemini: int = Field(ge=1, le=100)
    tiger_data: int = Field(ge=1, le=100)


class ReportSource(BaseModel):
    url: str
    kind: str


class ScoutReport(BaseModel):
    team_id: str
    read: str
    originality: OriginalitySection
    build: ReportSection
    demo: ReportSection
    prize_fit: ReportSection
    scores: ScoutScores
    change_note: str
    sources: list[ReportSource] = []


class OddsPoint(BaseModel):
    time: datetime
    market_id: str
    odds: float
    note: str | None = None  # that run's change_note, shown beside the odds on the Scout reports tab


class TeamReport(BaseModel):
    team: Team
    report: ScoutReport | None  # null until Scout's first run finishes
    created_at: datetime | None
    stale: bool
    odds_history: list[OddsPoint]  # oldest first


# ---- Misc ------------------------------------------------------------------


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    db: Literal["connected", "not_connected", "error"]


# ---- Host flow: the event and the host page --------------------------------

MarketId = Literal["overall", "nimble", "gemini", "tiger_data"]


class EventCategory(BaseModel):
    name: str
    prize: str | None = None
    market_id: MarketId | None = None  # set when the category maps to one of the four markets


class EventExtractRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)


class EventDraft(BaseModel):
    """What Scout read from the host's event page, for the host to check before launch."""

    name: str  # empty when it could not be found; "name" is then listed in `missing`
    hosted_by: str | None = None
    location: str | None = None
    starts_at: datetime | None = None
    submissions_close_at: datetime | None = None
    source_url: str | None = None
    categories: list[EventCategory] = []
    missing: list[str] = []  # names of the fields above that were not on the page
    is_sample: bool = False  # true when Scout is off and this is canned data, not read from the URL


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    hosted_by: str | None = None
    location: str | None = None
    starts_at: datetime | None = None
    submissions_close_at: datetime | None = None
    source_url: str | None = None
    categories: list[EventCategory] = []
    # Hackcoin each attendee starts with. Chosen at the first launch and fixed from then on.
    starting_balance: int = Field(default=1000, ge=1, le=1_000_000)


class Event(EventCreate):
    slug: str


class HostMarketRow(BaseModel):
    id: str
    category: str
    status: MarketStatus
    leader_team_id: str | None  # null while no team has signed up
    leader_team_name: str | None
    leader_price: float | None
    staked: float
    winner_team_id: str | None = None


class HostSummary(BaseModel):
    attendees: int
    teams: int
    bets: int
    hackcoin_traded: float
    markets: list[HostMarketRow]
    top_forecasters: list[LeaderboardEntry]
