"""create breadth_snapshots

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MARKET_REGIME = sa.Enum("RISK_ON", "RISK_OFF", "NEUTRAL", name="market_regime", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "breadth_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("breadth_version", sa.String(length=32), nullable=False),
        sa.Column("universe_size", sa.Integer(), nullable=False),
        sa.Column("pct_above_sma50", sa.Numeric(9, 6), nullable=True),
        sa.Column("pct_above_sma200", sa.Numeric(9, 6), nullable=True),
        sa.Column("advancers", sa.Integer(), nullable=False),
        sa.Column("decliners", sa.Integer(), nullable=False),
        sa.Column("unchanged", sa.Integer(), nullable=False),
        sa.Column("new_highs_20", sa.Integer(), nullable=False),
        sa.Column("new_lows_20", sa.Integer(), nullable=False),
        sa.Column("regime", _MARKET_REGIME, nullable=False),
        sa.Column("regime_version", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("as_of", "breadth_version", name="uq_breadth_snapshot_identity"),
    )
    op.create_index("ix_breadth_snapshots_as_of", "breadth_snapshots", ["as_of"])


def downgrade() -> None:
    op.drop_index("ix_breadth_snapshots_as_of", table_name="breadth_snapshots")
    op.drop_table("breadth_snapshots")
