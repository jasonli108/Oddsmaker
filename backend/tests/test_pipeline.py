"""Scout pipeline rules that need no API calls or database."""

from datetime import datetime, timedelta, timezone

from app.scout import gemini, pipeline

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
