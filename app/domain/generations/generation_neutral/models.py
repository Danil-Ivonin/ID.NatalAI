from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.users.models import Person


class GenerationNeutral(Base):
    __tablename__ = "generation_neutral"
    __table_args__ = (Index("generation_neutral_person_id_idx", "person_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.person_id", ondelete="CASCADE"),
        nullable=False,
    )
    used_model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    person: Mapped["Person"] = relationship(back_populates="generation_neutral")
