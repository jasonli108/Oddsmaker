"""The 30-minute Scout timer. Started from app.main when SCOUT_ENABLED=true.

SCOUT_INTERVAL_MINUTES=0 turns the timer off, to save Gemini quota: Scout then runs only when a
team signs up and when someone presses Run Scout on a team's report.
"""

import asyncio
import logging

from app.config import get_settings
from app.scout import pipeline

log = logging.getLogger(__name__)


async def _run_forever() -> None:
    interval = get_settings().scout_interval_minutes * 60
    while True:
        try:
            await pipeline.refresh_all()
        except Exception:
            log.exception("Scout refresh failed; will retry at the next interval")
        await asyncio.sleep(interval)


def start() -> asyncio.Task | None:
    if get_settings().scout_interval_minutes <= 0:
        log.info("SCOUT_INTERVAL_MINUTES is 0, so no timed refresh: Scout runs at sign-up and from Run Scout")
        return None
    return asyncio.create_task(_run_forever(), name="scout-scheduler")
