from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.domain.generations.generation_neutral.models import GenerationNeutral
from app.domain.generations.generation_neutral.schemas import (
    GenerationNeutralCreate,
    GenerationNeutralRead,
    GenerationNeutralUpdate,
)
from app.repositories.generation_neutral_repository import (
    GenerationNeutralRepository,
)
from app.repositories.user_repository import UserRepository


class GenerationNeutralService:
    def __init__(
        self,
        repository: GenerationNeutralRepository,
        user_repository: UserRepository,
        commit: Callable[[], Awaitable[None]],
    ) -> None:
        self.repository = repository
        self.user_repository = user_repository
        self.commit = commit

    async def _require_person(self, person_id: UUID) -> None:
        if await self.user_repository.get_person_by_id(person_id) is None:
            raise NotFoundError("Person not found")

    @staticmethod
    def _read(row: GenerationNeutral) -> GenerationNeutralRead:
        return GenerationNeutralRead.model_validate(row)

    async def create(self, data: GenerationNeutralCreate) -> GenerationNeutralRead:
        await self._require_person(data.person_id)
        row = await self.repository.create(data)
        await self.commit()
        return self._read(row)

    async def list(self, person_id: UUID) -> list[GenerationNeutralRead]:
        await self._require_person(person_id)
        return [self._read(row) for row in await self.repository.list_by_person(person_id)]

    async def get(self, generation_id: UUID) -> GenerationNeutralRead:
        row = await self.repository.get(generation_id)
        if row is None:
            raise NotFoundError("Neutral generation not found")
        return self._read(row)

    async def update(
        self,
        generation_id: UUID,
        data: GenerationNeutralUpdate,
    ) -> GenerationNeutralRead:
        row = await self.repository.update(generation_id, data)
        if row is None:
            raise NotFoundError("Neutral generation not found")
        await self.commit()
        return self._read(row)

    async def delete(self, generation_id: UUID) -> None:
        if not await self.repository.delete(generation_id):
            raise NotFoundError("Neutral generation not found")
        await self.commit()
