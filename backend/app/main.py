import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.routers import bets, events, markets, teams, users
from app.schemas import Health
from app.scout import scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.open_pool()
    scout_task = scheduler.start() if get_settings().scout_enabled else None
    yield
    if scout_task is not None:
        scout_task.cancel()
    await db.close_pool()


app = FastAPI(title="Oddsmaker API", description="Play-money prediction market for hackathons.", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(markets.router)
api.include_router(bets.router)
api.include_router(teams.router)
api.include_router(users.router)
api.include_router(events.router)


@api.get("/health", response_model=Health, tags=["misc"])
async def health():
    return Health(db=await db.status())


app.include_router(api)
