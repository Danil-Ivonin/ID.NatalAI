from sqlalchemy import Enum
from sqlalchemy.dialects import postgresql

from app.core.database import Base


def test_metadata_contains_persistence_tables() -> None:
    import app.db.models  # noqa: F401

    assert sorted(Base.metadata.tables) == [
        "character_examples",
        "characters",
        "neutral_generations",
        "persons",
        "users",
    ]


def test_character_examples_match_planning_schema() -> None:
    import app.db.models  # noqa: F401

    examples = Base.metadata.tables["character_examples"]
    assert examples.c.embedding.type.dim == 3072
    assert next(iter(examples.c.character_id.foreign_keys)).ondelete == "CASCADE"
    assert "character_examples_character_id_idx" in {
        index.name for index in examples.indexes
    }
    assert examples.c.humor_types.type.item_type.name == "humor_type"
    assert examples.c.speech_patterns.type.item_type.name == "speech_pattern"
    assert isinstance(
        examples.c.emotion.type.dialect_impl(postgresql.dialect()),
        Enum,
    )


def test_neutral_generations_store_reading_as_jsonb() -> None:
    import app.db.models  # noqa: F401

    generations = Base.metadata.tables["neutral_generations"]
    assert list(generations.c.keys()) == ["id", "reading"]
    assert isinstance(
        generations.c.reading.type.dialect_impl(postgresql.dialect()),
        postgresql.JSONB,
    )
