"""Sample data behind the mock endpoints, taken from the Markets tab design.

Everything here is fake. As each service function gets a real implementation it stops
importing from this module; delete the module once nothing imports it.
"""

from datetime import datetime, timedelta, timezone

from app.schemas import (
    BetFeedItem,
    LeaderboardEntry,
    MarketDetail,
    MarketHistory,
    MarketSummary,
    MarketTeam,
    MarketTotals,
    OddsPoint,
    OriginalitySection,
    PricePoint,
    ReportSection,
    ReportSource,
    ScoutFeedItem,
    ScoutReport,
    ScoutScores,
    SimilarProject,
    Team,
    TeamReport,
    TeamSeries,
    User,
)

TEAM_COLORS = ["#7DB8FF", "#FFB454", "#D2B8FF", "#4FC9B0", "#F29BB7", "#C9D1D8"]

TEAMS = [
    Team(id="orbit", name="Team Orbit", idea="Invoice checker that verifies vendors before you pay", color=TEAM_COLORS[0],
         repo_url="https://github.com/example/orbit", demo_url="https://orbit.example.com"),
    Team(id="ledger", name="Ledgerline", idea="Synthetic financials for private startups", color=TEAM_COLORS[1],
         repo_url="https://github.com/example/ledgerline", demo_url="https://ledgerline.example.com"),
    Team(id="parsel", name="Parsel", idea="Price-drop refund claims from a receipt photo", color=TEAM_COLORS[2],
         repo_url="https://github.com/example/parsel", demo_url="https://parsel.example.com"),
    Team(id="night", name="Night Shift", idea="Agent that triages on-call alerts overnight", color=TEAM_COLORS[3],
         repo_url="https://github.com/example/night-shift"),
    Team(id="kiln", name="Kiln", idea="Personal inflation index from your own basket", color=TEAM_COLORS[4],
         repo_url="https://github.com/example/kiln", demo_url="https://kiln.example.com"),
    Team(id="tally", name="Tally", idea="Track records for financial pundits", color=TEAM_COLORS[5],
         repo_url="https://github.com/example/tally"),
]
TEAMS_BY_ID = {t.id: t for t in TEAMS}

MARKETS = [
    MarketSummary(id="overall", title="Who takes 1st place overall?", category="Best overall", status="open"),
    MarketSummary(id="nimble", title="Who wins Best use of Nimble?", category="Best use of Nimble", status="open"),
    MarketSummary(id="gemini", title="Who wins Best use of Gemini?", category="Best use of Gemini", status="open"),
    MarketSummary(id="tiger_data", title="Who wins Best use of Tiger Data?", category="Best use of Tiger Data", status="open"),
]
MARKETS_BY_ID = {m.id: m for m in MARKETS}

# Percent per team, in TEAMS order. Each row sums to 100.
_PRICES = {
    "overall": [31, 24, 18, 12, 9, 6],
    "nimble": [28, 30, 8, 6, 6, 22],
    "gemini": [24, 10, 34, 14, 10, 8],
    "tiger_data": [12, 16, 10, 8, 44, 10],
}
_SCOUT_ODDS = {
    "overall": [27, 29, 16, 13, 10, 5],
    "nimble": [30, 28, 9, 7, 6, 20],
    "gemini": [22, 12, 36, 12, 10, 8],
    "tiger_data": [10, 18, 10, 8, 46, 8],
}
_STAKED = [1420, 1180, 890, 610, 450, 300]

USER = User(id="00000000-0000-4000-8000-000000000001", display_name="You", balance=1000)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def market_detail(market_id: str) -> MarketDetail:
    summary = MARKETS_BY_ID[market_id]
    teams = [
        MarketTeam(
            team_id=t.id,
            name=t.name,
            idea=t.idea,
            color=t.color,
            price=_PRICES[market_id][i] / 100,
            multiple=round(100 / _PRICES[market_id][i], 2),
            scout_odds=_SCOUT_ODDS[market_id][i] / 100,
            staked=_STAKED[i],
        )
        for i, t in enumerate(TEAMS)
    ]
    teams.sort(key=lambda t: t.price, reverse=True)
    return MarketDetail(
        **summary.model_dump(),
        totals=MarketTotals(team_count=len(TEAMS), hackcoin_traded=sum(_STAKED), forecaster_count=37),
        teams=teams,
    )


def market_history(market_id: str) -> MarketHistory:
    """Three hours of per-minute points drifting from an even split to today's price."""
    now = _now().replace(second=0, microsecond=0)
    minutes = 180
    even = 1 / len(TEAMS)
    series = []
    for i, t in enumerate(TEAMS):
        end = _PRICES[market_id][i] / 100
        points = [
            PricePoint(time=now - timedelta(minutes=minutes - m), price=round(even + (end - even) * m / minutes, 4))
            for m in range(0, minutes + 1, 10)
        ]
        series.append(TeamSeries(team_id=t.id, name=t.name, color=t.color, points=points))
    return MarketHistory(market_id=market_id, series=series)


def market_feed(market_id: str) -> list[BetFeedItem | ScoutFeedItem]:
    now = _now()

    def bet(n: int, who: str, team_id: str, stake: int, price: float, seconds_ago: int) -> BetFeedItem:
        t = TEAMS_BY_ID[team_id]
        return BetFeedItem(id=f"bet-{n}", time=now - timedelta(seconds=seconds_ago), user_display_name=who,
                           team_id=t.id, team_name=t.name, team_color=t.color, stake=stake, price=price)

    ledger = TEAMS_BY_ID["ledger"]
    return [
        bet(1, "Maya", "orbit", 50, 0.31, 12),
        ScoutFeedItem(id="scout-1", time=now - timedelta(minutes=2), team_id=ledger.id, team_name=ledger.name,
                      team_color=ledger.color, price_from=0.22, price_to=0.24, note="after its latest report"),
        bet(2, "Dev", "kiln", 200, 0.09, 4 * 60),
        bet(3, "Priya", "parsel", 75, 0.17, 7 * 60),
        bet(4, "Jonah", "ledger", 120, 0.22, 9 * 60),
        bet(5, "Aiko", "night", 40, 0.13, 11 * 60),
    ]


def leaderboard() -> list[LeaderboardEntry]:
    rows = [("Maya", 1840.5), ("Dev", 1420), ("Priya", 1110), (USER.display_name, USER.balance), ("Jonah", 880), ("Aiko", 640)]
    return [
        LeaderboardEntry(rank=i + 1, user_id=f"00000000-0000-4000-8000-{i + 1:012d}", display_name=name, balance=balance)
        for i, (name, balance) in enumerate(rows)
    ]


def team_report(team_id: str) -> TeamReport:
    team = TEAMS_BY_ID[team_id]
    i = TEAMS.index(team)
    now = _now()
    report = ScoutReport(
        team_id=team.id,
        read=f"{team.name} has a working demo and steady commits, but the idea sits in a crowded space. "
             "Worth a look at the current price if the demo holds up.",
        originality=OriginalitySection(
            label="Crowded",
            finding="2 similar projects found in past hackathon galleries.",
            similar=[
                SimilarProject(title="A similar project from a past hackathon", url="https://example.com/similar-1"),
                SimilarProject(title="Another close match", url="https://example.com/similar-2"),
            ],
        ),
        build=ReportSection(label="On pace", finding="14 commits, 3 in the last 30 minutes."),
        demo=ReportSection(label="Live" if team.demo_url else "Missing",
                           finding="Loads in 1.2 s." if team.demo_url else "No demo link submitted yet."),
        prize_fit=ReportSection(label="Strong", finding="Strong for Nimble and Gemini."),
        scores=ScoutScores(overall=62, nimble=71, gemini=55, tiger_data=30),
        change_note="Demo went live since last report.",
        sources=[ReportSource(url=u, kind=k) for u, k in ((team.repo_url, "repo"), (team.demo_url, "demo")) if u],
    )
    notes = ["Opening odds, idea only", "First commits to the main flow", "Second similar project found",
             report.change_note]
    odds_history = [
        OddsPoint(time=now - timedelta(minutes=30 * (3 - step)), market_id=market_id,
                  odds=round((odds[i] - (3 - step)) / 100, 4), note=notes[step])
        for market_id, odds in _SCOUT_ODDS.items()
        for step in range(4)
    ]
    return TeamReport(team=team, report=report, created_at=now - timedelta(minutes=4), stale=False,
                      odds_history=odds_history)
