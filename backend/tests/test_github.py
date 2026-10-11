"""GitHub URL parsing and the Link-header count. No API calls, so the hourly limit isn't spent."""

import httpx
import pytest

from app.scout import github


@pytest.mark.parametrize("url", [
    "https://github.com/jasonli108/Oddsmaker",
    "https://github.com/jasonli108/Oddsmaker.git",
    "https://github.com/jasonli108/Oddsmaker/tree/main/backend",
    "git@github.com:jasonli108/Oddsmaker.git",
])
def test_parse_repo_url(url):
    assert github.parse_repo_url(url) == ("jasonli108", "Oddsmaker")


def test_parse_repo_url_rejects_other_hosts():
    with pytest.raises(github.GitHubError):
        github.parse_repo_url("https://gitlab.com/team/app")


def test_count_from_link_reads_last_page():
    link = '<https://api.github.com/repositories/1/commits?per_page=1&page=2>; rel="next", ' \
           '<https://api.github.com/repositories/1/commits?per_page=1&page=57>; rel="last"'
    response = httpx.Response(200, json=[{"sha": "a"}], headers={"link": link})
    assert github.count_from_link(response) == 57


def test_count_from_link_without_link_header_counts_the_page():
    assert github.count_from_link(httpx.Response(200, json=[{"sha": "a"}])) == 1
