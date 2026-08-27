from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.domain.readings.schemas import (
    AspectEvidence,
    BlockStylePlan,
    NeutralBlock,
    NeutralChartReading,
)


def valid_reading_payload() -> dict:
    return {
        "subject": {"display_name": "Анна", "sex": "female"},
        "blocks": [
            {
                "id": "general",
                "title": "Общая информация",
                "summary": "Нейтральная сводка.",
                "facts": [{
                    "id": "general_01",
                    "statement": "Важна самостоятельность.",
                    "kind": "tendency",
                    "themes": ["самостоятельность"],
                    "importance": "high",
                    "evidence": [{
                        "type": "placement", "body": "Sun", "sign": "Leo", "house": 1,
                    }],
                }],
                "hooks": [{
                    "id": "general_hook_01",
                    "type": "mask_vs_inner_state",
                    "fact_ids": ["general_01"],
                    "neutral_angle": "Уверенность зависит от признания.",
                    "priority": "high",
                }],
            },
            {"id": "love", "title": "Любовь и отношения", "summary": "Нейтральная сводка.", "facts": [], "hooks": []},
            {"id": "work_money", "title": "Работа и деньги", "summary": "Нейтральная сводка.", "facts": [], "hooks": []},
            {"id": "inner_demons", "title": "Внутренние демоны", "summary": "Нейтральная сводка.", "facts": [], "hooks": []},
        ],
    }


def valid_plan_payload() -> dict:
    return {
        "block_arc": "От наблюдения к прямому выводу.",
        "hook_plans": [{
            "hook_id": "general_hook_01",
            "rhetorical_goal": "Вскрыть зависимость от признания.",
            "emotion": "skepticism",
            "humor_types": ["irony"],
            "speech_patterns": ["observation", "short_verdict"],
            "retrieval_intent": "Скептический ответ на самообман.",
        }],
    }


def test_neutral_reading_accepts_planning_contract() -> None:
    reading = NeutralChartReading.model_validate(valid_reading_payload())
    assert [block.id for block in reading.blocks] == [
        "general", "love", "work_money", "inner_demons",
    ]


def test_neutral_reading_requires_ordered_unique_blocks() -> None:
    payload = valid_reading_payload()
    payload["blocks"] = list(reversed(payload["blocks"]))
    with pytest.raises(ValidationError, match="general, love, work_money, inner_demons"):
        NeutralChartReading.model_validate(payload)


def test_hook_must_reference_fact_in_same_block() -> None:
    payload = valid_reading_payload()
    payload["blocks"][0]["hooks"][0]["fact_ids"] = ["missing"]
    with pytest.raises(ValidationError, match="missing"):
        NeutralChartReading.model_validate(payload)


def test_fact_and_hook_ids_are_globally_unique() -> None:
    payload = valid_reading_payload()
    payload["blocks"][1]["facts"] = [deepcopy(payload["blocks"][0]["facts"][0])]
    with pytest.raises(ValidationError, match="fact IDs must be unique"):
        NeutralChartReading.model_validate(payload)


def test_style_plan_covers_every_hook_once() -> None:
    block = NeutralBlock.model_validate(valid_reading_payload()["blocks"][0])
    plan = BlockStylePlan.model_validate(valid_plan_payload())
    assert plan.validate_for(block) is plan
    missing = BlockStylePlan(block_arc="Короткая дуга.", hook_plans=[])
    with pytest.raises(ValueError, match="exactly once"):
        missing.validate_for(block)


def test_style_plan_rejects_duplicate_hook_ids() -> None:
    payload = valid_plan_payload()
    payload["hook_plans"].append(deepcopy(payload["hook_plans"][0]))
    with pytest.raises(ValidationError, match="hook IDs must be unique"):
        BlockStylePlan.model_validate(payload)


def test_aspect_evidence_uses_contract_alias_for_input_and_output() -> None:
    evidence = AspectEvidence.model_validate(
        {"type": "aspect", "from": "Venus", "to": "Saturn", "aspect": "square"}
    )

    assert evidence.model_dump(mode="json") == {
        "type": "aspect",
        "from": "Venus",
        "to": "Saturn",
        "aspect": "square",
    }
    with pytest.raises(ValidationError):
        AspectEvidence.model_validate(
            {
                "type": "aspect",
                "from_body": "Venus",
                "to": "Saturn",
                "aspect": "square",
            }
        )
