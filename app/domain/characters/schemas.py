from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.characters.enums import CharacterEmotion, HumorType, SpeechPattern

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Embedding = Annotated[list[float], Field(min_length=3072, max_length=3072)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CharacterCore(StrictModel):
    self_image: NonBlankStr
    worldview: list[NonBlankStr]
    values: list[NonBlankStr]
    blind_spots: list[NonBlankStr]


class AstrologyPosition(StrictModel):
    role: NonBlankStr
    interpretation_style: NonBlankStr


class ReaderRelationship(StrictModel):
    position: NonBlankStr
    address: NonBlankStr
    distance: NonBlankStr
    care_style: NonBlankStr


class Voice(StrictModel):
    diction: list[NonBlankStr]
    syntax: list[NonBlankStr]
    directness: NonBlankStr
    emotional_range: list[NonBlankStr]


class Humor(StrictModel):
    targets: list[NonBlankStr]
    boundaries: list[NonBlankStr]
    mechanics: list[NonBlankStr]


class MonologueStructure(StrictModel):
    opening: NonBlankStr
    development: NonBlankStr
    transitions: NonBlankStr
    ending: NonBlankStr


class CharacterProfileBody(StrictModel):
    core: CharacterCore
    astrology_position: AstrologyPosition
    reader_relationship: ReaderRelationship
    voice: Voice
    humor: Humor
    monologue_structure: MonologueStructure
    do_not: list[NonBlankStr]


class CharacterProfileCreate(CharacterProfileBody):
    name: NonBlankStr


class CharacterProfile(CharacterProfileCreate):
    character_id: int = Field(gt=0)


class CharacterExampleCreate(StrictModel):
    character_id: int = Field(gt=0)
    raw_text: NonBlankStr
    clean_text: NonBlankStr
    context: NonBlankStr
    emotion: CharacterEmotion
    rhetorical_function: NonBlankStr
    humor_types: list[HumorType] = Field(default_factory=list, max_length=2)
    speech_patterns: list[SpeechPattern] = Field(default_factory=list, max_length=3)
    embedding: Embedding | None = None
    active: bool = True


class CharacterExample(CharacterExampleCreate):
    id: int = Field(gt=0)


class CharacterExampleEmbedding(StrictModel):
    embedding: Embedding


class CharacterExampleSearch(StrictModel):
    character_id: int = Field(gt=0)
    embedding: Embedding
    emotion: CharacterEmotion
    humor_types: list[HumorType] = Field(default_factory=list, max_length=2)
    speech_patterns: list[SpeechPattern] = Field(default_factory=list, max_length=3)
    exclude_ids: set[int] = Field(default_factory=set)
    limit: int = Field(default=8, ge=1, le=100)
