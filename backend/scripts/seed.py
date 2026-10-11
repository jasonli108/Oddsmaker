"""Seed the sample event, set up for a demo: four markets, six sample teams, a report on each. Safe to re-run.

    cd backend && .venv/bin/python -m scripts.seed                  # make db-seed
    cd backend && .venv/bin/python -m scripts.seed --closes-in 15   # make db-seed CLOSES_IN=15

The sample event is the deployment's first event (id 1), which the landing page links to as
"See a live market". If a first event already exists, the sample markets and teams join it, and
so does any market, team or player saved before events were separate. Events that hosts launch
are untouched.

Its submissions close a few minutes after it is seeded (DEFAULT_CLOSES_IN), so one demo can show
team sign-up and betting, then both closing, then the host picking winners. Seeding again leaves
that deadline alone; --closes-in MINUTES restarts the clock. It does not reopen a market whose
winner has been picked.

Every sample team gets a sample Scout report (scripts/sample_reports.py) unless it already has a
report, and the odds are then set from the reports the way Scout sets them, so prices differ from
team to team. Each market also gets one opening price tick per team, so the price chart has a
line from the start instead of staying empty until the first bet.
"""

import argparse
import asyncio
import sys

import psycopg
from psycopg.types.json import Jsonb

from app import db, sample_data
from app.config import get_settings
from app.events import sample as sample_event
from app.market import pricing
from app.scout import pipeline
from scripts.sample_reports import sample_report

SAMPLE_EVENT_SLUG = "ai-engineer-nyc-2026"
# Minutes from seeding until the sample event's submissions close.
DEFAULT_CLOSES_IN = 15


def main(closes_in: int | None = None) -> None:
    settings = get_settings()
    if not settings.database_url:
        sys.exit("DATABASE_URL is not set. Copy backend/.env.example to backend/.env first.")
    seed_each = settings.seed_per_market / len(sample_data.TEAMS)
    # The same details the setup flow shows as its sample draft.
    details = sample_event.event_draft("")
    categories = Jsonb(
        [{**c.model_dump(), "create_market": c.market_id is not None} for c in details.categories]
    )
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            "INSERT INTO events (id, slug, name, hosted_by, location, categories, starting_balance) "
            "VALUES (1, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (SAMPLE_EVENT_SLUG, details.name, details.hosted_by, details.location, categories, settings.starting_balance),
        )
        first = conn.execute("SELECT slug FROM events WHERE id = 1").fetchone()
        if first is None:
            sys.exit(f"A host has already launched an event called '{SAMPLE_EVENT_SLUG}', so the sample event can't be added.")
        event = first[0]
        if event == SAMPLE_EVENT_SLUG:
            # Also for a sample event seeded before it had these details or a deadline.
            conn.execute(
                "UPDATE events SET hosted_by = %s, location = %s, categories = %s, "
                "submissions_close_at = coalesce(submissions_close_at, now() + make_interval(mins => %s)) WHERE id = 1",
                (details.hosted_by, details.location, categories, DEFAULT_CLOSES_IN),
            )
        if closes_in is not None:
            conn.execute(
                "UPDATE events SET submissions_close_at = now() + make_interval(mins => %s) WHERE id = 1", (closes_in,)
            )
        for table in ("markets", "teams", "users"):
            conn.execute(f"UPDATE {table} SET event_slug = %s WHERE event_slug IS NULL", (event,))
        for m in sample_data.MARKETS:
            conn.execute(
                "INSERT INTO markets (id, title, category, event_slug) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (m.id, m.title, m.category, event),
            )
        for t in sample_data.TEAMS:
            conn.execute(
                "INSERT INTO teams (id, name, idea, repo_url, demo_url, color, event_slug) VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                (t.id, t.name, t.idea, t.repo_url, t.demo_url, t.color, event),
            )
        for m in sample_data.MARKETS:
            for t in sample_data.TEAMS:
                conn.execute(
                    "INSERT INTO positions (market_id, team_id, seed) VALUES (%s, %s, %s) "
                    "ON CONFLICT (market_id, team_id) DO NOTHING",
                    (m.id, t.id, seed_each),
                )
        for m in sample_data.MARKETS:
            if conn.execute("SELECT 1 FROM price_ticks WHERE market_id = %s LIMIT 1", (m.id,)).fetchone():
                continue
            rows = conn.execute(
                "SELECT team_id, seed + staked FROM positions WHERE market_id = %s", (m.id,)
            ).fetchall()
            prices = pricing.prices_from_weights({team: float(w) for team, w in rows}, settings.price_floor)
            conn.cursor().executemany(
                "INSERT INTO price_ticks (market_id, team_id, price, source) VALUES (%s, %s, %s, 'scout')",
                [(m.id, team, price) for team, price in prices.items()],
            )
        # A sample report for each sample team that has none. A team Scout has reported on keeps its own.
        new_reports = 0
        for t in sample_data.TEAMS:
            if conn.execute("SELECT 1 FROM reports WHERE team_id = %s LIMIT 1", (t.id,)).fetchone():
                continue
            report = sample_report(t)
            conn.execute("INSERT INTO reports (team_id, body) VALUES (%s, %s)", (t.id, Jsonb(report.model_dump(mode="json"))))
            new_reports += 1
        closes_at, minutes_left = conn.execute(
            "SELECT submissions_close_at, ceil(extract(epoch FROM submissions_close_at - now()) / 60)::int "
            "FROM events WHERE id = 1"
        ).fetchone()
    if new_reports:
        asyncio.run(_set_odds_from_reports(event))

    print(f"Seeded {len(sample_data.MARKETS)} markets and {len(sample_data.TEAMS)} teams in the event '{event}'.")
    print(f"Sample Scout reports added: {new_reports}." + (" Odds are set from them." if new_reports else ""))
    restart = f"`make db-seed CLOSES_IN={DEFAULT_CLOSES_IN}`"
    if closes_at is None:
        print(f"This event has no submission deadline, so it never closes. Set one with {restart}.")
        return
    at = closes_at.astimezone().strftime("%H:%M on %b %d")  # this machine's time zone
    if minutes_left <= 0:
        print(f"Submissions closed at {at}: sign-up and betting are closed. Reopen them with {restart}.")
    else:
        print(f"Submissions close at {at}, in {minutes_left} minutes. Restart the clock with {restart}.")


async def _set_odds_from_reports(event: str) -> None:
    """Scout's own repricing step for this event, so the sample reports move the prices as a real run would."""
    await db.open_pool()
    try:
        await pipeline.reprice_markets(event)
    finally:
        await db.close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the sample event.")
    parser.add_argument(
        "--closes-in", type=int, metavar="MINUTES",
        help=f"set the event's submissions to close this many minutes from now (a new sample event gets {DEFAULT_CLOSES_IN})",
    )
    main(parser.parse_args().closes_in)
