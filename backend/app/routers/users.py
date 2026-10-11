from fastapi import APIRouter, HTTPException

from app.market import service
from app.schemas import LeaderboardEntry, User, UserCreate

router = APIRouter(tags=["users"])


@router.post("/users", response_model=User, status_code=201)
async def create_user(body: UserCreate):
    return await service.create_user(body.display_name)


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await service.get_user(user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard():
    return await service.get_leaderboard()
