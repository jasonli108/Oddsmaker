"""Scout: publishes a report on every team and sets the odds.

Runs once when a team signs up and then every 30 minutes. Each run ends by re-splitting
the seed so prices move. Step numbers below match the build spec's "Scout pipeline".

Rule for every step: a failed fetch must not zero a team. If a step fails, reuse that
team's last report and save it with stale = true.
"""

import logging

from app import sample_data
from app.market import service as market_service
from app.schemas import Team, TeamReport

log = logging.getLogger(__name__)


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
