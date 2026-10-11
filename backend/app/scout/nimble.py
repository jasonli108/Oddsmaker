"""Nimble: live web evidence for Scout.

Used for three things (build spec, "Scout pipeline"):
- search the web and past hackathon galleries for the same idea (originality check)
- extract a team's deployed demo page: is it up, load time, visible text, screenshot if offered
- extract the event page and search past winners, to learn what judges reward

Check exact endpoints and parameters before writing the calls: https://docs.nimbleway.com/home
Use httpx.AsyncClient with settings.nimble_api_key. Raise on failure; the pipeline decides what
a failed fetch means (it must never zero a team).
"""

from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    url: str
    description: str


@dataclass
class PageExtract:
    url: str
    is_up: bool
    load_ms: int | None
    text: str
    screenshot_png: bytes | None = None


async def search(query: str, limit: int = 5) -> list[SearchResult]:
    raise NotImplementedError("TODO(scout)")


async def extract(url: str) -> PageExtract:
    raise NotImplementedError("TODO(scout)")
