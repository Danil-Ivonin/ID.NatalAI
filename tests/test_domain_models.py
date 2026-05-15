from sqlalchemy.dialects import postgresql

from app.core.database import Base


def test_domain_metadata_contains_task_two_tables_and_indexes() -> None:
    import app.domain.generation.models  # noqa: F401
    import app.domain.persona.models  # noqa: F401
    import app.domain.prompts.models  # noqa: F401

    assert sorted(Base.metadata.tables) == [
        "generation_runs",
        "generations",
        "persona_phrase_templates",
        "persona_quotes",
        "persona_style_examples",
        "persona_style_profiles",
        "personas",
        "prompt_templates",
    ]

    personas = Base.metadata.tables["personas"]
    prompt_templates = Base.metadata.tables["prompt_templates"]
    generations = Base.metadata.tables["generations"]
    generation_runs = Base.metadata.tables["generation_runs"]

    assert "ix_personas_slug" in {index.name for index in personas.indexes}
    assert "ix_prompt_templates_type_active" in {
        index.name for index in prompt_templates.indexes
    }
    assert "ix_generations_status" in {index.name for index in generations.indexes}
    assert "ix_generation_runs_generation_id" in {
        index.name for index in generation_runs.indexes
    }
    assert isinstance(
        prompt_templates.c.metadata.type.dialect_impl(postgresql.dialect()),
        postgresql.JSONB,
    )


def test_domain_enums_expose_expected_values() -> None:
    from app.domain.generation.enums import Gender, GenerationStage, GenerationStatus
    from app.domain.prompts.enums import PromptTemplateType

    assert [gender.value for gender in Gender] == ["male", "female"]
    assert [status.value for status in GenerationStatus] == [
        "pending",
        "processing",
        "completed",
        "failed",
    ]
    assert [stage.value for stage in GenerationStage] == [
        "natal_chart_build",
        "astrology_profile_extraction",
        "styled_report_generation",
    ]
    assert [template_type.value for template_type in PromptTemplateType] == [
        "astrology_profile_extraction",
        "styled_report_generation",
    ]
