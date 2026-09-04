from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.domain.generations.models import Generation
from app.domain.generations.schemas import GenerationCreate, GenerationRead, GenerationUpdate
from app.repositories.character_repository import CharacterRepository
from app.repositories.generation_repository import GenerationRepository
from app.repositories.user_repository import UserRepository


class GenerationService:
    def __init__(
        self,
        repository: GenerationRepository,
        user_repository: UserRepository,
        character_repository: CharacterRepository,
        commit: Callable[[], Awaitable[None]],
    ) -> None:
        self.repository = repository
        self.user_repository = user_repository
        self.character_repository = character_repository
        self.commit = commit

    @staticmethod
    def _read(row: Generation) -> GenerationRead:
        return GenerationRead.model_validate(row)

    async def create(self, data: GenerationCreate) -> GenerationRead:
        if await self.user_repository.get_person_by_id(data.person_id) is None:
            raise NotFoundError("Person not found")
        if await self.character_repository.get_profile(data.character_id) is None:
            raise NotFoundError("Character not found")
        row = await self.repository.create(data)
        await self.commit()
        return self._read(row)

    async def list(self, person_id: UUID) -> list[GenerationRead]:
        if await self.user_repository.get_person_by_id(person_id) is None:
            raise NotFoundError("Person not found")
        return [self._read(row) for row in await self.repository.list_by_person(person_id)]

    async def get(self, generation_id: UUID) -> GenerationRead:
        row = await self.repository.get(generation_id)
        if row is None:
            raise NotFoundError("Generation not found")
        return self._read(row)

    async def update(self, generation_id: UUID, data: GenerationUpdate) -> GenerationRead:
        row = await self.repository.update(generation_id, data)
        if row is None:
            raise NotFoundError("Generation not found")
        await self.commit()
        return self._read(row)

    async def delete(self, generation_id: UUID) -> None:
        if not await self.repository.delete(generation_id):
            raise NotFoundError("Generation not found")
        await self.commit()
