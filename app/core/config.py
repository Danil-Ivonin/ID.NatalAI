from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ValidationFailure


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/natalai",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        alias="CELERY_RESULT_BACKEND",
    )
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_model_profile: str = Field(
        default="openai/gpt-5",
        alias="OPENROUTER_MODEL_PROFILE",
    )
    openrouter_model_report: str = Field(
        default="openai/gpt-5",
        alias="OPENROUTER_MODEL_REPORT",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    def require_openrouter_api_key(self) -> None:
        if not self.openrouter_api_key.strip():
            raise ValidationFailure("OPENROUTER_API_KEY is required for AI generation")


@lru_cache
def get_settings() -> Settings:
    return Settings()
