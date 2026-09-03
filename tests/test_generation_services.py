from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.domain.generations.astro_charts.schemas import AstroChartCreate, AstroChartUpdate
from app.domain.generations.generation_neutral.schemas import (
    GenerationNeutralCreate,
    GenerationNeutralResult,
    GenerationNeutralUpdate,
)


class Commit:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> None:
        self.calls += 1


class UserRepository:
    def __init__(self, person=None) -> None:
        self.person = person

    async def get_person_by_id(self, person_id):
        return self.person


class Storage:
    def __init__(self) -> None:
        self.keys = []

    def presigned_url(self, object_key: str) -> str:
        self.keys.append(object_key)
        return f"https://s3.test/{object_key}"


class Repository:
    def __init__(self, row=None) -> None:
        self.row = row
        self.created = []

    async def create(self, data):
        self.created.append(data)
        return self.row

    async def list_by_person(self, person_id):
        return [] if self.row is None else [self.row]

    async def get(self, row_id):
        return self.row

    async def update(self, row_id, data):
        return self.row

    async def delete(self, row_id):
        return self.row is not None


def neutral_result() -> GenerationNeutralResult:
    return GenerationNeutralResult.model_validate(
        {
            "blocks": [
                {
                    "id": block_id,
                    "title": block_id,
                    "summary": "Сводка.",
                    "facts": [],
                    "hooks": [],
                }
                for block_id in ["general", "love", "work_money", "inner_demons"]
            ]
        }
    )


@pytest.mark.asyncio
async def test_astro_chart_service_checks_person_commits_and_signs_url() -> None:
    from app.services.astro_chart_service import AstroChartService

    person_id = uuid4()
    row = SimpleNamespace(
        id=uuid4(),
        person_id=person_id,
        natal_xml="<chart />",
        chart_svg="charts/a.svg",
    )
    repository = Repository(row)
    commit = Commit()
    storage = Storage()
    service = AstroChartService(
        repository, UserRepository(SimpleNamespace()), storage, commit
    )

    created = await service.create(
        AstroChartCreate(
            person_id=person_id,
            natal_xml="<chart />",
            chart_svg="charts/a.svg",
        )
    )
    updated = await service.update(row.id, AstroChartUpdate(chart_svg="charts/b.svg"))

    assert created.chart_svg == "https://s3.test/charts/a.svg"
    assert updated.id == row.id
    assert storage.keys == ["charts/a.svg", "charts/a.svg"]
    assert commit.calls == 2


@pytest.mark.asyncio
async def test_generation_neutral_service_returns_typed_result_and_commits() -> None:
    from app.services.generation_neutral_service import GenerationNeutralService

    person_id = uuid4()
    result = neutral_result()
    row = SimpleNamespace(
        id=uuid4(),
        person_id=person_id,
        used_model="model",
        prompt="prompt",
        token_usage={"total_tokens": 42},
        result=result.model_dump(mode="json"),
    )
    commit = Commit()
    service = GenerationNeutralService(
        Repository(row), UserRepository(SimpleNamespace()), commit
    )

    created = await service.create(
        GenerationNeutralCreate(
            person_id=person_id,
            used_model="model",
            prompt="prompt",
            token_usage={"total_tokens": 42},
            result=result,
        )
    )
    updated = await service.update(row.id, GenerationNeutralUpdate(prompt="new"))
    await service.delete(row.id)

    assert created.result.blocks[0].id.value == "general"
    assert updated.id == row.id
    assert commit.calls == 3


@pytest.mark.asyncio
async def test_generation_services_reject_missing_person_and_resource() -> None:
    from app.services.astro_chart_service import AstroChartService
    from app.services.generation_neutral_service import GenerationNeutralService

    person_id = uuid4()
    commit = Commit()
    astro = AstroChartService(Repository(), UserRepository(), Storage(), commit)
    neutral = GenerationNeutralService(Repository(), UserRepository(), commit)

    with pytest.raises(NotFoundError, match="Person not found"):
        await astro.list(person_id)
    with pytest.raises(NotFoundError, match="Person not found"):
        await neutral.create(
            GenerationNeutralCreate(
                person_id=person_id,
                used_model="model",
                prompt="prompt",
                token_usage={},
                result=neutral_result(),
            )
        )
    with pytest.raises(NotFoundError, match="Astro chart not found"):
        await astro.get(uuid4())
    with pytest.raises(NotFoundError, match="Neutral generation not found"):
        await neutral.delete(uuid4())

    assert commit.calls == 0
