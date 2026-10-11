"""The sample event's canned Scout reports (scripts/sample_reports.py)."""

from app import sample_data
from app.market import pricing
from app.schemas import Team
from scripts.sample_reports import sample_report


def test_every_sample_team_has_a_report_marked_as_a_sample():
    for team in sample_data.TEAMS:
        report = sample_report(team)
        assert report.team_id == team.id
        assert report.read.startswith("Sample report.") and "Sample report" in report.change_note
        assert (report.demo.label == "Missing") == (team.demo_url is None)
        assert report.originality.similar == []  # a made-up link would be reused by a real Scout run
        assert [s.kind for s in report.sources] == ["repo", "demo"][: 1 + bool(team.demo_url)]


def test_only_the_sample_teams_get_one():
    assert sample_report(Team(id="night-owls", name="Night Owls", idea="x", color="#fff")) is None


def test_sample_scores_give_each_market_a_different_favourite():
    scores = {t.id: sample_report(t).scores for t in sample_data.TEAMS}
    favourite = {}
    for market_id in ("overall", "nimble", "gemini", "tiger_data"):
        odds = pricing.odds_from_scores({team: getattr(s, market_id) for team, s in scores.items()})
        favourite[market_id] = max(odds, key=odds.get)
    assert favourite == {"overall": "ledger", "nimble": "orbit", "gemini": "parsel", "tiger_data": "kiln"}
