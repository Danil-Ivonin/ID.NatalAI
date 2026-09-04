from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.generations.models import GenerationCharacterReview
from app.domain.generations.schemas import (
    GenerationCharacterReviewCreate,
    GenerationCharacterReviewUpdate,
)


class GenerationCharacterReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: GenerationCharacterReviewCreate) -> GenerationCharacterReview:
        row = GenerationCharacterReview(**data.model_dump())
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_by_generation(self, generation_id: UUID) -> list[GenerationCharacterReview]:
        result = await self.session.execute(
            select(GenerationCharacterReview)
            .where(GenerationCharacterReview.generation_id == generation_id)
            .order_by(GenerationCharacterReview.id)
        )
        return list(result.scalars().all())

    async def get(self, review_id: UUID) -> GenerationCharacterReview | None:
        return await self.session.get(GenerationCharacterReview, review_id)

    async def update(
        self, review_id: UUID, data: GenerationCharacterReviewUpdate
    ) -> GenerationCharacterReview | None:
        row = await self.get(review_id)
        if row is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await self.session.flush()
        return row

    async def delete(self, review_id: UUID) -> bool:
        row = await self.get(review_id)
        if row is None:
            return False
        await self.session.delete(row)
        return True
