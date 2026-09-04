from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.generations.models import GenerationCharacterBlock
from app.domain.generations.schemas import (
    GenerationCharacterBlockCreate,
    GenerationCharacterBlockUpdate,
)


class GenerationCharacterBlockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, data: GenerationCharacterBlockCreate
    ) -> GenerationCharacterBlock:
        row = GenerationCharacterBlock(**data.model_dump())
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_by_generation(
        self, generation_id: UUID
    ) -> list[GenerationCharacterBlock]:
        result = await self.session.execute(
            select(GenerationCharacterBlock)
            .where(GenerationCharacterBlock.generation_id == generation_id)
            .order_by(GenerationCharacterBlock.id)
        )
        return list(result.scalars().all())

    async def get(self, block_id: UUID) -> GenerationCharacterBlock | None:
        return await self.session.get(GenerationCharacterBlock, block_id)

    async def update(
        self, block_id: UUID, data: GenerationCharacterBlockUpdate
    ) -> GenerationCharacterBlock | None:
        row = await self.get(block_id)
        if row is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await self.session.flush()
        return row

    async def delete(self, block_id: UUID) -> bool:
        row = await self.get(block_id)
        if row is None:
            return False
        await self.session.delete(row)
        return True
