from conftest import _allows_schema_management


def test_schema_management_guard_accepts_test_env_postgres_asyncpg_test_db() -> None:
    assert _allows_schema_management(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/natalai_test",
        app_env="test",
    )
    assert _allows_schema_management(
        "postgresql+asyncpg://postgres:postgres@db:5432/app_test",
        app_env="test",
    )


def test_schema_management_guard_rejects_non_test_app_env() -> None:
    assert not _allows_schema_management(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/natalai_test",
        app_env="development",
    )


def test_schema_management_guard_rejects_test_substring_outside_database_name() -> None:
    assert not _allows_schema_management(
        "postgresql+asyncpg://test_user:postgres@localhost:5432/natalai",
        app_env="test",
    )
    assert not _allows_schema_management(
        "postgresql+asyncpg://postgres:postgres@test-db:5432/natalai",
        app_env="test",
    )


def test_schema_management_guard_rejects_wrong_backend_or_driver() -> None:
    assert not _allows_schema_management(
        "postgresql://postgres:postgres@localhost:5432/natalai_test",
        app_env="test",
    )
    assert not _allows_schema_management(
        "sqlite+aiosqlite:///natalai_test.db",
        app_env="test",
    )
