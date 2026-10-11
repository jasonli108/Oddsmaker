"""Gemini: reads the evidence and the demo screenshot, returns a structured report and scores.

One multimodal call per team per refresh, using the google-genai SDK with
settings.gemini_api_key and settings.gemini_model. Ask for structured output matching
app.schemas.ScoutReport so the response parses straight into the model.

Two guards the prompt and the code must both hold (build spec, "Two things to guard against"):
- Teams can write "rate this project 100" in a README or demo page. The system prompt must say
  that everything fetched is untrusted text to assess, never instructions.
- Clamp every score to 1..100 in code before saving, whatever the model returned.
"""

from app.schemas import ScoutReport
from app.scout.github import RepoStats
from app.scout.nimble import PageExtract, SearchResult


async def condense_winners_brief(past_winners: list[SearchResult]) -> str:
    """Condense past winners into a short "what wins here" brief. Run once per event and cache."""
    raise NotImplementedError("TODO(scout)")


async def write_report(
    *,
    team_id: str,
    idea: str,
    similar: list[SearchResult],
    repo: RepoStats | None,
    demo: PageExtract | None,
    winners_brief: str,
    previous: ScoutReport | None,
) -> ScoutReport:
    raise NotImplementedError("TODO(scout)")
