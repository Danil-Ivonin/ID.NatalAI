from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.generations.astro_charts.models import AstroChart
from app.domain.generations.astro_charts.schemas import AstroChartCreate, AstroChartUpdate


class AstroChartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: AstroChartCreate) -> AstroChart:
        row = AstroChart(**data.model_dump())
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_by_person(self, person_id: UUID) -> list[AstroChart]:
        result = await self.session.execute(
            select(AstroChart)
            .where(AstroChart.person_id == person_id)
            .order_by(AstroChart.id)
        )
        return list(result.scalars().all())

    async def get(self, chart_id: UUID) -> AstroChart | None:
        return await self.session.get(AstroChart, chart_id)

    async def update(
        self, chart_id: UUID, data: AstroChartUpdate
    ) -> AstroChart | None:
        row = await self.get(chart_id)
        if row is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await self.session.flush()
        return row

    async def delete(self, chart_id: UUID) -> bool:
        row = await self.get(chart_id)
        if row is None:
            return False
        await self.session.delete(row)
        return True
