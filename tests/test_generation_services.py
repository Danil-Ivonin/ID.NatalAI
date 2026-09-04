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


class CharacterRepository:
    def __init__(self, character=None) -> None:
        self.character = character

    async def get_profile(self, character_id):
        return self.character


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
    generation_id = uuid4()
    row = SimpleNamespace(
        id=uuid4(),
        person_id=person_id,
        generation_id=generation_id,
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
            generation_id=generation_id,
            natal_xml="<chart />",
            chart_svg="charts/a.svg",
        )
    )
    updated = await service.update(row.id, AstroChartUpdate(chart_svg="charts/b.svg"))

    assert created.chart_svg == "https://s3.test/charts/a.svg"
    assert created.generation_id == generation_id
    assert updated.id == row.id
    assert storage.keys == ["charts/a.svg", "charts/a.svg"]
    assert commit.calls == 2


@pytest.mark.asyncio
async def test_generation_neutral_service_returns_typed_result_and_commits() -> None:
    from app.services.generation_neutral_service import GenerationNeutralService

    person_id = uuid4()
    generation_id = uuid4()
    result = neutral_result()
    row = SimpleNamespace(
        id=uuid4(),
        person_id=person_id,
        generation_id=generation_id,
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
            generation_id=generation_id,
            used_model="model",
            prompt="prompt",
            token_usage={"total_tokens": 42},
            result=result,
        )
    )
    updated = await service.update(row.id, GenerationNeutralUpdate(prompt="new"))
    await service.delete(row.id)

    assert created.result.blocks[0].id.value == "general"
    assert created.generation_id == generation_id
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


@pytest.mark.asyncio
async def test_generation_service_checks_parents_and_commits_crud() -> None:
    from app.domain.generations.schemas import GenerationCreate, GenerationUpdate
    from app.services.generation_service import GenerationService

    person_id = uuid4()
    character_id = uuid4()
    row = SimpleNamespace(
        generation_id=uuid4(),
        person_id=person_id,
        character_id=character_id,
        used_examples=[],
        current_block="general",
        status="pending",
        payed=False,
        payment_id=None,
    )
    commit = Commit()
    service = GenerationService(
        Repository(row),
        UserRepository(SimpleNamespace()),
        CharacterRepository(SimpleNamespace()),
        commit,
    )

    created = await service.create(
        GenerationCreate(
            person_id=person_id,
            character_id=character_id,
            current_block="general",
        )
    )
    await service.update(row.generation_id, GenerationUpdate(payed=True))
    await service.delete(row.generation_id)

    assert created.generation_id == row.generation_id
    assert commit.calls == 3

    missing = GenerationService(
        Repository(), UserRepository(), CharacterRepository(), Commit()
    )
    with pytest.raises(NotFoundError, match="Person not found"):
        await missing.create(
            GenerationCreate(
                person_id=person_id,
                character_id=character_id,
                current_block="general",
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "service_name", "create_name", "not_found"),
    [
        (
            "app.services.generation_style_plan_service",
            "GenerationStylePlanService",
            "GenerationStylePlanCreate",
            "Generation style plan not found",
        ),
        (
            "app.services.generation_character_block_service",
            "GenerationCharacterBlockService",
            "GenerationCharacterBlockCreate",
            "Generation character block not found",
        ),
    ],
)
async def test_generation_step_services_require_generation_and_commit(
    module, service_name, create_name, not_found
) -> None:
    from importlib import import_module

    from app.domain.generations import schemas

    row = SimpleNamespace(
        id=uuid4(),
        plan_id=uuid4(),
        generation_id=uuid4(),
        block="general",
        status="pending",
        used_model="model",
        prompt="prompt",
        token_usage={},
        result={},
    )
    commit = Commit()
    service_type = getattr(import_module(module), service_name)
    service = service_type(Repository(row), Repository(row), commit)
    payload = getattr(schemas, create_name)(
        generation_id=row.generation_id,
        block="general",
        used_model="model",
        prompt="prompt",
        token_usage={},
        result={},
    )

    assert (await service.create(payload)).generation_id == row.generation_id
    await service.delete(row.id if "Review" in service_name else row.plan_id)
    assert commit.calls == 2

    missing = service_type(Repository(), Repository(), Commit())
    with pytest.raises(NotFoundError, match="Generation not found"):
        await missing.create(payload)
