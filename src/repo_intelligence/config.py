
from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_token: str | None = Field(default=None)
    github_api_base_url: HttpUrl = "https://api.github.com"
    request_timeout_seconds: float = Field(default=20, gt=0, le=120)
    max_search_results: int = Field(default=10, ge=1, le=30)
    max_file_bytes: int = Field(default=200_000, ge=1_000, le=1_000_000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
