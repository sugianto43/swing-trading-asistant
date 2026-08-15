from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SUPPORTED_DATABASE_SCHEMES = ("postgresql+psycopg://", "sqlite+pysqlite://", "sqlite://")


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    app_name: str = "idx-swing-api"
    app_env: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/idx_swing"
    )

    git_sha: str = Field(default="unknown")

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Never committed (env var / .env, gitignored). Optional: absence just
    # means the real GeminiProvider can't be constructed — FixtureLLMProvider
    # and the entire test suite never need it.
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-2.0-flash")

    redis_url: str = Field(default="redis://localhost:6379/0")

    # Real portfolio capital used by the scheduled pipeline's risk/trade-plan
    # stage (MASTER-PRD FR-011: position sizing must use portfolio capital,
    # not a placeholder). Must be set explicitly for a real deployment —
    # the default is illustrative only, same caveat as backtesting's.
    pipeline_capital: float = Field(default=100_000_000.0)

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("database_url must not be empty")
        if not value.startswith(_SUPPORTED_DATABASE_SCHEMES):
            raise ValueError(
                f"database_url must use one of {_SUPPORTED_DATABASE_SCHEMES}, got: {value!r}"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
