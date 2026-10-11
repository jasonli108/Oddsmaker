"""Seed the four markets and the six sample teams. Safe to re-run.

    cd backend && .venv/bin/python -m scripts.seed

Every team starts with an even share of each market's seed. Scout's first run replaces that
split with its own odds. Each market also gets one opening price tick per team, so the price
chart has a line from the start instead of staying empty until the first bet.
"""

import sys

import psycopg

from app import sample_data
from app.config import get_settings
from app.market import pricing


def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        sys.exit("DATABASE_URL is not set. Copy backend/.env.example to backend/.env first.")
    seed_each = settings.seed_per_market / len(sample_data.TEAMS)
    with psycopg.connect(settings.database_url) as conn:
        for m in sample_data.MARKETS:
            conn.execute(
                "INSERT INTO markets (id, title, category) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (m.id, m.title, m.category),
            )
        for t in sample_data.TEAMS:
            conn.execute(
                "INSERT INTO teams (id, name, idea, repo_url, demo_url, color) VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                (t.id, t.name, t.idea, t.repo_url, t.demo_url, t.color),
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
    print(f"Seeded {len(sample_data.MARKETS)} markets and {len(sample_data.TEAMS)} teams.")


if __name__ == "__main__":
    main()
