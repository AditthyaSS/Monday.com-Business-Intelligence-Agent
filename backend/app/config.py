"""Server-side settings loaded from environment variables and .env."""

from __future__ import annotations

from functools import lru_cache
import os as _os
import pathlib as _pathlib

from pydantic import AliasChoices, Field, field_validator, model_validator
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


def _int_or_default(v: object, default: int) -> int:
    """Parse v as int; fall back to default if blank/invalid."""
    if v is None:
        return default
    s = str(v).strip()
    if not s:
        return default
    try:
        return int(s)
    except (ValueError, TypeError):
        return default


class Settings(BaseSettings):
    """Application settings; secrets are never exposed by this module."""

    model_config = SettingsConfigDict(
        env_file=_find_env(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    monday_api_token: str = Field(
        default="",
        validation_alias=AliasChoices("MONDAY_API_TOKEN", "MONDAY_API_KEY"),
    )
    monday_api_version: str = Field(default="2024-01")
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash")
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

    @field_validator(
        "gemini_fallback_model", "deals_board_id", "work_orders_board_id",
        "today_override", mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        """Treat empty strings as None for optional fields."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "cache_ttl_seconds", "answer_cache_ttl_seconds", "rate_limit_per_min",
        "per_ip_questions_per_day", "global_llm_calls_per_day",
        "max_llm_calls_per_question", "fiscal_year_start_month",
        mode="before",
    )
    @classmethod
    def _coerce_int(cls, v: object) -> object:
        """Coerce string integers tolerantly; blank → keep default via None."""
        if v is None:
            return v
        if isinstance(v, int):
            return v
        s = str(v).strip()
        if not s:
            return None  # pydantic will use the field default
        return int(s)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one cached settings object for the process."""
    return Settings()
