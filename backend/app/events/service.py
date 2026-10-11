"""The host flow: launching an event and the host page's numbers.

Launching an event saves its row and opens its markets, one per prize category the host ticked.
The markets are opened by market.service.open_market. This service may read any table but must
never write positions, price_ticks, bets or balances; winner picking goes through the existing
POST /api/markets/{id}/resolve.
"""

import logging
import re

from psycopg.types.json import Jsonb

from app import db
from app.config import get_settings
from app.events import sample
from app.market import service as market
from app.schemas import Event, EventCategory, EventCreate, EventDraft, HostMarketRow, HostSummary, MarketId
from app.scout import pipeline

log = logging.getLogger(__name__)

_EVENT_COLUMNS = (
    "slug, name, hosted_by, location, starts_at, submissions_close_at, source_url, categories, starting_balance"
)
_DRAFT_FIELDS = ["name", "hosted_by", "location", "starts_at", "submissions_close_at", "categories"]


class EventError(Exception):
    """An event that is understood but can't be launched as asked. The router turns it into a 400."""


def market_id_for(category_name: str) -> MarketId | None:
    """Which of Scout's four scores fits a prize category, if any. Scout uses this in extract_event."""
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


async def get_event(slug: str | None = None) -> Event | None:
    """The event with this slug. Without one, the first event this deployment ran."""
    async with db.get_pool().connection() as conn:
        if slug is None:
            cur = await conn.execute(f"SELECT {_EVENT_COLUMNS} FROM events ORDER BY id LIMIT 1")
        else:
            cur = await conn.execute(f"SELECT {_EVENT_COLUMNS} FROM events WHERE slug = %s", (slug,))
        row = await cur.fetchone()
    return _event(row) if row else None


def _wants_market(category: EventCategory) -> bool:
    return category.create_market if category.create_market is not None else category.market_id is not None


async def create_event(body: EventCreate) -> Event:
    """Launch a new event: save it and open a market for every category the host ticked.

    Each event is separate. Its slug, which names it in the attendee link, is made from the name
    and never changes; a second event of the same name gets a numbered slug. A category Scout has
    no score for (anything but overall, Nimble, Gemini and Tiger Data) is priced by the overall score.
    """
    categories = [
        c.model_copy(update={"market_id": c.market_id or market_id_for(c.name), "create_market": _wants_market(c)})
        for c in body.categories
    ]
    with_market = [c for c in categories if c.create_market]
    if not with_market:
        raise EventError("Add at least one prize category with a market, so attendees have something to bet on.")
    base = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-") or "event"
    async with db.get_pool().connection() as conn:
        async with conn.transaction():
            # One launch at a time, so two events of the same name can't pick the same slug.
            await conn.execute("LOCK TABLE events IN SHARE ROW EXCLUSIVE MODE")
            taken = {
                r["slug"]
                for r in await (await conn.execute("SELECT slug FROM events WHERE slug LIKE %s", (base + "%",))).fetchall()
            }
            slug, n = base, 2
            while slug in taken:
                slug, n = f"{base}-{n}", n + 1
            row = await (
                await conn.execute(
                    f"INSERT INTO events ({_EVENT_COLUMNS}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    f"RETURNING {_EVENT_COLUMNS}",
                    (
                        slug,
                        body.name,
                        body.hosted_by,
                        body.location,
                        body.starts_at,
                        body.submissions_close_at,
                        body.source_url,
                        Jsonb([c.model_dump() for c in categories]),
                        body.starting_balance,
                    ),
                )
            ).fetchone()
            for order, category in enumerate(with_market):
                await market.open_market(conn, slug, category.name, category.market_id or "overall", order)
    return _event(row)


async def host_summary(event_slug: str | None = None) -> HostSummary | None:
    """One event's numbers for its host page. Read-only. None if there is no such event."""
    async with db.get_pool().connection() as conn:
        if event_slug is not None:
            if not await (await conn.execute("SELECT 1 FROM events WHERE slug = %s", (event_slug,))).fetchone():
                return None
        in_event = "(%(e)s::text IS NULL OR event_slug = %(e)s)"
        counts = await (
            await conn.execute(
                f"SELECT (SELECT count(*) FROM users WHERE {in_event}) AS attendees, "
                f"(SELECT count(*) FROM teams WHERE {in_event}) AS teams, "
                "count(b.id) AS bets, coalesce(sum(b.stake), 0) AS traded "
                f"FROM (SELECT id FROM markets WHERE {in_event}) m LEFT JOIN bets b ON b.market_id = m.id",
                {"e": event_slug},
            )
        ).fetchone()

    rows = []
    for summary in await market.list_markets(event_slug):
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
        top_forecasters=await market.get_leaderboard(limit=5, event_slug=event_slug),
    )
