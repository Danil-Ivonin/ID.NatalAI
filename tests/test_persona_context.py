from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import app.db.models  # noqa: F401
from app.core.database import Base, engine
from app.domain.persona.context import PersonaContext, PersonaContextProvider
from app.domain.persona.schemas import (
    PersonaCreate,
    PersonaPhraseTemplateCreate,
    PersonaQuoteCreate,
    PersonaStyleExampleCreate,
    PersonaStyleProfileCreate,
)
from app.repositories.persona_repository import PersonaRepository


class RepositoryPersonaContextProvider:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    async def get_context(self, persona_id: UUID) -> PersonaContext:
        persona = await self.repository.get_context_persona(persona_id)
        style_profile = await self.repository.get_style_profile(persona_id)
        quotes = await self.repository.list_allowed_quotes(persona_id)
        phrase_templates = await self.repository.list_phrase_templates(persona_id)
        style_examples = await self.repository.list_style_examples(persona_id)

        if persona is None or style_profile is None:
            raise LookupError("Persona context is incomplete")

        return PersonaContext(
            persona_name=persona.name,
            persona_slug=persona.slug,
            persona_description=persona.description,
            voice_description=style_profile.voice_description,
            humor_style=style_profile.humor_style,
            speech_patterns=style_profile.speech_patterns,
            allowed_rules=style_profile.allowed_rules,
            forbidden_rules=style_profile.forbidden_rules,
            allowed_quotes=[quote.text for quote in quotes],
            phrase_templates=[template.template for template in phrase_templates],
            style_examples=[example.text for example in style_examples],
        )


async def _ensure_postgres_schema_or_skip() -> None:
    try:
        async with engine.begin() as connection:
            await connection.execute(text("select 1"))
            await connection.run_sync(Base.metadata.create_all)
    except (OSError, SQLAlchemyError) as exc:
        pytest.skip(f"PostgreSQL test DB is not reachable: {exc}")


@pytest.mark.asyncio
async def test_persona_context_provider_loads_repository_context_from_db() -> None:
    await _ensure_postgres_schema_or_skip()

    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        repository = PersonaRepository(session)
        slug = f"context-{uuid4().hex}"
        persona = await repository.create(
            PersonaCreate(
                name="Shrek",
                slug=slug,
                description="Direct fairy tale swamp wisdom.",
                style_profile=PersonaStyleProfileCreate(
                    voice_description="Blunt, warm, and impatient.",
                    humor_style="Dry roasts.",
                    speech_patterns=["short sentences"],
                    forbidden_rules=["no hate"],
                    allowed_rules=["tease lightly"],
                ),
                quotes=[
                    PersonaQuoteCreate(
                        text="Better out than in.",
                        usage_context="general",
                        is_allowed=True,
                    ),
                    PersonaQuoteCreate(
                        text="Forbidden quote.",
                        usage_context="do not use",
                        is_allowed=False,
                    ),
                ],
                phrase_templates=[
                    PersonaPhraseTemplateCreate(
                        type="intro",
                        template="{subject}, listen.",
                        usage="openings",
                    )
                ],
                style_examples=[
                    PersonaStyleExampleCreate(
                        title="Advice",
                        text="That plan needs boots.",
                        tags=["advice"],
                    )
                ],
            )
        )
        await session.commit()

        provider: PersonaContextProvider = RepositoryPersonaContextProvider(repository)

        context = await provider.get_context(persona.id)

    assert context.persona_name == "Shrek"
    assert context.allowed_quotes == ["Better out than in."]
    assert "Forbidden quote." not in context.allowed_quotes
    assert context.phrase_templates == ["{subject}, listen."]
    assert context.style_examples == ["That plan needs boots."]
