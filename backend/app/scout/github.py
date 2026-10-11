"""GitHub API: exact repo stats for free, so Nimble calls aren't spent on them.

Use httpx against https://api.github.com with settings.github_token if set
(60 requests an hour without a token, 5,000 with one).

Four requests per repo, so six teams every 30 minutes (48 an hour) fit without a token:
- total commits and contributors: ask for one item per page and read the last page number
  from the Link header, instead of paging through everything
- commits since 30 minutes ago, on the default branch
- one compare from before the oldest of those commits to the newest, for files changed

Raise GitHubError on failure; the pipeline decides what a failed fetch means. RepoNotFound, a
GitHubError, means the link will never work, so the pipeline treats it as no repo rather than
as a failed fetch.
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.config import get_settings

API_URL = "https://api.github.com"
RECENT_MINUTES = 30
TIMEOUT_SECONDS = 20


class GitHubError(Exception):
    pass


class RepoNotFound(GitHubError):
    """The link isn't a public GitHub repo (another host, private, or mistyped). Retrying won't help."""


@dataclass
class RepoStats:
    commit_count: int
    contributor_count: int
    commits_last_30_min: int
    files_changed_last_30_min: int


async def repo_stats(repo_url: str) -> RepoStats:
    owner, repo = parse_repo_url(repo_url)
    base = f"/repos/{owner}/{repo}"
    since = (datetime.now(timezone.utc) - timedelta(minutes=RECENT_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
    async with _client() as client:
        first_commit, contributors, recent = await asyncio.gather(
            _get(client, f"{base}/commits", per_page=1),
            _get(client, f"{base}/contributors", per_page=1, anon="true"),
            _get(client, f"{base}/commits", per_page=100, since=since),
        )
        if first_commit is None:  # an empty repo has no commits yet
            return RepoStats(0, 0, 0, 0)
        recent_commits = recent.json() if recent else []
        files = await _files_changed(client, base, recent_commits)
    return RepoStats(
        commit_count=count_from_link(first_commit),
        contributor_count=count_from_link(contributors) if contributors else 0,
        commits_last_30_min=len(recent_commits),
        files_changed_last_30_min=files,
    )


def parse_repo_url(url: str) -> tuple[str, str]:
    """owner and repo from https://github.com/owner/repo, with or without .git or a /tree/... path."""
    match = re.search(r"github\.com[/:]([\w.-]+)/([\w.-]+)", url)
    if not match:
        raise RepoNotFound(f"not a GitHub repo link: {url}")
    owner, repo = match.groups()
    return owner, repo.removesuffix(".git")


def count_from_link(response: httpx.Response) -> int:
    """With per_page=1, the last page number in the Link header is the total item count."""
    last = response.links.get("last", {}).get("url")
    if last:
        return int(httpx.URL(last).params["page"])
    return len(response.json())


async def _files_changed(client: httpx.AsyncClient, base: str, recent_commits: list[dict]) -> int:
    """Distinct files changed by the recent commits (newest first, as GitHub returns them)."""
    if not recent_commits:
        return 0
    newest, oldest = recent_commits[0]["sha"], recent_commits[-1]
    if oldest["parents"]:
        compare = await _get(client, f"{base}/compare/{oldest['parents'][0]['sha']}...{newest}")
        return len(compare.json().get("files", [])) if compare else 0
    # The repo's first commit is in the window, so there is nothing to compare against.
    commit = await _get(client, f"{base}/commits/{newest}")
    return len(commit.json().get("files", [])) if commit else 0


def _client() -> httpx.AsyncClient:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = get_settings().github_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.AsyncClient(base_url=API_URL, headers=headers, timeout=TIMEOUT_SECONDS)


async def _get(client: httpx.AsyncClient, path: str, **params) -> httpx.Response | None:
    """The response, or None for an empty repo (GitHub answers 409 or 204)."""
    try:
        response = await client.get(path, params=params)
    except httpx.HTTPError as e:
        raise GitHubError(f"{path}: {e!r}") from e
    if response.status_code in (204, 409):
        return None
    if response.status_code == 404:
        raise RepoNotFound(f"{path}: not found (private or mistyped repo)")
    if response.status_code != 200:
        # 403 or 429 with x-ratelimit-remaining 0 is the hourly limit.
        remaining = response.headers.get("x-ratelimit-remaining")
        raise GitHubError(f"{path}: HTTP {response.status_code} (rate limit left: {remaining}): {response.text[:200]}")
    return response
