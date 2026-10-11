"""The host flow backend: reading an event page, saving the event, and the host page's numbers."""

from datetime import datetime, timedelta, timezone

import pytest
from psycopg.types.json import Jsonb

from app import sample_data
from app.config import get_settings
from app.events import service as events
from app.schemas import EventCategory, EventDraft
from app.scout import gemini, nimble, pipeline

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
def scout_keys(monkeypatch):
    """Scout has both of its keys. SCOUT_ENABLED stays false: reading an event page doesn't wait for it."""
    monkeypatch.setattr(get_settings(), "nimble_api_key", "test-nimble-key")
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-gemini-key")


def refuse_to_read(monkeypatch):
    async def extract_event(url):
        raise AssertionError("Scout must not be asked to read the page")

    monkeypatch.setattr(pipeline, "extract_event", extract_event)


# ---- Reading the event page ------------------------------------------------


def test_extract_serves_marked_sample_data_without_scouts_keys(client, monkeypatch):
    refuse_to_read(monkeypatch)
    draft = client.post("/api/events/extract", json={"url": EVENT_URL}).json()
    assert draft["is_sample"] is True
    assert draft["name"] == "AI Engineer NYC 2026" and draft["source_url"] == EVENT_URL
    assert draft["missing"] == ["starts_at"] and draft["starts_at"] is None
    by_name = {c["name"]: c for c in draft["categories"]}
    assert by_name["Best use of Tiger Data"]["market_id"] == "tiger_data"
    assert by_name["Best use of Snowflake"]["market_id"] is None  # Scout can't score it, so no market
    assert by_name["Best use of Nimble"]["prize"] is None


@pytest.mark.parametrize("missing_key", ["nimble_api_key", "gemini_api_key"])
def test_extract_needs_both_keys(client, scout_keys, monkeypatch, missing_key):
    monkeypatch.setattr(get_settings(), missing_key, "")
    refuse_to_read(monkeypatch)
    assert client.post("/api/events/extract", json={"url": EVENT_URL}).json()["is_sample"] is True


def test_extract_uses_scout_when_it_has_its_keys(client, scout_keys, monkeypatch):
    async def extract_event(url):
        return EventDraft(name="Real Hack", categories=[EventCategory(name="Best use of Gemini", market_id="gemini")])

    monkeypatch.setattr(pipeline, "extract_event", extract_event)
    assert get_settings().scout_enabled is False  # the timed refresh is off; the host's read still runs
    draft = client.post("/api/events/extract", json={"url": EVENT_URL}).json()
    assert draft["name"] == "Real Hack" and draft["is_sample"] is False
    assert draft["source_url"] == EVENT_URL  # filled in when Scout leaves it out


def test_the_whole_read_from_page_text_to_draft(client, scout_keys, monkeypatch):
    """Everything between the endpoint and the two outside calls: Nimble's page in, the draft out."""
    seen = {}

    async def extract(url, *, screenshot=True, render=True):
        seen["nimble"] = (url, screenshot, render)
        return nimble.PageExtract(url=url, is_up=True, load_ms=800, text="AI Engineer NYC 2026 ... Best use of Gemini: swag")

    async def read_event_page(page):
        seen["gemini"] = page.text
        return gemini.GeminiEvent(
            name=" AI Engineer NYC 2026 ", hosted_by="MLH", location="New York, NY",
            starts_at="2026-10-11T09:00:00-04:00", submissions_close_at="tonight",  # not a time: counts as missing
            categories=[
                gemini.GeminiEventCategory(name="Best use of Gemini API", prize="Swag kits"),
                gemini.GeminiEventCategory(name="Best use of Snowflake", prize=""),
            ],
        )

    monkeypatch.setattr(nimble, "extract", extract)
    monkeypatch.setattr(gemini, "read_event_page", read_event_page)
    draft = client.post("/api/events/extract", json={"url": EVENT_URL}).json()
    assert seen["nimble"] == (EVENT_URL, False, False) and "Best use of Gemini" in seen["gemini"]
    assert (draft["name"], draft["hosted_by"], draft["location"]) == ("AI Engineer NYC 2026", "MLH", "New York, NY")
    assert draft["starts_at"] in ("2026-10-11T09:00:00-04:00", "2026-10-11T13:00:00Z")
    assert draft["submissions_close_at"] is None and draft["missing"] == ["submissions_close_at"]
    assert draft["categories"] == [
        {"name": "Best use of Gemini API", "prize": "Swag kits", "market_id": "gemini", "create_market": None},
        {"name": "Best use of Snowflake", "prize": None, "market_id": None, "create_market": None},
    ]
    assert draft["is_sample"] is False and draft["source_url"] == EVENT_URL


def test_a_failed_read_returns_an_empty_draft_not_sample_data(client, scout_keys, monkeypatch):
    async def extract_event(url):
        raise RuntimeError("Nimble is down")

    monkeypatch.setattr(pipeline, "extract_event", extract_event)
    draft = client.post("/api/events/extract", json={"url": EVENT_URL}).json()
    assert draft["name"] == "" and draft["categories"] == [] and draft["is_sample"] is False
    assert set(draft["missing"]) >= {"name", "location", "submissions_close_at", "categories"}


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


# ---- Launching an event -----------------------------------------------------


def in_an_hour() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def launch(client, **changes) -> dict:
    """Launch EVENT with these changes. Unless a deadline is given, submissions close in an hour,
    so sign-ups and bets are open whatever the time is when the tests run."""
    res = client.post("/api/events", json={**EVENT, "submissions_close_at": in_an_hour(), **changes}, headers=HOST)
    assert res.status_code == 201, res.text
    return res.json()


def join(client, name="Maya", event=None) -> dict:
    res = client.post("/api/users", json={"display_name": name, "event_slug": event})
    assert res.status_code == 201, res.text
    return res.json()


def sign_up(client, name, event):
    return client.post("/api/teams", json={"name": name, "idea": "An idea", "event_slug": event})


def close_submissions(db, event: str) -> None:
    """Move an event past its deadline: no more sign-ups or bets, and the host can pick winners."""
    db.execute("UPDATE events SET submissions_close_at = now() - interval '1 second' WHERE slug = %s", (event,))


def markets_of(client, event) -> list[dict]:
    return client.get("/api/markets", params={"event": event}).json()


def test_there_is_no_event_before_setup(client):
    assert client.get("/api/event").status_code == 404
    assert client.get("/api/events/ai-engineer-nyc-2026").status_code == 404
    assert client.get("/api/host/summary", params={"event": "nope"}, headers=HOST).status_code == 404


def test_launch_saves_the_event_and_opens_its_markets(client):
    saved = launch(client, submissions_close_at=EVENT["submissions_close_at"])
    assert saved["slug"] == "ai-engineer-nyc-2026"
    assert saved["submissions_close_at"] in ("2026-10-11T23:59:00-04:00", "2026-10-12T03:59:00Z")
    assert client.get("/api/events/ai-engineer-nyc-2026").json() == saved
    assert client.get("/api/event").json() == saved  # the first event
    # A market for the category that asked for one, and none for the other.
    assert [(c["name"], c["create_market"]) for c in saved["categories"]] == [
        ("Best overall", True), ("Best use of Snowflake", False),
    ]
    assert [(m["id"], m["title"], m["score_key"], m["status"]) for m in markets_of(client, saved["slug"])] == [
        ("ai-engineer-nyc-2026--best-overall", "Who wins Best overall?", "overall", "open"),
    ]
    market = client.get("/api/markets/ai-engineer-nyc-2026--best-overall").json()
    assert market["teams"] == [] and market["event_slug"] == saved["slug"]


def test_the_host_decides_which_categories_get_a_market(client):
    categories = [
        {"name": "Best design", "create_market": True},  # no Scout score of its own: priced by the overall score
        {"name": "Best use of Gemini API", "prize": "Swag", "create_market": True},
        {"name": "Best overall", "market_id": "overall", "create_market": False},
        {"name": "Best Design!", "create_market": True},  # boils down to the same id as the first
    ]
    event = launch(client, name="Design Jam", categories=categories)
    assert [(m["id"], m["category"], m["score_key"]) for m in markets_of(client, event["slug"])] == [
        ("design-jam--best-design", "Best design", "overall"),
        ("design-jam--best-use-of-gemini-api", "Best use of Gemini API", "gemini"),
        ("design-jam--best-design-2", "Best Design!", "overall"),
    ]


def test_every_launch_is_its_own_event(client, db):
    first = launch(client, starting_balance=500)
    second = launch(client, starting_balance=2000)
    assert (first["slug"], second["slug"]) == ("ai-engineer-nyc-2026", "ai-engineer-nyc-2026-2")
    assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 2
    assert client.get(f"/api/events/{first['slug']}").json()["starting_balance"] == 500
    assert markets_of(client, first["slug"])[0]["id"] != markets_of(client, second["slug"])[0]["id"]
    # Each event hands out its own starting amount.
    assert join(client, "Maya", first["slug"])["balance"] == 500
    assert join(client, "Maya", second["slug"])["balance"] == 2000


def test_events_do_not_share_teams_players_or_markets(client):
    alpha, beta = launch(client, name="Alpha Hack"), launch(client, name="Beta Hack")
    a, b = alpha["slug"], beta["slug"]
    a_market, b_market = markets_of(client, a)[0]["id"], markets_of(client, b)[0]["id"]

    owls = sign_up(client, "Night Owls", a).json()
    assert owls["event_slug"] == a
    assert [t["id"] for t in client.get("/api/teams", params={"event": a}).json()] == ["night-owls"]
    assert client.get("/api/teams", params={"event": b}).json() == []
    assert [t["team_id"] for t in client.get(f"/api/markets/{a_market}").json()["teams"]] == ["night-owls"]
    assert client.get(f"/api/markets/{b_market}").json()["teams"] == []
    assert client.get("/api/markets/overall").json()["totals"]["team_count"] == 6  # the fixture's market

    # The same team name is free in another event, and taken in its own.
    assert sign_up(client, "Night Owls", a).status_code == 400
    other_owls = sign_up(client, "Night Owls", b)
    assert other_owls.status_code == 201 and other_owls.json()["id"] == "night-owls-2"

    # A player belongs to the event they joined: their Hackcoin can't be staked anywhere else.
    maya = join(client, "Maya", a)
    assert maya["event_slug"] == a
    elsewhere = client.post("/api/bets", json={"user_id": maya["id"], "market_id": b_market, "team_id": "night-owls-2", "stake": 10})
    assert elsewhere.status_code == 400 and "different event" in elsewhere.json()["detail"]
    here = client.post("/api/bets", json={"user_id": maya["id"], "market_id": a_market, "team_id": "night-owls", "stake": 10})
    assert here.status_code == 200

    assert [e["display_name"] for e in client.get("/api/leaderboard", params={"event": a}).json()] == ["Maya"]
    assert client.get("/api/leaderboard", params={"event": b}).json() == []

    in_a = client.get("/api/host/summary", params={"event": a}, headers=HOST).json()
    in_b = client.get("/api/host/summary", params={"event": b}, headers=HOST).json()
    assert (in_a["attendees"], in_a["teams"], in_a["bets"], in_a["hackcoin_traded"]) == (1, 1, 1, 10)
    assert (in_b["attendees"], in_b["teams"], in_b["bets"], in_b["hackcoin_traded"]) == (0, 1, 0, 0)
    assert [m["id"] for m in in_a["markets"]] == [a_market] and in_a["markets"][0]["staked"] == 10
    assert [f["display_name"] for f in in_a["top_forecasters"]] == ["Maya"] and in_b["top_forecasters"] == []


def test_launching_needs_the_host_password_a_name_and_a_market(client):
    assert client.post("/api/events", json=EVENT).status_code == 401
    assert client.post("/api/events", json=EVENT, headers={"X-Host-Password": "wrong"}).status_code == 401
    assert client.post("/api/events", json={**EVENT, "name": ""}, headers=HOST).status_code == 422
    bad_market = {**EVENT, "categories": [{"name": "Best pizza", "market_id": "pizza"}]}
    assert client.post("/api/events", json=bad_market, headers=HOST).status_code == 422
    for categories in ([], [{"name": "Best overall", "market_id": "overall", "create_market": False}]):
        no_market = client.post("/api/events", json={**EVENT, "categories": categories}, headers=HOST)
        assert no_market.status_code == 400 and "at least one" in no_market.json()["detail"]
    for missing in ({**EVENT, "submissions_close_at": None}, {k: v for k, v in EVENT.items() if k != "submissions_close_at"}):
        no_deadline = client.post("/api/events", json=missing, headers=HOST)
        assert no_deadline.status_code == 400 and "when submissions close" in no_deadline.json()["detail"]
    assert client.get("/api/event").status_code == 404


def test_joining_or_signing_up_for_an_unknown_event_is_refused(client):
    assert client.post("/api/users", json={"display_name": "Maya", "event_slug": "nope"}).status_code == 400
    assert sign_up(client, "Night Owls", "nope").status_code == 400


# ---- The submission deadline: bets before it, winners after it ---------------


def test_betting_closes_and_winner_picking_opens_at_the_submission_deadline(client, db):
    event = launch(client)
    market_id = markets_of(client, event["slug"])[0]["id"]
    sign_up(client, "Night Owls", event["slug"])
    user = join(client, event=event["slug"])
    bet = {"user_id": user["id"], "market_id": market_id, "team_id": "night-owls", "stake": 10}
    pick_winner = lambda: client.post(f"/api/markets/{market_id}/resolve", json={"winner_team_id": "night-owls"}, headers=HOST)  # noqa: E731

    # Before the deadline: bets are taken, and the host can't close the market yet.
    assert client.post("/api/bets", json=bet).status_code == 200
    too_early = pick_winner()
    assert too_early.status_code == 400 and "still open" in too_early.json()["detail"]
    assert client.get(f"/api/markets/{market_id}").json()["status"] == "open"

    close_submissions(db, event["slug"])

    # After it: no more bets, and the host can pick the winner.
    too_late = client.post("/api/bets", json=bet)
    assert too_late.status_code == 400 and "submissions have closed" in too_late.json()["detail"]
    assert client.get(f"/api/users/{user['id']}").json()["balance"] == 990  # only the first bet was taken
    assert pick_winner().status_code == 200


def test_team_sign_up_closes_at_the_submission_deadline(client, db):
    event = launch(client)
    market_id = markets_of(client, event["slug"])[0]["id"]
    assert sign_up(client, "Night Owls", event["slug"]).status_code == 201
    close_submissions(db, event["slug"])
    late = sign_up(client, "Late Entry", event["slug"])
    assert late.status_code == 400 and "sign-up is closed" in late.json()["detail"]
    assert [t["team_id"] for t in client.get(f"/api/markets/{market_id}").json()["teams"]] == ["night-owls"]
    # Another event that is still open is not affected.
    other = launch(client, name="Still Open")
    assert sign_up(client, "Late Entry", other["slug"]).status_code == 201


# ---- One team per player ----------------------------------------------------


def test_a_player_can_sign_up_one_team_per_event(client):
    event = launch(client)
    maya, dev = join(client, "Maya", event["slug"]), join(client, "Dev", event["slug"])
    as_maya = {"idea": "An idea", "event_slug": event["slug"], "creator_user_id": maya["id"]}
    assert client.post("/api/teams", json={**as_maya, "name": "Night Owls"}).status_code == 201
    second = client.post("/api/teams", json={**as_maya, "name": "Early Birds"})
    assert second.status_code == 400 and "already signed up a team" in second.json()["detail"]
    # Someone else can still add theirs.
    assert client.post("/api/teams", json={**as_maya, "name": "Early Birds", "creator_user_id": dev["id"]}).status_code == 201
    assert [t["name"] for t in client.get("/api/teams", params={"event": event["slug"]}).json()] == ["Night Owls", "Early Birds"]


# ---- Starting balance: the host's choice, per event --------------------------


def test_starting_balance_defaults_to_1000(client):
    event = launch(client)
    assert event["starting_balance"] == 1000
    assert join(client, "In the event", event["slug"])["balance"] == 1000


def test_the_host_chooses_the_starting_balance(client):
    event = launch(client, starting_balance=500)
    sign_up(client, "Night Owls", event["slug"])
    user = join(client, event=event["slug"])
    assert user["balance"] == 500
    # The whole amount is theirs to stake, and no more than that.
    bet = {"user_id": user["id"], "market_id": markets_of(client, event["slug"])[0]["id"], "team_id": "night-owls"}
    assert client.post("/api/bets", json={**bet, "stake": 501}).status_code == 400
    assert client.post("/api/bets", json={**bet, "stake": 500}).json()["new_balance"] == 0


def test_net_profit_does_not_assume_a_1000_start(client, db):
    event = launch(client, starting_balance=500)
    market_id = markets_of(client, event["slug"])[0]["id"]
    sign_up(client, "Night Owls", event["slug"])
    sign_up(client, "Early Birds", event["slug"])
    user = join(client, event=event["slug"])
    summary = lambda: client.get(f"/api/users/{user['id']}/summary").json()  # noqa: E731
    assert summary()["net_profit"] == 0  # not -500
    bet = client.post("/api/bets", json={"user_id": user["id"], "market_id": market_id, "team_id": "night-owls", "stake": 100}).json()
    assert bet["multiple"] == pytest.approx(2)  # two teams, neither seeded yet
    assert summary()["net_profit"] == -100
    close_submissions(db, event["slug"])
    client.post(f"/api/markets/{market_id}/resolve", json={"winner_team_id": "night-owls"}, headers=HOST)
    after = summary()
    assert after["net_profit"] == pytest.approx(100) and after["rank"] == 1
    assert after["user"]["balance"] == pytest.approx(600)


@pytest.mark.parametrize("amount", [0, -100, 1_000_001, 12.5, "lots"])
def test_starting_balance_must_be_a_sensible_whole_number(client, amount):
    assert client.post("/api/events", json={**EVENT, "starting_balance": amount}, headers=HOST).status_code == 422
    assert client.get("/api/event").status_code == 404


# ---- Scout prices each event on its own -------------------------------------


def save_report(db, team_id, **scores):
    body = sample_data.team_report("orbit").report.model_dump(mode="json")
    body["team_id"] = team_id
    body["scores"].update(scores)
    db.execute("INSERT INTO reports (team_id, body) VALUES (%s, %s)", (team_id, Jsonb(body)))


def test_scout_prices_a_market_from_its_own_events_teams(client, db, call):
    categories = [
        {"name": "Best use of Gemini", "create_market": True},
        {"name": "Best design", "create_market": True},
    ]
    event = launch(client, name="Alpha Hack", categories=categories)
    gemini_market, design_market = (m["id"] for m in markets_of(client, event["slug"]))
    sign_up(client, "Night Owls", event["slug"])
    sign_up(client, "Early Birds", event["slug"])
    save_report(db, "night-owls", overall=75, gemini=100)
    save_report(db, "orbit", overall=100)  # a team in another event must not move this one
    call(pipeline.reprice_markets)

    odds = lambda market_id: {t["team_id"]: t["scout_odds"] for t in client.get(f"/api/markets/{market_id}").json()["teams"]}  # noqa: E731
    # Early Birds has no report yet, so it counts as a neutral 50. The seed is split to the cent, hence abs.
    assert odds(gemini_market) == pytest.approx({"night-owls": 100 / 150, "early-birds": 50 / 150}, abs=1e-4)
    assert odds(design_market) == pytest.approx({"night-owls": 75 / 125, "early-birds": 50 / 125}, abs=1e-4)  # the overall score
    assert set(odds("overall")) == set(sample_data.TEAMS_BY_ID)  # the fixture's market has only its own teams
    assert odds("overall")["orbit"] == pytest.approx(100 / 350, abs=1e-4)

    history = client.get("/api/teams/night-owls/report").json()["odds_history"]
    assert {p["market_id"]: p["odds"] for p in history}["gemini"] == pytest.approx(100 / 150, abs=1e-4)


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
