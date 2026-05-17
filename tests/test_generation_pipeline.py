from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, time
from uuid import uuid4

import pytest
import respx
from httpx import Response

from app.core.exceptions import NotFoundError
from app.domain.generation.ai_schemas import AstrologyProfile, StyledNatalReport
from app.domain.generation.enums import GenerationStage, GenerationStatus
from app.domain.persona.models import (
    Persona,
    PersonaPhraseTemplate,
    PersonaQuote,
    PersonaStyleExample,
    PersonaStyleProfile,
)
from app.domain.prompts.enums import PromptTemplateType
from app.domain.prompts.models import PromptTemplate


def _profile_payload() -> dict:
    placement = {
        "name": "Sun in Aries",
        "meaning": "Direct and forceful.",
        "evidence": ["Sun sign Aries"],
    }
    trait = {"name": "bold", "description": "Acts first.", "evidence": ["Mars"]}
    pattern = {
        "name": "fast ignition",
        "description": "Starts quickly.",
        "evidence": ["Cardinal"],
    }
    strength_weakness = {
        "strength": "decisive",
        "weakness": "impatient",
        "evidence": ["Aries Sun"],
    }
    return {
        "subject": {
            "person_name": "Ada",
            "gender": "female",
            "birth_date": "1990-01-02",
            "birth_time": "03:04:00",
            "birth_place": "Moscow, Russia",
        },
        "chart_core": {
            "big_three": {
                "sun": placement,
                "moon": placement,
                "ascendant": placement,
                "summary": "Fire-forward.",
                "evidence": ["Big three"],
            },
            "dominants": {
                "planets": ["Mars"],
                "signs": ["Aries"],
                "elements": ["Fire"],
                "modalities": ["Cardinal"],
                "summary": "Action-led.",
                "evidence": ["Dominants"],
            },
            "main_life_pattern": pattern,
        },
        "important_configurations": [
            {
                "name": "T-square",
                "description": "Pressure pattern.",
                "impact": "Creates urgency.",
                "evidence": ["Aspect"],
            }
        ],
        "sections": {
            "general": {
                "traits": [trait],
                "patterns": [pattern],
                "strengths_weaknesses": [strength_weakness],
                "summary": "General summary.",
                "evidence": ["General"],
            },
            "love_and_sex": {
                "rahu_ketu": {
                    "rahu": "Rahu theme",
                    "ketu": "Ketu theme",
                    "evidence": ["Nodes"],
                },
                "love": {
                    "description": "Love theme.",
                    "blocks": ["defensiveness"],
                    "evidence": ["Venus"],
                },
                "sex": {
                    "description": "Sex theme.",
                    "blocks": ["control"],
                    "evidence": ["Mars"],
                },
                "summary": "Relationship summary.",
                "evidence": ["Love"],
            },
            "career_and_money": {
                "career": {
                    "description": "Career theme.",
                    "best_paths": ["founder"],
                    "risks": ["burnout"],
                    "evidence": ["MC"],
                },
                "money": {
                    "description": "Money theme.",
                    "earning_patterns": ["bursts"],
                    "risks": ["impulse"],
                    "evidence": ["2nd house"],
                },
                "summary": "Work summary.",
                "evidence": ["Career"],
            },
            "demons": {
                "lilith": {
                    "description": "Shadow theme.",
                    "triggers": ["dismissal"],
                    "evidence": ["Lilith"],
                },
                "inner_demons": [pattern],
                "self_sabotage": [pattern],
                "summary": "Shadow summary.",
                "evidence": ["Demons"],
            },
        },
        "cross_connections": [pattern],
        "generation_brief": {
            "core_character": "fast, blunt, intense",
            "main_conflict": "speed versus patience",
            "main_strength": "decisiveness",
            "main_weakness": "reactivity",
            "best_humor_angles": ["roast impatience"],
            "sensitive_topics_to_avoid": ["health"],
            "recommended_tone": "sharp but not cruel",
        },
    }


def _report_payload() -> dict:
    section = {"title": "General", "text": "Readable section text."}
    return {
        "title": "Natal report",
        "intro": {"title": "Intro", "text": "Intro text."},
        "general": section,
        "love_and_sex": {"title": "Love", "text": "Love text."},
        "career_and_money": {"title": "Career", "text": "Career text."},
        "demons": {"title": "Demons", "text": "Demons text."},
        "final_summary": {"title": "Final", "text": "Final text."},
    }


@dataclass
class FakeSettings:
    openrouter_api_key: str = "secret-key"
    openrouter_base_url: str = "https://openrouter.test/api/v1"
    openrouter_model_profile: str = "profile-model"
    openrouter_model_report: str = "report-model"


@pytest.mark.asyncio
async def test_postgres_persona_context_provider_loads_active_context() -> None:
    from app.services.persona_context_service import PostgresPersonaContextProvider

    persona_id = uuid4()
    repository = FakePersonaRepository(persona_id=persona_id)

    context = await PostgresPersonaContextProvider(repository).get_context(persona_id)

    assert context.persona_name == "Ada Persona"
    assert context.voice_description == "Direct."
    assert context.allowed_quotes == ["Allowed quote."]
    assert context.phrase_templates == ["{subject}, listen."]
    assert context.style_examples == ["Example text."]


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["persona", "style"])
async def test_postgres_persona_context_provider_raises_for_missing_context(
    missing: str,
) -> None:
    from app.services.persona_context_service import PostgresPersonaContextProvider

    repository = FakePersonaRepository(persona_id=uuid4(), missing=missing)

    with pytest.raises(NotFoundError):
        await PostgresPersonaContextProvider(repository).get_context(uuid4())


@pytest.mark.asyncio
async def test_openrouter_client_excludes_api_key_from_result_and_sends_bearer_header() -> None:
    from app.services.openrouter_client import OpenRouterClient

    with respx.mock(assert_all_called=True) as router:
        route = router.post("https://openrouter.test/api/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [{"message": {"content": "{\"ok\": true}"}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 5},
                },
            )
        )

        async with OpenRouterClient(settings=FakeSettings()) as client:
            result = await client.chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "hello"}],
                response_format={"type": "json_schema"},
            )

    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer secret-key"
    assert result.content == "{\"ok\": true}"
    assert result.input_tokens == 3
    assert result.output_tokens == 5
    assert "secret-key" not in json.dumps(result.raw_response)
    assert not hasattr(result, "raw_request")


@pytest.mark.asyncio
async def test_ai_generation_service_marks_generation_failed_when_openrouter_errors() -> None:
    from app.core.exceptions import OpenRouterTemporaryError
    from app.services.ai_generation_service import AIGenerationService

    generation = FakeGeneration()
    generation_repository = FakeGenerationRepository(generation)
    service = AIGenerationService(
        generation_repository=generation_repository,
        prompt_template_repository=FakePromptRepository(),
        natal_chart_service=FakeNatalChartService(),
        prompt_builder=FakePromptBuilder(),
        persona_context_provider=FakeContextProvider(),
        openrouter_client=FailingOpenRouterClient(),
        settings=FakeSettings(),
    )

    with pytest.raises(OpenRouterTemporaryError):
        await service.generate(generation.id)

    assert generation_repository.statuses == [GenerationStatus.PROCESSING]
    assert generation_repository.failed == [(generation.id, "temporary outage")]
    assert generation_repository.runs[-1]["stage"] == GenerationStage.ASTROLOGY_PROFILE_EXTRACTION
    assert generation_repository.runs[-1]["error_message"] == "temporary outage"
    assert generation_repository.runs[-1]["raw_request"]["messages"] == "[redacted]"


@pytest.mark.asyncio
async def test_ai_generation_service_successful_orchestration_records_outputs_and_runs() -> None:
    from app.services.ai_generation_service import AIGenerationService

    generation = FakeGeneration()
    generation_repository = FakeGenerationRepository(generation)
    openrouter_client = SuccessfulOpenRouterClient()

    await AIGenerationService(
        generation_repository=generation_repository,
        prompt_template_repository=FakePromptRepository(),
        natal_chart_service=FakeNatalChartService(),
        prompt_builder=FakePromptBuilder(),
        persona_context_provider=FakeContextProvider(),
        openrouter_client=openrouter_client,
        settings=FakeSettings(),
    ).generate(generation.id)

    assert generation_repository.statuses == [GenerationStatus.PROCESSING]
    assert generation_repository.natal_xml == [(generation.id, "<chart />")]
    assert AstrologyProfile.model_validate(generation_repository.profile[1])
    assert generation_repository.result[1]["title"] == "Natal report"
    assert generation_repository.result[2] == (
        "Natal report\n\n"
        "Intro\nIntro text.\n\n"
        "General\nReadable section text.\n\n"
        "Love\nLove text.\n\n"
        "Career\nCareer text.\n\n"
        "Demons\nDemons text.\n\n"
        "Final\nFinal text."
    )
    assert [run["stage"] for run in generation_repository.runs] == [
        GenerationStage.NATAL_CHART_BUILD,
        GenerationStage.ASTROLOGY_PROFILE_EXTRACTION,
        GenerationStage.STYLED_REPORT_GENERATION,
    ]
    assert [call["model"] for call in openrouter_client.calls] == [
        "profile-model",
        "report-model",
    ]
    assert openrouter_client.calls[0]["response_format"]["json_schema"]["name"] == (
        "AstrologyProfile"
    )
    assert openrouter_client.calls[1]["response_format"]["json_schema"]["name"] == (
        "StyledNatalReport"
    )


class FakePersonaRepository:
    def __init__(self, persona_id, missing: str | None = None) -> None:
        self.persona_id = persona_id
        self.missing = missing

    async def get_context_persona(self, persona_id):
        if self.missing == "persona":
            return None
        return Persona(
            id=persona_id,
            name="Ada Persona",
            slug="ada",
            description="Sharp persona.",
            is_active=True,
        )

    async def get_style_profile(self, persona_id):
        if self.missing == "style":
            return None
        return PersonaStyleProfile(
            persona_id=persona_id,
            voice_description="Direct.",
            humor_style="Dry.",
            speech_patterns=["short"],
            allowed_rules=["tease"],
            forbidden_rules=["no hate"],
        )

    async def list_allowed_quotes(self, persona_id):
        return [
            PersonaQuote(
                persona_id=persona_id,
                text="Allowed quote.",
                usage_context=None,
                is_allowed=True,
            )
        ]

    async def list_phrase_templates(self, persona_id):
        return [
            PersonaPhraseTemplate(
                persona_id=persona_id,
                type="intro",
                template="{subject}, listen.",
                usage=None,
            )
        ]

    async def list_style_examples(self, persona_id):
        return [
            PersonaStyleExample(
                persona_id=persona_id,
                title="Example",
                text="Example text.",
                tags=[],
            )
        ]


class FakeGeneration:
    def __init__(self) -> None:
        self.id = uuid4()
        self.person_name = "Ada"
        self.gender = "female"
        self.birth_date = date(1990, 1, 2)
        self.birth_time = time(3, 4)
        self.birth_city = "Moscow"
        self.birth_country = "Russia"
        self.birth_lat = 55.7558
        self.birth_lng = 37.6173
        self.birth_timezone = "Europe/Moscow"
        self.persona_id = uuid4()


class FakeGenerationRepository:
    def __init__(self, generation) -> None:
        self.generation = generation
        self.statuses = []
        self.natal_xml = []
        self.profile = None
        self.result = None
        self.failed = []
        self.runs = []

    async def get(self, generation_id):
        return self.generation if generation_id == self.generation.id else None

    async def set_status(self, generation_id, status):
        self.statuses.append(status)

    async def save_natal_xml(self, generation_id, natal_xml):
        self.natal_xml.append((generation_id, natal_xml))

    async def save_profile(self, generation_id, profile):
        self.profile = (generation_id, profile)

    async def save_result(self, generation_id, result_json, result_text):
        self.result = (generation_id, result_json, result_text)

    async def fail(self, generation_id, error_message):
        self.failed.append((generation_id, error_message))

    async def create_run(self, values):
        self.runs.append(values)
        return values


class FakePromptRepository:
    async def get_active(self, template_type):
        return PromptTemplate(
            id=uuid4(),
            name=template_type.value,
            type=template_type,
            version=1,
            content=f"{template_type.value} template",
            is_active=True,
            template_metadata={},
        )


class FakeNatalChartResult:
    natal_xml = "<chart />"


class FakeNatalChartService:
    def build_natal_chart(self, **kwargs):
        return FakeNatalChartResult()


class FakePromptBuilder:
    def build_astrology_profile_prompt(self, **kwargs):
        return [{"role": "user", "content": "profile prompt"}]

    def build_styled_report_prompt(self, **kwargs):
        return [{"role": "user", "content": "report prompt"}]


class FakeContextProvider:
    async def get_context(self, persona_id):
        return {"persona": str(persona_id)}


class FakeOpenRouterResult:
    def __init__(self, content: str, model: str) -> None:
        self.content = content
        self.raw_response = {"model": model}
        self.input_tokens = 11
        self.output_tokens = 17
        self.latency_ms = 23


class SuccessfulOpenRouterClient:
    def __init__(self) -> None:
        self.calls = []

    async def chat_completion(self, model, messages, response_format=None):
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "response_format": response_format,
            }
        )
        if model == "profile-model":
            return FakeOpenRouterResult(json.dumps(_profile_payload()), model)
        return FakeOpenRouterResult(json.dumps(_report_payload()), model)


class FailingOpenRouterClient:
    async def chat_completion(self, model, messages, response_format=None):
        from app.core.exceptions import OpenRouterTemporaryError

        raise OpenRouterTemporaryError("temporary outage")
