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
    assert "ALTER TABLE generation_character_review RENAME TO generation_character_blocks" in result.stdout
    assert "ADD COLUMN generation_id UUID" in result.stdout
