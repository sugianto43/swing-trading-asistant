"""create indicator_snapshots table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "indicator_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("indicator_version", sa.String(length=32), nullable=False),
        sa.Column("sma_20", sa.Numeric(18, 6), nullable=True),
        sa.Column("sma_50", sa.Numeric(18, 6), nullable=True),
        sa.Column("sma_200", sa.Numeric(18, 6), nullable=True),
        sa.Column("ema_20", sa.Numeric(18, 6), nullable=True),
        sa.Column("ema_50", sa.Numeric(18, 6), nullable=True),
        sa.Column("rsi_14", sa.Numeric(9, 6), nullable=True),
        sa.Column("atr_14", sa.Numeric(18, 6), nullable=True),
        sa.Column("macd", sa.Numeric(18, 6), nullable=True),
        sa.Column("macd_signal", sa.Numeric(18, 6), nullable=True),
        sa.Column("macd_histogram", sa.Numeric(18, 6), nullable=True),
        sa.Column("bb_upper", sa.Numeric(18, 6), nullable=True),
        sa.Column("bb_middle", sa.Numeric(18, 6), nullable=True),
        sa.Column("bb_lower", sa.Numeric(18, 6), nullable=True),
        sa.Column("volume_sma_20", sa.Numeric(18, 6), nullable=True),
        sa.Column("relative_volume", sa.Numeric(18, 6), nullable=True),
        sa.Column("rolling_high_20", sa.Numeric(18, 6), nullable=True),
        sa.Column("rolling_low_20", sa.Numeric(18, 6), nullable=True),
        sa.Column("return_1d", sa.Numeric(18, 6), nullable=True),
        sa.Column("volatility_20", sa.Numeric(18, 6), nullable=True),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "instrument_id",
            "trade_date",
            "indicator_version",
            name="uq_indicator_snapshot_identity",
        ),
    )
    op.create_index(
        "ix_indicator_snapshots_instrument_id", "indicator_snapshots", ["instrument_id"]
    )
    op.create_index("ix_indicator_snapshots_trade_date", "indicator_snapshots", ["trade_date"])


def downgrade() -> None:
    op.drop_index("ix_indicator_snapshots_trade_date", table_name="indicator_snapshots")
    op.drop_index("ix_indicator_snapshots_instrument_id", table_name="indicator_snapshots")
    op.drop_table("indicator_snapshots")
