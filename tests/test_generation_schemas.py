from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError


RESULT = {
    "blocks": [
        {
            "id": "general",
            "title": "Общая информация",
            "summary": "Сводка.",
            "facts": [
                {
                    "id": "general_01",
                    "statement": "Важна самостоятельность.",
                    "kind": "tendency",
                    "themes": ["самостоятельность"],
                    "importance": "high",
                    "evidence": [
                        {
                            "type": "placement",
                            "body": "Sun",
                            "sign": "Leo",
                            "house": 1,
                        }
                    ],
                }
            ],
            "hooks": [
                {
                    "id": "general_hook_01",
                    "type": "mask_vs_inner_state",
                    "fact_ids": ["general_01"],
                    "neutral_angle": "Уверенность зависит от признания.",
                    "priority": "high",
                }
            ],
        },
        {
            "id": "love",
            "title": "Любовь и отношения",
            "summary": "Сводка.",
            "facts": [],
            "hooks": [],
        },
        {
            "id": "work_money",
            "title": "Работа и деньги",
            "summary": "Сводка.",
            "facts": [],
            "hooks": [],
        },
        {
            "id": "inner_demons",
            "title": "Внутренние демоны",
            "summary": "Сводка.",
            "facts": [],
            "hooks": [],
        },
    ]
}


def test_generation_neutral_result_requires_ordered_blocks() -> None:
    from app.domain.generations.generation_neutral.schemas import (
        GenerationNeutralResult,
    )

    result = GenerationNeutralResult.model_validate(RESULT)

    assert [block.id.value for block in result.blocks] == [
        "general",
        "love",
        "work_money",
        "inner_demons",
    ]


@pytest.mark.parametrize("blocks", [RESULT["blocks"][:-1], RESULT["blocks"][::-1]])
def test_generation_neutral_result_rejects_wrong_blocks(blocks) -> None:
    from app.domain.generations.generation_neutral.schemas import (
        GenerationNeutralResult,
    )

    with pytest.raises(ValidationError):
        GenerationNeutralResult.model_validate({"blocks": blocks})


def test_generation_neutral_result_rejects_invalid_references_and_duplicate_ids() -> None:
    from app.domain.generations.generation_neutral.schemas import (
        GenerationNeutralResult,
    )

    missing_reference = deepcopy(RESULT)
    missing_reference["blocks"][0]["hooks"][0]["fact_ids"] = ["missing"]
    duplicate = deepcopy(RESULT)
    duplicate["blocks"][1]["facts"] = [deepcopy(duplicate["blocks"][0]["facts"][0])]

    with pytest.raises(ValidationError):
        GenerationNeutralResult.model_validate(missing_reference)
    with pytest.raises(ValidationError):
        GenerationNeutralResult.model_validate(duplicate)


def test_generation_create_requires_person_and_valid_result() -> None:
    from app.domain.generations.generation_neutral.schemas import (
        GenerationNeutralCreate,
    )

    with pytest.raises(ValidationError):
        GenerationNeutralCreate.model_validate(
            {
                "used_model": "model",
                "prompt": "prompt",
                "token_usage": {"total_tokens": 42},
                "result": RESULT,
            }
        )


def test_astro_chart_rejects_malformed_xml_and_requires_person() -> None:
    from app.domain.generations.astro_charts.schemas import AstroChartCreate

    with pytest.raises(ValidationError):
        AstroChartCreate(
            person_id=uuid4(),
            natal_xml="<broken",
            chart_svg="charts/a.svg",
        )
    with pytest.raises(ValidationError):
        AstroChartCreate(natal_xml="<chart />", chart_svg="charts/a.svg")


def test_update_schemas_reject_null_required_columns() -> None:
    from app.domain.generations.astro_charts.schemas import AstroChartUpdate
    from app.domain.generations.generation_neutral.schemas import (
        GenerationNeutralUpdate,
    )

    with pytest.raises(ValidationError):
        AstroChartUpdate(natal_xml=None)
    with pytest.raises(ValidationError):
        GenerationNeutralUpdate(prompt=None)


def test_generation_result_preserves_from_alias_in_json() -> None:
    from app.domain.generations.generation_neutral.schemas import AspectEvidence

    evidence = AspectEvidence.model_validate(
        {"type": "aspect", "from": "Sun", "to": "Moon", "aspect": "trine"}
    )

    assert evidence.model_dump(mode="json") == {
        "type": "aspect",
        "from": "Sun",
        "to": "Moon",
        "aspect": "trine",
    }
