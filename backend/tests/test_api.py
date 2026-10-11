"""Contract smoke tests: every endpoint answers and its body validates against app.schemas.

These pass against the mock data and should keep passing as real implementations land.
"""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_list_markets_has_the_four_prize_categories():
    ids = [m["id"] for m in client.get("/api/markets").json()]
    assert ids == ["overall", "nimble", "gemini", "tiger_data"]


def test_market_prices_sum_to_one():
    market = client.get("/api/markets/overall").json()
    assert abs(sum(t["price"] for t in market["teams"]) - 1) < 1e-6


def test_market_history_and_feed():
    history = client.get("/api/markets/overall/history").json()
    assert history["series"] and history["series"][0]["points"]
    feed = client.get("/api/markets/overall/feed").json()
    assert {item["kind"] for item in feed} <= {"bet", "scout"}


def test_unknown_market_is_404():
    assert client.get("/api/markets/nope").status_code == 404


def test_place_bet_locks_the_multiple():
    body = {"user_id": "u1", "market_id": "overall", "team_id": "orbit", "stake": 100}
    receipt = client.post("/api/bets", json=body).json()
    assert receipt["potential_payout"] == round(100 * receipt["multiple"], 2)
    assert receipt["new_balance"] == 900


def test_bet_above_balance_is_rejected():
    body = {"user_id": "u1", "market_id": "overall", "team_id": "orbit", "stake": 5000}
    assert client.post("/api/bets", json=body).status_code == 400


def test_create_team_and_read_report():
    body = {"name": "New Team", "idea": "An idea", "repo_url": "https://github.com/example/new"}
    res = client.post("/api/teams", json=body)
    assert res.status_code == 201 and res.json()["id"] == "new-team"
    assert client.get("/api/teams").status_code == 200
    report = client.get("/api/teams/orbit/report").json()
    assert set(report["report"]["scores"]) == {"overall", "nimble", "gemini", "tiger_data"}


def test_users_and_leaderboard():
    user = client.post("/api/users", json={"display_name": "Maya"}).json()
    assert user["balance"] == 1000
    assert client.get(f"/api/users/{user['id']}").status_code == 200
    assert client.get("/api/leaderboard").json()[0]["rank"] == 1


def test_resolve_needs_the_host_password():
    body = {"winner_team_id": "orbit"}
    assert client.post("/api/markets/overall/resolve", json=body).status_code == 401
    headers = {"X-Host-Password": get_settings().host_password}
    res = client.post("/api/markets/overall/resolve", json=body, headers=headers)
    assert res.status_code == 200 and res.json()["market"]["status"] == "resolved"
