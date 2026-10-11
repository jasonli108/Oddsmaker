"""The host password check, as a dependency for host-only routes.

    @router.get("/host/summary", dependencies=[Depends(require_host)])

Same rule as resolve_market in routers/markets.py: the X-Host-Password header must match
HOST_PASSWORD from backend/.env.
"""

import secrets

from fastapi import Header, HTTPException

from app.config import get_settings


def require_host(x_host_password: str = Header(default="")) -> None:
    expected = get_settings().host_password
    if not secrets.compare_digest(x_host_password.encode(), expected.encode()):
        raise HTTPException(401, "Host password required")
