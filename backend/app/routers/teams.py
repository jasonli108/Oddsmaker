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
    team = await service.create_team(body)
    # Scout's first run takes a while (web search, demo fetch, Gemini), so it runs after the response.
    background.add_task(pipeline.run_for_team, team)
    return team


@router.get("/{team_id}/report", response_model=TeamReport)
async def get_team_report(team_id: str):
    report = await pipeline.get_team_report(team_id)
    if report is None:
        raise HTTPException(404, "Team not found")
    return report
