from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.generations.schemas import (
    GenerationBlock,
    GenerationProcessStatus,
    GenerationStatus,
)

if TYPE_CHECKING:
    from app.domain.characters.models import Character
    from app.domain.users.models import Person


def _enum_values(enum: type) -> list[str]:
    return [item.value for item in enum]


GENERATION_BLOCK = Enum(
    GenerationBlock, name="generation_block", values_callable=_enum_values
)
GENERATION_STATUS = Enum(
    GenerationStatus, name="generation_status", values_callable=_enum_values
)
GENERATION_PROCESS_STATUS = Enum(
    GenerationProcessStatus,
    name="generation_process_status",
    values_callable=_enum_values,
)


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (
        Index("generations_person_id_idx", "person_id"),
        Index("generations_character_id_idx", "character_id"),
    )

    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.person_id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    used_examples: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, server_default=text("'{}'::uuid[]"), nullable=False
    )
    current_block: Mapped[GenerationBlock] = mapped_column(GENERATION_BLOCK, nullable=False)
    status: Mapped[GenerationProcessStatus] = mapped_column(
        GENERATION_PROCESS_STATUS,
        default=GenerationProcessStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )
    payed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    person: Mapped["Person"] = relationship(back_populates="generations")
    character: Mapped["Character"] = relationship(back_populates="generations")
    style_plans: Mapped[list["GenerationStylePlan"]] = relationship(
        back_populates="generation", cascade="all, delete-orphan", passive_deletes=True
    )
    character_blocks: Mapped[list["GenerationCharacterBlock"]] = relationship(
        back_populates="generation", cascade="all, delete-orphan", passive_deletes=True
    )


class GenerationStylePlan(Base):
    __tablename__ = "generation_style_plans"
    __table_args__ = (Index("generation_style_plans_generation_id_idx", "generation_id"),)

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generations.generation_id", ondelete="CASCADE"), nullable=False
    )
    block: Mapped[GenerationBlock] = mapped_column(GENERATION_BLOCK, nullable=False)
    status: Mapped[GenerationStatus] = mapped_column(
        GENERATION_STATUS,
        default=GenerationStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )
    used_model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    generation: Mapped[Generation] = relationship(back_populates="style_plans")


class GenerationCharacterBlock(Base):
    __tablename__ = "generation_character_blocks"
    __table_args__ = (Index("generation_character_blocks_generation_id_idx", "generation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generations.generation_id", ondelete="CASCADE"), nullable=False
    )
    block: Mapped[GenerationBlock] = mapped_column(GENERATION_BLOCK, nullable=False)
    status: Mapped[GenerationStatus] = mapped_column(
        GENERATION_STATUS,
        default=GenerationStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )
    used_model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    generation: Mapped[Generation] = relationship(back_populates="character_blocks")
