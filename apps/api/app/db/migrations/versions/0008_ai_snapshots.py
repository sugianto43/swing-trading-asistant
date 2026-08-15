"""create analysis_snapshots

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("tool_calls", sa.JSON(), nullable=False),
        sa.Column("structured_data_snapshot", sa.JSON(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("guardrail_flags", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_analysis_snapshots_instrument_id", "analysis_snapshots", ["instrument_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_snapshots_instrument_id", table_name="analysis_snapshots")
    op.drop_table("analysis_snapshots")
