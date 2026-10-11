"""Scout: publishes a report on every team and sets the odds.

Runs once when a team signs up and then every 30 minutes. Each run ends by re-splitting
the seed so prices move. Step numbers below match the build spec's "Scout pipeline".

Rule for every step: a failed fetch must not zero a team. If a step fails, reuse that
team's last report and save it with stale = true. A team with no report yet is priced on
NEUTRAL_SCORE, so it never sits at the price floor because Scout failed.

Caching needs no extra table (docs/scout.md): a team's similar projects are searched once and
kept in its report, and the "what wins here" brief lives in memory until the server restarts.
"""

import asyncio
import logging
from datetime import datetime

from psycopg.types.json import Jsonb

from app import db
from app.config import get_settings
from app.market import pricing
from app.market import service as market_service
from app.schemas import EventCategory, EventDraft, OddsPoint, ScoutReport, ScoutScores, Team, TeamReport
from app.scout import gemini, github, nimble

log = logging.getLogger(__name__)

# EventDraft fields the host has to fill in by hand when the page doesn't give them.
DRAFT_FIELDS = ("name", "hosted_by", "location", "starts_at", "submissions_close_at", "categories")
# The markets Scout scores: overall, nimble, gemini, tiger_data.
MARKET_IDS = list(ScoutScores.model_fields)
# A team without a report yet is priced as if Scout had scored it this in every category.
NEUTRAL_SCORE = 50
# Teams refreshed at once, to go easy on Gemini (which answers 503 when busy) and Nimble.
PARALLEL_TEAMS = 3
SIMILAR_LIMIT = 6
GALLERY_DOMAINS = ["devpost.com"]

_brief: str | None = None
_brief_lock = asyncio.Lock()


# ---- The host's event page ---------------------------------------------------


async def extract_event(url: str) -> EventDraft:
    """Read the host's event page into a draft for them to check (POST /api/events/extract).

    One Nimble extract and one Gemini call. Raises if the page is down or either call fails;
    app.events.service then shows the host an empty draft rather than sample data.
    """
    page = await nimble.extract(url, screenshot=False, render=False)
    if not page.is_up or not page.text.strip():
        raise nimble.NimbleError(f"event page did not load or had no text: {url}")
    log.info("Read event page %s: %d characters", url, len(page.text))
    return event_draft(url, await gemini.read_event_page(page))


def event_draft(url: str, event: gemini.GeminiEvent) -> EventDraft:
    # Imported here, not at the top, because app.events.service imports this module.
    from app.events.service import market_id_for

    draft = EventDraft(
        name=event.name.strip(),
        hosted_by=event.hosted_by.strip() or None,
        location=event.location.strip() or None,
        starts_at=_parse_time(event.starts_at),
        submissions_close_at=_parse_time(event.submissions_close_at),
        source_url=url,
        categories=[
            EventCategory(name=c.name.strip(), prize=c.prize.strip() or None, market_id=market_id_for(c.name))
            for c in event.categories
            if c.name.strip()
        ],
    )
    draft.missing = [field for field in DRAFT_FIELDS if not getattr(draft, field)]
    return draft


def _parse_time(value: str) -> datetime | None:
    """An ISO 8601 time with a UTC offset. A time without one counts as missing: saving it would assume UTC."""
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


# ---- Once per event ----------------------------------------------------------


async def prepare_event() -> str:
    """Steps 1 and 2: the "what wins here" brief, built once and kept in memory.

    1. nimble.extract on the event page the host saved (or EVENT_URL), for the prize criteria.
    2. nimble.search for winning projects in hackathon galleries, then gemini.condense_winners_brief.
    Returns "" if that fails, so reports are still written; the next run tries again.
    """
    global _brief
    async with _brief_lock:
        if _brief is None:
            _brief = await _build_brief()
        return _brief or ""


async def _build_brief() -> str | None:
    # Imported here, not at the top, because app.events.service imports this module.
    from app.events.service import get_event

    try:
        event = await get_event()
    except Exception:
        log.warning("Could not read the saved event; building the brief without it", exc_info=True)
        event = None
    url = (event.source_url if event else None) or get_settings().event_url
    page = None
    if url:
        try:
            page = await nimble.extract(url, screenshot=False, render=False)
        except Exception:
            log.warning("Could not read the event page %s for the brief", url, exc_info=True)
    query = f"winning projects at {event.name}" if event else "winning AI hackathon projects"
    try:
        winners = await nimble.search(query, limit=5, domains=GALLERY_DOMAINS)
        brief = await gemini.condense_winners_brief(winners, page if page and page.text.strip() else None)
    except Exception:
        log.warning("Could not build the what-wins-here brief; reports go ahead without it", exc_info=True)
        return None
    log.info("Built the what-wins-here brief from %d past projects", len(winners))
    return brief


# ---- Once per team -----------------------------------------------------------


async def prepare_team(team: Team) -> list[nimble.SearchResult]:
    """Step 3: projects with the same idea, in hackathon galleries first and then the wider web.

    Two Nimble searches. The results are kept in the team's report, so later runs reuse them
    from there (_similar_from) instead of searching again.
    """
    gallery, web = await asyncio.gather(
        nimble.search(team.idea, limit=SIMILAR_LIMIT, domains=GALLERY_DOMAINS),
        nimble.search(team.idea, limit=SIMILAR_LIMIT),
    )
    return similar_projects(team, gallery + web)


def similar_projects(team: Team, results: list[nimble.SearchResult]) -> list[nimble.SearchResult]:
    """Drop duplicates and the team's own pages, and keep the top SIMILAR_LIMIT."""
    own = {_url_key(u) for u in (team.repo_url, team.demo_url) if u}
    seen: set[str] = set()
    kept = []
    for r in results:
        key = _url_key(r.url)
        if key in seen or key in own or r.title.strip().lower() == team.name.strip().lower():
            continue
        seen.add(key)
        kept.append(r)
    return kept[:SIMILAR_LIMIT]


def _url_key(url: str) -> str:
    return url.strip().rstrip("/").lower().removeprefix("https://").removeprefix("http://").removeprefix("www.")


def _similar_from(report: ScoutReport) -> list[nimble.SearchResult]:
    return [nimble.SearchResult(title=s.title, url=s.url, description=s.description) for s in report.originality.similar]


# ---- Every 30 minutes per team -----------------------------------------------


async def refresh_team(team: Team, brief: str = "") -> None:
    """Steps 4 to 6 for one team: gather the evidence, write a report and save it.

    If a fetch or Gemini fails and the team has a report, that report is saved again with
    stale = true. Before its first report, a failed repo or demo check is reported to Gemini as
    our failure instead of blocking the report.
    """
    previous = await _latest_report(team.id)
    try:
        report = await _write_report(team, previous, brief)
    except Exception:
        log.exception("Scout could not refresh %s", team.id)
        if previous:
            await _save_report(previous, stale=True)
        return
    await _save_report(report, stale=False)
    log.info("New report for %s: %s", team.id, report.scores.model_dump())


async def _write_report(team: Team, previous: ScoutReport | None, brief: str) -> ScoutReport:
    similar = _similar_from(previous) if previous else await prepare_team(team)
    first = previous is None
    repo, demo = await asyncio.gather(_repo_stats(team, tolerate=first), _demo(team, tolerate=first))
    return await gemini.write_report(
        team=team, similar=similar, repo=repo, demo=demo, winners_brief=brief, previous=previous
    )


async def _repo_stats(team: Team, *, tolerate: bool) -> github.RepoStats | None:
    """Step 4. None for no link or a link that will never work; a failed fetch raises unless tolerated."""
    if not team.repo_url:
        return None
    try:
        return await github.repo_stats(team.repo_url)
    except github.RepoNotFound:
        log.info("%s's repo link isn't a public GitHub repo: %s", team.id, team.repo_url)
        return None
    except github.GitHubError:
        if not tolerate:
            raise
        log.warning("GitHub stats failed for %s; its first report goes ahead without them", team.id, exc_info=True)
        return None


async def _demo(team: Team, *, tolerate: bool) -> nimble.PageExtract | None:
    """Step 5. A demo that is down comes back with is_up = False; only a failed fetch raises."""
    if not team.demo_url:
        return None
    try:
        return await nimble.extract(team.demo_url)
    except nimble.NimbleError:
        if not tolerate:
            raise
        log.warning("Demo check failed for %s; its first report goes ahead without it", team.id, exc_info=True)
        return None


async def _latest_report(team_id: str) -> ScoutReport | None:
    async with db.get_pool().connection() as conn:
        row = await (
            await conn.execute(
                "SELECT body FROM reports WHERE team_id = %s ORDER BY created_at DESC, id DESC LIMIT 1", (team_id,)
            )
        ).fetchone()
    return ScoutReport(**row["body"]) if row else None


async def _save_report(report: ScoutReport, *, stale: bool) -> None:
    async with db.get_pool().connection() as conn:
        await conn.execute(
            "INSERT INTO reports (team_id, body, stale) VALUES (%s, %s, %s)",
            (report.team_id, Jsonb(report.model_dump(mode="json")), stale),
        )


# ---- Setting the odds --------------------------------------------------------


async def reprice_markets() -> None:
    """Steps 7 and 8, after the reports are saved.

    7. For each market, odds = pricing.odds_from_scores over every team's latest score for that
       category, with NEUTRAL_SCORE for a team that has no report yet.
    8. Hand the odds to market.service.apply_scout_odds, which re-splits the seed and writes the
       price ticks. Scout never writes to positions or price_ticks itself. The feed picks up any
       team whose price moved a point or more.
    """
    teams = await market_service.list_teams()
    async with db.get_pool().connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT DISTINCT ON (team_id) team_id, body->'scores' AS scores FROM reports "
                "ORDER BY team_id, created_at DESC, id DESC"
            )
        ).fetchall()
    latest = {r["team_id"]: r["scores"] for r in rows}
    for market_id in MARKET_IDS:
        scores = {t.id: latest.get(t.id, {}).get(market_id, NEUTRAL_SCORE) for t in teams}
        await market_service.apply_scout_odds(market_id, pricing.odds_from_scores(scores))


# ---- Entry points ------------------------------------------------------------


async def run_for_team(team: Team) -> None:
    """Called by POST /api/teams right after sign-up: steps 3 to 8 for one new team."""
    if not get_settings().scout_enabled:
        log.info("SCOUT_ENABLED is false, so no report for %s", team.id)
        return
    await refresh_team(team, await prepare_event())
    await reprice_markets()


async def refresh_all() -> None:
    """Called by the scheduler: steps 4 to 8 for every team that is due, a few at a time.

    A team with a report from the last SCOUT_INTERVAL_MINUTES is skipped, so restarting the
    server (or uvicorn --reload on every save) doesn't spend credits on teams Scout just covered.
    The scheduler waits a full interval after each run, so its own runs never skip anyone.
    """
    minutes = get_settings().scout_interval_minutes
    recent = await _recently_reported(minutes)
    due = [t for t in await market_service.list_teams() if t.id not in recent]
    if not due:
        log.info("Every team has a report from the last %d minutes; nothing to refresh", minutes)
        return
    brief = await prepare_event()
    limit = asyncio.Semaphore(PARALLEL_TEAMS)

    async def refresh(team: Team) -> None:
        async with limit:
            await refresh_team(team, brief)

    results = await asyncio.gather(*(refresh(t) for t in due), return_exceptions=True)
    for team, result in zip(due, results):
        if isinstance(result, Exception):
            log.error("Scout refresh crashed for %s", team.id, exc_info=result)
    await reprice_markets()


async def _recently_reported(minutes: int) -> set[str]:
    """Teams whose latest report, fresh or stale, is younger than `minutes`, by the database's clock."""
    async with db.get_pool().connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT team_id FROM reports GROUP BY team_id HAVING max(created_at) > now() - make_interval(mins => %s)",
                (minutes,),
            )
        ).fetchall()
    return {r["team_id"] for r in rows}


# ---- Reading reports ---------------------------------------------------------


async def get_team_report(team_id: str) -> TeamReport | None:
    """Latest report for a team plus the history of Scout's odds, for GET /api/teams/:id/report."""
    team = await market_service.get_team(team_id)
    if team is None:
        return None
    async with db.get_pool().connection() as conn:
        latest = await (
            await conn.execute(
                "SELECT body, created_at, stale FROM reports WHERE team_id = %s ORDER BY created_at DESC, id DESC LIMIT 1",
                (team_id,),
            )
        ).fetchone()
        if latest is None:
            # The frontend shows "writing its first report".
            return TeamReport(team=team, report=None, created_at=None, stale=False, odds_history=[])
        rows = await (
            await conn.execute(
                "SELECT team_id, created_at, stale, body->'scores' AS scores, body->>'change_note' AS note "
                "FROM reports ORDER BY created_at, id"
            )
        ).fetchall()
        joined = await (await conn.execute("SELECT id, created_at FROM teams")).fetchall()
    return TeamReport(
        team=team,
        report=ScoutReport(**latest["body"]),
        created_at=latest["created_at"],
        stale=latest["stale"],
        odds_history=odds_history(team_id, rows, {t["id"]: t["created_at"] for t in joined}),
    )


def odds_history(team_id: str, rows: list[dict], joined: dict[str, datetime]) -> list[OddsPoint]:
    """Scout's odds for one team after each of its fresh reports, oldest first.

    Recomputed from the reports by reprice_markets' rule: at each report's time, every team that
    had signed up is scored by its latest report so far, or NEUTRAL_SCORE. `rows` is every report,
    oldest first, with team_id, created_at, stale, scores and note; `joined` maps team id to when
    it signed up. Stale reports repeat an old one, so they add no point.
    """
    latest: dict[str, dict] = {}
    points = []
    for row in rows:
        latest[row["team_id"]] = row["scores"]
        if row["team_id"] != team_id or row["stale"]:
            continue
        teams = [tid for tid, at in joined.items() if at <= row["created_at"]] or [team_id]
        for market_id in MARKET_IDS:
            scores = {tid: latest.get(tid, {}).get(market_id, NEUTRAL_SCORE) for tid in teams}
            odds = pricing.odds_from_scores(scores).get(team_id, 0.0)
            points.append(OddsPoint(time=row["created_at"], market_id=market_id, odds=round(odds, 4), note=row["note"]))
    return points
