"""free generation flow

Revision ID: 0004_free_generation
Revises: 0003_generation_crud
Create Date: 2026-09-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_free_generation"
down_revision: str | Sequence[str] | None = "0003_generation_crud"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE generation_block ADD VALUE IF NOT EXISTS 'intro' BEFORE 'general'")
    op.execute("ALTER TYPE generation_status RENAME VALUE 'complited' TO 'completed'")
    op.execute("ALTER TYPE generation_process_status ADD VALUE IF NOT EXISTS 'processing'")
    op.execute(
        "ALTER TYPE generation_process_status ADD VALUE IF NOT EXISTS "
        "'character_block_generating'"
    )
    op.execute("ALTER TYPE generation_process_status ADD VALUE IF NOT EXISTS 'completed'")

    op.rename_table("generation_character_review", "generation_character_blocks")
    op.execute(
        "ALTER INDEX generation_character_review_generation_id_idx "
        "RENAME TO generation_character_blocks_generation_id_idx"
    )

    for table_name in ("astro_charts", "generation_neutral"):
        op.add_column(
            table_name,
            sa.Column("generation_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            f"{table_name}_generation_id_fkey",
            table_name,
            "generations",
            ["generation_id"],
            ["generation_id"],
            ondelete="CASCADE",
        )
        op.create_index(
            f"{table_name}_generation_id_idx",
            table_name,
            ["generation_id"],
            unique=True,
        )


def downgrade() -> None:
    for table_name in ("generation_neutral", "astro_charts"):
        op.drop_index(f"{table_name}_generation_id_idx", table_name=table_name)
        op.drop_constraint(
            f"{table_name}_generation_id_fkey", table_name, type_="foreignkey"
        )
        op.drop_column(table_name, "generation_id")

    op.execute(
        "ALTER INDEX generation_character_blocks_generation_id_idx "
        "RENAME TO generation_character_review_generation_id_idx"
    )
    op.rename_table("generation_character_blocks", "generation_character_review")
    op.execute("ALTER TYPE generation_status RENAME VALUE 'completed' TO 'complited'")
