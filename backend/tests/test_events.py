"""The host flow backend: reading an event page, saving the event, and the host page's numbers."""

import pytest

from app.config import get_settings
from app.events import service as events
from app.schemas import EventCategory, EventDraft
from app.scout import pipeline

HOST = {"X-Host-Password": "test-host-password"}
EVENT_URL = "https://www.mlh.com/events/ai-engineer-nyc-2026"

EVENT = {
    "name": "AI Engineer NYC 2026",
    "hosted_by": "AI Engineer and Major League Hacking",
    "location": "New York, NY",
    "starts_at": "2026-10-11T09:00:00-04:00",
    "submissions_close_at": "2026-10-11T23:59:00-04:00",
    "source_url": EVENT_URL,
    "categories": [
        {"name": "Best overall", "prize": "1st $1,024", "market_id": "overall"},
        {"name": "Best use of Snowflake", "prize": None, "market_id": None},
    ],
}


@pytest.fixture
def scout_on(monkeypatch):
    monkeypatch.setattr(get_settings(), "scout_enabled", True)


# ---- Reading the event page ------------------------------------------------


def test_extract_serves_marked_sample_data_while_scout_is_off(client):
    draft = client.post("/api/events/extract", json={"url": EVENT_URL}).json()
    assert draft["is_sample"] is True
    assert draft["name"] == "AI Engineer NYC 2026" and draft["source_url"] == EVENT_URL
    assert draft["missing"] == ["starts_at"] and draft["starts_at"] is None
    by_name = {c["name"]: c for c in draft["categories"]}
    assert by_name["Best use of Tiger Data"]["market_id"] == "tiger_data"
    assert by_name["Best use of Snowflake"]["market_id"] is None  # Scout can't score it, so no market
    assert by_name["Best use of Nimble"]["prize"] is None


def test_extract_uses_scout_when_it_is_on(client, scout_on, monkeypatch):
    async def extract_event(url):
        return EventDraft(name="Real Hack", categories=[EventCategory(name="Best use of Gemini", market_id="gemini")])

    monkeypatch.setattr(pipeline, "extract_event", extract_event, raising=False)
    draft = client.post("/api/events/extract", json={"url": EVENT_URL}).json()
    assert draft["name"] == "Real Hack" and draft["is_sample"] is False
    assert draft["source_url"] == EVENT_URL  # filled in when Scout leaves it out


def test_a_failed_read_returns_an_empty_draft_not_sample_data(client, scout_on, monkeypatch):
    async def extract_event(url):
        raise RuntimeError("Nimble is down")

    monkeypatch.setattr(pipeline, "extract_event", extract_event, raising=False)
    draft = client.post("/api/events/extract", json={"url": EVENT_URL}).json()
    assert draft["name"] == "" and draft["categories"] == [] and draft["is_sample"] is False
    assert set(draft["missing"]) >= {"name", "location", "submissions_close_at", "categories"}


def test_scout_on_but_not_written_yet_falls_back_to_sample(client, scout_on, monkeypatch):
    monkeypatch.delattr(pipeline, "extract_event", raising=False)
    assert client.post("/api/events/extract", json={"url": EVENT_URL}).json()["is_sample"] is True


@pytest.mark.parametrize("url", ["mlh.com/events/x", "ftp://mlh.com/x", "javascript:alert(1)", "   "])
def test_extract_rejects_things_that_are_not_web_links(client, url):
    res = client.post("/api/events/extract", json={"url": url})
    assert res.status_code == 400 and "https://" in res.json()["detail"]


@pytest.mark.parametrize(
    "name, market_id",
    [
        ("Best overall", "overall"),
        ("Best Use of Gemini API", "gemini"),
        ("Best use of Tiger Data", "tiger_data"),
        ("Best use of Nimble", "nimble"),
        ("Best use of Snowflake", None),
        ("Best use of Sentry", None),
    ],
)
def test_categories_map_to_the_four_markets(name, market_id):
    assert events.market_id_for(name) == market_id


# ---- Saving and reading the event ------------------------------------------


def test_there_is_no_event_before_setup(client):
    assert client.get("/api/event").status_code == 404


def test_launch_saves_the_event(client):
    res = client.put("/api/event", json=EVENT, headers=HOST)
    assert res.status_code == 200
    saved = res.json()
    assert saved["slug"] == "ai-engineer-nyc-2026"
    assert saved["categories"] == EVENT["categories"]
    assert saved["submissions_close_at"] in ("2026-10-11T23:59:00-04:00", "2026-10-12T03:59:00Z")
    assert client.get("/api/event").json() == saved


def test_saving_again_replaces_the_single_event(client, db):
    client.put("/api/event", json=EVENT, headers=HOST)
    client.put("/api/event", json={"name": "Renamed Hack", "categories": []}, headers=HOST)
    assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 1
    event = client.get("/api/event").json()
    assert (event["slug"], event["location"], event["categories"]) == ("renamed-hack", None, [])


def test_saving_needs_the_host_password_and_a_name(client):
    assert client.put("/api/event", json=EVENT).status_code == 401
    assert client.put("/api/event", json=EVENT, headers={"X-Host-Password": "wrong"}).status_code == 401
    assert client.put("/api/event", json={**EVENT, "name": ""}, headers=HOST).status_code == 422
    bad_market = {**EVENT, "categories": [{"name": "Best pizza", "market_id": "pizza"}]}
    assert client.put("/api/event", json=bad_market, headers=HOST).status_code == 422
    assert client.get("/api/event").status_code == 404


def test_saving_the_event_never_touches_markets(client, db):
    before = db.execute("SELECT count(*) FROM markets").fetchone()[0], db.execute("SELECT count(*) FROM positions").fetchone()[0]
    client.put("/api/event", json=EVENT, headers=HOST)
    after = db.execute("SELECT count(*) FROM markets").fetchone()[0], db.execute("SELECT count(*) FROM positions").fetchone()[0]
    assert before == after == (4, 24)


# ---- Starting balance: chosen at launch, fixed afterwards -------------------


def join(client, name="Maya") -> dict:
    return client.post("/api/users", json={"display_name": name}).json()


def test_starting_balance_defaults_to_1000(client):
    assert join(client, "Before launch")["balance"] == 1000
    saved = client.put("/api/event", json=EVENT, headers=HOST).json()
    assert saved["starting_balance"] == 1000
    assert join(client, "After launch")["balance"] == 1000


def test_the_host_chooses_the_starting_balance_at_launch(client):
    saved = client.put("/api/event", json={**EVENT, "starting_balance": 500}, headers=HOST).json()
    assert saved["starting_balance"] == 500
    assert client.get("/api/event").json()["starting_balance"] == 500
    user = join(client)
    assert user["balance"] == 500
    # The whole amount is theirs to stake, and no more than that.
    bet = {"user_id": user["id"], "market_id": "overall", "team_id": "orbit"}
    assert client.post("/api/bets", json={**bet, "stake": 501}).status_code == 400
    assert client.post("/api/bets", json={**bet, "stake": 500}).json()["new_balance"] == 0


def test_starting_balance_cannot_change_after_launch(client):
    client.put("/api/event", json={**EVENT, "starting_balance": 500}, headers=HOST)
    changed = client.put("/api/event", json={**EVENT, "starting_balance": 2000}, headers=HOST)
    assert changed.status_code == 400 and "can't be changed" in changed.json()["detail"]
    # Leaving it out means the default of 1,000, which is also a change.
    assert client.put("/api/event", json=EVENT, headers=HOST).status_code == 400
    assert client.get("/api/event").json()["starting_balance"] == 500
    assert join(client)["balance"] == 500


def test_other_details_can_still_be_edited_after_launch(client):
    client.put("/api/event", json={**EVENT, "starting_balance": 500}, headers=HOST)
    renamed = client.put("/api/event", json={**EVENT, "name": "Renamed Hack", "starting_balance": 500}, headers=HOST)
    assert renamed.status_code == 200
    assert (renamed.json()["name"], renamed.json()["starting_balance"]) == ("Renamed Hack", 500)


@pytest.mark.parametrize("amount", [0, -100, 1_000_001, 12.5, "lots"])
def test_starting_balance_must_be_a_sensible_whole_number(client, amount):
    assert client.put("/api/event", json={**EVENT, "starting_balance": amount}, headers=HOST).status_code == 422
    assert client.get("/api/event").status_code == 404


# ---- The host page ---------------------------------------------------------


def test_host_summary_needs_the_password(client):
    assert client.get("/api/host/summary").status_code == 401
    assert client.get("/api/host/summary", headers={"X-Host-Password": "wrong"}).status_code == 401


def test_host_summary_on_a_fresh_event(client):
    summary = client.get("/api/host/summary", headers=HOST).json()
    assert (summary["attendees"], summary["teams"], summary["bets"], summary["hackcoin_traded"]) == (0, 6, 0, 0)
    assert [m["id"] for m in summary["markets"]] == ["overall", "nimble", "gemini", "tiger_data"]
    overall = summary["markets"][0]
    assert overall["category"] == "Best overall" and overall["status"] == "open"
    assert overall["leader_team_name"] == "Team Orbit" and overall["leader_price"] == pytest.approx(0.27)
    assert overall["staked"] == 0 and overall["winner_team_id"] is None
    assert summary["top_forecasters"] == []


def test_host_summary_counts_activity_and_shows_winners(client):
    users = [client.post("/api/users", json={"display_name": f"Player {i}"}).json() for i in range(7)]
    for i, user in enumerate(users):
        client.post("/api/bets", json={"user_id": user["id"], "market_id": "overall", "team_id": "ledger", "stake": 100 + i})
    client.post("/api/bets", json={"user_id": users[0]["id"], "market_id": "nimble", "team_id": "kiln", "stake": 50})
    client.post("/api/markets/nimble/resolve", json={"winner_team_id": "kiln"}, headers=HOST)

    summary = client.get("/api/host/summary", headers=HOST).json()
    assert (summary["attendees"], summary["teams"], summary["bets"]) == (7, 6, 8)
    assert summary["hackcoin_traded"] == sum(100 + i for i in range(7)) + 50

    overall, nimble = summary["markets"][0], summary["markets"][1]
    assert overall["leader_team_id"] == "ledger" and overall["staked"] == sum(100 + i for i in range(7))
    assert (nimble["status"], nimble["winner_team_id"], nimble["staked"]) == ("resolved", "kiln", 50)

    top = summary["top_forecasters"]
    assert len(top) == 5 and top[0]["display_name"] == "Player 0"  # won 6x on the nimble market
    assert [e["balance"] for e in top] == sorted((e["balance"] for e in top), reverse=True)


def test_host_summary_with_no_teams(client, db):
    # DELETE, not TRUNCATE ... CASCADE: markets reference teams, so a cascade would empty markets too.
    db.execute("DELETE FROM positions")
    db.execute("DELETE FROM teams")
    overall = client.get("/api/host/summary", headers=HOST).json()["markets"][0]
    assert (overall["leader_team_id"], overall["leader_team_name"], overall["leader_price"]) == (None, None, None)
