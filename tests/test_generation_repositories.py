from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.domain.generations.astro_charts.schemas import AstroChartCreate, AstroChartUpdate
from app.domain.generations.generation_neutral.schemas import (
    GenerationNeutralCreate,
    GenerationNeutralResult,
    GenerationNeutralUpdate,
)


class ScalarResult:
    def __init__(self, values) -> None:
        self.values = values

    def all(self):
        return self.values


class ExecuteResult:
    def __init__(self, values) -> None:
        self.values = values

    def scalars(self):
        return ScalarResult(self.values)


class FakeSession:
    def __init__(self, *, get_result=None, execute_results=()) -> None:
        self.get_result = get_result
        self.execute_results = list(execute_results)
        self.added = []
        self.deleted = []
        self.statements = []
        self.flushed = 0

    def add(self, row) -> None:
        if row.id is None:
            row.id = uuid4()
        self.added.append(row)

    async def get(self, model, row_id):
        return self.get_result

    async def execute(self, statement):
        self.statements.append(statement)
        return ExecuteResult(self.execute_results.pop(0))

    async def flush(self) -> None:
        self.flushed += 1

    async def delete(self, row) -> None:
        self.deleted.append(row)


def result() -> GenerationNeutralResult:
    return GenerationNeutralResult.model_validate(
        {
            "blocks": [
                {
                    "id": block_id,
                    "title": title,
                    "summary": "Сводка.",
                    "facts": [],
                    "hooks": [],
                }
                for block_id, title in [
                    ("general", "Общая информация"),
                    ("love", "Любовь и отношения"),
                    ("work_money", "Работа и деньги"),
                    ("inner_demons", "Внутренние демоны"),
                ]
            ]
        }
    )


@pytest.mark.asyncio
async def test_astro_chart_repository_crud_lifecycle() -> None:
    from app.repositories.astro_chart_repository import AstroChartRepository

    person_id = uuid4()
    create_session = FakeSession()
    created = await AstroChartRepository(create_session).create(
        AstroChartCreate(
            person_id=person_id,
            natal_xml="<chart />",
            chart_svg="charts/a.svg",
        )
    )
    session = FakeSession(get_result=created, execute_results=[[created]])
    repository = AstroChartRepository(session)

    assert await repository.list_by_person(person_id) == [created]
    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert "astro_charts.person_id" in sql
    assert await repository.get(created.id) is created
    updated = await repository.update(
        created.id, AstroChartUpdate(chart_svg="charts/b.svg")
    )
    assert updated is not None and updated.chart_svg == "charts/b.svg"
    assert await repository.delete(created.id)
    assert session.deleted == [created]


@pytest.mark.asyncio
async def test_generation_neutral_repository_crud_lifecycle() -> None:
    from app.repositories.generation_neutral_repository import (
        GenerationNeutralRepository,
    )

    person_id = uuid4()
    create_session = FakeSession()
    created = await GenerationNeutralRepository(create_session).create(
        GenerationNeutralCreate(
            person_id=person_id,
            used_model="openai/model",
            prompt="prompt",
            token_usage={"total_tokens": 42},
            result=result(),
        )
    )
    session = FakeSession(get_result=created, execute_results=[[created]])
    repository = GenerationNeutralRepository(session)

    assert created.result["blocks"][0]["id"] == "general"
    assert await repository.list_by_person(person_id) == [created]
    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert "generation_neutral.person_id" in sql
    assert await repository.get(created.id) is created
    updated = await repository.update(
        created.id, GenerationNeutralUpdate(prompt="new prompt")
    )
    assert updated is not None and updated.prompt == "new prompt"
    assert await repository.delete(created.id)
    assert session.deleted == [created]


@pytest.mark.asyncio
async def test_generation_repositories_return_missing_without_mutation() -> None:
    from app.repositories.astro_chart_repository import AstroChartRepository
    from app.repositories.generation_neutral_repository import (
        GenerationNeutralRepository,
    )

    session = FakeSession()
    assert await AstroChartRepository(session).update(uuid4(), AstroChartUpdate()) is None
    assert not await GenerationNeutralRepository(session).delete(uuid4())
    assert session.flushed == 0
    assert session.deleted == []
