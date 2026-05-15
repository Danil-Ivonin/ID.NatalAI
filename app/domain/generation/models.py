import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.generation.enums import Gender, GenerationStage, GenerationStatus

if TYPE_CHECKING:
    from app.domain.persona.models import Persona
    from app.domain.prompts.models import PromptTemplate


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (Index("ix_generations_status", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_name: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[Gender | None] = mapped_column(String(16))
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[time] = mapped_column(Time, nullable=False)
    birth_city: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_country: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_lat: Mapped[float] = mapped_column(Float, nullable=False)
    birth_lng: Mapped[float] = mapped_column(Float, nullable=False)
    birth_timezone: Mapped[str] = mapped_column(String(255), nullable=False)
    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False
    )
    status: Mapped[GenerationStatus] = mapped_column(
        String(32), default=GenerationStatus.PENDING, nullable=False
    )
    natal_xml: Mapped[str | None] = mapped_column(Text)
    astrology_profile_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_text: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    persona: Mapped["Persona"] = relationship(back_populates="generations")
    runs: Mapped[list["GenerationRun"]] = relationship(
        back_populates="generation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GenerationRun(Base):
    __tablename__ = "generation_runs"
    __table_args__ = (Index("ix_generation_runs_generation_id", "generation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generations.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[GenerationStage] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_templates.id")
    )
    prompt_template_version: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    raw_request: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    generation: Mapped[Generation] = relationship(back_populates="runs")
    prompt_template: Mapped["PromptTemplate | None"] = relationship(
        back_populates="generation_runs"
    )
