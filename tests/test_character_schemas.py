from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.domain.characters.enums import CharacterEmotion, HumorType, SpeechPattern
from app.domain.characters.schemas import (
    CharacterExampleCreate,
    CharacterExampleSearch,
    CharacterProfile,
)


VALID_PROFILE = {
    "character_id": 1,
    "name": "Имя персонажа",
    "core": {
        "self_image": "Считает себя честным собеседником.",
        "worldview": ["Люди часто называют привычку судьбой."],
        "values": ["Честность"],
        "blind_spots": ["Недооценивает осторожность"],
    },
    "astrology_position": {
        "role": "Использует астрологию для разговора о выборе.",
        "interpretation_style": "Психологический интерпретатор",
    },
    "reader_relationship": {
        "position": "Собеседник",
        "address": "На ты",
        "distance": "Близкая",
        "care_style": "Критикует поступок, а не человека.",
    },
    "voice": {
        "diction": ["Разговорная лексика"],
        "syntax": ["Короткие выводы после наблюдения"],
        "directness": "Прямо",
        "emotional_range": ["calm", "skepticism"],
    },
    "humor": {
        "targets": ["Самообман"],
        "boundaries": ["Не шутит над травмой"],
        "mechanics": ["Наблюдение, снижение пафоса, вывод"],
    },
    "monologue_structure": {
        "opening": "Начинает с наблюдения.",
        "development": "Раскрывает противоречие.",
        "transitions": "Связывает темы общим мотивом.",
        "ending": "Оставляет направление для действия.",
    },
    "do_not": ["Не превращать голос в пародию"],
}

VALID_EXAMPLE = {
    "character_id": 1,
    "raw_text": "Исходная реплика",
    "clean_text": "Очищенная реплика",
    "context": "Ответ на попытку оправдаться",
    "emotion": "skepticism",
    "rhetorical_function": "Вскрыть самообман",
    "humor_types": ["irony"],
    "speech_patterns": ["observation", "short_verdict"],
}


def test_character_profile_matches_planning_contract() -> None:
    profile = CharacterProfile.model_validate(VALID_PROFILE)
    assert profile.character_id == 1
    assert profile.voice.directness == "Прямо"
    assert profile.core.worldview == ["Люди часто называют привычку судьбой."]


def test_character_profile_forbids_unknown_fields() -> None:
    payload = deepcopy(VALID_PROFILE)
    payload["voice"]["catchphrases"] = ["Нет"]
    with pytest.raises(ValidationError):
        CharacterProfile.model_validate(payload)


def test_character_example_enforces_embedding_dimension() -> None:
    with pytest.raises(ValidationError):
        CharacterExampleCreate(**VALID_EXAMPLE, embedding=[0.0] * 3071)
    example = CharacterExampleCreate(**VALID_EXAMPLE, embedding=[0.1] * 3072)
    assert len(example.embedding or []) == 3072


def test_character_example_search_enforces_tag_limits() -> None:
    with pytest.raises(ValidationError):
        CharacterExampleSearch(
            character_id=1,
            embedding=[0.1] * 3072,
            emotion="calm",
            humor_types=["irony", "sarcasm", "deadpan"],
        )


@pytest.mark.parametrize(
    "invalid",
    [float("nan"), float("inf"), -float("inf"), True, "1", 4e38],
)
def test_embedding_rejects_non_pgvector_components(invalid) -> None:
    embedding = [0.1] * 3072
    embedding[0] = invalid

    with pytest.raises(ValidationError):
        CharacterExampleCreate(**VALID_EXAMPLE, embedding=embedding)


def test_embedding_rejects_zero_vector() -> None:
    with pytest.raises(ValidationError, match="non-zero"):
        CharacterExampleSearch(
            character_id=1,
            embedding=[0.0] * 3072,
            emotion="calm",
        )

    with pytest.raises(ValidationError, match="non-zero"):
        CharacterExampleSearch(
            character_id=1,
            embedding=[1e-300] * 3072,
            emotion="calm",
        )


@pytest.mark.parametrize("invalid_id", [0, -1])
def test_search_rejects_non_positive_excluded_ids(invalid_id: int) -> None:
    with pytest.raises(ValidationError):
        CharacterExampleSearch(
            character_id=1,
            embedding=[0.1] * 3072,
            emotion="calm",
            exclude_ids={invalid_id},
        )


def test_style_enums_match_planning_vocabulary() -> None:
    assert len(CharacterEmotion) == 21
    assert len(HumorType) == 19
    assert len(SpeechPattern) == 25
    assert CharacterEmotion.SKEPTICISM == "skepticism"
    assert HumorType.SELF_IRONY == "self_irony"
    assert SpeechPattern.SHORT_VERDICT == "short_verdict"
