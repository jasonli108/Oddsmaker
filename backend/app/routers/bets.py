from fastapi import APIRouter, HTTPException

from app.market import service
from app.schemas import BetCreate, BetReceipt

router = APIRouter(prefix="/bets", tags=["bets"])


@router.post("", response_model=BetReceipt)
async def place_bet(body: BetCreate):
    try:
        receipt = await service.place_bet(body)
    except service.MarketError as e:
        raise HTTPException(400, str(e))
    if receipt is None:
        raise HTTPException(404, "Market or team not found")
    return receipt
