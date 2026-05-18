import pytest

from app.domain.persona.models import (
    Persona,
    PersonaPhraseTemplate,
    PersonaQuote,
    PersonaStyleExample,
    PersonaStyleProfile,
)
from app.domain.prompts.enums import PromptTemplateType
from app.domain.prompts.models import PromptTemplate


class FakeExecuteResult:
    def __init__(self, scalar=None, scalars=None) -> None:
        self.scalar = scalar
        self.scalars_values = scalars or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return self

    def all(self):
        return self.scalars_values


class FakeSeedSession:
    def __init__(self) -> None:
        self.prompts = []
        self.personas = []
        self.style_profiles = []
        self.quotes = []
        self.phrase_templates = []
        self.style_examples = []
        self.added = []
        self.flushed = 0
        self.committed = 0
        self.executed = []

    def add(self, instance) -> None:
        self.added.append(instance)
        if isinstance(instance, PromptTemplate):
            self.prompts.append(instance)
        elif isinstance(instance, Persona):
            self.personas.append(instance)
        elif isinstance(instance, PersonaStyleProfile):
            self.style_profiles.append(instance)
        elif isinstance(instance, PersonaQuote):
            self.quotes.append(instance)
        elif isinstance(instance, PersonaPhraseTemplate):
            self.phrase_templates.append(instance)
        elif isinstance(instance, PersonaStyleExample):
            self.style_examples.append(instance)

    async def execute(self, statement):
        self.executed.append(statement)
        sql = str(statement)
        if "FROM prompt_templates" in sql:
            prompt_type = statement.compile().params.get("type_1")
            version = statement.compile().params.get("version_1")
            rows = [
                prompt
                for prompt in self.prompts
                if prompt.type == prompt_type and prompt.version == version
            ]
            return FakeExecuteResult(scalar=rows[0] if rows else None, scalars=rows)
        if "FROM personas" in sql:
            slug = statement.compile().params.get("slug_1")
            rows = [persona for persona in self.personas if persona.slug == slug]
            return FakeExecuteResult(scalar=rows[0] if rows else None, scalars=rows)
        if "FROM persona_style_profiles" in sql:
            rows = [
                profile
                for profile in self.style_profiles
                if profile.persona_id == statement.compile().params.get("persona_id_1")
            ]
            return FakeExecuteResult(scalar=rows[0] if rows else None, scalars=rows)
        if "FROM persona_quotes" in sql:
            text = statement.compile().params.get("text_1")
            rows = [quote for quote in self.quotes if quote.text == text]
            return FakeExecuteResult(scalar=rows[0] if rows else None, scalars=rows)
        if "FROM persona_phrase_templates" in sql:
            params = statement.compile().params
            rows = [
                template
                for template in self.phrase_templates
                if template.template == params.get("template_1")
                and template.type == params.get("type_1")
            ]
            return FakeExecuteResult(scalar=rows[0] if rows else None, scalars=rows)
        if "FROM persona_style_examples" in sql:
            title = statement.compile().params.get("title_1")
            rows = [example for example in self.style_examples if example.title == title]
            return FakeExecuteResult(scalar=rows[0] if rows else None, scalars=rows)
        raise AssertionError(f"unexpected statement: {sql}")

    async def flush(self) -> None:
        self.flushed += 1

    async def commit(self) -> None:
        self.committed += 1


def test_seed_data_contains_required_prompt_and_persona_markers() -> None:
    from app.db import seed

    prompt_types = {prompt.type for prompt in seed.PROMPT_TEMPLATES}

    assert prompt_types == {
        PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION,
        PromptTemplateType.STYLED_REPORT_GENERATION,
    }
    assert all(prompt.version == 1 and prompt.is_active for prompt in seed.PROMPT_TEMPLATES)
    assert all("USER PROMPT TEMPLATE" in prompt.content for prompt in seed.PROMPT_TEMPLATES)
    assert any("наталь" in prompt.content.lower() for prompt in seed.PROMPT_TEMPLATES)
    assert seed.SHREK_PERSONA.slug == "shrek"
    assert seed.SHREK_PERSONA.name == "Шрек"
    assert any("maximum-intensity roast" in rule for rule in seed.SHREK_STYLE.allowed_rules)
    assert any("protected-class dehumanization" in rule for rule in seed.SHREK_STYLE.forbidden_rules)
    assert seed.SHREK_PHRASE_TEMPLATES
    assert seed.SHREK_STYLE_EXAMPLES


@pytest.mark.asyncio
async def test_dry_run_prints_plan_without_opening_session(monkeypatch, capsys) -> None:
    from app.db import seed

    def fail_session_factory():
        raise AssertionError("dry run must not open a database session")

    monkeypatch.setattr(seed, "async_session_factory", fail_session_factory)

    await seed.run_seed(dry_run=True)

    output = capsys.readouterr().out
    assert "DRY RUN" in output
    assert "prompt_template astrology_profile_extraction v1" in output
    assert "persona shrek" in output


@pytest.mark.asyncio
async def test_seed_is_idempotent_by_natural_keys() -> None:
    from app.db import seed

    session = FakeSeedSession()

    first_plan = await seed.seed_session(session)
    second_plan = await seed.seed_session(session)

    assert any(item.action == "insert" for item in first_plan)
    assert all(item.action == "update" for item in second_plan)
    assert len(session.prompts) == 2
    assert len(session.personas) == 1
    assert len(session.style_profiles) == 1
    assert len(session.quotes) == len({quote.text for quote in session.quotes})
    assert len(session.phrase_templates) == {
        (template.template, template.type) for template in session.phrase_templates
    }.__len__()
    assert len(session.style_examples) == len(
        {example.title for example in session.style_examples}
    )
    assert session.committed == 2
