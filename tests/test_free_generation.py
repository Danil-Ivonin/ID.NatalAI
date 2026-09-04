import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.openrouter_client import OpenRouterChatResult


class Repository:
    def __init__(self, row=None) -> None:
        self.row = row
        self.created = []
        self.updates = []

    async def get(self, _row_id):
        return self.row

    async def create(self, data):
        self.created.append(data)
        if hasattr(data, "generation_id") and hasattr(data, "block"):
            return SimpleNamespace(id=uuid4(), **data.model_dump())
        if hasattr(data, "generation_id") and hasattr(data, "natal_xml"):
            return SimpleNamespace(id=uuid4(), **data.model_dump())
        if hasattr(data, "person_id") and hasattr(data, "character_id"):
            return SimpleNamespace(generation_id=uuid4(), **data.model_dump())
        return SimpleNamespace(id=uuid4(), **data.model_dump(mode="json"))

    async def update(self, row_id, data):
        self.updates.append((row_id, data))
        return self.row


class UserRepository:
    def __init__(self, person) -> None:
        self.person = person

    async def get_person_by_id(self, _person_id):
        return self.person


class CharacterRepository:
    def __init__(self, character) -> None:
        self.character = character

    async def get_profile(self, _character_id):
        return self.character


class NatalChart:
    def build_natal_chart(self, **_kwargs):
        return SimpleNamespace(
            natal_xml="<chart />",
            chart_svg='<svg xmlns="http://www.w3.org/2000/svg" />',
        )


class Storage:
    def __init__(self) -> None:
        self.uploaded = []

    async def upload(self, key, content, mime_type):
        self.uploaded.append((key, content, mime_type))

    def presigned_url(self, key):
        return f"https://s3.test/{key}"


class OpenRouter:
    def __init__(self, payloads) -> None:
        self.payloads = iter(payloads)
        self.calls = []

    async def chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        return OpenRouterChatResult(
            content=json.dumps(next(self.payloads)),
            raw_response={},
            input_tokens=10,
            output_tokens=20,
            latency_ms=1,
        )


class Settings:
    openrouter_model_profile = "planner"
    openrouter_model_report = "writer"


@pytest.mark.asyncio
async def test_free_generation_persists_every_stage_and_returns_chart_and_blocks() -> None:
    from app.services.free_generation_service import FreeGenerationService

    person_id = uuid4()
    character_id = uuid4()
    person = SimpleNamespace(
        person_id=person_id,
        name="Анна",
        sex="female",
        birth_date=__import__("datetime").date(1992, 8, 14),
        birth_time=__import__("datetime").time(6, 45),
        birth_lat=51.6608,
        birth_lng=39.2003,
        birth_timezone="Europe/Moscow",
        birth_city="Воронеж",
        birth_nation="RU",
    )
    character = SimpleNamespace(
        model_dump=lambda mode=None: {"name": "Персонаж", "voice": "ироничный"}
    )
    neutral = {
        "blocks": [
            {
                "id": block,
                "title": block,
                "summary": "Сводка.",
                "facts": [],
                "hooks": [],
            }
            for block in ["general", "love", "work_money", "inner_demons"]
        ]
    }
    intro = {"title": "Вступление", "text": "Привет."}
    style_plan = {"block_arc": "От знакомства к выводу.", "hook_plans": []}
    general = {"title": "Общее", "text": "Основной текст."}
    generations = Repository()
    charts = Repository()
    neutrals = Repository()
    plans = Repository()
    blocks = Repository()
    commits = 0

    async def commit():
        nonlocal commits
        commits += 1

    events = []
    storage = Storage()
    openrouter = OpenRouter([neutral, intro, style_plan, general])
    service = FreeGenerationService(
        generation_repository=generations,
        astro_chart_repository=charts,
        neutral_repository=neutrals,
        style_plan_repository=plans,
        character_block_repository=blocks,
        user_repository=UserRepository(person),
        character_repository=CharacterRepository(character),
        natal_chart_service=NatalChart(),
        storage=storage,
        openrouter=openrouter,
        settings=Settings(),
        commit=commit,
        rollback=lambda: None,
    )

    result = await service.generate(person_id, character_id, events.append)

    assert [event["stage"] for event in events] == [
        "generation_created",
        "astro_chart_created",
        "neutral_generated",
        "intro_generated",
        "general_style_plan_generated",
        "general_generated",
    ]
    assert [row.block.value for row in blocks.created] == ["intro", "general"]
    assert plans.created[0].block.value == "general"
    assert result == {
        "generation_id": str(generations.created[0].person_id and events[0]["generation_id"]),
        "chart_url": f"https://s3.test/generations/{events[0]['generation_id']}/natal-chart.svg",
        "blocks": {"intro": intro, "general": general},
    }
    assert storage.uploaded[0][2] == "image/svg+xml"
    assert commits == 7
    payloads = [json.loads(call["messages"][-1]["content"]) for call in openrouter.calls]
    for index in (0, 1, 3):
        assert payloads[index]["subject"] == {"display_name": "Анна", "sex": "female"}
    for index in (1, 2, 3):
        assert payloads[index]["current_block"] == neutral["blocks"][0]
    for index in (2, 3):
        assert payloads[index]["previous_blocks"] == {"intro": intro}
    assert payloads[3]["style_plan"] == style_plan
    assert openrouter.calls[1]["messages"][:2] == openrouter.calls[3]["messages"][:2]
    for row, call in zip(
        [neutrals.created[0], blocks.created[0], plans.created[0], blocks.created[1]],
        openrouter.calls,
    ):
        assert json.loads(row.prompt) == call["messages"]
