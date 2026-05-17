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


class FakeWriteSession(FakeSession):
    async def refresh(self, instance) -> None:
        raise AssertionError("repository should re-query instead of refreshing")


class FakeScalarResult:
    def __init__(self, values) -> None:
        self.values = values

    def all(self):
        return self.values


class FakeExecuteResult:
    def __init__(self, scalar=None, scalars=None) -> None:
        self.scalar = scalar
        self.scalars_values = scalars

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return FakeScalarResult(self.scalars_values)


class FakeExecuteSession:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.executed = []

    async def execute(self, statement):
        self.executed.append(statement)
        return self.results.pop(0)


class FakePromptWriteSession(FakeSession):
    def __init__(self, get_result=None) -> None:
        super().__init__(get_result=get_result)
        self.operations = []
        self.executed = []

    def add(self, instance) -> None:
        super().add(instance)
        self.operations.append(("add", instance))

    async def execute(self, statement):
        self.executed.append(statement)
        self.operations.append(("execute", statement))
        return FakeExecuteResult(scalars=[])

    async def flush(self) -> None:
        await super().flush()
        self.operations.append(("flush", None))

    async def refresh(self, instance) -> None:
        await super().refresh(instance)
        self.operations.append(("refresh", instance))


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
async def test_persona_create_builds_nested_context_data(monkeypatch) -> None:
    from app.repositories.persona_repository import PersonaRepository

    session = FakeWriteSession()
    repository = PersonaRepository(session)
    loaded_persona = object()

    async def fake_get(persona_id):
        assert persona_id == session.added[0].id
        return loaded_persona

    monkeypatch.setattr(repository, "get", fake_get)

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

    created_persona = session.added[0]
    assert persona is loaded_persona
    assert created_persona.style_profile.voice_description == "Blunt, warm, and impatient."
    assert [quote.text for quote in created_persona.quotes] == [
        "Better out than in.",
        "Forbidden quote.",
    ]
    assert created_persona.phrase_templates[0].template == "{subject}, listen."
    assert created_persona.style_examples[0].tags == ["advice"]


@pytest.mark.asyncio
async def test_persona_context_loading_methods_execute_queries_and_return_results() -> None:
    from app.domain.persona.models import (
        Persona,
        PersonaPhraseTemplate,
        PersonaQuote,
        PersonaStyleExample,
        PersonaStyleProfile,
    )
    from app.repositories.persona_repository import PersonaRepository

    persona_id = uuid4()
    persona = Persona(
        id=persona_id,
        name="Shrek",
        slug="shrek",
        description="Direct swamp wisdom.",
        is_active=True,
    )
    style_profile = PersonaStyleProfile(
        persona_id=persona_id,
        voice_description="Blunt.",
        humor_style="Dry.",
        speech_patterns=["short"],
        forbidden_rules=["no hate"],
        allowed_rules=["tease lightly"],
    )
    allowed_quote = PersonaQuote(
        persona_id=persona_id,
        text="Better out than in.",
        usage_context="general",
        is_allowed=True,
    )
    phrase_template = PersonaPhraseTemplate(
        persona_id=persona_id,
        type="intro",
        template="{subject}, listen.",
        usage="openings",
    )
    style_example = PersonaStyleExample(
        persona_id=persona_id,
        title="Advice",
        text="That plan needs boots.",
        tags=["advice"],
    )
    session = FakeExecuteSession(
        [
            FakeExecuteResult(scalar=persona),
            FakeExecuteResult(scalar=style_profile),
            FakeExecuteResult(scalars=[allowed_quote]),
            FakeExecuteResult(scalars=[phrase_template]),
            FakeExecuteResult(scalars=[style_example]),
        ]
    )
    repository = PersonaRepository(session)

    assert await repository.get_context_persona(persona_id) is persona
    assert await repository.get_style_profile(persona_id) is style_profile
    assert await repository.list_allowed_quotes(persona_id) == [allowed_quote]
    assert await repository.list_phrase_templates(persona_id) == [phrase_template]
    assert await repository.list_style_examples(persona_id) == [style_example]

    assert len(session.executed) == 5
    compiled_queries = [str(statement) for statement in session.executed]
    assert "FROM personas" in compiled_queries[0]
    assert "personas.is_active IS true" in compiled_queries[0]
    assert "FROM persona_style_profiles" in compiled_queries[1]
    assert "FROM persona_quotes" in compiled_queries[2]
    assert "persona_quotes.is_allowed IS true" in compiled_queries[2]
    assert "FROM persona_phrase_templates" in compiled_queries[3]
    assert "FROM persona_style_examples" in compiled_queries[4]


@pytest.mark.asyncio
async def test_persona_get_and_list_eager_load_all_read_relationships() -> None:
    from app.repositories.persona_repository import PersonaRepository

    session = FakeExecuteSession(
        [
            FakeExecuteResult(scalar=None),
            FakeExecuteResult(scalars=[]),
        ]
    )
    repository = PersonaRepository(session)

    await repository.get(uuid4())
    await repository.list()

    assert len(session.executed[0]._with_options) == 4
    assert len(session.executed[1]._with_options) == 4


@pytest.mark.asyncio
async def test_prompt_template_create_uses_metadata_alias() -> None:
    from app.repositories.prompt_template_repository import PromptTemplateRepository

    session = FakePromptWriteSession()
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
async def test_prompt_template_create_active_bulk_deactivates_before_insert() -> None:
    from app.repositories.prompt_template_repository import PromptTemplateRepository

    session = FakePromptWriteSession()
    repository = PromptTemplateRepository(session)

    created = await repository.create(
        PromptTemplateCreate(
            name="Profile v2",
            type=PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION,
            version=2,
            content="new",
            is_active=True,
            metadata={},
        )
    )

    assert created.is_active is True
    assert [operation for operation, _ in session.operations] == [
        "execute",
        "flush",
        "add",
        "flush",
        "refresh",
    ]
    deactivation_statement = session.executed[0]
    assert deactivation_statement.is_update
    compiled = str(deactivation_statement.compile(compile_kwargs={"literal_binds": True}))
    assert compiled.startswith("UPDATE prompt_templates")
    assert "is_active=false" in compiled


@pytest.mark.asyncio
async def test_prompt_activate_bulk_deactivates_and_flushes_before_target_activation(
    monkeypatch,
) -> None:
    from app.repositories.prompt_template_repository import PromptTemplateRepository

    target = PromptTemplate(
        id=uuid4(),
        name="Profile v2",
        type=PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION,
        version=2,
        content="new",
        is_active=False,
        template_metadata={},
    )
    session = FakePromptWriteSession()
    repository = PromptTemplateRepository(session)

    async def fake_get(template_id):
        return target if template_id == target.id else None

    monkeypatch.setattr(repository, "get", fake_get)

    activated = await repository.activate(target.id)

    assert activated is target
    assert target.is_active is True
    assert [operation for operation, _ in session.operations] == [
        "execute",
        "flush",
        "flush",
        "refresh",
    ]
    deactivation_statement = session.executed[0]
    assert deactivation_statement.is_update
    compiled = str(deactivation_statement.compile(compile_kwargs={"literal_binds": True}))
    assert compiled.startswith("UPDATE prompt_templates")
    assert "is_active=false" in compiled
    assert "prompt_templates.id !=" in compiled
