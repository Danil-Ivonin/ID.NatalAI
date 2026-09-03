"""users and generations

Revision ID: 0001_users_and_generations
Revises:
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_users_and_generations"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

sex_enum = postgresql.ENUM(
    "male",
    "female",
    "undefined",
    name="sex_enum",
    create_type=False,
)


def upgrade() -> None:
    sex_enum.create(op.get_bind(), checkfirst=False)
    op.create_table(
        "users",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column(
            "confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "persons",
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sex", sex_enum, nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("birth_time", sa.Time(), nullable=False),
        sa.Column("birth_lat", sa.Float(), nullable=False),
        sa.Column("birth_lng", sa.Float(), nullable=False),
        sa.Column("birth_timezone", sa.String(length=255), nullable=False),
        sa.Column("birth_city", sa.String(length=255), nullable=False),
        sa.Column("birth_nation", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("person_id"),
    )
    op.create_index("ix_user_person_id", "persons", ["user_id", "person_id"])
    op.create_table(
        "astro_charts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("natal_xml", sa.Text(), nullable=False),
        sa.Column("chart_svg", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.person_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("astro_charts_person_id_idx", "astro_charts", ["person_id"])
    op.create_table(
        "generation_neutral",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("used_model", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("token_usage", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.person_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "generation_neutral_person_id_idx", "generation_neutral", ["person_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "generation_neutral_person_id_idx", table_name="generation_neutral"
    )
    op.drop_table("generation_neutral")
    op.drop_index("astro_charts_person_id_idx", table_name="astro_charts")
    op.drop_table("astro_charts")
    op.drop_index("ix_user_person_id", table_name="persons")
    op.drop_table("persons")
    op.drop_table("users")
    sex_enum.drop(op.get_bind(), checkfirst=False)
