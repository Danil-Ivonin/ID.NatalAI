from collections import Counter
from enum import StrEnum
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )


class BlockId(StrEnum):
    GENERAL = "general"
    LOVE = "love"
    WORK_MONEY = "work_money"
    INNER_DEMONS = "inner_demons"


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PlacementEvidence(StrictModel):
    type: Literal["placement"]
    body: NonBlankStr
    sign: NonBlankStr
    house: int = Field(ge=1, le=12)


class AspectEvidence(StrictModel):
    type: Literal["aspect"]
    from_body: NonBlankStr = Field(alias="from", serialization_alias="from")
    to: NonBlankStr
    aspect: NonBlankStr


class HouseEvidence(StrictModel):
    type: Literal["house"]
    house: int = Field(ge=1, le=12)


class AngleEvidence(StrictModel):
    type: Literal["angle"]
    angle: NonBlankStr


Evidence = Annotated[
    PlacementEvidence | AspectEvidence | HouseEvidence | AngleEvidence,
    Field(discriminator="type"),
]


class Fact(StrictModel):
    id: NonBlankStr
    statement: NonBlankStr
    kind: NonBlankStr
    themes: list[NonBlankStr] = Field(min_length=1, max_length=4)
    importance: Priority
    evidence: list[Evidence] = Field(min_length=1)


class Hook(StrictModel):
    id: NonBlankStr
    type: NonBlankStr
    fact_ids: list[NonBlankStr] = Field(min_length=1)
    neutral_angle: NonBlankStr
    priority: Priority


class Block(StrictModel):
    id: BlockId
    title: NonBlankStr
    summary: NonBlankStr
    facts: list[Fact]
    hooks: list[Hook] = Field(max_length=5)

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        fact_ids = {fact.id for fact in self.facts}
        missing = {
            fact_id
            for hook in self.hooks
            for fact_id in hook.fact_ids
            if fact_id not in fact_ids
        }
        if missing:
            raise ValueError(f"hook references missing facts: {sorted(missing)}")
        return self


class GenerationNeutralResult(StrictModel):
    blocks: list[Block] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_document(self) -> Self:
        expected = [
            BlockId.GENERAL,
            BlockId.LOVE,
            BlockId.WORK_MONEY,
            BlockId.INNER_DEMONS,
        ]
        if [block.id for block in self.blocks] != expected:
            raise ValueError(
                "blocks must be ordered: general, love, work_money, inner_demons"
            )
        fact_ids = [fact.id for block in self.blocks for fact in block.facts]
        hook_ids = [hook.id for block in self.blocks for hook in block.hooks]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("fact IDs must be unique")
        if len(hook_ids) != len(set(hook_ids)):
            raise ValueError("hook IDs must be unique")
        return self


class GenerationNeutralCreate(StrictModel):
    person_id: UUID
    generation_id: UUID | None = None
    used_model: NonBlankStr
    prompt: NonBlankStr
    token_usage: dict[str, Any]
    result: GenerationNeutralResult


class GenerationNeutralUpdate(StrictModel):
    used_model: NonBlankStr | None = None
    prompt: NonBlankStr | None = None
    token_usage: dict[str, Any] | None = None
    result: GenerationNeutralResult | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("updated fields cannot be null")
        return data


class GenerationNeutralRead(GenerationNeutralCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
