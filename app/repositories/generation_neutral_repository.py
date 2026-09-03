from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.generations.generation_neutral.models import GenerationNeutral
from app.domain.generations.generation_neutral.schemas import (
    GenerationNeutralCreate,
    GenerationNeutralUpdate,
)


class GenerationNeutralRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: GenerationNeutralCreate) -> GenerationNeutral:
        values = data.model_dump(mode="json", exclude={"person_id"})
        row = GenerationNeutral(person_id=data.person_id, **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_by_person(self, person_id: UUID) -> list[GenerationNeutral]:
        result = await self.session.execute(
            select(GenerationNeutral)
            .where(GenerationNeutral.person_id == person_id)
            .order_by(GenerationNeutral.id)
        )
        return list(result.scalars().all())

    async def get(self, generation_id: UUID) -> GenerationNeutral | None:
        return await self.session.get(GenerationNeutral, generation_id)

    async def update(
        self,
        generation_id: UUID,
        data: GenerationNeutralUpdate,
    ) -> GenerationNeutral | None:
        row = await self.get(generation_id)
        if row is None:
            return None
        for field, value in data.model_dump(mode="json", exclude_unset=True).items():
            setattr(row, field, value)
        await self.session.flush()
        return row

    async def delete(self, generation_id: UUID) -> bool:
        row = await self.get(generation_id)
        if row is None:
            return False
        await self.session.delete(row)
        return True
