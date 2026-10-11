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


@router.get("/event", response_model=Event)
async def get_event():
    event = await service.get_event()
    if event is None:
        raise HTTPException(404, "No event has been set up yet")
    return event


@router.put("/event", response_model=Event, dependencies=[Depends(require_host)])
async def save_event(body: EventCreate):
    return await service.save_event(body)


@router.get("/host/summary", response_model=HostSummary, dependencies=[Depends(require_host)])
async def host_summary():
    return await service.host_summary()
