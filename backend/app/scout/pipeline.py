"""Scout: publishes a report on every team and sets the odds.

Runs once when a team signs up and then every 30 minutes. Each run ends by re-splitting
the seed so prices move. Step numbers below match the build spec's "Scout pipeline".

Rule for every step: a failed fetch must not zero a team. If a step fails, reuse that
team's last report and save it with stale = true.
"""

import logging
from datetime import datetime

from app import sample_data
from app.market import service as market_service
from app.schemas import EventCategory, EventDraft, Team, TeamReport
from app.scout import gemini, nimble

log = logging.getLogger(__name__)

# EventDraft fields the host has to fill in by hand when the page doesn't give them.
DRAFT_FIELDS = ("name", "hosted_by", "location", "starts_at", "submissions_close_at", "categories")


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


async def prepare_event() -> None:
    """Once per event, cached.

    1. nimble.extract on settings.event_url for each prize category and its criteria.
    2. nimble.search for past winners of similar hackathons, then gemini.condense_winners_brief.
    """
    # TODO(scout): the spec's seven tables have nowhere to cache this brief or step 3's results.
    # Simplest options: a JSON file on disk, or one extra key/value table. Your call.
    raise NotImplementedError("TODO(scout)")


async def prepare_team(team: Team) -> None:
    """Once per team at sign-up, cached.

    3. nimble.search on the team's one-line idea across the web and hackathon galleries.
       Keep the top matches with title, link and a one-line description.
    """
    raise NotImplementedError("TODO(scout)")


async def refresh_team(team: Team) -> None:
    """Every 30 minutes per team.

    4. github.repo_stats on the repo link.
    5. nimble.extract on the demo link, with a screenshot if one comes back.
    6. gemini.write_report with all of the above, then clamp scores and INSERT into reports.
    """
    raise NotImplementedError("TODO(scout)")


async def reprice_markets() -> None:
    """After every team has a fresh report.

    7. For each market, odds = pricing.odds_from_scores over that category's scores.
    8. Hand the odds to market.service.apply_scout_odds, which re-splits the seed and writes the
       price ticks. Scout never writes to positions or price_ticks itself. The feed picks up any
       team whose price moved a point or more.
    """
    raise NotImplementedError("TODO(scout)")


async def run_for_team(team: Team) -> None:
    """Called by POST /api/teams right after sign-up: steps 3 to 8 for one new team."""
    # TODO(scout): prepare_team, refresh_team, reprice_markets.
    log.info("Scout is not implemented yet; skipping first run for %s", team.id)


async def refresh_all() -> None:
    """Called by the scheduler: steps 4 to 8 for every team."""
    # TODO(scout): refresh_team for each team (asyncio.gather, tolerate failures), then reprice_markets.
    log.info("Scout is not implemented yet; skipping refresh")


async def get_team_report(team_id: str) -> TeamReport | None:
    """Latest report for a team plus the history of Scout's odds, for GET /api/teams/:id/report."""
    # TODO(scout): latest row from reports; odds history from scout-sourced price_ticks or past reports.
    team = await market_service.get_team(team_id)
    if team is None:
        return None
    if team_id not in sample_data.TEAMS_BY_ID:
        # A real team Scout has not reported on yet. The frontend shows "writing its first report".
        return TeamReport(team=team, report=None, created_at=None, stale=False, odds_history=[])
    return sample_data.team_report(team_id)
