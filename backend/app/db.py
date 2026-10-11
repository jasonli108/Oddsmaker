"""Tiger Data connection pool.

Usage in a service function:

    async with get_pool().connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT ...", (param,))
"""

import logging

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings

log = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None


async def open_pool() -> None:
    """Open the pool at startup. A missing or unreachable database is not fatal while routes are mocked."""
    global _pool
    url = get_settings().database_url
    if not url:
        log.warning("DATABASE_URL is not set; running without a database")
        return
    pool = AsyncConnectionPool(url, min_size=1, max_size=10, open=False, kwargs={"row_factory": dict_row})
    try:
        await pool.open(wait=True, timeout=5)
    except Exception:
        log.exception("Could not connect to the database; running without one")
        await pool.close()
        return
    _pool = pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Database is not connected. Set DATABASE_URL in backend/.env and run `make db`.")
    return _pool


async def status() -> str:
    """One of 'connected', 'not_connected', 'error'. Used by GET /api/health."""
    if _pool is None:
        return "not_connected"
    try:
        async with _pool.connection() as conn:
            await conn.execute("SELECT 1")
        return "connected"
    except Exception:
        log.exception("Database health check failed")
        return "error"
