import subprocess


def test_migrations_create_character_parent_before_generations() -> None:
    result = subprocess.run(
        ["alembic", "upgrade", "head", "--sql"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.index("CREATE TABLE characters") < result.stdout.index(
        "CREATE TABLE generations"
    )
