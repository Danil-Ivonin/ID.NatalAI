from struct import pack, unpack
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PositiveInt, StringConstraints

from app.domain.characters.enums import CharacterEmotion, HumorType, SpeechPattern

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
FLOAT32_MAX = 3.4028234663852886e38
EmbeddingValue = Annotated[
    float,
    Field(
        strict=True,
        allow_inf_nan=False,
        ge=-FLOAT32_MAX,
        le=FLOAT32_MAX,
    ),
]


def _non_zero(values: list[float]) -> list[float]:
    if not any(unpack("!f", pack("!f", value))[0] for value in values):
        raise ValueError("embedding must be non-zero")
    return values


Embedding = Annotated[
    list[EmbeddingValue],
    Field(min_length=3072, max_length=3072),
    AfterValidator(_non_zero),
]


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
    exclude_ids: set[PositiveInt] = Field(default_factory=set)
    limit: int = Field(default=8, ge=1, le=100)
