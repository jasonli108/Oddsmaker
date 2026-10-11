"""API tests against a real (local, throwaway) database. See conftest.py for the setup.

The `client` fixture seeds four markets and six teams; in the overall market the seed follows
the build spec's worked example, so Orbit opens at 27%.
"""

import pytest
from psycopg.types.json import Jsonb

from app import sample_data
from app.market import service
from app.scout import pipeline


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


# ---- Scout moves the price --------------------------------------------------


def test_scout_odds_resplit_the_seed_and_move_prices(client, call, db):
    user = join(client)
    bet(client, user["id"], "orbit", 100)
    call(service.apply_scout_odds, "overall", {"orbit": 30, "ledger": 70})  # shares need not sum to 1

    assert dict(db.execute("SELECT team_id, seed FROM positions WHERE market_id = 'overall'")) == {
        "orbit": 600, "ledger": 1400, "parsel": 0, "night": 0, "kiln": 0, "tally": 0,
    }
    market = client.get("/api/markets/overall").json()
    orbit = team(market, "orbit")
    assert orbit["scout_odds"] == pytest.approx(0.3)
    assert orbit["staked"] == 100  # the bet is untouched
    assert team(market, "parsel")["price"] == pytest.approx(0.02)  # no seed, so the floor
    assert sum(t["price"] for t in market["teams"]) == pytest.approx(1)
    assert db.execute("SELECT count(*) FROM price_ticks WHERE source = 'scout'").fetchone()[0] == 6


def test_scout_cannot_move_a_resolved_or_unknown_market(call, db):
    db.execute("UPDATE markets SET status = 'resolved', winner_team_id = 'ledger' WHERE id = 'overall'")
    call(service.apply_scout_odds, "overall", {"orbit": 1})
    call(service.apply_scout_odds, "nope", {"orbit": 1})
    assert db.execute("SELECT seed FROM positions WHERE market_id = 'overall' AND team_id = 'orbit'").fetchone()[0] == 540
    assert db.execute("SELECT count(*) FROM price_ticks").fetchone()[0] == 0


# ---- History and feed --------------------------------------------------------


def test_history_comes_from_the_continuous_aggregate(client):
    assert all(s["points"] == [] for s in client.get("/api/markets/overall/history").json()["series"])
    user = join(client)
    bet(client, user["id"], "orbit", 100)
    bet(client, user["id"], "orbit", 100)

    history = client.get("/api/markets/overall/history").json()
    assert history["market_id"] == "overall" and len(history["series"]) == 6
    orbit = next(s for s in history["series"] if s["team_id"] == "orbit")
    # Two bets in the same minute collapse into one point holding the last price.
    assert len(orbit["points"]) == 1
    assert orbit["points"][0]["price"] == pytest.approx(740 / 2200)
    assert orbit["name"] == "Team Orbit" and orbit["color"].startswith("#")
    assert client.get("/api/markets/nope/history").status_code == 404


def test_feed_lists_bets_and_scout_moves_newest_first(client, call):
    maya, dev = join(client, "Maya"), join(client, "Dev")
    bet(client, maya["id"], "orbit", 50)
    bet(client, dev["id"], "kiln", 200)
    # Scout swaps its view of Parsel and Night Shift and leaves everyone else's seed as it was.
    call(service.apply_scout_odds, "overall", {"orbit": 540, "ledger": 500, "parsel": 260, "night": 400, "kiln": 200, "tally": 100})

    feed = client.get("/api/markets/overall/feed").json()
    times = [item["time"] for item in feed]
    assert times == sorted(times, reverse=True)

    bets = [i for i in feed if i["kind"] == "bet"]
    assert [(b["user_display_name"], b["team_name"], b["stake"]) for b in bets] == [("Dev", "Kiln", 200), ("Maya", "Team Orbit", 50)]
    assert bets[1]["price"] == pytest.approx(0.27)

    moves = {i["team_id"]: i for i in feed if i["kind"] == "scout"}
    # Only the two teams whose price moved by a point or more get a card.
    assert set(moves) == {"parsel", "night"}
    assert moves["parsel"]["price_from"] == pytest.approx(400 / 2250)
    assert moves["parsel"]["price_to"] == pytest.approx(260 / 2250)
    assert feed[0]["kind"] == "scout"  # Scout moved last
    assert client.get("/api/markets/nimble/feed").json() == []
    assert client.get("/api/markets/nope/feed").status_code == 404


def test_feed_is_capped_at_20(client):
    user = join(client)
    for _ in range(25):
        bet(client, user["id"], "orbit", 1)
    assert len(client.get("/api/markets/overall/feed").json()) == 20


# ---- Team sign-up ------------------------------------------------------------


def test_a_new_team_enters_every_market_at_the_floor(client, db):
    body = {"name": "Night Owls", "idea": "Flashcards from lecture audio", "repo_url": "https://github.com/example/owls"}
    res = client.post("/api/teams", json=body)
    assert res.status_code == 201
    created = res.json()
    assert created["id"] == "night-owls" and created["demo_url"] is None and created["color"] == "#7DB8FF"  # 7th team wraps round
    assert created in client.get("/api/teams").json()

    for market_id in ("overall", "nimble", "gemini", "tiger_data"):
        market = client.get(f"/api/markets/{market_id}").json()
        owls = team(market, "night-owls")
        assert owls["price"] == pytest.approx(0.02) and owls["multiple"] == pytest.approx(50)
        assert market["totals"]["team_count"] == 7
        assert sum(t["price"] for t in market["teams"]) == pytest.approx(1)
    # It has a report page straight away, with no report on it yet.
    report = client.get("/api/teams/night-owls/report").json()
    assert report["team"]["name"] == "Night Owls" and report["report"] is None


def test_team_names_are_unique_and_ids_never_collide(client):
    assert client.post("/api/teams", json={"name": "Night Owls", "idea": "x"}).status_code == 201
    dup = client.post("/api/teams", json={"name": "night owls", "idea": "y"})
    assert dup.status_code == 400 and "already" in dup.json()["detail"]
    # A different name that boils down to the same id gets a suffix.
    assert client.post("/api/teams", json={"name": "Night-Owls!", "idea": "z"}).json()["id"] == "night-owls-2"
    assert client.post("/api/teams", json={"name": "!!!", "idea": "z"}).json()["id"] == "team"


def test_a_new_team_skips_resolved_markets(client, db):
    db.execute("UPDATE markets SET status = 'resolved', winner_team_id = 'ledger' WHERE id = 'nimble'")
    client.post("/api/teams", json={"name": "Late Entry", "idea": "x"})
    assert client.get("/api/markets/nimble").json()["totals"]["team_count"] == 6
    assert client.get("/api/markets/overall").json()["totals"]["team_count"] == 7


# ---- Resolving and the leaderboard -------------------------------------------

HOST = {"X-Host-Password": "test-host-password"}


def resolve(client, winner="orbit", market_id="overall", headers=HOST):
    return client.post(f"/api/markets/{market_id}/resolve", json={"winner_team_id": winner}, headers=headers)


def test_resolving_pays_winners_their_locked_multiple(client):
    maya, dev, priya = join(client, "Maya"), join(client, "Dev"), join(client, "Priya")
    first = bet(client, maya["id"], "orbit", 100).json()   # 27%, pays 370.37
    second = bet(client, maya["id"], "orbit", 100).json()  # 30.5%, pays less
    bet(client, dev["id"], "ledger", 300)
    assert second["multiple"] < first["multiple"]

    res = resolve(client, "orbit")
    assert res.status_code == 200
    result = res.json()
    assert result["market"] == {**result["market"], "id": "overall", "status": "resolved", "winner_team_id": "orbit"}
    assert result["bets_paid"] == 2
    assert result["total_paid"] == pytest.approx(first["potential_payout"] + second["potential_payout"])

    balance = lambda u: client.get(f"/api/users/{u['id']}").json()["balance"]  # noqa: E731
    assert balance(maya) == pytest.approx(800 + first["potential_payout"] + second["potential_payout"])
    assert balance(dev) == 700      # lost the stake, paid nothing
    assert balance(priya) == 1000   # never bet

    market = client.get("/api/markets/overall").json()
    assert market["status"] == "resolved" and market["winner_team_id"] == "orbit"
    board = client.get("/api/leaderboard").json()
    assert [(e["rank"], e["display_name"]) for e in board] == [(1, "Maya"), (2, "Priya"), (3, "Dev")]


def test_a_market_resolves_only_once(client):
    maya = join(client)
    bet(client, maya["id"], "orbit", 100)
    assert resolve(client, "orbit").status_code == 200
    again = resolve(client, "orbit")
    assert again.status_code == 400 and "already" in again.json()["detail"]
    assert client.get(f"/api/users/{maya['id']}").json()["balance"] == pytest.approx(900 + 370.37)
    assert bet(client, maya["id"], "orbit", 10).status_code == 400


def test_resolve_checks_the_password_and_the_winner(client):
    assert resolve(client, headers={}).status_code == 401
    assert resolve(client, headers={"X-Host-Password": "wrong"}).status_code == 401
    assert resolve(client, winner="nobody").status_code == 404
    assert resolve(client, market_id="nope").status_code == 404
    assert client.get("/api/markets/overall").json()["status"] == "open"


def test_resolving_one_market_leaves_the_others_open(client):
    maya = join(client)
    resolve(client, "orbit", market_id="overall")
    assert bet(client, maya["id"], "orbit", 10, market_id="nimble").status_code == 200


def test_leaderboard_ties_share_a_rank(client):
    assert client.get("/api/leaderboard").json() == []
    maya, _dev, _priya = join(client, "Maya"), join(client, "Dev"), join(client, "Priya")
    bet(client, maya["id"], "orbit", 100)
    assert [(e["rank"], e["display_name"], e["balance"]) for e in client.get("/api/leaderboard").json()] == [
        (1, "Dev", 1000), (1, "Priya", 1000), (3, "Maya", 900),
    ]


# ---- Scout reports -----------------------------------------------------------


def save_report(db, team_id, overall, stale=False):
    body = sample_data.team_report(team_id).report.model_dump(mode="json")
    body["scores"]["overall"] = overall
    db.execute("INSERT INTO reports (team_id, body, stale) VALUES (%s, %s, %s)", (team_id, Jsonb(body), stale))


def test_team_report_is_the_latest_saved_report(client, db):
    assert client.get("/api/teams/orbit/report").json()["report"] is None
    save_report(db, "orbit", 60)
    save_report(db, "orbit", 60, stale=True)  # a refresh that failed and reused the last report
    report = client.get("/api/teams/orbit/report").json()
    assert set(report["report"]["scores"]) == {"overall", "nimble", "gemini", "tiger_data"}
    assert report["stale"] is True
    # One point per market for the fresh report; the stale copy adds none.
    assert [p["market_id"] for p in report["odds_history"]] == ["overall", "nimble", "gemini", "tiger_data"]
    assert client.get("/api/teams/nobody/report").status_code == 404


def test_scout_sets_the_odds_from_the_latest_scores(client, db, call):
    save_report(db, "orbit", 100)
    call(pipeline.reprice_markets)
    # Orbit scores 100; the five teams with no report yet count as a neutral 50 each.
    assert team(client.get("/api/markets/overall").json(), "orbit")["scout_odds"] == pytest.approx(100 / 350)
