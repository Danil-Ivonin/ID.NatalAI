from datetime import date, time
from inspect import iscoroutinefunction
from uuid import uuid4

import pytest

from app.domain.generation.enums import GenerationStatus
from app.domain.generation.schemas import BirthPlace, GenerationCreate
from app.domain.persona.schemas import (
    PersonaCreate,
    PersonaPhraseTemplateCreate,
    PersonaQuoteCreate,
    PersonaStyleExampleCreate,
    PersonaStyleProfileCreate,
)
from app.domain.prompts.enums import PromptTemplateType
from app.domain.prompts.models import PromptTemplate
from app.domain.prompts.schemas import PromptTemplateCreate


class FakeSession:
    def __init__(self, get_result=None) -> None:
        self.added = []
        self.get_result = get_result
        self.flushed = 0
        self.refreshed = []

    def add(self, instance) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushed += 1

    async def refresh(self, instance) -> None:
        self.refreshed.append(instance)

    async def get(self, model, model_id):
        return self.get_result


def test_repository_methods_are_async_contracts() -> None:
    from app.repositories.generation_repository import GenerationRepository
    from app.repositories.persona_repository import PersonaRepository
    from app.repositories.prompt_template_repository import PromptTemplateRepository

    generation_methods = [
        "create",
        "get",
        "set_status",
        "save_natal_xml",
        "save_profile",
        "save_result",
        "fail",
        "create_run",
    ]
    persona_methods = [
        "create",
        "update",
        "get",
        "list",
        "get_active",
        "get_context_persona",
        "get_style_profile",
        "list_allowed_quotes",
        "list_phrase_templates",
        "list_style_examples",
    ]
    prompt_methods = ["create", "list", "get", "get_active", "activate"]

    for repository_cls, methods in [
        (GenerationRepository, generation_methods),
        (PersonaRepository, persona_methods),
        (PromptTemplateRepository, prompt_methods),
    ]:
        for method in methods:
            assert iscoroutinefunction(getattr(repository_cls, method))


@pytest.mark.asyncio
async def test_generation_create_flattens_birth_place_and_starts_pending() -> None:
    from app.repositories.generation_repository import GenerationRepository

    session = FakeSession()
    repository = GenerationRepository(session)
    persona_id = uuid4()

    generation = await repository.create(
        GenerationCreate(
            person_name="Ada",
            gender=None,
            birth_date=date(1990, 1, 2),
            birth_time=time(3, 4),
            birth_place=BirthPlace(
                city="Moscow",
                country="Russia",
                lat=55.7558,
                lng=37.6173,
                timezone="Europe/Moscow",
            ),
            persona_id=persona_id,
        )
    )

    assert session.added == [generation]
    assert session.flushed == 1
    assert session.refreshed == [generation]
    assert generation.persona_id == persona_id
    assert generation.birth_city == "Moscow"
    assert generation.birth_country == "Russia"
    assert generation.birth_lat == 55.7558
    assert generation.birth_lng == 37.6173
    assert generation.birth_timezone == "Europe/Moscow"
    assert generation.status == GenerationStatus.PENDING


@pytest.mark.asyncio
async def test_generation_save_result_sets_completed_state() -> None:
    from app.domain.generation.models import Generation
    from app.repositories.generation_repository import GenerationRepository

    generation = Generation(
        person_name=None,
        gender=None,
        birth_date=date(1990, 1, 2),
        birth_time=time(3, 4),
        birth_city="Moscow",
        birth_country="Russia",
        birth_lat=55.7558,
        birth_lng=37.6173,
        birth_timezone="Europe/Moscow",
        persona_id=uuid4(),
    )
    repository = GenerationRepository(FakeSession(get_result=generation))

    await repository.save_result(generation.id, {"title": "Report"}, "Report text")

    assert generation.result_json == {"title": "Report"}
    assert generation.result_text == "Report text"
    assert generation.status == GenerationStatus.COMPLETED
    assert generation.completed_at is not None


@pytest.mark.asyncio
async def test_persona_create_builds_nested_context_data() -> None:
    from app.repositories.persona_repository import PersonaRepository

    session = FakeSession()
    repository = PersonaRepository(session)

    persona = await repository.create(
        PersonaCreate(
            name="Shrek",
            slug="shrek",
            description="Direct fairy tale swamp wisdom.",
            style_profile=PersonaStyleProfileCreate(
                voice_description="Blunt, warm, and impatient.",
                humor_style="Dry roasts.",
                speech_patterns=["short sentences"],
                forbidden_rules=["no hate"],
                allowed_rules=["tease lightly"],
            ),
            quotes=[
                PersonaQuoteCreate(text="Better out than in.", is_allowed=True),
                PersonaQuoteCreate(text="Forbidden quote.", is_allowed=False),
            ],
            phrase_templates=[
                PersonaPhraseTemplateCreate(
                    type="intro",
                    template="{subject}, listen.",
                    usage="openings",
                )
            ],
            style_examples=[
                PersonaStyleExampleCreate(
                    title="Advice",
                    text="That plan needs boots.",
                    tags=["advice"],
                )
            ],
        )
    )

    assert session.added == [persona]
    assert persona.style_profile.voice_description == "Blunt, warm, and impatient."
    assert [quote.text for quote in persona.quotes] == [
        "Better out than in.",
        "Forbidden quote.",
    ]
    assert persona.phrase_templates[0].template == "{subject}, listen."
    assert persona.style_examples[0].tags == ["advice"]


@pytest.mark.asyncio
async def test_prompt_template_create_uses_metadata_alias() -> None:
    from app.repositories.prompt_template_repository import PromptTemplateRepository

    session = FakeSession()
    repository = PromptTemplateRepository(session)

    template = await repository.create(
        PromptTemplateCreate(
            name="Profile v1",
            type=PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION,
            version=1,
            content="Extract profile",
            metadata={"model": "test-model"},
        )
    )

    assert session.added == [template]
    assert template.template_metadata == {"model": "test-model"}
    assert template.is_active is True


@pytest.mark.asyncio
async def test_prompt_activate_deactivates_existing_templates(monkeypatch) -> None:
    from app.repositories.prompt_template_repository import PromptTemplateRepository

    active = PromptTemplate(
        id=uuid4(),
        name="Profile v1",
        type=PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION,
        version=1,
        content="old",
        is_active=True,
        template_metadata={},
    )
    target = PromptTemplate(
        id=uuid4(),
        name="Profile v2",
        type=PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION,
        version=2,
        content="new",
        is_active=False,
        template_metadata={},
    )
    repository = PromptTemplateRepository(FakeSession())

    async def fake_get(template_id):
        return target if template_id == target.id else None

    async def fake_list(template_type=None):
        assert template_type == PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION
        return [active, target]

    monkeypatch.setattr(repository, "get", fake_get)
    monkeypatch.setattr(repository, "list", fake_list)

    activated = await repository.activate(target.id)

    assert activated is target
    assert active.is_active is False
    assert target.is_active is True
