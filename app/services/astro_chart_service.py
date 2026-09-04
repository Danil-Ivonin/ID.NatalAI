from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.domain.generations.astro_charts.models import AstroChart
from app.domain.generations.astro_charts.schemas import (
    AstroChartCreate,
    AstroChartRead,
    AstroChartUpdate,
)
from app.repositories.astro_chart_repository import AstroChartRepository
from app.repositories.user_repository import UserRepository
from app.services.chart_image_storage import ChartImageStorage


class AstroChartService:
    def __init__(
        self,
        repository: AstroChartRepository,
        user_repository: UserRepository,
        storage: ChartImageStorage,
        commit: Callable[[], Awaitable[None]],
    ) -> None:
        self.repository = repository
        self.user_repository = user_repository
        self.storage = storage
        self.commit = commit

    async def _require_person(self, person_id: UUID) -> None:
        if await self.user_repository.get_person_by_id(person_id) is None:
            raise NotFoundError("Person not found")

    def _read(self, row: AstroChart) -> AstroChartRead:
        chart_key = row.chart_svg
        if row.generation_id is not None and row.chart_svg.lstrip().startswith("<svg"):
            chart_key = f"generations/{row.generation_id}/natal-chart.svg"
        return AstroChartRead(
            id=row.id,
            person_id=row.person_id,
            generation_id=row.generation_id,
            natal_xml=row.natal_xml,
            chart_svg=self.storage.presigned_url(chart_key),
        )

    async def create(self, data: AstroChartCreate) -> AstroChartRead:
        await self._require_person(data.person_id)
        row = await self.repository.create(data)
        await self.commit()
        return self._read(row)

    async def list(self, person_id: UUID) -> list[AstroChartRead]:
        await self._require_person(person_id)
        return [self._read(row) for row in await self.repository.list_by_person(person_id)]

    async def get(self, chart_id: UUID) -> AstroChartRead:
        row = await self.repository.get(chart_id)
        if row is None:
            raise NotFoundError("Astro chart not found")
        return self._read(row)

    async def update(
        self, chart_id: UUID, data: AstroChartUpdate
    ) -> AstroChartRead:
        row = await self.repository.update(chart_id, data)
        if row is None:
            raise NotFoundError("Astro chart not found")
        await self.commit()
        return self._read(row)

    async def delete(self, chart_id: UUID) -> None:
        if not await self.repository.delete(chart_id):
            raise NotFoundError("Astro chart not found")
        await self.commit()
