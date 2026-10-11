"""Nimble: live web evidence for Scout.

Used for three things (build spec, "Scout pipeline"):
- search the web and past hackathon galleries for the same idea (originality check)
- extract a team's deployed demo page: is it up, load time, visible text, screenshot if offered
- extract the event page and search past winners, to learn what judges reward

Docs: https://docs.nimbleway.com/home. Shapes below were checked against live responses:
- search returns a long page summary in `description`; `content` stays empty unless
  full_content is set, so we cut `description` down to one line.
- extract returns the target's HTTP status as top-level `status_code` (a dead Vercel deploy is
  a successful call with status_code 404), and the screenshot as a list in `data.screenshots`.

Raise NimbleError on failure; the pipeline decides what a failed fetch means (it must never
zero a team).
"""

import base64
import re
from dataclasses import dataclass

import httpx

from app.config import get_settings

BASE_URL = "https://sdk.nimbleway.com/v2"
# Rendered extracts took 3 to 7 seconds in testing.
TIMEOUT_SECONDS = 60
DESCRIPTION_CHARS = 200


# Nimble's error messages that mean the site is down, not that Nimble failed. Seen live:
# "nx_domain_error" (HTTP 400) for a demo link whose domain doesn't exist.
SITE_DOWN_REASONS = {"nx_domain_error"}


class NimbleError(Exception):
    def __init__(self, message: str, reason: str | None = None):
        super().__init__(message)
        self.reason = reason  # Nimble's own error message, e.g. "nx_domain_error"


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


async def search(query: str, limit: int = 5, *, domains: list[str] | None = None) -> list[SearchResult]:
    """Top web results for a query. Pass domains to search only those sites, e.g. devpost.com."""
    payload: dict = {"query": query, "max_results": limit}
    if domains:
        payload["include_domains"] = domains
    return parse_search(await _post("/search", payload))


async def extract(url: str, *, screenshot: bool = True, render: bool = True) -> PageExtract:
    """Load a page and return its text, status and (in a browser) a screenshot.

    render=True loads it in a headless browser, which single-page demo apps need. render=False is
    a plain HTTP fetch: faster, and enough for pages that send their content in the HTML, like
    Luma, Devpost and MLH. If a live page comes back with no text, it is fetched once more the
    other way: Luma's event pages come back empty in the browser but complete over HTTP.
    """
    page = await _extract(url, render=render, screenshot=screenshot)
    if page.is_up and not page.text.strip():
        retry = await _extract(url, render=not render, screenshot=screenshot and not render)
        if retry.text.strip():
            return retry
    return page


async def _extract(url: str, *, render: bool, screenshot: bool) -> PageExtract:
    # A screenshot needs the browser, so it is only asked for when rendering.
    formats = ["markdown", "screenshot"] if screenshot and render else ["markdown"]
    try:
        body = await _post("/extract", {"url": url, "render": render, "formats": formats})
    except NimbleError as e:
        if e.reason in SITE_DOWN_REASONS:
            return PageExtract(url=url, is_up=False, load_ms=None, text="")
        raise
    if body.get("status") != "success":
        raise NimbleError(f"extract {url}: status {body.get('status')!r}")
    return parse_extract(url, body)


def parse_search(body: dict) -> list[SearchResult]:
    return [
        SearchResult(title=r.get("title") or "", url=r["url"], description=_one_line(r.get("description") or ""))
        for r in body.get("results", [])
        if r.get("url")
    ]


def parse_extract(url: str, body: dict) -> PageExtract:
    data = body.get("data") or {}
    status_code = body.get("status_code") or 0
    shots = data.get("screenshots") or []
    return PageExtract(
        url=body.get("url") or url,
        is_up=200 <= status_code < 400,
        # Nimble's time to load and render the page, the closest thing it reports to load time.
        load_ms=(body.get("metadata") or {}).get("query_duration"),
        text=data.get("markdown") or "",
        screenshot_png=base64.b64decode(shots[0]) if shots else None,
    )


def _one_line(text: str) -> str:
    """Strip markdown symbols and newlines, and cut to one short line."""
    text = " ".join(re.sub(r"[\\#*_`>|]+", " ", text).split())
    return text if len(text) <= DESCRIPTION_CHARS else text[: DESCRIPTION_CHARS - 1].rstrip() + "…"


async def _post(path: str, payload: dict) -> dict:
    key = get_settings().nimble_api_key
    if not key:
        raise NimbleError("NIMBLE_API_KEY is not set in backend/.env")
    try:
        async with httpx.AsyncClient(
            base_url=BASE_URL, headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT_SECONDS
        ) as client:
            response = await client.post(path, json=payload)
    except httpx.HTTPError as e:
        raise NimbleError(f"{path}: {e!r}") from e
    if response.status_code != 200:
        # Nimble's error body says why (e.g. a 500 with "please try again"); keep it in the message.
        try:
            reason = response.json().get("message")
        except ValueError:
            reason = None
        raise NimbleError(f"{path}: HTTP {response.status_code}: {response.text[:300]}", reason)
    return response.json()
