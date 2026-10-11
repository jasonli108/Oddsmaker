-- Oddsmaker schema for Tiger Data (TimescaleDB).
-- Idempotent: safe to re-run. Apply with `make db-init` (backend/scripts/init_db.py).
-- Prices and odds are stored as fractions between 0 and 1 (0.27 = 27%).

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS teams (
    id          TEXT PRIMARY KEY,                -- slug, e.g. 'orbit'
    name        TEXT NOT NULL UNIQUE,
    idea        TEXT NOT NULL,
    repo_url    TEXT,
    demo_url    TEXT,
    color       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS markets (
    id              TEXT PRIMARY KEY,            -- 'overall' | 'nimble' | 'gemini' | 'tiger_data'; same keys as Scout's scores
    title           TEXT NOT NULL,               -- the question, e.g. 'Who takes 1st place overall?'
    category        TEXT NOT NULL,               -- the prize, e.g. 'Best overall'
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    winner_team_id  TEXT REFERENCES teams (id)
);

CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name  TEXT NOT NULL,
    balance       NUMERIC(12, 2) NOT NULL DEFAULT 1000 CHECK (balance >= 0),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The weights. A team's price is (seed + staked) / sum(seed + staked) over its market.
CREATE TABLE IF NOT EXISTS positions (
    market_id  TEXT NOT NULL REFERENCES markets (id),
    team_id    TEXT NOT NULL REFERENCES teams (id),
    seed       NUMERIC(12, 2) NOT NULL DEFAULT 0,
    staked     NUMERIC(12, 2) NOT NULL DEFAULT 0,
    PRIMARY KEY (market_id, team_id)
);

CREATE TABLE IF NOT EXISTS bets (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users (id),
    market_id     TEXT NOT NULL REFERENCES markets (id),
    team_id       TEXT NOT NULL REFERENCES teams (id),
    stake         NUMERIC(12, 2) NOT NULL CHECK (stake > 0),
    price_at_bet  DOUBLE PRECISION NOT NULL,
    multiple      DOUBLE PRECISION NOT NULL,     -- locked at bet time, never recomputed
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bets_market_created_idx ON bets (market_id, created_at DESC);
CREATE INDEX IF NOT EXISTS bets_user_idx ON bets (user_id);

CREATE TABLE IF NOT EXISTS reports (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    team_id     TEXT NOT NULL REFERENCES teams (id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    body        JSONB NOT NULL,                  -- the Gemini output, see ScoutReport in backend/app/schemas.py
    stale       BOOLEAN NOT NULL DEFAULT FALSE   -- true when a fetch failed and the last report was reused
);
CREATE INDEX IF NOT EXISTS reports_team_created_idx ON reports (team_id, created_at DESC);

-- The only time-series table: one row per team per market every time a price changes.
CREATE TABLE IF NOT EXISTS price_ticks (
    time       TIMESTAMPTZ NOT NULL DEFAULT now(),
    market_id  TEXT NOT NULL REFERENCES markets (id),
    team_id    TEXT NOT NULL REFERENCES teams (id),
    price      DOUBLE PRECISION NOT NULL,
    source     TEXT NOT NULL CHECK (source IN ('bet', 'scout'))
);
SELECT create_hypertable('price_ticks', by_range('time'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS price_ticks_market_team_time_idx ON price_ticks (market_id, team_id, time DESC);

-- Price chart source: last price per team per minute. GET /markets/:id/history reads this, not raw ticks.
CREATE MATERIALIZED VIEW IF NOT EXISTS price_ticks_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 minute', time) AS bucket,
    market_id,
    team_id,
    last(price, time) AS price
FROM price_ticks
GROUP BY bucket, market_id, team_id
WITH NO DATA;

-- Real-time aggregation: include ticks newer than the last materialisation so the chart is live.
ALTER MATERIALIZED VIEW price_ticks_1m SET (timescaledb.materialized_only = false);

SELECT add_continuous_aggregate_policy(
    'price_ticks_1m',
    start_offset      => INTERVAL '1 hour',
    end_offset        => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists     => TRUE
);
