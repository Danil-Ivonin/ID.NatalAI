from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Identity, Index, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domain.characters.enums import CharacterEmotion, HumorType, SpeechPattern


def _enum_values(enum_class: type) -> list[str]:
    return [member.value for member in enum_class]


CHARACTER_EMOTION = Enum(
    CharacterEmotion,
    name="character_emotion",
    values_callable=_enum_values,
)
HUMOR_TYPE = Enum(HumorType, name="humor_type", values_callable=_enum_values)
SPEECH_PATTERN = Enum(
    SpeechPattern,
    name="speech_pattern",
    values_callable=_enum_values,
)


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class CharacterExample(Base):
    __tablename__ = "character_examples"
    __table_args__ = (
        Index("character_examples_character_id_idx", "character_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    character_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    clean_text: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[CharacterEmotion] = mapped_column(
        CHARACTER_EMOTION,
        nullable=False,
    )
    rhetorical_function: Mapped[str] = mapped_column(Text, nullable=False)
    humor_types: Mapped[list[HumorType]] = mapped_column(
        ARRAY(HUMOR_TYPE),
        default=list,
        server_default=text("'{}'::humor_type[]"),
        nullable=False,
    )
    speech_patterns: Mapped[list[SpeechPattern]] = mapped_column(
        ARRAY(SPEECH_PATTERN),
        default=list,
        server_default=text("'{}'::speech_pattern[]"),
        nullable=False,
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(3072))
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
