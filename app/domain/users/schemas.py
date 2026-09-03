from datetime import date, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.users.enums import Sex


class UserCreate(BaseModel):
    email: str = Field(min_length=1, max_length=255)


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=1, max_length=255)
    confirmed: bool = Field(default=False)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: str | None
    confirmed: bool


class PersonBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sex: Sex | None = None
    birth_date: date
    birth_time: time
    birth_lat: float = Field(ge=-90, le=90)
    birth_lng: float = Field(ge=-180, le=180)
    birth_timezone: str = Field(min_length=1, max_length=255)
    birth_city: str = Field(min_length=1, max_length=255)
    birth_nation: str = Field(min_length=1, max_length=255)


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sex: Sex | None = None
    birth_date: date | None = None
    birth_time: time | None = None
    birth_lat: float| None = Field(default=None, ge=-90, le=90)
    birth_lng: float| None = Field(default=None, ge=-180, le=180)
    birth_timezone: str | None = Field(default=None, min_length=1, max_length=255)
    birth_city: str | None = Field(default=None, min_length=1, max_length=255)
    birth_nation: str | None = Field(default=None, min_length=1, max_length=255)


class PersonRead(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    person_id: UUID
    user_id: UUID
