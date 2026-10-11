"""Scout reports for the six sample teams, so the sample event has reports and uneven odds.

Canned text, not a Scout run: every one opens with "Sample report." so nobody reading it takes
it for Scout's work. The sample teams' links are made up, so Scout could not read them anyway.
Scores are in Scout's four categories; a team's odds in a market are its score over the total
of every team's score, which is how scout.pipeline.reprice_markets sets them.
"""

from app.schemas import OriginalitySection, ReportSection, ReportSource, ScoutReport, ScoutScores, Team

CHANGE_NOTE = "Sample report, seeded for the demo. Not from a live Scout run."

# team id -> read, originality, build, demo, prize fit (each a label and a finding), then scores.
# Labels are the ones Scout uses (frontend/src/scout.ts colours them).
_REPORTS = {
    "orbit": (
        "A focused tool with a working demo: it checks a vendor against public records before an invoice is paid. "
        "The idea has competitors, but the build is ahead of most of the room.",
        ("Some overlap", "Vendor-verification tools exist, but few sit inside the invoice step."),
        ("On pace", "Steady commits through the day, with the main flow working end to end."),
        ("Live", "The demo loads and runs the check on a sample invoice."),
        ("Strong", "Web lookups are the core of the product, a good fit for the Nimble prize."),
        ScoutScores(overall=54, nimble=60, gemini=44, tiger_data=20),
    ),
    "ledger": (
        "The most complete project so far: it generates plausible financial statements for private startups and "
        "shows them in a clean dashboard. Strong on execution, less so on novelty.",
        ("Some overlap", "Synthetic-data generators are common; applying one to startup financials is less so."),
        ("On pace", "Frequent commits from the whole team, with generation and the dashboard both in place."),
        ("Live", "The demo loads quickly and produces a full set of statements."),
        ("Strong", "A contender for the overall prize, and it leans on web data for its benchmarks."),
        ScoutScores(overall=58, nimble=56, gemini=24, tiger_data=36),
    ),
    "parsel": (
        "Photograph a receipt and it files a price-drop refund claim for you. The image reading is the clever "
        "part and it works in the demo; the claim filing is still a mock-up.",
        ("Fresh", "No close match turned up for refund claims driven by a receipt photo."),
        ("Slowing", "A fast start, then few commits in the last hour."),
        ("Live", "The demo reads a receipt photo; submitting the claim is not wired up yet."),
        ("Strong", "Reading receipts from a photo makes it a strong fit for the Gemini prize."),
        ScoutScores(overall=32, nimble=18, gemini=72, tiger_data=20),
    ),
    "night": (
        "An agent that sorts on-call alerts overnight so only the urgent ones wake someone. A useful idea in a "
        "busy field, with no demo to judge yet.",
        ("Crowded", "Several alert-triage and on-call products already do this."),
        ("Slowing", "The repo has the alert intake working; little has landed since."),
        ("Missing", "No demo link was submitted."),
        ("Fair", "Could suit the Gemini prize if the triage step is shown working."),
        ScoutScores(overall=26, nimble=14, gemini=24, tiger_data=16),
    ),
    "kiln": (
        "Builds a personal inflation index from the prices of what you actually buy. A small project with a "
        "clear idea, and the one that makes the most of time-series data.",
        ("Some overlap", "Personal inflation calculators exist, mostly without a live price history."),
        ("On pace", "Regular commits, with price history and the index chart both working."),
        ("Live", "The demo loads and charts an index for a sample basket."),
        ("Strong", "Price history over time is the product, a strong fit for the Tiger Data prize."),
        ScoutScores(overall=20, nimble=12, gemini=20, tiger_data=92),
    ),
    "tally": (
        "Keeps a track record of financial pundits' predictions. The data gathering is under way, but there is "
        "little to show for it yet.",
        ("Crowded", "Prediction trackers for pundits and forecasters have been built several times."),
        ("Stalled", "A handful of early commits and none recently."),
        ("Missing", "No demo link was submitted."),
        ("Fair", "Collecting predictions from the web suits the Nimble prize, if it gets that far."),
        ScoutScores(overall=10, nimble=40, gemini=16, tiger_data=16),
    ),
}


def sample_report(team: Team) -> ScoutReport | None:
    """The sample report for one of the six sample teams, or None for any other team."""
    if team.id not in _REPORTS:
        return None
    read, originality, build, demo, prize_fit, scores = _REPORTS[team.id]
    return ScoutReport(
        team_id=team.id,
        read=f"Sample report. {read}",
        # No similar projects listed: a made-up link here would be reused by a later real Scout run.
        originality=OriginalitySection(label=originality[0], finding=originality[1]),
        build=ReportSection(label=build[0], finding=build[1]),
        demo=ReportSection(label=demo[0], finding=demo[1]),
        prize_fit=ReportSection(label=prize_fit[0], finding=prize_fit[1]),
        scores=scores,
        change_note=CHANGE_NOTE,
        sources=[ReportSource(url=u, kind=k) for u, k in ((team.repo_url, "repo"), (team.demo_url, "demo")) if u],
    )
