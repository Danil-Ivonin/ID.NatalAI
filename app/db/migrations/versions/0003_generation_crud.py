"""generation crud

Revision ID: 0003_generation_crud
Revises: 0002_character_parent
Create Date: 2026-09-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_generation_crud"
down_revision: str | Sequence[str] | None = "0002_character_parent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

generation_block = postgresql.ENUM(
    "general",
    "love",
    "work_money",
    "inner_demons",
    name="generation_block",
    create_type=False,
)
generation_status = postgresql.ENUM(
    "pending",
    "processing",
    "complited",
    "failed",
    name="generation_status",
    create_type=False,
)
generation_process_status = postgresql.ENUM(
    "pending",
    "style_plan_generating",
    "character_review_generating",
    "failed",
    name="generation_process_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    generation_block.create(bind, checkfirst=False)
    generation_status.create(bind, checkfirst=False)
    generation_process_status.create(bind, checkfirst=False)

    op.create_table(
        "generations",
        sa.Column(
            "generation_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "used_examples",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default=sa.text("'{}'::uuid[]"),
            nullable=False,
        ),
        sa.Column("current_block", generation_block, nullable=False),
        sa.Column(
            "status",
            generation_process_status,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "payed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.person_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("generation_id"),
    )
    op.create_index("generations_person_id_idx", "generations", ["person_id"])
    op.create_index(
        "generations_character_id_idx", "generations", ["character_id"]
    )

    for table_name, id_name in (
        ("generation_style_plans", "plan_id"),
        ("generation_character_review", "id"),
    ):
        op.create_table(
            table_name,
            sa.Column(
                id_name,
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("uuidv7()"),
                nullable=False,
            ),
            sa.Column(
                "generation_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column("block", generation_block, nullable=False),
            sa.Column(
                "status",
                generation_status,
                server_default=sa.text("'pending'"),
                nullable=False,
            ),
            sa.Column("used_model", sa.Text(), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("token_usage", postgresql.JSONB(), nullable=False),
            sa.Column("result", postgresql.JSONB(), nullable=False),
            sa.ForeignKeyConstraint(
                ["generation_id"],
                ["generations.generation_id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint(id_name),
        )
        op.create_index(
            f"{table_name}_generation_id_idx", table_name, ["generation_id"]
        )


def downgrade() -> None:
    for table_name in (
        "generation_character_review",
        "generation_style_plans",
    ):
        op.drop_index(f"{table_name}_generation_id_idx", table_name=table_name)
        op.drop_table(table_name)
    op.drop_index("generations_character_id_idx", table_name="generations")
    op.drop_index("generations_person_id_idx", table_name="generations")
    op.drop_table("generations")

    bind = op.get_bind()
    generation_process_status.drop(bind, checkfirst=False)
    generation_status.drop(bind, checkfirst=False)
    generation_block.drop(bind, checkfirst=False)
