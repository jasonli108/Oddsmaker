# Oddsmaker

A play-money prediction market for hackathons. Attendees bet Hackcoin on which team wins each prize, and an AI scout publishes a report on every team and sets the odds. **Play money only: no real money anywhere.**

The full plan is in [`brainstorming/Oddsmaker build spec.md`](brainstorming/Oddsmaker%20build%20spec.md). The Markets tab design is the HTML file next to it.

**New here?** Read this page, then [Team agreements](#team-agreements). If you work with Claude Code, [`CLAUDE.md`](CLAUDE.md) gives it the same rules.

## Where the sponsor tools are used

| Tool | Job | Code |
| --- | --- | --- |
| **Nimble** | Searches the web and past hackathon galleries for the same idea, extracts each team's live demo page, reads the event page and past winners | `backend/app/scout/nimble.py` |
| **Gemini** | Reads that evidence plus a screenshot of the demo and returns a structured report and a score per prize | `backend/app/scout/gemini.py` |
| **Tiger Data** | The only database. `price_ticks` is a hypertable, and the price chart reads a continuous aggregate over it | `db/schema.sql` |

## Status

The market is **real** end to end: sign-up, bets, prices, the price chart, the trade feed, resolving a market and the leaderboard all read and write Tiger Data. Scout reports still answer with **sample data** in their final shape, and Scout does not move prices yet; a newly signed-up team sits at the 2% floor until it does.

## Layout

```
backend/            FastAPI
  app/schemas.py      the API contract (single source of truth)
  app/routers/        thin HTTP layer, no logic
  app/market/         prices, bets, resolution, teams, users   -> stream A
  app/scout/          Nimble, GitHub, Gemini, the 30-minute timer -> stream C
  app/events/         the host flow: the event row and the host page's numbers
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

The API needs a database. `DATABASE_URL` in `backend/.env` decides which one: the local Docker database from `make db`, or Tiger Cloud. `make db-init` and `make db-seed` act on whichever it points at, so check it before you run them.

Tests never use `DATABASE_URL`. They create and wipe their own `oddsmaker_test` database in the local Docker Postgres, and refuse to run against anything that isn't on localhost. Without Docker running, the database tests are skipped.

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
| `POST /events/extract` | Host setup | Reads the host's event page into a draft to check. Sample data, marked as such, until Scout can read event pages |
| `GET /event`, `PUT /event` | Header, host setup | The one event this deployment runs. Saving needs `X-Host-Password` and never creates markets |
| `GET /host/summary` | Host page | Attendees, teams, bets, Hackcoin traded, a row per market, top five forecasters. Needs `X-Host-Password` |
| `GET /health` | | Reports whether the database is connected |

**Conventions**

- Prices and odds are fractions from 0 to 1 (`0.27` is 27%). The frontend formats them.
- A payout multiple is `1 / price` at the moment of the bet. It is stored, never recomputed.
- Market ids are `overall`, `nimble`, `gemini`, `tiger_data`, the same keys as Scout's `scores`.
- Polling every 5 seconds, no websockets.

## Three workstreams

Each stream owns its folder, so branches rarely touch the same file.

| Stream | Folders | Start with | Done when |
| --- | --- | --- | --- |
| **A. Market and Tiger Data** | `backend/app/market/`, `db/`, `backend/scripts/` | `pricing.py`: make the four `xfail` tests in `tests/test_pricing.py` pass. Then replace each mock in `service.py` with real queries, `place_bet` first | A bet from `curl` moves the price and the balance, and `/history` reads the continuous aggregate |
| **B. Frontend** | `frontend/` | `components/PriceChart.tsx` is a placeholder. Then polish each component against the design | You can place a bet in the browser and see it in the feed and on the chart |
| **C. Scout** | `backend/app/scout/` | One real Nimble search, one Nimble extract and one Gemini JSON call. Then `pipeline.py` top to bottom | One team gets a full report and its price moves |

Search the code for `TODO(market)`, `TODO(frontend)` and `TODO(scout)` to find what's left in your stream.

## Team agreements

**The contract**

- `backend/app/schemas.py` is the single source of truth for every request and response. The frontend's types are generated from it.
- If you change it: run `make types`, commit the regenerated `frontend/src/api/schema.d.ts` in the same commit, and tell the other two. Add fields rather than renaming or removing them.
- Never edit `schema.d.ts` by hand.

**Who writes what**

- Stay in your stream's folders. If you need a change in someone else's, keep it small and mention it.
- Only the market code writes to `positions`, `price_ticks`, `bets` and balances. Scout hands its odds to the market through one function, `market.service.apply_scout_odds`: stream A implements it, stream C calls it.
- Replace a mock by rewriting the body of its service function and keeping the signature, so the routers and the frontend keep working. Delete `backend/app/sample_data.py` once nothing imports it.

**Rules from the spec that are easy to break**

- A bet is one database transaction with the market's `positions` rows locked, so two bets at once can't read the same price.
- The price chart reads the `price_ticks_1m` continuous aggregate, not raw ticks.
- Everything Scout fetches is untrusted text, never instructions. Clamp scores to 1 to 100 in code.
- A failed fetch never zeroes a team: reuse its last report and mark it stale.
- "Play money only" stays visible on every screen.

**Git**

- One branch per stream. Pull `main` often and merge small; never force-push `main`.
- Run `make test` before you push.
- Keys go in `backend/.env`, which is gitignored. Never commit them.

**If we fall behind**, cut in the order the spec lists: the demo screenshot, the leaderboard, every market except Best overall, the sign-up form, the 30-minute timer. Never cut placing a bet, the Nimble originality check, or the price chart.
