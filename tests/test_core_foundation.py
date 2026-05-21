import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.exceptions import NatalAIError, NotFoundError, ValidationFailure
from app.core.logging import ExtraFormatter, configure_logging


def test_settings_defaults_are_test_friendly() -> None:
    settings = get_settings()

    assert settings.app_env == "test"
    assert settings.database_url.endswith("/natalai_test")
    assert settings.openrouter_api_key == "test-key"


def test_settings_runtime_validation_rejects_empty_openrouter_key() -> None:
    from app.core.config import Settings

    settings = Settings(OPENROUTER_API_KEY=" ")

    try:
        settings.require_openrouter_api_key()
    except ValidationFailure as exc:
        assert "OPENROUTER_API_KEY" in str(exc)
    else:
        raise AssertionError("expected ValidationFailure")


def test_database_sessionmaker_creates_async_sessions() -> None:
    session = async_session_factory()

    assert isinstance(session, AsyncSession)


def test_exception_hierarchy() -> None:
    assert issubclass(NotFoundError, NatalAIError)


def test_configure_logging_uses_standard_logging() -> None:
    configure_logging()

    assert logging.getLogger().handlers


def test_extra_formatter_includes_context_fields() -> None:
    formatter = ExtraFormatter("%(levelname)s %(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="generation stage started",
        args=(),
        exc_info=None,
    )
    record.generation_id = "generation-1"
    record.stage = "natal_chart_build"

    assert (
        formatter.format(record)
        == "INFO generation stage started generation_id=generation-1 stage=natal_chart_build"
    )
