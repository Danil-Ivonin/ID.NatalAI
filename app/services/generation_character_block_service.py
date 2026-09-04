from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.domain.generations.models import GenerationCharacterBlock
from app.domain.generations.schemas import (
    GenerationCharacterBlockCreate,
    GenerationCharacterBlockRead,
    GenerationCharacterBlockUpdate,
)
from app.repositories.generation_character_block_repository import (
    GenerationCharacterBlockRepository,
)
from app.repositories.generation_repository import GenerationRepository


class GenerationCharacterBlockService:
    def __init__(
        self,
        repository: GenerationCharacterBlockRepository,
        generation_repository: GenerationRepository,
        commit: Callable[[], Awaitable[None]],
    ) -> None:
        self.repository = repository
        self.generation_repository = generation_repository
        self.commit = commit

    @staticmethod
    def _read(row: GenerationCharacterBlock) -> GenerationCharacterBlockRead:
        return GenerationCharacterBlockRead.model_validate(row)

    async def create(
        self, data: GenerationCharacterBlockCreate
    ) -> GenerationCharacterBlockRead:
        if await self.generation_repository.get(data.generation_id) is None:
            raise NotFoundError("Generation not found")
        row = await self.repository.create(data)
        await self.commit()
        return self._read(row)

    async def list(self, generation_id: UUID) -> list[GenerationCharacterBlockRead]:
        if await self.generation_repository.get(generation_id) is None:
            raise NotFoundError("Generation not found")
        return [
            self._read(row)
            for row in await self.repository.list_by_generation(generation_id)
        ]

    async def get(self, block_id: UUID) -> GenerationCharacterBlockRead:
        row = await self.repository.get(block_id)
        if row is None:
            raise NotFoundError("Generation character block not found")
        return self._read(row)

    async def update(
        self, block_id: UUID, data: GenerationCharacterBlockUpdate
    ) -> GenerationCharacterBlockRead:
        row = await self.repository.update(block_id, data)
        if row is None:
            raise NotFoundError("Generation character block not found")
        await self.commit()
        return self._read(row)

    async def delete(self, block_id: UUID) -> None:
        if not await self.repository.delete(block_id):
            raise NotFoundError("Generation character block not found")
        await self.commit()
