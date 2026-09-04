from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.domain.generations.models import GenerationStylePlan
from app.domain.generations.schemas import (
    GenerationStylePlanCreate,
    GenerationStylePlanRead,
    GenerationStylePlanUpdate,
)
from app.repositories.generation_repository import GenerationRepository
from app.repositories.generation_style_plan_repository import GenerationStylePlanRepository


class GenerationStylePlanService:
    def __init__(
        self,
        repository: GenerationStylePlanRepository,
        generation_repository: GenerationRepository,
        commit: Callable[[], Awaitable[None]],
    ) -> None:
        self.repository = repository
        self.generation_repository = generation_repository
        self.commit = commit

    @staticmethod
    def _read(row: GenerationStylePlan) -> GenerationStylePlanRead:
        return GenerationStylePlanRead.model_validate(row)

    async def create(self, data: GenerationStylePlanCreate) -> GenerationStylePlanRead:
        if await self.generation_repository.get(data.generation_id) is None:
            raise NotFoundError("Generation not found")
        row = await self.repository.create(data)
        await self.commit()
        return self._read(row)

    async def list(self, generation_id: UUID) -> list[GenerationStylePlanRead]:
        if await self.generation_repository.get(generation_id) is None:
            raise NotFoundError("Generation not found")
        return [self._read(row) for row in await self.repository.list_by_generation(generation_id)]

    async def get(self, plan_id: UUID) -> GenerationStylePlanRead:
        row = await self.repository.get(plan_id)
        if row is None:
            raise NotFoundError("Generation style plan not found")
        return self._read(row)

    async def update(
        self, plan_id: UUID, data: GenerationStylePlanUpdate
    ) -> GenerationStylePlanRead:
        row = await self.repository.update(plan_id, data)
        if row is None:
            raise NotFoundError("Generation style plan not found")
        await self.commit()
        return self._read(row)

    async def delete(self, plan_id: UUID) -> None:
        if not await self.repository.delete(plan_id):
            raise NotFoundError("Generation style plan not found")
        await self.commit()
