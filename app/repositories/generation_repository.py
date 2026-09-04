from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.generations.models import Generation
from app.domain.generations.schemas import GenerationCreate, GenerationUpdate


class GenerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: GenerationCreate) -> Generation:
        row = Generation(**data.model_dump())
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_by_person(self, person_id: UUID) -> list[Generation]:
        result = await self.session.execute(
            select(Generation)
            .where(Generation.person_id == person_id)
            .order_by(Generation.generation_id)
        )
        return list(result.scalars().all())

    async def get(self, generation_id: UUID) -> Generation | None:
        return await self.session.get(Generation, generation_id)

    async def update(self, generation_id: UUID, data: GenerationUpdate) -> Generation | None:
        row = await self.get(generation_id)
        if row is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await self.session.flush()
        return row

    async def delete(self, generation_id: UUID) -> bool:
        row = await self.get(generation_id)
        if row is None:
            return False
        await self.session.delete(row)
        return True
