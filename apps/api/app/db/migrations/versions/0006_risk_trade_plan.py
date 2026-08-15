"""create trade_plans

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SETUP_TYPE = sa.Enum(
    "BREAKOUT",
    "PULLBACK_CONTINUATION",
    "MOMENTUM_CONTINUATION",
    "MA_RECLAIM",
    "VOLATILITY_SQUEEZE",
    name="setup_type",
    native_enum=False,
)
_TRADE_PLAN_STATUS = sa.Enum("VALID", "REJECTED", name="trade_plan_status", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "trade_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column(
            "scan_candidate_id", sa.Uuid(), sa.ForeignKey("scan_candidates.id"), nullable=True
        ),
        sa.Column("setup_type", _SETUP_TYPE, nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("risk_version", sa.String(length=32), nullable=False),
        sa.Column("score_version", sa.String(length=32), nullable=True),
        sa.Column("indicator_version", sa.String(length=32), nullable=True),
        sa.Column("status", _TRADE_PLAN_STATUS, nullable=False),
        sa.Column("rejection_reasons", sa.JSON(), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("stop_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("target_prices", sa.JSON(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("allocation_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("allocation_pct", sa.Numeric(9, 4), nullable=False),
        sa.Column("max_loss_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("risk_reward_ratio", sa.Numeric(9, 4), nullable=True),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("invalidation_conditions", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "instrument_id",
            "plan_date",
            "setup_type",
            "risk_version",
            name="uq_trade_plan_identity",
        ),
    )
    op.create_index("ix_trade_plans_instrument_id", "trade_plans", ["instrument_id"])
    op.create_index("ix_trade_plans_plan_date", "trade_plans", ["plan_date"])


def downgrade() -> None:
    op.drop_index("ix_trade_plans_plan_date", table_name="trade_plans")
    op.drop_index("ix_trade_plans_instrument_id", table_name="trade_plans")
    op.drop_table("trade_plans")
