"""Server-side settings loaded from environment variables and .env."""

from functools import lru_cache
import os as _os
import pathlib as _pathlib

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def _find_env() -> list[str]:
    """Search for .env starting from cwd up to 3 parent directories."""
    candidates = []
    p = _pathlib.Path(_os.getcwd())
    for _ in range(4):
        candidate = p / ".env"
        if candidate.exists():
            candidates.append(str(candidate))
        p = p.parent
    return candidates or [".env"]


class Settings(BaseSettings):
    """Application settings; secrets are never exposed by this module."""

    model_config = SettingsConfigDict(env_file=_find_env(), env_file_encoding="utf-8", extra="ignore")

    monday_api_token: str = Field(min_length=1, validation_alias=AliasChoices("MONDAY_API_TOKEN", "MONDAY_API_KEY"))
    monday_api_version: str = Field(min_length=1)
    gemini_api_key: str = Field(min_length=1)
    gemini_model: str = Field(min_length=1)
    gemini_fallback_model: str | None = None
    deals_board_id: str | None = None
    work_orders_board_id: str | None = None
    cache_ttl_seconds: int = 300
    answer_cache_ttl_seconds: int = 21600
    rate_limit_per_min: int = 4
    per_ip_questions_per_day: int = 6
    global_llm_calls_per_day: int = 16
    max_llm_calls_per_question: int = 3
    today_override: str | None = None
    app_tz: str = "Asia/Kolkata"
    fiscal_year_start_month: int = 4


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one cached settings object for the process."""

    return Settings()

