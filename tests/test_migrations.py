import pytest

from app.domain.characters.enums import CharacterEmotion, HumorType, SpeechPattern
from app.domain.characters.models import Character, CharacterExample
from app.domain.characters.schemas import CharacterExampleSearch
from app.repositories.character_example_repository import CharacterExampleRepository


@pytest.mark.db_integration
@pytest.mark.asyncio
async def test_pgvector_search_keeps_tag_mismatches_as_candidates(db_session) -> None:
    character = Character(name="Test", profile={})
    db_session.add(character)
    await db_session.flush()
    matching = CharacterExample(
        character_id=character.id,
        raw_text="raw one",
        clean_text="clean one",
        context="context one",
        emotion=CharacterEmotion.CALM,
        rhetorical_function="support",
        humor_types=[HumorType.IRONY],
        speech_patterns=[SpeechPattern.OBSERVATION],
        embedding=[1.0] + [0.0] * 3071,
    )
    mismatch = CharacterExample(
        character_id=character.id,
        raw_text="raw two",
        clean_text="clean two",
        context="context two",
        emotion=CharacterEmotion.ANGER,
        rhetorical_function="challenge",
        humor_types=[],
        speech_patterns=[],
        embedding=[1.0] + [0.0] * 3071,
    )
    excluded = CharacterExample(
        character_id=character.id,
        raw_text="raw excluded",
        clean_text="clean excluded",
        context="context excluded",
        emotion=CharacterEmotion.CALM,
        rhetorical_function="exclude",
        humor_types=[HumorType.IRONY],
        speech_patterns=[SpeechPattern.OBSERVATION],
        embedding=[1.0] + [0.0] * 3071,
    )
    inactive = CharacterExample(
        character_id=character.id,
        raw_text="raw inactive",
        clean_text="clean inactive",
        context="context inactive",
        emotion=CharacterEmotion.CALM,
        rhetorical_function="inactive",
        humor_types=[HumorType.IRONY],
        speech_patterns=[SpeechPattern.OBSERVATION],
        embedding=[1.0] + [0.0] * 3071,
        active=False,
    )
    missing_embedding = CharacterExample(
        character_id=character.id,
        raw_text="raw missing",
        clean_text="clean missing",
        context="context missing",
        emotion=CharacterEmotion.CALM,
        rhetorical_function="missing embedding",
        humor_types=[HumorType.IRONY],
        speech_patterns=[SpeechPattern.OBSERVATION],
        embedding=None,
    )
    db_session.add_all([mismatch, matching, excluded, inactive, missing_embedding])
    await db_session.flush()

    found = await CharacterExampleRepository(db_session).search(
        CharacterExampleSearch(
            character_id=character.id,
            embedding=[1.0] + [0.0] * 3071,
            emotion=CharacterEmotion.CALM,
            humor_types=[HumorType.IRONY],
            speech_patterns=[SpeechPattern.OBSERVATION],
            exclude_ids={excluded.id},
            limit=10,
        )
    )

    assert [example.id for example in found] == [matching.id, mismatch.id]
