from datetime import date, datetime, time
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.domain.generation.enums import Gender, GenerationStatus


class BirthPlace(BaseModel):
    city: str
    country: str
    lat: float
    lng: float
    timezone: str


class GenerationCreate(BaseModel):
    person_name: str | None = None
    gender: Gender | None = None
    birth_date: date
    birth_time: time
    birth_place: BirthPlace
    persona_id: UUID


class GenerationCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generation_id: UUID = Field(
        validation_alias=AliasChoices("generation_id", "id"),
        serialization_alias="generation_id",
    )
    status: GenerationStatus


class GenerationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generation_id: UUID = Field(
        validation_alias=AliasChoices("generation_id", "id"),
        serialization_alias="generation_id",
    )
    status: GenerationStatus
    result_text: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
