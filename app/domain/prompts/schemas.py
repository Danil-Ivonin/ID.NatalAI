from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.domain.prompts.enums import PromptTemplateType


class PromptTemplateBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: PromptTemplateType
    version: int
    content: str
    is_active: bool = True
    template_metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("template_metadata", "metadata"),
        serialization_alias="metadata",
    )


class PromptTemplateCreate(PromptTemplateBase):
    pass


class PromptTemplateRead(PromptTemplateBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class PromptTemplateActivateResponse(PromptTemplateBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    prompt_template_id: UUID = Field(
        validation_alias=AliasChoices("prompt_template_id", "id"),
        serialization_alias="prompt_template_id",
    )
    created_at: datetime
    updated_at: datetime
