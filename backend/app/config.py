from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str | None = None
    host_password: str = "change-me"
    cors_origins: str = "http://localhost:5173"

    nimble_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    github_token: str | None = None
    event_url: str | None = None
    scout_enabled: bool = False
    scout_interval_minutes: int = 30

    # Market rules from the build spec. Change here, not inline.
    starting_balance: int = 1000
    seed_per_market: int = 2000
    price_floor: float = 0.02

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
