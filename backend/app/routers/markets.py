import secrets

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.market import service
from app.schemas import FeedItem, MarketDetail, MarketHistory, MarketSummary, ResolveRequest, ResolveResult

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("", response_model=list[MarketSummary])
async def list_markets():
    return await service.list_markets()


@router.get("/{market_id}", response_model=MarketDetail)
async def get_market(market_id: str):
    market = await service.get_market(market_id)
    if market is None:
        raise HTTPException(404, "Market not found")
    return market


@router.get("/{market_id}/history", response_model=MarketHistory)
async def get_history(market_id: str):
    history = await service.get_history(market_id)
    if history is None:
        raise HTTPException(404, "Market not found")
    return history


@router.get("/{market_id}/feed", response_model=list[FeedItem])
async def get_feed(market_id: str):
    feed = await service.get_feed(market_id)
    if feed is None:
        raise HTTPException(404, "Market not found")
    return feed


@router.post("/{market_id}/resolve", response_model=ResolveResult)
async def resolve_market(market_id: str, body: ResolveRequest, x_host_password: str = Header(default="")):
    if not secrets.compare_digest(x_host_password, get_settings().host_password):
        raise HTTPException(401, "Host password required")
    try:
        result = await service.resolve_market(market_id, body.winner_team_id)
    except service.MarketError as e:
        raise HTTPException(400, str(e))
    if result is None:
        raise HTTPException(404, "Market or team not found")
    return result
