"""Test setup: every test runs against a throwaway local database, never the shared one.

Tests create users and bets and wipe every table between runs. backend/.env usually points at
Tiger Cloud, so this file swaps DATABASE_URL for a local `oddsmaker_test` database before the
app loads, and refuses to run at all if that URL is not on this machine.

Needs the Docker database from `make db` (or `docker compose up -d db`). Without it, the
database tests are skipped and only the pure tests run.
"""

import os
from urllib.parse import urlparse

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://oddsmaker:oddsmaker@localhost:5432/oddsmaker_test"
)
if urlparse(TEST_DATABASE_URL).hostname not in ("localhost", "127.0.0.1"):
    pytest.exit("Refusing to run tests: TEST_DATABASE_URL must point at a database on localhost.", returncode=2)

# Set before anything imports app.config, so the app under test can only ever see the test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["HOST_PASSWORD"] = "test-host-password"
os.environ["SCOUT_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app import sample_data  # noqa: E402
from app.config import REPO_ROOT  # noqa: E402
from app.main import app  # noqa: E402
from scripts.init_db import statements  # noqa: E402

# The build spec's worked example: Orbit holds 540 of the 2,000 seed in the overall market.
OVERALL_SEED = {"orbit": 540, "ledger": 500, "parsel": 400, "night": 260, "kiln": 200, "tally": 100}


@pytest.fixture(scope="session")
def _database():
    """Create the test database if needed and apply the schema. Skips database tests if Postgres is down."""
    name = psycopg.conninfo.conninfo_to_dict(TEST_DATABASE_URL)["dbname"]
    try:
        with psycopg.connect(make_conninfo(TEST_DATABASE_URL, dbname="postgres"), autocommit=True, connect_timeout=3) as admin:
            if not admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
                admin.execute(f'CREATE DATABASE "{name}"')
    except psycopg.OperationalError as e:
        pytest.skip(f"Local Postgres is not reachable, so database tests are skipped. Run `make db`. ({e})")
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        for statement in statements((REPO_ROOT / "db" / "schema.sql").read_text()):
            conn.execute(statement)


@pytest.fixture(scope="session")
def _client(_database):
    # One client for the whole run: entering it starts the app and opens its connection pool.
    with TestClient(app) as client:
        yield client


@pytest.fixture
def db(_database):
    """A direct connection to a freshly wiped and seeded test database, for setup and assertions."""
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE bets, reports, price_ticks, positions, users, markets, teams RESTART IDENTITY CASCADE")
        for m in sample_data.MARKETS:
            conn.execute("INSERT INTO markets (id, title, category) VALUES (%s, %s, %s)", (m.id, m.title, m.category))
        for t in sample_data.TEAMS:
            conn.execute(
                "INSERT INTO teams (id, name, idea, repo_url, demo_url, color) VALUES (%s, %s, %s, %s, %s, %s)",
                (t.id, t.name, t.idea, t.repo_url, t.demo_url, t.color),
            )
        for m in sample_data.MARKETS:
            for t in sample_data.TEAMS:
                seed = OVERALL_SEED[t.id] if m.id == "overall" else 2000 / len(sample_data.TEAMS)
                conn.execute("INSERT INTO positions (market_id, team_id, seed) VALUES (%s, %s, %s)", (m.id, t.id, seed))
        yield conn


@pytest.fixture
def client(_client, db):
    """The API, on a freshly seeded database."""
    return _client
