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
