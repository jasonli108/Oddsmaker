"""Scout pipeline rules that need no API calls or database."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.schemas import ReportSection, Team
from app.scout import gemini, github, nimble, pipeline

URL = "https://luma.com/AIEngineerNYHackathon"


def event(**fields) -> gemini.GeminiEvent:
    return gemini.GeminiEvent(**{
        "name": "AI Engineer NYC Hackathon", "hosted_by": "AI Engineer and MLH", "location": "New York, NY",
        "starts_at": "2026-10-11T09:00:00-04:00", "submissions_close_at": "2026-10-11T23:59:00-04:00",
        "categories": [], **fields,
    })


def test_event_draft_keeps_times_with_an_offset():
    draft = pipeline.event_draft(URL, event())
    assert draft.submissions_close_at == datetime(2026, 10, 11, 23, 59, tzinfo=timezone(timedelta(hours=-4)))
    assert draft.source_url == URL and draft.is_sample is False


def test_times_without_an_offset_or_unreadable_count_as_missing():
    draft = pipeline.event_draft(URL, event(starts_at="2026-10-11T09:00:00", submissions_close_at="Sunday night"))
    assert draft.starts_at is None and draft.submissions_close_at is None
    assert {"starts_at", "submissions_close_at"} <= set(draft.missing)


def test_categories_map_to_markets_and_empty_prizes_become_none():
    draft = pipeline.event_draft(URL, event(categories=[
        gemini.GeminiEventCategory(name="Best Use of Gemini API", prize="MLH swag kits"),
        gemini.GeminiEventCategory(name="Best use of Snowflake", prize=""),
        gemini.GeminiEventCategory(name="  ", prize="dropped"),
    ]))
    assert [(c.name, c.prize, c.market_id) for c in draft.categories] == [
        ("Best Use of Gemini API", "MLH swag kits", "gemini"),
        ("Best use of Snowflake", None, None),
    ]


def test_missing_lists_every_empty_field():
    draft = pipeline.event_draft(URL, event(name="", hosted_by=" ", location="", starts_at="", submissions_close_at=""))
    assert draft.missing == list(pipeline.DRAFT_FIELDS)


# ---- Similar projects ----------------------------------------------------------------

TEAM = Team(id="orbit", name="Orbit", idea="Live odds for hackathon prizes", repo_url="https://github.com/a/orbit",
            demo_url="https://orbit.vercel.app", color="#7DB8FF")


def result(title, url):
    return nimble.SearchResult(title=title, url=url, description="")


def test_similar_projects_drop_duplicates_and_the_teams_own_pages():
    kept = pipeline.similar_projects(TEAM, [
        result("Bet-3", "https://devpost.com/software/bet-3"),
        result("Bet-3 again", "https://www.devpost.com/software/bet-3/"),
        result("Orbit", "https://devpost.com/software/orbit"),  # the team's own gallery page
        result("Orbit demo", "https://orbit.vercel.app/"),
        result("HackBet", "https://devpost.com/software/hackbet"),
    ])
    assert [r.title for r in kept] == ["Bet-3", "HackBet"]


# ---- Odds history ----------------------------------------------------------------------

T0 = datetime(2026, 10, 11, 13, 0, tzinfo=timezone.utc)


def at(minutes):
    return T0 + timedelta(minutes=minutes)


def scores(overall):
    return {"overall": overall, "nimble": 50, "gemini": 50, "tiger_data": 50}


def test_odds_history_follows_the_repricing_rule():
    joined = {"orbit": at(0), "ledger": at(0), "late": at(45)}
    rows = [
        {"team_id": "orbit", "created_at": at(1), "stale": False, "scores": scores(75), "note": "First report."},
        {"team_id": "ledger", "created_at": at(2), "stale": False, "scores": scores(25), "note": None},
        {"team_id": "orbit", "created_at": at(31), "stale": False, "scores": scores(75), "note": "Demo went live."},
        {"team_id": "orbit", "created_at": at(61), "stale": True, "scores": scores(75), "note": "Demo went live."},
        {"team_id": "orbit", "created_at": at(62), "stale": False, "scores": scores(75), "note": "Steady."},
    ]
    overall = [p for p in pipeline.odds_history("orbit", rows, joined) if p.market_id == "overall"]
    # At 13:01 ledger has no report yet (neutral 50): 75 / 125. At 13:31: 75 / 100. The stale
    # copy adds no point. At 14:02 the late team counts at neutral 50: 75 / 150.
    assert [(p.odds, p.note) for p in overall] == [(0.6, "First report."), (0.75, "Demo went live."), (0.5, "Steady.")]


# ---- What happens when a fetch fails ---------------------------------------------------

PREVIOUS = gemini.build_report(TEAM, gemini.GeminiReply(
    read="Worth a look.", originality=ReportSection(label="Fresh", finding="x"),
    build=ReportSection(label="On pace", finding="x"), demo=ReportSection(label="Live", finding="x"),
    prize_fit=ReportSection(label="Fair", finding="x"),
    scores=gemini.GeminiScores(overall=60, nimble=40, gemini=40, tiger_data=40), change_note="First report.",
), [result("Bet-3", "https://devpost.com/software/bet-3")])


@pytest.fixture
def scout(monkeypatch):
    """Fakes for every outside call. Set .previous, or .fail to the names of calls that should fail."""
    state = SimpleNamespace(previous=None, fail=set(), saved=[], searches=0, report_inputs=None)

    async def latest_report(team_id):
        return state.previous

    async def save_report(report, *, stale):
        state.saved.append((report, stale))

    async def search(query, limit=5, *, domains=None):
        state.searches += 1
        if "search" in state.fail:
            raise nimble.NimbleError("search failed")
        return [result("HackBet", "https://devpost.com/software/hackbet")]

    async def extract(url, *, screenshot=True, render=True):
        if "demo" in state.fail:
            raise nimble.NimbleError("Nimble 500")
        return nimble.PageExtract(url=url, is_up=True, load_ms=900, text="Orbit")

    async def repo_stats(url):
        if "repo_404" in state.fail:
            raise github.RepoNotFound("private")
        if "repo" in state.fail:
            raise github.GitHubError("rate limited")
        return github.RepoStats(12, 3, 2, 5)

    async def write_report(**inputs):
        if "gemini" in state.fail:
            raise gemini.GeminiError("503 on every model")
        state.report_inputs = inputs
        return PREVIOUS.model_copy(update={"change_note": "New report."})

    monkeypatch.setattr(pipeline, "_latest_report", latest_report)
    monkeypatch.setattr(pipeline, "_save_report", save_report)
    monkeypatch.setattr(nimble, "search", search)
    monkeypatch.setattr(nimble, "extract", extract)
    monkeypatch.setattr(github, "repo_stats", repo_stats)
    monkeypatch.setattr(gemini, "write_report", write_report)
    return state


def refresh(state):
    asyncio.run(pipeline.refresh_team(TEAM, "brief"))
    return [(report.change_note, stale) for report, stale in state.saved]


def test_a_later_run_reuses_the_saved_search(scout):
    scout.previous = PREVIOUS
    assert refresh(scout) == [("New report.", False)]
    assert scout.searches == 0
    assert [r.url for r in scout.report_inputs["similar"]] == ["https://devpost.com/software/bet-3"]


@pytest.mark.parametrize("failing", ["gemini", "demo", "repo"])
def test_a_failed_fetch_saves_the_last_report_as_stale(scout, failing):
    scout.previous, scout.fail = PREVIOUS, {failing}
    assert refresh(scout) == [("First report.", True)]


def test_a_private_repo_is_no_repo_not_a_failure(scout):
    scout.previous, scout.fail = PREVIOUS, {"repo_404"}
    assert refresh(scout) == [("New report.", False)]
    assert scout.report_inputs["repo"] is None


def test_a_first_report_goes_ahead_when_the_demo_check_fails(scout):
    scout.fail = {"demo"}
    assert refresh(scout) == [("New report.", False)]
    assert scout.report_inputs["demo"] is None and scout.searches == 2


@pytest.mark.parametrize("failing", ["search", "gemini"])
def test_a_first_run_without_search_or_gemini_saves_nothing(scout, failing):
    scout.fail = {failing}
    assert refresh(scout) == []


def test_nothing_runs_while_scout_is_off(scout):
    asyncio.run(pipeline.run_for_team(TEAM))  # SCOUT_ENABLED is false in tests
    assert scout.saved == [] and scout.searches == 0


# ---- The 30-minute refresh -------------------------------------------------------------


@pytest.fixture
def refresh_all(monkeypatch):
    """Run pipeline.refresh_all with two teams, where `recent` lists the ones reported on lately."""
    state = SimpleNamespace(recent=set(), refreshed=[], briefs=0, repriced=0)
    teams = [TEAM, TEAM.model_copy(update={"id": "ledger", "name": "Ledgerline"})]

    async def list_teams():
        return teams

    async def recently_reported(minutes):
        return state.recent

    async def prepare_event(event_slug=None):
        state.briefs += 1
        return "brief"

    async def refresh_team(team, brief):
        state.refreshed.append(team.id)

    async def reprice_markets(event_slug=None):
        state.repriced += 1

    monkeypatch.setattr(pipeline.market_service, "list_teams", list_teams)
    monkeypatch.setattr(pipeline, "_recently_reported", recently_reported)
    monkeypatch.setattr(pipeline, "prepare_event", prepare_event)
    monkeypatch.setattr(pipeline, "refresh_team", refresh_team)
    monkeypatch.setattr(pipeline, "reprice_markets", reprice_markets)

    def run(recent):
        state.recent = recent
        asyncio.run(pipeline.refresh_all())
        return state

    return run


def test_refresh_all_skips_teams_reported_on_lately(refresh_all):
    state = refresh_all({"orbit"})
    assert state.refreshed == ["ledger"] and state.repriced == 1


def test_a_restart_right_after_a_refresh_spends_nothing(refresh_all):
    state = refresh_all({"orbit", "ledger"})
    assert state.refreshed == [] and state.briefs == 0 and state.repriced == 0


# ---- The host's Run Scout button ---------------------------------------------------------


@pytest.fixture
def run_scout(monkeypatch):
    """Run pipeline.scout_team with Scout on, and a refresh that fails with `state.problem`."""
    state = SimpleNamespace(problem=None, repriced=0, events=[])

    async def get_team(team_id):
        return TEAM.model_copy(update={"event_slug": "ai-engineer-nyc"}) if team_id == "orbit" else None

    async def prepare_event(event_slug=None):
        state.events.append(("brief", event_slug))
        return "brief"

    async def refresh_team(team, brief):
        return state.problem

    async def reprice_markets(event_slug=None):
        state.repriced += 1
        state.events.append(("reprice", event_slug))

    async def get_team_report(team_id):
        return "the new report"

    monkeypatch.setattr(pipeline, "get_settings", lambda: SimpleNamespace(scout_enabled=True))
    monkeypatch.setattr(pipeline, "_last_run", {})
    monkeypatch.setattr(pipeline.market_service, "get_team", get_team)
    monkeypatch.setattr(pipeline, "prepare_event", prepare_event)
    monkeypatch.setattr(pipeline, "refresh_team", refresh_team)
    monkeypatch.setattr(pipeline, "reprice_markets", reprice_markets)
    monkeypatch.setattr(pipeline, "get_team_report", get_team_report)
    return state


def test_run_scout_writes_one_report_and_reprices(run_scout):
    assert asyncio.run(pipeline.scout_team("orbit")) == "the new report"
    # The team's own event: its brief, and only its markets are repriced.
    assert run_scout.events == [("brief", "ai-engineer-nyc"), ("reprice", "ai-engineer-nyc")]


def test_run_scout_on_an_unknown_team_is_none(run_scout):
    assert asyncio.run(pipeline.scout_team("nobody")) is None


def test_run_scout_tells_the_host_why_it_failed(run_scout):
    run_scout.problem = "Gemini's daily quota is used up."
    with pytest.raises(pipeline.ScoutError, match="quota is used up"):
        asyncio.run(pipeline.scout_team("orbit"))
    assert run_scout.repriced == 0


def test_run_scout_waits_out_the_cooldown_for_each_team(run_scout):
    asyncio.run(pipeline.scout_team("orbit"))
    with pytest.raises(pipeline.ScoutBusy, match="Try again in 10 minutes"):
        asyncio.run(pipeline.scout_team("orbit"))
    assert run_scout.repriced == 1
    # A failed run counts too, or repeated clicks on a failing team would spend credits each time.
    pipeline._last_run["orbit"] -= pipeline.RUN_SCOUT_COOLDOWN_MINUTES * 60
    run_scout.problem = "Gemini is overloaded right now."
    with pytest.raises(pipeline.ScoutError):
        asyncio.run(pipeline.scout_team("orbit"))
    with pytest.raises(pipeline.ScoutBusy):
        asyncio.run(pipeline.scout_team("orbit"))


def test_run_scout_is_refused_while_scout_is_off():
    with pytest.raises(pipeline.ScoutError, match="switched off"):  # SCOUT_ENABLED is false in tests
        asyncio.run(pipeline.scout_team("orbit"))


def test_a_used_up_gemini_quota_reads_plainly(scout):
    scout.previous, scout.fail = PREVIOUS, {"gemini"}
    error = gemini.GeminiError("gemini-3.5-flash: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, ...}}")
    assert "daily quota is used up" in pipeline._reason(error)
    assert pipeline._reason(nimble.NimbleError("/search: HTTP 500")) == "/search: HTTP 500"
