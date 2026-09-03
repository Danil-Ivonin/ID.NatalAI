from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

from app.core.database import Base


def test_generation_models_require_person_and_uuid7() -> None:
    import app.domain.generations.astro_charts.models  # noqa: F401
    import app.domain.generations.generation_neutral.models  # noqa: F401

    charts = Base.metadata.tables["astro_charts"]
    neutral = Base.metadata.tables["generation_neutral"]

    assert str(charts.c.id.server_default.arg) == "uuidv7()"
    assert str(neutral.c.id.server_default.arg) == "uuidv7()"
    assert not charts.c.person_id.nullable
    assert not neutral.c.person_id.nullable
    assert next(iter(charts.c.person_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(neutral.c.person_id.foreign_keys)).ondelete == "CASCADE"
    assert isinstance(charts.c.natal_xml.type, Text)
    assert isinstance(charts.c.chart_svg.type, Text)
    assert isinstance(
        neutral.c.result.type.dialect_impl(postgresql.dialect()), postgresql.JSONB
    )
    assert isinstance(
        neutral.c.token_usage.type.dialect_impl(postgresql.dialect()),
        postgresql.JSONB,
    )


def test_person_has_generation_relationships() -> None:
    import app.db.models  # noqa: F401
    from app.domain.users.models import Person

    assert {"astro_charts", "generation_neutral"} <= {
        relationship.key for relationship in Person.__mapper__.relationships
    }
