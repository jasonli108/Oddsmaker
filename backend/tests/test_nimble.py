"""Parsing of Nimble responses. Bodies are trimmed copies of real responses, so no credits are spent."""

import asyncio
import base64

from app.scout import nimble

PNG = b"\x89PNG\r\n\x1a\nfake"


def test_search_keeps_one_line_description():
    body = {
        "total_results": 2,
        "results": [
            {
                "title": "NBA Playoffs Prediction Market Hackathon",
                "description": "\\## Hackathon Introduction\nBuild AI trading automations " + "x" * 500,
                "url": "https://dorahacks.io/hackathon/nba-prediction-market/detail",
                "content": "",
            },
            {"title": "No link", "description": "dropped", "url": ""},
        ],
    }
    [result] = nimble.parse_search(body)
    assert result.url == "https://dorahacks.io/hackathon/nba-prediction-market/detail"
    assert result.description.startswith("Hackathon Introduction Build AI trading")
    assert "\n" not in result.description and "#" not in result.description
    assert len(result.description) <= nimble.DESCRIPTION_CHARS


def test_extract_live_page_with_screenshot():
    body = {
        "url": "https://example.com/",
        "status": "success",
        "status_code": 200,
        "data": {"markdown": "Example Domain", "screenshots": [base64.b64encode(PNG).decode()]},
        "metadata": {"query_duration": 1537, "driver": "vx8"},
    }
    page = nimble.parse_extract("https://example.com", body)
    assert page.is_up
    assert page.load_ms == 1537
    assert page.text == "Example Domain"
    assert page.screenshot_png == PNG


def test_extract_retries_the_other_way_when_a_live_page_has_no_text(monkeypatch):
    calls = []

    async def fake_extract(url, *, render, screenshot):
        calls.append((render, screenshot))
        text = "" if render else "# AI Engineer New York Hackathon"
        return nimble.PageExtract(url=url, is_up=True, load_ms=100, text=text)

    monkeypatch.setattr(nimble, "_extract", fake_extract)
    page = asyncio.run(nimble.extract("https://luma.com/x"))
    assert page.text == "# AI Engineer New York Hackathon"
    assert calls == [(True, True), (False, False)]  # no screenshot without the browser


def test_extract_dead_deploy_is_down_not_an_error():
    body = {
        "url": "https://gone.vercel.app/",
        "status": "success",
        "status_code": 404,
        "data": {"markdown": "# This page doesn't exist"},
        "metadata": {"query_duration": 2415},
    }
    page = nimble.parse_extract("https://gone.vercel.app", body)
    assert not page.is_up
    assert page.screenshot_png is None
