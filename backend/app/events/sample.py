"""The canned event draft served while Scout cannot read event pages.

Everything here is made up, taken from the "Confirm details" design. It is returned with
is_sample = true so the review screen can say so instead of presenting it as read from the URL.
"""

from datetime import datetime, timedelta, timezone

from app.schemas import EventCategory, EventDraft

EDT = timezone(timedelta(hours=-4))


def event_draft(source_url: str) -> EventDraft:
    return EventDraft(
        name="AI Engineer NYC 2026",
        hosted_by="AI Engineer and Major League Hacking",
        location="New York, NY",
        starts_at=None,
        submissions_close_at=datetime(2026, 10, 11, 23, 59, tzinfo=EDT),
        source_url=source_url,
        categories=[
            EventCategory(name="Best overall", prize="1st $1,024 · 2nd $512 · 3rd $256", market_id="overall"),
            EventCategory(name="Best use of Gemini API", prize="MLH swag kits", market_id="gemini"),
            EventCategory(name="Best use of Tiger Data", prize="Stream Deck Mini", market_id="tiger_data"),
            EventCategory(name="Best use of Snowflake", prize="Arduino Student Kit"),
            EventCategory(name="Best use of Nimble", prize=None, market_id="nimble"),
            EventCategory(name="Best use of Sentry", prize="Mechanical keyboards"),
        ],
        missing=["starts_at"],
        is_sample=True,
    )
