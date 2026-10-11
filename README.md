# Oddsmaker

A play-money prediction market for hackathons. Attendees bet Hackcoin on which team wins each prize, and an AI scout publishes a report on every team and sets the odds. **Play money only: no real money anywhere.**

The full plan is in [`brainstorming/Oddsmaker build spec.md`](brainstorming/Oddsmaker%20build%20spec.md). The Markets tab design is the HTML file next to it.

## Where the sponsor tools are used

| Tool | Job | Code |
| --- | --- | --- |
| **Nimble** | Searches the web and past hackathon galleries for the same idea, extracts each team's live demo page, reads the event page and past winners | `backend/app/scout/nimble.py` |
| **Gemini** | Reads that evidence plus a screenshot of the demo and returns a structured report and a score per prize | `backend/app/scout/gemini.py` |
| **Tiger Data** | The only database. `price_ticks` is a hypertable, and the price chart reads a continuous aggregate over it | `db/schema.sql` |

## Status

This is the skeleton. Every endpoint answers with **sample data** in its final shape, the database schema is real, and the frontend's four tabs are wired to the API. Nothing is persisted yet: placing a bet returns a receipt but does not move the price.

## Layout

```
backend/            FastAPI
  app/schemas.py      the API contract (single source of truth)
  app/routers/        thin HTTP layer, no logic
  app/market/         prices, bets, resolution, teams, users   -> stream A
  app/scout/          Nimble, GitHub, Gemini, the 30-minute timer -> stream C
  app/sample_data.py  what the mock endpoints return; delete when nothing imports it
  scripts/            init_db, seed, export_openapi
  tests/
frontend/           Vite + React + TypeScript                   -> stream B
  src/api/            client.ts, types.ts, schema.d.ts (generated, don't edit)
  src/pages/          Markets, Scout reports, Leaderboard, Sign up
  src/components/
db/schema.sql       seven tables, hypertable, continuous aggregate
docker-compose.yml  local TimescaleDB
```

## Run it

Needs Python 3.11+, Node 20+, and Docker for the local database.

```bash
make setup      # venv, pip install, npm install, creates backend/.env
make db         # start local TimescaleDB, apply schema, seed 4 markets and 6 sample teams
make backend    # http://localhost:8000  (interactive docs at /docs)
make frontend   # http://localhost:5173  (proxies /api to the backend)
make test       # backend tests and frontend typecheck
```

The API runs without a database while the endpoints are mocked, so `make db` is optional for frontend work. To use Tiger Cloud instead of Docker, put its connection string in `DATABASE_URL` in `backend/.env` and run `make db-init db-seed`.

API keys go in `backend/.env` (never committed). See `backend/.env.example` for every setting.

## API

All routes are under `/api`. Shapes are defined in `backend/app/schemas.py`.

| Endpoint | Used by | Does |
| --- | --- | --- |
| `GET /markets` | Category pills | Lists the four markets |
| `GET /markets/:id` | Markets tab | Teams with price, multiple, Scout's odds, plus totals |
| `GET /markets/:id/history` | Price chart | Per-minute prices from the continuous aggregate |
| `GET /markets/:id/feed` | Latest trades | Last 20 bets and Scout moves, newest first |
| `POST /bets` | Bet slip | Places the bet, returns the locked multiple and new balance |
| `POST /markets/:id/resolve` | Host only | Sets the winner and pays out. Needs the `X-Host-Password` header |
| `GET /teams` | Scout reports tab | Lists teams |
| `POST /teams` | Sign-up form | Creates the team, starts Scout's first run |
| `GET /teams/:id/report` | Scout summary, Scout reports tab | Latest report plus the history of Scout's odds |
| `POST /users`, `GET /users/:id` | Header | Display name in, user with a 1,000 Hackcoin balance out |
| `GET /leaderboard` | Leaderboard tab | Users ranked by balance |
| `GET /health` | | Reports whether the database is connected |

**Conventions**

- Prices and odds are fractions from 0 to 1 (`0.27` is 27%). The frontend formats them.
- A payout multiple is `1 / price` at the moment of the bet. It is stored, never recomputed.
- Market ids are `overall`, `nimble`, `gemini`, `tiger_data`, the same keys as Scout's `scores`.
- Polling every 5 seconds, no websockets.

## Three workstreams

Each stream owns its folder, so branches rarely touch the same file.

| Stream | Owns | Start with | Done when |
| --- | --- | --- | --- |
| **A. Market and Tiger Data** | `backend/app/market/`, `db/`, `backend/scripts/` | `pricing.py`: make the four `xfail` tests in `tests/test_pricing.py` pass. Then replace each mock in `service.py` with real queries, `place_bet` first | A bet from `curl` moves the price and the balance, and `/history` reads the continuous aggregate |
| **B. Frontend** | `frontend/` | `components/PriceChart.tsx` is a placeholder. Then polish each component against the design | You can place a bet in the browser and see it in the feed and on the chart |
| **C. Scout** | `backend/app/scout/` | One real Nimble search, one Nimble extract and one Gemini JSON call. Then `pipeline.py` top to bottom | One team gets a full report and its price moves |

**Where streams meet**

- `backend/app/schemas.py` is the contract. If you change it, run `make types`, commit the regenerated `frontend/src/api/schema.d.ts`, and tell the others.
- Scout hands odds to the market through one function, `market.service.apply_scout_odds`. Stream A implements it; stream C calls it. Scout never writes to `positions` or `price_ticks` directly.
- Search the code for `TODO(market)`, `TODO(frontend)` and `TODO(scout)` to find what's left.

**Working together**

- Branch from `main`, keep pull requests small, merge often.
- `make test` before you push.
