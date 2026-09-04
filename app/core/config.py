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
    chart_image_s3_endpoint_url: str = Field(
        default="",
        alias="CHART_IMAGE_S3_ENDPOINT_URL",
    )
    chart_image_s3_region: str = Field(
        default="us-east-1",
        alias="CHART_IMAGE_S3_REGION",
    )
    chart_image_public_endpoint_url: str = Field(
        default="",
        alias="CHART_IMAGE_PUBLIC_ENDPOINT_URL",
    )
    chart_image_s3_bucket: str = Field(
        default="natalai-charts",
        alias="CHART_IMAGE_S3_BUCKET",
    )
    chart_image_s3_access_key_id: str = Field(
        default="",
        alias="CHART_IMAGE_S3_ACCESS_KEY_ID",
    )
    chart_image_s3_secret_access_key: str = Field(
        default="",
        alias="CHART_IMAGE_S3_SECRET_ACCESS_KEY",
    )
    chart_image_url_expires_seconds: int = Field(
        default=86400,
        alias="CHART_IMAGE_URL_EXPIRES_SECONDS",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    def require_openrouter_api_key(self) -> None:
        if not self.openrouter_api_key.strip():
            raise ValidationFailure("OPENROUTER_API_KEY is required for AI generation")


@lru_cache
def get_settings() -> Settings:
    return Settings()
