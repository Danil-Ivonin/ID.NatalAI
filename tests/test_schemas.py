from datetime import date, datetime, time, timezone
from typing import Protocol
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.generation.enums import GenerationStatus
from app.domain.generation.schemas import (
    BirthPlace,
    GenerationCreate,
    GenerationDetailResponse,
)
from app.domain.generation.ai_schemas import AstrologyProfile, StyledNatalReport
from app.domain.persona.context import PersonaContext, PersonaContextProvider
from app.domain.prompts.enums import PromptTemplateType
from app.domain.prompts.models import PromptTemplate
from app.domain.prompts.schemas import PromptTemplateActivateResponse, PromptTemplateRead


def test_generation_create_accepts_missing_person_name_and_null_gender() -> None:
    payload = {
        "birth_date": date(1990, 1, 2),
        "birth_time": time(3, 4),
        "birth_place": {
            "city": "Moscow",
            "country": "Russia",
            "lat": 55.7558,
            "lng": 37.6173,
            "timezone": "Europe/Moscow",
        },
        "persona_id": uuid4(),
    }

    model = GenerationCreate.model_validate(payload)

    assert model.person_name is None
    assert model.gender is None
    assert model.birth_place.city == "Moscow"


def test_generation_create_accepts_explicit_null_person_name_and_gender() -> None:
    model = GenerationCreate(
        person_name=None,
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
        persona_id=uuid4(),
    )

    assert model.person_name is None
    assert model.gender is None


@pytest.mark.parametrize("gender", ["other", "unknown"])
def test_generation_create_rejects_invalid_gender(gender: str) -> None:
    with pytest.raises(ValidationError):
        GenerationCreate(
            person_name=None,
            gender=gender,
            birth_date=date(1990, 1, 2),
            birth_time=time(3, 4),
            birth_place=BirthPlace(
                city="Moscow",
                country="Russia",
                lat=55.7558,
                lng=37.6173,
                timezone="Europe/Moscow",
            ),
            persona_id=uuid4(),
        )


def test_generation_detail_response_can_validate_orm_shaped_object() -> None:
    generation_id = uuid4()
    created_at = datetime(2026, 5, 15, tzinfo=timezone.utc)
    source = type(
        "GenerationLike",
        (),
        {
            "id": generation_id,
            "status": GenerationStatus.PENDING,
            "result_text": None,
            "error_message": None,
            "created_at": created_at,
            "completed_at": None,
        },
    )()

    response = GenerationDetailResponse.model_validate(source)

    assert response.generation_id == generation_id
    assert response.created_at == created_at


def _valid_astrology_profile_payload() -> dict:
    placement = {
        "name": "Sun in Aries",
        "meaning": "Direct and forceful.",
        "evidence": ["Sun sign Aries"],
    }
    trait = {"name": "bold", "description": "Acts first.", "evidence": ["Mars emphasis"]}
    pattern = {
        "name": "fast ignition",
        "description": "Starts quickly.",
        "evidence": ["Cardinal placements"],
    }
    strength_weakness = {
        "strength": "decisive",
        "weakness": "impatient",
        "evidence": ["Aries Sun"],
    }

    return {
        "subject": {
            "person_name": None,
            "gender": None,
            "birth_date": "1990-01-02",
            "birth_time": "03:04:00",
            "birth_place": "Moscow, Russia",
        },
        "chart_core": {
            "big_three": {
                "sun": placement,
                "moon": placement,
                "ascendant": placement,
                "summary": "Fire-forward presentation.",
                "evidence": ["Sun/Moon/ASC synthesis"],
            },
            "dominants": {
                "planets": ["Mars"],
                "signs": ["Aries"],
                "elements": ["Fire"],
                "modalities": ["Cardinal"],
                "summary": "Action-led chart.",
                "evidence": ["Dominant Mars"],
            },
            "main_life_pattern": pattern,
        },
        "important_configurations": [
            {
                "name": "T-square",
                "description": "Pressure pattern.",
                "impact": "Creates urgency.",
                "evidence": ["Aspect pattern"],
            }
        ],
        "sections": {
            "general": {
                "traits": [trait],
                "patterns": [pattern],
                "strengths_weaknesses": [strength_weakness],
                "summary": "General summary.",
                "evidence": ["General synthesis"],
            },
            "love_and_sex": {
                "rahu_ketu": {
                    "rahu": "Rahu theme",
                    "ketu": "Ketu theme",
                    "evidence": ["Node axis"],
                },
                "love": {
                    "description": "Love theme.",
                    "blocks": ["defensiveness"],
                    "evidence": ["Venus aspect"],
                },
                "sex": {
                    "description": "Sex theme.",
                    "blocks": ["control"],
                    "evidence": ["Mars aspect"],
                },
                "summary": "Relationship summary.",
                "evidence": ["Love synthesis"],
            },
            "career_and_money": {
                "career": {
                    "description": "Career theme.",
                    "best_paths": ["founder"],
                    "risks": ["burnout"],
                    "evidence": ["MC ruler"],
                },
                "money": {
                    "description": "Money theme.",
                    "earning_patterns": ["bursts"],
                    "risks": ["impulse"],
                    "evidence": ["2nd house"],
                },
                "summary": "Work summary.",
                "evidence": ["Career synthesis"],
            },
            "demons": {
                "lilith": {
                    "description": "Shadow theme.",
                    "triggers": ["dismissal"],
                    "evidence": ["Lilith placement"],
                },
                "inner_demons": [pattern],
                "self_sabotage": [pattern],
                "summary": "Shadow summary.",
                "evidence": ["Demons synthesis"],
            },
        },
        "cross_connections": [pattern],
        "generation_brief": {
            "core_character": "fast, blunt, intense",
            "main_conflict": "speed versus patience",
            "main_strength": "decisiveness",
            "main_weakness": "reactivity",
            "best_humor_angles": ["roast the impatience"],
            "sensitive_topics_to_avoid": ["health"],
            "recommended_tone": "sharp but not cruel",
        },
    }


def test_astrology_profile_rejects_extra_fields_and_requires_evidence() -> None:
    valid = _valid_astrology_profile_payload()
    assert AstrologyProfile.model_validate(valid).subject.person_name is None

    with pytest.raises(ValidationError):
        AstrologyProfile.model_validate(valid | {"unexpected": "field"})

    invalid_missing_evidence = _valid_astrology_profile_payload()
    del invalid_missing_evidence["chart_core"]["main_life_pattern"]["evidence"]

    with pytest.raises(ValidationError):
        AstrologyProfile.model_validate(invalid_missing_evidence)


def test_styled_natal_report_rejects_extra_fields() -> None:
    section = {"title": "General", "text": "Text."}
    payload = {
        "title": "Natal report",
        "intro": section,
        "general": section,
        "love_and_sex": section,
        "career_and_money": section,
        "demons": section,
        "final_summary": section,
    }

    assert StyledNatalReport.model_validate(payload).title == "Natal report"

    with pytest.raises(ValidationError):
        StyledNatalReport.model_validate(payload | {"extra": "nope"})


def test_persona_context_schema_and_provider_protocol_shape() -> None:
    context = PersonaContext(
        persona_name="Shrek",
        persona_slug="shrek",
        persona_description=None,
        voice_description="Direct.",
        humor_style="Dry.",
        speech_patterns=["short sentences"],
        allowed_rules=["roast lightly"],
        forbidden_rules=["no hate"],
        allowed_quotes=["Better out than in."],
        phrase_templates=["{subject}, listen."],
        style_examples=["That is a terrible idea."],
    )

    assert context.allowed_quotes == ["Better out than in."]
    assert issubclass(PersonaContextProvider, Protocol)

    with pytest.raises(ValidationError):
        PersonaContext.model_validate(context.model_dump() | {"extra": "nope"})


def test_prompt_template_activate_response_exposes_read_fields_and_metadata_alias() -> None:
    prompt_template_id = uuid4()
    created_at = datetime(2026, 5, 15, tzinfo=timezone.utc)
    updated_at = datetime(2026, 5, 16, tzinfo=timezone.utc)
    source = type(
        "PromptTemplateLike",
        (),
        {
            "id": prompt_template_id,
            "name": "Astrology profile v1",
            "type": PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION,
            "version": 1,
            "content": "Extract profile",
            "is_active": True,
            "template_metadata": {"model": "test-model"},
            "created_at": created_at,
            "updated_at": updated_at,
        },
    )()

    response = PromptTemplateActivateResponse.model_validate(source)

    assert response.prompt_template_id == prompt_template_id
    assert response.name == "Astrology profile v1"
    assert response.content == "Extract profile"
    assert response.template_metadata == {"model": "test-model"}
    assert response.created_at == created_at
    assert response.updated_at == updated_at
    assert response.model_dump(by_alias=True)["metadata"] == {"model": "test-model"}


def test_prompt_template_read_prefers_orm_template_metadata_over_sqlalchemy_metadata() -> None:
    prompt_template_id = uuid4()
    created_at = datetime(2026, 5, 15, tzinfo=timezone.utc)
    updated_at = datetime(2026, 5, 16, tzinfo=timezone.utc)
    source = PromptTemplate(
        id=prompt_template_id,
        name="Astrology profile v2",
        type=PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION,
        version=2,
        content="Extract profile",
        is_active=True,
        template_metadata={"model": "test-model"},
    )
    source.created_at = created_at
    source.updated_at = updated_at

    response = PromptTemplateRead.model_validate(source)

    assert response.id == prompt_template_id
    assert response.template_metadata == {"model": "test-model"}
    assert response.model_dump(by_alias=True)["metadata"] == {"model": "test-model"}
