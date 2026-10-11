"""GitHub API: exact repo stats for free, so Nimble calls aren't spent on them.

Use httpx against https://api.github.com with settings.github_token if set
(60 requests an hour without a token, 5,000 with one).
"""

from dataclasses import dataclass


@dataclass
class RepoStats:
    commit_count: int
    contributor_count: int
    commits_last_30_min: int
    files_changed_last_30_min: int


async def repo_stats(repo_url: str) -> RepoStats:
    raise NotImplementedError("TODO(scout)")
