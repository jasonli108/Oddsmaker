"""The 30-minute Scout timer. Started from app.main when SCOUT_ENABLED=true."""

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


def start() -> asyncio.Task:
    return asyncio.create_task(_run_forever(), name="scout-scheduler")
