from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.domain.persona.context import PersonaContext
from app.repositories.persona_repository import PersonaRepository


class PostgresPersonaContextProvider:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    async def get_context(self, persona_id: UUID) -> PersonaContext:
        persona = await self.repository.get_context_persona(persona_id)
        if persona is None:
            raise NotFoundError(f"Active persona not found: {persona_id}")

        style_profile = await self.repository.get_style_profile(persona_id)
        if style_profile is None:
            raise NotFoundError(f"Persona style profile not found: {persona_id}")

        quotes = await self.repository.list_allowed_quotes(persona_id)
        phrase_templates = await self.repository.list_phrase_templates(persona_id)
        style_examples = await self.repository.list_style_examples(persona_id)

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
