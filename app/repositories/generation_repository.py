from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.domain.generation.enums import GenerationStatus
from app.domain.generation.models import Generation, GenerationRun
from app.domain.generation.schemas import GenerationCreate


class GenerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: GenerationCreate) -> Generation:
        generation = Generation(
            person_name=data.person_name,
            gender=data.gender,
            birth_date=data.birth_date,
            birth_time=data.birth_time,
            birth_city=data.birth_place.city,
            birth_country=data.birth_place.country,
            birth_lat=data.birth_place.lat,
            birth_lng=data.birth_place.lng,
            birth_timezone=data.birth_place.timezone,
            persona_id=data.persona_id,
            status=GenerationStatus.PENDING,
        )
        self.session.add(generation)
        await self.session.flush()
        await self.session.refresh(generation)
        return generation

    async def get(self, generation_id: UUID) -> Generation | None:
        return await self.session.get(Generation, generation_id)

    async def set_status(
        self, generation_id: UUID, status: GenerationStatus
    ) -> None:
        generation = await self.get(generation_id)
        if generation is not None:
            generation.status = status
            await self.session.flush()

    async def save_natal_xml(self, generation_id: UUID, natal_xml: str) -> None:
        generation = await self.get(generation_id)
        if generation is not None:
            generation.natal_xml = natal_xml
            await self.session.flush()

    async def save_profile(self, generation_id: UUID, profile: dict[str, Any]) -> None:
        generation = await self.get(generation_id)
        if generation is not None:
            generation.astrology_profile_json = profile
            await self.session.flush()

    async def save_result(
        self,
        generation_id: UUID,
        result_json: dict[str, Any],
        result_text: str,
    ) -> None:
        generation = await self.get(generation_id)
        if generation is not None:
            generation.result_json = result_json
            generation.result_text = result_text
            generation.status = GenerationStatus.COMPLETED
            generation.completed_at = datetime.now(UTC)
            await self.session.flush()

    async def fail(self, generation_id: UUID, error_message: str) -> None:
        generation = await self.get(generation_id)
        if generation is not None:
            generation.status = GenerationStatus.FAILED
            generation.error_message = error_message
            await self.session.flush()

    async def create_run(self, values: dict[str, Any]) -> GenerationRun:
        run = GenerationRun(**values)
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run
