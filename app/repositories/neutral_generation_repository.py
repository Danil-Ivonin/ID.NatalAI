from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.readings.models import NeutralGeneration as NeutralGenerationRow
from app.domain.readings.schemas import NeutralChartReading, NeutralGeneration


class NeutralGenerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_generation(row: NeutralGenerationRow) -> NeutralGeneration:
        return NeutralGeneration(id=row.id, reading=row.reading)

    async def create(self, reading: NeutralChartReading) -> NeutralGeneration:
        row = NeutralGenerationRow(reading=reading.model_dump(mode="json"))
        self.session.add(row)
        await self.session.flush()
        return self._to_generation(row)

    async def get(self, generation_id: int) -> NeutralGeneration | None:
        row = await self.session.get(NeutralGenerationRow, generation_id)
        return None if row is None else self._to_generation(row)
