"""create scan_runs and scan_candidates tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
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
_SCAN_STATUS = sa.Enum(
    "RUNNING", "SUCCEEDED", "FAILED", "PARTIAL", name="scan_status", native_enum=False
)


def upgrade() -> None:
    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scan_date", sa.Date(), nullable=False),
        sa.Column("score_version", sa.String(length=32), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", _SCAN_STATUS, nullable=False),
        sa.Column("symbols_scanned", sa.Integer(), nullable=False),
        sa.Column("symbols_skipped_stale", sa.Integer(), nullable=False),
        sa.Column("candidates_found", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_scan_runs_scan_date", "scan_runs", ["scan_date"])

    op.create_table(
        "scan_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("scan_date", sa.Date(), nullable=False),
        sa.Column("setup_type", _SETUP_TYPE, nullable=False),
        sa.Column("indicator_version", sa.String(length=32), nullable=False),
        sa.Column("score_version", sa.String(length=32), nullable=False),
        sa.Column("composite_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("trend_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("momentum_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("volume_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("price_structure_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("volatility_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("setup_quality_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("risk_reward_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("qualifying_conditions", sa.JSON(), nullable=False),
        sa.Column("invalidation_conditions", sa.JSON(), nullable=False),
        sa.Column("scan_run_id", sa.Uuid(), sa.ForeignKey("scan_runs.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "instrument_id",
            "scan_date",
            "setup_type",
            "indicator_version",
            "score_version",
            name="uq_scan_candidate_identity",
        ),
    )
    op.create_index("ix_scan_candidates_instrument_id", "scan_candidates", ["instrument_id"])
    op.create_index("ix_scan_candidates_scan_date", "scan_candidates", ["scan_date"])


def downgrade() -> None:
    op.drop_index("ix_scan_candidates_scan_date", table_name="scan_candidates")
    op.drop_index("ix_scan_candidates_instrument_id", table_name="scan_candidates")
    op.drop_table("scan_candidates")
    op.drop_index("ix_scan_runs_scan_date", table_name="scan_runs")
    op.drop_table("scan_runs")
