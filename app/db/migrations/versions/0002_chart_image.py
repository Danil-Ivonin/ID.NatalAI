"""Add natal chart image fields to generations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_chart_image"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generations",
        sa.Column("chart_image_object_key", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "generations",
        sa.Column("chart_image_mime_type", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generations", "chart_image_mime_type")
    op.drop_column("generations", "chart_image_object_key")
