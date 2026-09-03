import pytest

from app.domain.readings.schemas import NeutralChartReading, NeutralGeneration
from app.repositories.neutral_generation_repository import NeutralGenerationRepository


def reading() -> NeutralChartReading:
    return NeutralChartReading.model_validate(
        {
            "subject": {"display_name": "Анна", "sex": "female"},
            "blocks": [
                {
                    "id": block_id,
                    "title": title,
                    "summary": "Нейтральная сводка.",
                    "facts": [],
                    "hooks": [],
                }
                for block_id, title in [
                    ("general", "Общая информация"),
                    ("love", "Любовь и отношения"),
                    ("work_money", "Работа и деньги"),
                    ("inner_demons", "Внутренние демоны"),
                ]
            ],
        }
    )


class FakeSession:
    def __init__(self, get_result=None) -> None:
        self.get_result = get_result
        self.added = []
        self.flushed = 0

    def add(self, row) -> None:
        row.id = 1
        self.added.append(row)

    async def flush(self) -> None:
        self.flushed += 1

    async def get(self, model, row_id):
        return self.get_result


@pytest.mark.asyncio
async def test_neutral_generation_repository_round_trips_typed_reading() -> None:
    session = FakeSession()

    created = await NeutralGenerationRepository(session).create(reading())

    assert created == NeutralGeneration(id=1, reading=reading())
    assert session.added[0].reading["subject"]["sex"] == "female"
    assert session.flushed == 1


@pytest.mark.asyncio
async def test_neutral_generation_repository_gets_existing_record() -> None:
    create_session = FakeSession()
    await NeutralGenerationRepository(create_session).create(reading())

    loaded = await NeutralGenerationRepository(
        FakeSession(get_result=create_session.added[0])
    ).get(1)

    assert loaded == NeutralGeneration(id=1, reading=reading())


@pytest.mark.asyncio
async def test_neutral_generation_repository_returns_none_when_missing() -> None:
    assert await NeutralGenerationRepository(FakeSession()).get(999) is None
