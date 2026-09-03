from sqlalchemy import Enum
from sqlalchemy.dialects import postgresql

from app.core.database import Base


def test_metadata_contains_persistence_tables() -> None:
    import app.db.models  # noqa: F401

    assert sorted(Base.metadata.tables) == [
        "astro_charts",
        "character_examples",
        "characters",
        "generation_neutral",
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


def test_generation_neutral_stores_result_and_usage_as_jsonb() -> None:
    import app.db.models  # noqa: F401

    generations = Base.metadata.tables["generation_neutral"]
    assert isinstance(
        generations.c.result.type.dialect_impl(postgresql.dialect()),
        postgresql.JSONB,
    )
    assert isinstance(
        generations.c.token_usage.type.dialect_impl(postgresql.dialect()),
        postgresql.JSONB,
    )
