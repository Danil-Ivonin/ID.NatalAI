"""character persistence

Revision ID: 0001_character_persistence
Revises:
Create Date: 2026-08-27
"""

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_character_persistence"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


character_emotion = postgresql.ENUM(
    "calm",
    "curiosity",
    "playfulness",
    "amusement",
    "warmth",
    "empathy",
    "admiration",
    "hope",
    "confidence",
    "surprise",
    "skepticism",
    "irritation",
    "frustration",
    "anxiety",
    "tension",
    "melancholy",
    "sadness",
    "bitterness",
    "indignation",
    "anger",
    "determination",
    name="character_emotion",
    create_type=False,
)
humor_type = postgresql.ENUM(
    "irony",
    "self_irony",
    "sarcasm",
    "hyperbole",
    "understatement",
    "absurdity",
    "bathos",
    "comic_comparison",
    "reversal",
    "parody",
    "wordplay",
    "literalism",
    "deadpan",
    "mock_seriousness",
    "comic_enumeration",
    "personification",
    "false_naivety",
    "callback",
    "dark_humor",
    name="humor_type",
    create_type=False,
)
speech_pattern = postgresql.ENUM(
    "direct_address",
    "observation",
    "rhetorical_question",
    "question_answer",
    "short_verdict",
    "contrast",
    "antithesis",
    "gradation",
    "parallelism",
    "anaphora",
    "repetition",
    "enumeration",
    "metaphor",
    "analogy",
    "aphorism",
    "paradox",
    "parenthesis",
    "aside",
    "dialogue_imitation",
    "false_concession",
    "self_correction",
    "imperative",
    "abrupt_sentence",
    "long_observation",
    "callback",
    name="speech_pattern",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    character_emotion.create(bind, checkfirst=False)
    humor_type.create(bind, checkfirst=False)
    speech_pattern.create(bind, checkfirst=False)

    op.create_table(
        "characters",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("profile", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "character_examples",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("character_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("clean_text", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("emotion", character_emotion, nullable=False),
        sa.Column("rhetorical_function", sa.Text(), nullable=False),
        sa.Column(
            "humor_types",
            postgresql.ARRAY(humor_type),
            server_default=sa.text("'{}'::humor_type[]"),
            nullable=False,
        ),
        sa.Column(
            "speech_patterns",
            postgresql.ARRAY(speech_pattern),
            server_default=sa.text("'{}'::speech_pattern[]"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(3072), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "character_examples_character_id_idx",
        "character_examples",
        ["character_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "character_examples_character_id_idx",
        table_name="character_examples",
    )
    op.drop_table("character_examples")
    op.drop_table("characters")
    bind = op.get_bind()
    speech_pattern.drop(bind, checkfirst=False)
    humor_type.drop(bind, checkfirst=False)
    character_emotion.drop(bind, checkfirst=False)
