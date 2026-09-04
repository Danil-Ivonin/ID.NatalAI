from collections import Counter
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.characters.enums import CharacterEmotion, HumorType, SpeechPattern
from app.domain.generations.generation_neutral.schemas import Block

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class GenerationBlock(StrEnum):
    INTRO = "intro"
    GENERAL = "general"
    LOVE = "love"
    WORK_MONEY = "work_money"
    INNER_DEMONS = "inner_demons"


class GenerationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationProcessStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    STYLE_PLAN_GENERATING = "style_plan_generating"
    CHARACTER_BLOCK_GENERATING = "character_block_generating"
    COMPLETED = "completed"
    FAILED = "failed"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerationCreate(StrictModel):
    person_id: UUID
    character_id: UUID
    used_examples: list[UUID] = Field(default_factory=list)
    current_block: GenerationBlock = GenerationBlock.INTRO
    status: GenerationProcessStatus = GenerationProcessStatus.PENDING
    payed: bool = False
    payment_id: UUID | None = None


class GenerationUpdate(StrictModel):
    used_examples: list[UUID] | None = None
    current_block: GenerationBlock | None = None
    status: GenerationProcessStatus | None = None
    payed: bool | None = None
    payment_id: UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict) and any(
            value is None for field, value in data.items() if field != "payment_id"
        ):
            raise ValueError("updated fields cannot be null")
        return data


class GenerationRead(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    person_id: UUID
    character_id: UUID
    used_examples: list[UUID] = Field(default_factory=list)
    current_block: GenerationBlock
    status: GenerationProcessStatus = GenerationProcessStatus.PENDING
    payed: bool = False
    payment_id: UUID | None = None
    generation_id: UUID


class GenerationStepUpdate(StrictModel):
    block: GenerationBlock | None = None
    status: GenerationStatus | None = None
    used_model: NonBlankStr | None = None
    prompt: NonBlankStr | None = None
    token_usage: dict[str, Any] | None = None
    result: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("updated fields cannot be null")
        return data


class GenerationStepCreate(StrictModel):
    generation_id: UUID
    block: GenerationBlock
    status: GenerationStatus = GenerationStatus.PENDING
    used_model: NonBlankStr
    prompt: NonBlankStr
    token_usage: dict[str, Any]
    result: dict[str, Any]


class HookStylePlan(StrictModel):
    hook_id: NonBlankStr
    rhetorical_goal: NonBlankStr
    emotion: CharacterEmotion
    humor_types: list[HumorType] = Field(default_factory=list, max_length=2)
    speech_patterns: list[SpeechPattern] = Field(default_factory=list, max_length=3)
    retrieval_intent: NonBlankStr


class BlockStylePlan(StrictModel):
    block_arc: NonBlankStr
    hook_plans: list[HookStylePlan]

    def validate_for(self, block: Block) -> "BlockStylePlan":
        expected = [hook.id for hook in block.hooks]
        actual = [plan.hook_id for plan in self.hook_plans]
        if Counter(actual) != Counter(expected):
            raise ValueError("style plan must cover every block hook exactly once")
        return self


class CharacterBlockResult(StrictModel):
    title: NonBlankStr
    text: NonBlankStr


class GenerationStylePlanCreate(GenerationStepCreate):
    pass


class GenerationStylePlanUpdate(GenerationStepUpdate):
    pass


class GenerationStylePlanRead(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    generation_id: UUID
    block: GenerationBlock
    status: GenerationStatus = GenerationStatus.PENDING
    used_model: NonBlankStr
    prompt: NonBlankStr
    token_usage: dict[str, Any]
    result: dict[str, Any]
    plan_id: UUID


class GenerationCharacterBlockCreate(GenerationStepCreate):
    pass


class GenerationCharacterBlockUpdate(GenerationStepUpdate):
    pass


class GenerationCharacterBlockRead(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    generation_id: UUID
    block: GenerationBlock
    status: GenerationStatus = GenerationStatus.PENDING
    used_model: NonBlankStr
    prompt: NonBlankStr
    token_usage: dict[str, Any]
    result: dict[str, Any]
    id: UUID
