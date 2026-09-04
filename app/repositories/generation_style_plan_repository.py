from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.generations.models import GenerationStylePlan
from app.domain.generations.schemas import GenerationStylePlanCreate, GenerationStylePlanUpdate


class GenerationStylePlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: GenerationStylePlanCreate) -> GenerationStylePlan:
        row = GenerationStylePlan(**data.model_dump())
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_by_generation(self, generation_id: UUID) -> list[GenerationStylePlan]:
        result = await self.session.execute(
            select(GenerationStylePlan)
            .where(GenerationStylePlan.generation_id == generation_id)
            .order_by(GenerationStylePlan.plan_id)
        )
        return list(result.scalars().all())

    async def get(self, plan_id: UUID) -> GenerationStylePlan | None:
        return await self.session.get(GenerationStylePlan, plan_id)

    async def update(self, plan_id: UUID, data: GenerationStylePlanUpdate) -> GenerationStylePlan | None:
        row = await self.get(plan_id)
        if row is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await self.session.flush()
        return row

    async def delete(self, plan_id: UUID) -> bool:
        row = await self.get(plan_id)
        if row is None:
            return False
        await self.session.delete(row)
        return True
