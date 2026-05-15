from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PersonaContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona_name: str
    persona_slug: str
    persona_description: str | None
    voice_description: str
    humor_style: str
    speech_patterns: list[str]
    allowed_rules: list[str]
    forbidden_rules: list[str]
    allowed_quotes: list[str]
    phrase_templates: list[str]
    style_examples: list[str]


class PersonaContextProvider(Protocol):
    async def get_context(self, persona_id: UUID) -> PersonaContext:
        ...
