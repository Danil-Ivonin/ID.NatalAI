from copy import deepcopy

import pytest
from sqlalchemy.dialects import postgresql

from app.domain.characters.enums import CharacterEmotion
from app.domain.characters.schemas import (
    CharacterExampleCreate,
    CharacterExampleEmbedding,
    CharacterExampleSearch,
    CharacterProfileCreate,
)
from app.repositories.character_example_repository import CharacterExampleRepository
from app.repositories.character_repository import CharacterRepository


PROFILE = {
    "name": "Имя персонажа",
    "core": {
        "self_image": "Честный собеседник.",
        "worldview": ["Привычку часто называют судьбой."],
        "values": ["Честность"],
        "blind_spots": ["Осторожность"],
    },
    "astrology_position": {
        "role": "Говорит о выборе.",
        "interpretation_style": "Психологический интерпретатор",
    },
    "reader_relationship": {
        "position": "Собеседник",
        "address": "На ты",
        "distance": "Близкая",
        "care_style": "Критикует поступок.",
    },
    "voice": {
        "diction": ["Разговорная"],
        "syntax": ["Короткий вывод"],
        "directness": "Прямо",
        "emotional_range": ["calm"],
    },
    "humor": {
        "targets": ["Самообман"],
        "boundaries": ["Травма"],
        "mechanics": ["Наблюдение и вывод"],
    },
    "monologue_structure": {
        "opening": "Наблюдение.",
        "development": "Противоречие.",
        "transitions": "Общий мотив.",
        "ending": "Направление.",
    },
    "do_not": ["Не пародировать"],
}


class ScalarResult:
    def __init__(self, values) -> None:
        self._values = values

    def all(self):
        return self._values


class ExecuteResult:
    def __init__(self, values) -> None:
        self._values = values

    def scalars(self):
        return ScalarResult(self._values)


class FakeSession:
    def __init__(self, get_result=None, search_results=()) -> None:
        self.get_result = get_result
        self.search_results = list(search_results)
        self.added = []
        self.flushed = 0
        self.statement = None

    def add(self, row) -> None:
        if row.id is None:
            row.id = len(self.added) + 1
        self.added.append(row)

    async def flush(self) -> None:
        self.flushed += 1

    async def get(self, model, row_id):
        return self.get_result

    async def execute(self, statement):
        self.statement = statement
        return ExecuteResult(self.search_results)


def profile_create(**changes) -> CharacterProfileCreate:
    return CharacterProfileCreate.model_validate(deepcopy(PROFILE) | changes)


def example_create(**changes) -> CharacterExampleCreate:
    values = {
        "character_id": 1,
        "raw_text": "Исходная реплика",
        "clean_text": "Чистая реплика",
        "context": "Контекст",
        "emotion": "skepticism",
        "rhetorical_function": "Вскрыть самообман",
        "humor_types": ["irony"],
        "speech_patterns": ["observation"],
    }
    return CharacterExampleCreate.model_validate(values | changes)


@pytest.mark.asyncio
async def test_character_repository_round_trips_typed_profile() -> None:
    session = FakeSession()
    created = await CharacterRepository(session).create(profile_create())

    assert created.character_id == 1
    assert created.name == "Имя персонажа"
    assert session.added[0].profile["voice"]["directness"] == "Прямо"
    assert "name" not in session.added[0].profile
    assert session.flushed == 1


@pytest.mark.asyncio
async def test_replace_profile_updates_whole_document() -> None:
    create_session = FakeSession()
    await CharacterRepository(create_session).create(profile_create())
    row = create_session.added[0]
    session = FakeSession(get_result=row)

    updated = await CharacterRepository(session).replace_profile(
        row.id,
        profile_create(name="Другое имя"),
    )

    assert updated is not None
    assert updated.name == "Другое имя"
    assert row.profile == profile_create(name="Другое имя").model_dump(
        mode="json", exclude={"name"}
    )


@pytest.mark.asyncio
async def test_replace_profile_returns_none_when_character_missing() -> None:
    repository = CharacterRepository(FakeSession(get_result=None))
    assert await repository.replace_profile(999, profile_create()) is None


@pytest.mark.asyncio
async def test_example_mutations_return_typed_models() -> None:
    create_session = FakeSession()
    created = await CharacterExampleRepository(create_session).create(example_create())
    row = create_session.added[0]
    update_session = FakeSession(get_result=row)
    repository = CharacterExampleRepository(update_session)

    embedded = await repository.set_embedding(
        row.id,
        CharacterExampleEmbedding(embedding=[0.0] * 3072),
    )
    inactive = await repository.set_active(row.id, False)

    assert created.id == row.id
    assert embedded is not None and len(embedded.embedding or []) == 3072
    assert inactive is not None and inactive.active is False
    assert update_session.flushed == 2


@pytest.mark.asyncio
async def test_search_builds_required_filters_and_soft_ranking() -> None:
    session = FakeSession()
    await CharacterExampleRepository(session).search(
        CharacterExampleSearch(
            character_id=7,
            embedding=[0.0] * 3072,
            emotion=CharacterEmotion.SKEPTICISM,
            humor_types=["irony"],
            speech_patterns=["observation"],
            exclude_ids={3, 4},
            limit=6,
        )
    )

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "character_examples.character_id" in sql
    assert "character_examples.active IS true" in sql
    assert "character_examples.embedding IS NOT NULL" in sql
    assert "<=>" in sql
    assert sql.count("&&") == 2
    assert "NOT IN" in sql
    assert "LIMIT" in sql


@pytest.mark.asyncio
async def test_search_omits_empty_optional_filters() -> None:
    session = FakeSession()
    await CharacterExampleRepository(session).search(
        CharacterExampleSearch(
            character_id=7,
            embedding=[0.0] * 3072,
            emotion="calm",
        )
    )

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "&&" not in sql
    assert "NOT IN" not in sql
