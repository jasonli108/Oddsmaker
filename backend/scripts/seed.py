"""Seed a sample event with four markets and six sample teams. Safe to re-run.

    cd backend && .venv/bin/python -m scripts.seed

The sample event is the deployment's first event (id 1), which the landing page links to as
"See a live market". If a first event already exists, the sample markets and teams join it, and
so does any market, team or player saved before events were separate. Events that hosts launch
are untouched.

Every team starts with an even share of each market's seed. Scout's first run replaces that
split with its own odds. Each market also gets one opening price tick per team, so the price
chart has a line from the start instead of staying empty until the first bet.
"""

import sys

import psycopg
from psycopg.types.json import Jsonb

from app import sample_data
from app.config import get_settings
from app.market import pricing


SAMPLE_EVENT_SLUG = "ai-engineer-nyc-2026"
SAMPLE_EVENT_NAME = "AI Engineer NYC 2026"


def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        sys.exit("DATABASE_URL is not set. Copy backend/.env.example to backend/.env first.")
    seed_each = settings.seed_per_market / len(sample_data.TEAMS)
    with psycopg.connect(settings.database_url) as conn:
        categories = [{"name": m.category, "prize": None, "market_id": m.id, "create_market": True} for m in sample_data.MARKETS]
        conn.execute(
            "INSERT INTO events (id, slug, name, categories, starting_balance) VALUES (1, %s, %s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (SAMPLE_EVENT_SLUG, SAMPLE_EVENT_NAME, Jsonb(categories), settings.starting_balance),
        )
        first = conn.execute("SELECT slug FROM events WHERE id = 1").fetchone()
        if first is None:
            sys.exit(f"A host has already launched an event called '{SAMPLE_EVENT_SLUG}', so the sample event can't be added.")
        event = first[0]
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
    print(f"Seeded {len(sample_data.MARKETS)} markets and {len(sample_data.TEAMS)} teams in the event '{event}'.")


if __name__ == "__main__":
    main()
