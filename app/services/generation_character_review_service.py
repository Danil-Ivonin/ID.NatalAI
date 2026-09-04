from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.domain.generations.models import GenerationCharacterReview
from app.domain.generations.schemas import (
    GenerationCharacterReviewCreate,
    GenerationCharacterReviewRead,
    GenerationCharacterReviewUpdate,
)
from app.repositories.generation_character_review_repository import (
    GenerationCharacterReviewRepository,
)
from app.repositories.generation_repository import GenerationRepository


class GenerationCharacterReviewService:
    def __init__(
        self,
        repository: GenerationCharacterReviewRepository,
        generation_repository: GenerationRepository,
        commit: Callable[[], Awaitable[None]],
    ) -> None:
        self.repository = repository
        self.generation_repository = generation_repository
        self.commit = commit

    @staticmethod
    def _read(row: GenerationCharacterReview) -> GenerationCharacterReviewRead:
        return GenerationCharacterReviewRead.model_validate(row)

    async def create(
        self, data: GenerationCharacterReviewCreate
    ) -> GenerationCharacterReviewRead:
        if await self.generation_repository.get(data.generation_id) is None:
            raise NotFoundError("Generation not found")
        row = await self.repository.create(data)
        await self.commit()
        return self._read(row)

    async def list(self, generation_id: UUID) -> list[GenerationCharacterReviewRead]:
        if await self.generation_repository.get(generation_id) is None:
            raise NotFoundError("Generation not found")
        return [self._read(row) for row in await self.repository.list_by_generation(generation_id)]

    async def get(self, review_id: UUID) -> GenerationCharacterReviewRead:
        row = await self.repository.get(review_id)
        if row is None:
            raise NotFoundError("Generation character review not found")
        return self._read(row)

    async def update(
        self, review_id: UUID, data: GenerationCharacterReviewUpdate
    ) -> GenerationCharacterReviewRead:
        row = await self.repository.update(review_id, data)
        if row is None:
            raise NotFoundError("Generation character review not found")
        await self.commit()
        return self._read(row)

    async def delete(self, review_id: UUID) -> None:
        if not await self.repository.delete(review_id):
            raise NotFoundError("Generation character review not found")
        await self.commit()
