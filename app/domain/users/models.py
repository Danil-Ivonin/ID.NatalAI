from datetime import date, time
import uuid

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Index, String, Time, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.users.enums import Sex


SEX = Enum(Sex, name="sex_enum", values_callable=lambda enum: [item.value for item in enum])


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    email: Mapped[str | None] = mapped_column(String(255))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)


class Person(Base):
    __tablename__ = "persons"
    __table_args__ = (Index("ix_user_person_id", "user_id", "person_id"),)

    person_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sex: Mapped[Sex] = mapped_column(SEX, nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[time] = mapped_column(Time, nullable=False)
    birth_lat: Mapped[float] = mapped_column(Float, nullable=False)
    birth_lng: Mapped[float] = mapped_column(Float, nullable=False)
    birth_timezone: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_city: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_nation: Mapped[str] = mapped_column(String(255), nullable=False)

    astro_charts: Mapped[list["AstroChart"]] = relationship(
        back_populates="person", cascade="all, delete-orphan", passive_deletes=True
    )
    generation_neutral: Mapped[list["GenerationNeutral"]] = relationship(
        back_populates="person", cascade="all, delete-orphan", passive_deletes=True
    )
