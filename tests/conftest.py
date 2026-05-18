import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/natalai_test",
)
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")

import app.db.models  # noqa: E402,F401


class CommitTrackingSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def pytest_configure(config) -> None:
    config.addinivalue_line(
        "markers",
        "db_integration: tests that require a reachable PostgreSQL test database",
    )


def _configured_database_url() -> tuple[str, str]:
    from app.core.config import get_settings

    settings = get_settings()
    return str(settings.database_url), settings.app_env


def _allows_schema_management(database_url: str, app_env: str) -> bool:
    parsed = make_url(database_url)
    database_name = parsed.database or ""
    return (
        app_env == "test"
        and parsed.drivername == "postgresql+asyncpg"
        and (database_name == "natalai_test" or database_name.endswith("_test"))
    )


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    from app.core.database import Base

    database_url, app_env = _configured_database_url()
    if not _allows_schema_management(database_url, app_env):
        database_name = make_url(database_url).database or "<unknown>"
        pytest.skip(
            "Refusing to manage schema because APP_ENV/DATABASE_URL are not "
            f"clearly test-scoped: APP_ENV={app_env}, database={database_name}"
        )

    test_engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        poolclass=NullPool,
    )

    try:
        async with test_engine.connect() as connection:
            await connection.execute(text("select 1"))
    except (OSError, SQLAlchemyError) as exc:
        await test_engine.dispose()
        pytest.skip(f"PostgreSQL test DB is not reachable: {exc}")

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()


@pytest.fixture
def fastapi_app():
    from app.main import app

    app.dependency_overrides.clear()
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def app_session() -> CommitTrackingSession:
    return CommitTrackingSession()


@pytest.fixture
def app_client(fastapi_app, app_session):
    from app.core.database import get_session

    async def override_get_session():
        yield app_session

    fastapi_app.dependency_overrides[get_session] = override_get_session
    with TestClient(fastapi_app) as test_client:
        test_client.fake_session = app_session
        yield test_client


@pytest.fixture
def generation_dispatch_spy(monkeypatch):
    from app.api.v1 import generations

    dispatched = []
    monkeypatch.setattr(generations, "dispatch_generation_job", dispatched.append)
    return dispatched
