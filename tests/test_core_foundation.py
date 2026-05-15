import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.exceptions import NatalAIError, NotFoundError
from app.core.logging import configure_logging


def test_settings_defaults_are_test_friendly() -> None:
    settings = get_settings()

    assert settings.app_env == "test"
    assert settings.database_url.endswith("/natalai_test")
    assert settings.openrouter_api_key == "test-key"


def test_database_sessionmaker_creates_async_sessions() -> None:
    session = async_session_factory()

    assert isinstance(session, AsyncSession)


def test_exception_hierarchy() -> None:
    assert issubclass(NotFoundError, NatalAIError)


def test_configure_logging_uses_standard_logging() -> None:
    configure_logging()

    assert logging.getLogger().handlers
