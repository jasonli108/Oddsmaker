"""API tests against a real (local, throwaway) database. See conftest.py for the setup.

The `client` fixture seeds four markets and six teams; in the overall market the seed follows
the build spec's worked example, so Orbit opens at 27%.
"""

import pytest

from app.config import get_settings


def join(client, name="Maya") -> dict:
    res = client.post("/api/users", json={"display_name": name})
    assert res.status_code == 201
    return res.json()


def bet(client, user_id, team_id="orbit", stake=100, market_id="overall"):
    return client.post("/api/bets", json={"user_id": user_id, "market_id": market_id, "team_id": team_id, "stake": stake})


def team(market: dict, team_id: str) -> dict:
    return next(t for t in market["teams"] if t["team_id"] == team_id)


def test_health_reports_the_database(client):
    assert client.get("/api/health").json() == {"status": "ok", "db": "connected"}


# ---- Reading markets -------------------------------------------------------


def test_list_markets_has_the_four_prize_categories_in_order(client):
    assert [m["id"] for m in client.get("/api/markets").json()] == ["overall", "nimble", "gemini", "tiger_data"]


def test_market_prices_come_from_the_seed(client):
    market = client.get("/api/markets/overall").json()
    orbit = team(market, "orbit")
    assert orbit["price"] == pytest.approx(0.27)
    assert orbit["scout_odds"] == pytest.approx(0.27)
    assert orbit["multiple"] == pytest.approx(3.7, abs=0.01)
    assert sum(t["price"] for t in market["teams"]) == pytest.approx(1)
    assert [t["team_id"] for t in market["teams"]][0] == "orbit"  # highest price first
    assert market["totals"] == {"team_count": 6, "hackcoin_traded": 0, "forecaster_count": 0}


def test_unknown_market_is_404(client):
    assert client.get("/api/markets/nope").status_code == 404


def test_teams_come_from_the_database(client, db):
    db.execute("INSERT INTO teams (id, name, idea, color) VALUES ('owls', 'Night Owls', 'Flashcards', '#fff')")
    names = [t["name"] for t in client.get("/api/teams").json()]
    assert len(names) == 7 and "Night Owls" in names


# ---- Users -----------------------------------------------------------------


def test_a_new_user_starts_with_1000_hackcoin(client):
    user = join(client)
    assert user["display_name"] == "Maya" and user["balance"] == 1000
    assert client.get(f"/api/users/{user['id']}").json() == user


@pytest.mark.parametrize("user_id", ["00000000-0000-4000-8000-000000000000", "not-a-uuid"])
def test_unknown_user_is_404(client, user_id):
    assert client.get(f"/api/users/{user_id}").status_code == 404


# ---- Placing a bet: the spec's worked example ------------------------------


def test_a_bet_locks_the_multiple_and_moves_the_price(client, db):
    user = join(client)
    receipt = bet(client, user["id"], "orbit", 100).json()

    assert receipt["price_at_bet"] == pytest.approx(0.27)
    assert receipt["multiple"] == pytest.approx(3.7, abs=0.01)
    assert receipt["potential_payout"] == pytest.approx(370.37)
    assert receipt["new_balance"] == 900

    market = client.get("/api/markets/overall").json()
    orbit = team(market, "orbit")
    assert orbit["price"] == pytest.approx(640 / 2100)  # 30.5%
    assert orbit["staked"] == 100
    assert orbit["scout_odds"] == pytest.approx(0.27)  # Scout's view does not move with bets
    assert sum(t["price"] for t in market["teams"]) == pytest.approx(1)
    assert market["totals"] == {"team_count": 6, "hackcoin_traded": 100, "forecaster_count": 1}
    assert client.get(f"/api/users/{user['id']}").json()["balance"] == 900

    # The multiple is stored, and every team in the market gets a price tick.
    stored = db.execute("SELECT stake, price_at_bet, multiple FROM bets").fetchone()
    assert stored == (100, pytest.approx(0.27), pytest.approx(1 / 0.27))
    ticks = dict(db.execute("SELECT team_id, price FROM price_ticks WHERE market_id = 'overall' AND source = 'bet'"))
    assert len(ticks) == 6 and ticks["orbit"] == pytest.approx(640 / 2100)


def test_the_next_bettor_gets_the_moved_price(client):
    first, second = join(client, "Maya"), join(client, "Dev")
    bet(client, first["id"], "orbit", 100)
    assert bet(client, second["id"], "orbit", 100).json()["price_at_bet"] == pytest.approx(640 / 2100)


def test_a_bet_only_moves_its_own_market(client):
    user = join(client)
    bet(client, user["id"], "orbit", 100, market_id="overall")
    nimble = client.get("/api/markets/nimble").json()
    assert team(nimble, "orbit")["price"] == pytest.approx(1 / 6)


def test_a_bet_above_the_balance_changes_nothing(client, db):
    user = join(client)
    res = bet(client, user["id"], "orbit", 1001)
    assert res.status_code == 400 and "balance" in res.json()["detail"]
    assert client.get(f"/api/users/{user['id']}").json()["balance"] == 1000
    assert db.execute("SELECT count(*) FROM bets").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM price_ticks").fetchone()[0] == 0
    assert team(client.get("/api/markets/overall").json(), "orbit")["price"] == pytest.approx(0.27)


def test_a_whole_balance_can_be_staked(client):
    user = join(client)
    assert bet(client, user["id"], "tally", 1000).json()["new_balance"] == 0
    assert bet(client, user["id"], "tally", 1).status_code == 400


@pytest.mark.parametrize("stake", [0, -5])
def test_a_stake_must_be_positive(client, stake):
    assert bet(client, join(client)["id"], "orbit", stake).status_code == 422


def test_bets_on_unknown_things_are_rejected(client):
    user = join(client)
    assert bet(client, user["id"], "nobody", 10).status_code == 404
    assert bet(client, user["id"], "orbit", 10, market_id="nope").status_code == 404
    assert bet(client, "00000000-0000-4000-8000-000000000000", "orbit", 10).status_code == 400
    assert bet(client, "not-a-uuid", "orbit", 10).status_code == 400


def test_no_bets_on_a_resolved_market(client, db):
    user = join(client)
    db.execute("UPDATE markets SET status = 'resolved', winner_team_id = 'ledger' WHERE id = 'overall'")
    res = bet(client, user["id"], "orbit", 10)
    assert res.status_code == 400 and "closed" in res.json()["detail"]
    assert client.get(f"/api/users/{user['id']}").json()["balance"] == 1000


def test_a_long_shot_is_floored_at_2_percent(client, db):
    db.execute("UPDATE positions SET seed = 1 WHERE market_id = 'overall' AND team_id = 'tally'")
    user = join(client)
    receipt = bet(client, user["id"], "tally", 10).json()
    assert receipt["price_at_bet"] == pytest.approx(0.02)
    assert receipt["multiple"] == pytest.approx(50)


# ---- Still on sample data: replace these as each piece becomes real --------


def test_market_history_and_feed(client):
    history = client.get("/api/markets/overall/history").json()
    assert history["series"] and history["series"][0]["points"]
    feed = client.get("/api/markets/overall/feed").json()
    assert {item["kind"] for item in feed} <= {"bet", "scout"}


def test_create_team_and_read_report(client):
    body = {"name": "New Team", "idea": "An idea", "repo_url": "https://github.com/example/new"}
    res = client.post("/api/teams", json=body)
    assert res.status_code == 201 and res.json()["id"] == "new-team"
    report = client.get("/api/teams/orbit/report").json()
    assert set(report["report"]["scores"]) == {"overall", "nimble", "gemini", "tiger_data"}


def test_leaderboard(client):
    assert client.get("/api/leaderboard").json()[0]["rank"] == 1


def test_resolve_needs_the_host_password(client):
    body = {"winner_team_id": "orbit"}
    assert client.post("/api/markets/overall/resolve", json=body).status_code == 401
    headers = {"X-Host-Password": get_settings().host_password}
    res = client.post("/api/markets/overall/resolve", json=body, headers=headers)
    assert res.status_code == 200 and res.json()["market"]["status"] == "resolved"
