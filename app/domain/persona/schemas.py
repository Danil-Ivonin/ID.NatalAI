from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PersonaStyleProfileBase(BaseModel):
    voice_description: str
    humor_style: str
    speech_patterns: list[str]
    forbidden_rules: list[str]
    allowed_rules: list[str]


class PersonaStyleProfileCreate(PersonaStyleProfileBase):
    pass


class PersonaStyleProfileUpdate(BaseModel):
    voice_description: str | None = None
    humor_style: str | None = None
    speech_patterns: list[str] | None = None
    forbidden_rules: list[str] | None = None
    allowed_rules: list[str] | None = None


class PersonaStyleProfileRead(PersonaStyleProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    persona_id: UUID
    created_at: datetime
    updated_at: datetime


class PersonaQuoteBase(BaseModel):
    text: str
    usage_context: str | None = None
    is_allowed: bool = True


class PersonaQuoteCreate(PersonaQuoteBase):
    pass


class PersonaQuoteRead(PersonaQuoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    persona_id: UUID
    created_at: datetime
    updated_at: datetime


class PersonaPhraseTemplateBase(BaseModel):
    type: str
    template: str
    usage: str | None = None


class PersonaPhraseTemplateCreate(PersonaPhraseTemplateBase):
    pass


class PersonaPhraseTemplateRead(PersonaPhraseTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    persona_id: UUID
    created_at: datetime
    updated_at: datetime


class PersonaStyleExampleBase(BaseModel):
    title: str
    text: str
    tags: list[str]


class PersonaStyleExampleCreate(PersonaStyleExampleBase):
    pass


class PersonaStyleExampleRead(PersonaStyleExampleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    persona_id: UUID
    created_at: datetime
    updated_at: datetime


class PersonaCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    is_active: bool = True
    style_profile: PersonaStyleProfileCreate | None = None
    quotes: list[PersonaQuoteCreate] = Field(default_factory=list)
    phrase_templates: list[PersonaPhraseTemplateCreate] = Field(default_factory=list)
    style_examples: list[PersonaStyleExampleCreate] = Field(default_factory=list)


class PersonaUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    is_active: bool | None = None
    style_profile: PersonaStyleProfileUpdate | None = None


class PersonaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    style_profile: PersonaStyleProfileRead | None = None
    quotes: list[PersonaQuoteRead] = Field(default_factory=list)
    phrase_templates: list[PersonaPhraseTemplateRead] = Field(default_factory=list)
    style_examples: list[PersonaStyleExampleRead] = Field(default_factory=list)
