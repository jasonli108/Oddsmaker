"""The host flow: the single event row and the host page's numbers.

This service may read any table. It must never write positions, price_ticks, bets or balances;
winner picking goes through the existing POST /api/markets/{id}/resolve.
"""

import logging
import re

from psycopg.types.json import Jsonb

from app import db
from app.config import get_settings
from app.events import sample
from app.market import service as market
from app.schemas import Event, EventCreate, EventDraft, HostMarketRow, HostSummary, MarketId
from app.scout import pipeline

log = logging.getLogger(__name__)

_EVENT_COLUMNS = "slug, name, hosted_by, location, starts_at, submissions_close_at, source_url, categories"
_DRAFT_FIELDS = ["name", "hosted_by", "location", "starts_at", "submissions_close_at", "categories"]


def market_id_for(category_name: str) -> MarketId | None:
    """Which of the four markets a prize category maps to, if any. Scout can use this in extract_event."""
    name = category_name.lower()
    if "nimble" in name:
        return "nimble"
    if "gemini" in name:
        return "gemini"
    if "tiger" in name or "timescale" in name:
        return "tiger_data"
    if "overall" in name or "grand prize" in name or "best hack" in name:
        return "overall"
    return None


async def extract_event(url: str) -> EventDraft:
    """Read the host's event page into a draft for them to check.

    Uses Scout's extract_event(url) -> EventDraft from app.scout.pipeline once it exists and
    SCOUT_ENABLED is true. Until then it serves canned data marked is_sample. If Scout is on but
    the read fails, the draft comes back empty with every field listed as missing: never canned
    data dressed up as the host's page.
    """
    scout_extract = getattr(pipeline, "extract_event", None)
    if not get_settings().scout_enabled or scout_extract is None:
        return sample.event_draft(url)
    try:
        draft: EventDraft = await scout_extract(url)
    except Exception:
        log.exception("Scout could not read the event page %s", url)
        return EventDraft(name="", source_url=url, missing=list(_DRAFT_FIELDS))
    return draft.model_copy(update={"source_url": draft.source_url or url, "is_sample": False})


def _event(row: dict) -> Event:
    return Event(**row)


async def get_event() -> Event | None:
    async with db.get_pool().connection() as conn:
        row = await (await conn.execute(f"SELECT {_EVENT_COLUMNS} FROM events WHERE id = 1")).fetchone()
    return _event(row) if row else None


async def save_event(body: EventCreate) -> Event:
    """Create or replace the single event row. Never creates or deletes markets."""
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-") or "event"
    values = (
        slug,
        body.name,
        body.hosted_by,
        body.location,
        body.starts_at,
        body.submissions_close_at,
        body.source_url,
        Jsonb([c.model_dump() for c in body.categories]),
    )
    async with db.get_pool().connection() as conn:
        row = await (
            await conn.execute(
                f"INSERT INTO events (id, {_EVENT_COLUMNS}) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (id) DO UPDATE SET slug = EXCLUDED.slug, name = EXCLUDED.name, "
                "hosted_by = EXCLUDED.hosted_by, location = EXCLUDED.location, starts_at = EXCLUDED.starts_at, "
                "submissions_close_at = EXCLUDED.submissions_close_at, source_url = EXCLUDED.source_url, "
                f"categories = EXCLUDED.categories RETURNING {_EVENT_COLUMNS}",
                values,
            )
        ).fetchone()
    return _event(row)


async def host_summary() -> HostSummary:
    """The host page's numbers. Read-only."""
    async with db.get_pool().connection() as conn:
        counts = await (
            await conn.execute(
                "SELECT (SELECT count(*) FROM users) AS attendees, (SELECT count(*) FROM teams) AS teams, "
                "(SELECT count(*) FROM bets) AS bets, (SELECT coalesce(sum(stake), 0) FROM bets) AS traded"
            )
        ).fetchone()

    rows = []
    for summary in await market.list_markets():
        detail = await market.get_market(summary.id)
        leader = detail.teams[0] if detail and detail.teams else None  # teams come sorted by price
        rows.append(
            HostMarketRow(
                id=summary.id,
                category=summary.category,
                status=summary.status,
                leader_team_id=leader.team_id if leader else None,
                leader_team_name=leader.name if leader else None,
                leader_price=leader.price if leader else None,
                staked=sum(t.staked for t in detail.teams) if detail else 0,
                winner_team_id=summary.winner_team_id,
            )
        )
    return HostSummary(
        attendees=counts["attendees"],
        teams=counts["teams"],
        bets=counts["bets"],
        hackcoin_traded=float(counts["traded"]),
        markets=rows,
        top_forecasters=await market.get_leaderboard(limit=5),
    )
