from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.db.models  # noqa: F401
from app.domain.persona.models import (
    Persona,
    PersonaPhraseTemplate,
    PersonaQuote,
    PersonaStyleExample,
    PersonaStyleProfile,
)
from app.domain.persona.schemas import PersonaCreate, PersonaUpdate


class PersonaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _read_options():
        return (
            selectinload(Persona.style_profile),
            selectinload(Persona.quotes),
            selectinload(Persona.phrase_templates),
            selectinload(Persona.style_examples),
        )

    async def create(self, data: PersonaCreate) -> Persona:
        persona = Persona(
            name=data.name,
            slug=data.slug,
            description=data.description,
            is_active=data.is_active,
            style_profile=(
                PersonaStyleProfile(**data.style_profile.model_dump())
                if data.style_profile is not None
                else None
            ),
            quotes=[PersonaQuote(**quote.model_dump()) for quote in data.quotes],
            phrase_templates=[
                PersonaPhraseTemplate(**template.model_dump())
                for template in data.phrase_templates
            ],
            style_examples=[
                PersonaStyleExample(**example.model_dump())
                for example in data.style_examples
            ],
        )
        self.session.add(persona)
        await self.session.flush()
        loaded_persona = await self.get(persona.id)
        if loaded_persona is None:
            raise LookupError("Created persona could not be loaded")
        return loaded_persona

    async def update(self, persona_id: UUID, data: PersonaUpdate) -> Persona | None:
        persona = await self.get(persona_id)
        if persona is None:
            return None

        values = data.model_dump(exclude_unset=True, exclude={"style_profile"})
        for field, value in values.items():
            setattr(persona, field, value)

        if data.style_profile is not None:
            style_values = data.style_profile.model_dump(exclude_unset=True)
            if persona.style_profile is None:
                persona.style_profile = PersonaStyleProfile(**style_values)
            else:
                for field, value in style_values.items():
                    setattr(persona.style_profile, field, value)

        await self.session.flush()
        loaded_persona = await self.get(persona_id)
        if loaded_persona is None:
            raise LookupError("Updated persona could not be loaded")
        return loaded_persona

    async def get(self, persona_id: UUID) -> Persona | None:
        statement = (
            select(Persona)
            .where(Persona.id == persona_id)
            .options(*self._read_options())
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list(self) -> list[Persona]:
        statement = (
            select(Persona)
            .options(*self._read_options())
            .order_by(Persona.created_at)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active(self, persona_id: UUID) -> Persona | None:
        statement = (
            select(Persona)
            .where(Persona.id == persona_id, Persona.is_active.is_(True))
            .options(*self._read_options())
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_context_persona(self, persona_id: UUID) -> Persona | None:
        statement = select(Persona).where(
            Persona.id == persona_id,
            Persona.is_active.is_(True),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_style_profile(
        self, persona_id: UUID
    ) -> PersonaStyleProfile | None:
        statement = select(PersonaStyleProfile).where(
            PersonaStyleProfile.persona_id == persona_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_allowed_quotes(self, persona_id: UUID) -> list[PersonaQuote]:
        statement = (
            select(PersonaQuote)
            .where(
                PersonaQuote.persona_id == persona_id,
                PersonaQuote.is_allowed.is_(True),
            )
            .order_by(PersonaQuote.created_at)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_phrase_templates(
        self, persona_id: UUID
    ) -> list[PersonaPhraseTemplate]:
        statement = (
            select(PersonaPhraseTemplate)
            .where(PersonaPhraseTemplate.persona_id == persona_id)
            .order_by(PersonaPhraseTemplate.created_at)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_style_examples(
        self, persona_id: UUID
    ) -> list[PersonaStyleExample]:
        statement = (
            select(PersonaStyleExample)
            .where(PersonaStyleExample.persona_id == persona_id)
            .order_by(PersonaStyleExample.created_at)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
