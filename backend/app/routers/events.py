from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_host
from app.events import service
from app.schemas import Event, EventCreate, EventDraft, EventExtractRequest, HostSummary

router = APIRouter(tags=["host"])


@router.post("/events/extract", response_model=EventDraft)
async def extract_event(body: EventExtractRequest):
    url = body.url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(400, "Enter the full link to your event page, starting with https://")
    return await service.extract_event(url)


@router.post("/events", response_model=Event, status_code=201, dependencies=[Depends(require_host)])
async def create_event(body: EventCreate):
    try:
        return await service.create_event(body)
    except service.EventError as e:
        raise HTTPException(400, str(e))


@router.get("/events/{slug}", response_model=Event)
async def get_event(slug: str):
    event = await service.get_event(slug)
    if event is None:
        raise HTTPException(404, "Event not found")
    return event


@router.get("/event", response_model=Event)
async def get_first_event():
    """The first event this deployment ran, for the landing page's "See a live market" link."""
    event = await service.get_event()
    if event is None:
        raise HTTPException(404, "No event has been set up yet")
    return event


@router.get("/host/summary", response_model=HostSummary, dependencies=[Depends(require_host)])
async def host_summary(event: str | None = None):
    summary = await service.host_summary(event)
    if summary is None:
        raise HTTPException(404, "Event not found")
    return summary
