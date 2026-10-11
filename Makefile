PY := backend/.venv/bin/python

.PHONY: setup db db-init db-seed db-reset backend frontend types test

setup: ## Install backend and frontend dependencies, create backend/.env
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install -q --upgrade pip
	backend/.venv/bin/pip install -q -r backend/requirements.txt
	cd frontend && npm install --no-fund --no-audit
	@test -f backend/.env || (cp backend/.env.example backend/.env && echo "Created backend/.env; add your API keys.")

db: ## Start local TimescaleDB, apply the schema, seed markets and sample teams
	docker compose up -d --wait db
	$(MAKE) db-init db-seed

db-init: ## Apply db/schema.sql to DATABASE_URL (local or Tiger Cloud)
	cd backend && .venv/bin/python -m scripts.init_db

db-seed:
	cd backend && .venv/bin/python -m scripts.seed

db-reset: ## Wipe the local database and rebuild it
	docker compose down -v
	$(MAKE) db

backend: ## API on http://localhost:8000 (docs at /docs)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend: ## App on http://localhost:5173
	cd frontend && npm run dev

types: ## Regenerate frontend types after changing backend/app/schemas.py
	cd backend && .venv/bin/python -m scripts.export_openapi > ../frontend/openapi.json
	cd frontend && npm run gen:types

test:
	cd backend && .venv/bin/python -m pytest -q
	cd frontend && npm run typecheck
