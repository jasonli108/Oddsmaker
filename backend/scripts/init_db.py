"""Apply db/schema.sql to DATABASE_URL. Safe to re-run.

    cd backend && .venv/bin/python -m scripts.init_db
"""

import sys

import psycopg

from app.config import REPO_ROOT, get_settings


def statements(sql: str) -> list[str]:
    """Split the schema into statements. It has no function bodies, so ';' at end of line is enough."""
    without_comments = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    return [s.strip() for s in without_comments.split(";") if s.strip()]


def main() -> None:
    url = get_settings().database_url
    if not url:
        sys.exit("DATABASE_URL is not set. Copy backend/.env.example to backend/.env first.")
    sql = (REPO_ROOT / "db" / "schema.sql").read_text()
    # autocommit: a continuous aggregate cannot be created inside a transaction block.
    with psycopg.connect(url, autocommit=True) as conn:
        for statement in statements(sql):
            conn.execute(statement)
    print("Schema applied.")


if __name__ == "__main__":
    main()
