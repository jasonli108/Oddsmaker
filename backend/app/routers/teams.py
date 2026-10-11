from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.market import service
from app.schemas import Team, TeamCreate, TeamReport
from app.scout import pipeline

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[Team])
async def list_teams():
    return await service.list_teams()


@router.post("", response_model=Team, status_code=201)
async def create_team(body: TeamCreate, background: BackgroundTasks):
    try:
        team = await service.create_team(body)
    except service.MarketError as e:
        raise HTTPException(400, str(e))
    # Scout's first run takes a while (web search, demo fetch, Gemini), so it runs after the response.
    background.add_task(pipeline.run_for_team, team)
    return team


@router.get("/{team_id}/report", response_model=TeamReport)
async def get_team_report(team_id: str):
    report = await pipeline.get_team_report(team_id)
    if report is None:
        raise HTTPException(404, "Team not found")
    return report


@router.post("/{team_id}/scout", response_model=TeamReport)
async def run_scout(team_id: str):
    # Open to anyone, so each team has a cooldown (pipeline.RUN_SCOUT_COOLDOWN_MINUTES). Takes up to a minute.
    try:
        report = await pipeline.scout_team(team_id)
    except pipeline.ScoutBusy as e:
        raise HTTPException(429, str(e))
    except pipeline.ScoutError as e:
        raise HTTPException(503, str(e))
    if report is None:
        raise HTTPException(404, "Team not found")
    return report
