from fastapi import APIRouter, HTTPException

from app.market import service
from app.schemas import LeaderboardEntry, TeamLeaderboardEntry, User, UserCreate, UserBet, UserSummary

router = APIRouter(tags=["users"])


@router.post("/users", response_model=User, status_code=201)
async def create_user(body: UserCreate):
    try:
        return await service.create_user(body.display_name, body.event_slug)
    except service.MarketError as e:
        raise HTTPException(400, str(e))


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await service.get_user(user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


@router.get("/users/{user_id}/summary", response_model=UserSummary)
async def get_user_summary(user_id: str):
    summary = await service.get_user_summary(user_id)
    if summary is None:
        raise HTTPException(404, "User not found")
    return summary


@router.get("/users/{user_id}/bets", response_model=list[UserBet])
async def get_user_bets(user_id: str):
    bets = await service.get_user_bets(user_id)
    if bets is None:
        raise HTTPException(404, "User not found")
    return bets


@router.get("/leaderboard/teams", response_model=list[TeamLeaderboardEntry])
async def get_team_leaderboard(event: str | None = None, market: str | None = None):
    return await service.get_team_leaderboard(event_slug=event, market_id=market)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(event: str | None = None):
    return await service.get_leaderboard(event_slug=event)
