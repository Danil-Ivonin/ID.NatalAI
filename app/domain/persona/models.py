import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.generation.models import Generation


class Persona(Base):
    __tablename__ = "personas"
    __table_args__ = (Index("ix_personas_slug", "slug", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    style_profile: Mapped["PersonaStyleProfile | None"] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    quotes: Mapped[list["PersonaQuote"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    phrase_templates: Mapped[list["PersonaPhraseTemplate"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    style_examples: Mapped[list["PersonaStyleExample"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    generations: Mapped[list["Generation"]] = relationship(back_populates="persona")


class PersonaStyleProfile(Base):
    __tablename__ = "persona_style_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False
    )
    voice_description: Mapped[str] = mapped_column(Text, nullable=False)
    humor_style: Mapped[str] = mapped_column(Text, nullable=False)
    speech_patterns: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    forbidden_rules: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    allowed_rules: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    persona: Mapped[Persona] = relationship(back_populates="style_profile")


class PersonaQuote(Base):
    __tablename__ = "persona_quotes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    usage_context: Mapped[str | None] = mapped_column(Text)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    persona: Mapped[Persona] = relationship(back_populates="quotes")


class PersonaPhraseTemplate(Base):
    __tablename__ = "persona_phrase_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    usage: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    persona: Mapped[Persona] = relationship(back_populates="phrase_templates")


class PersonaStyleExample(Base):
    __tablename__ = "persona_style_examples"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    persona: Mapped[Persona] = relationship(back_populates="style_examples")
