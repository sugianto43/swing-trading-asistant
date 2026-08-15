"""create backtest_runs, backtest_trades, backtest_equity_points, backtest_metrics

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
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
_BACKTEST_STATUS = sa.Enum(
    "RUNNING", "SUCCEEDED", "FAILED", name="backtest_status", native_enum=False
)
_EXECUTION_MODEL = sa.Enum("NEXT_OPEN", name="execution_model", native_enum=False)
_EXIT_REASON = sa.Enum(
    "STOP", "TARGET", "TIME", "END_OF_BACKTEST", name="exit_reason", native_enum=False
)


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("setup_type", _SETUP_TYPE, nullable=False),
        sa.Column("min_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(18, 2), nullable=False),
        sa.Column("risk_per_trade_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("max_concurrent_positions", sa.Integer(), nullable=False),
        sa.Column("fee_bps", sa.Numeric(9, 4), nullable=False),
        sa.Column("slippage_bps", sa.Numeric(9, 4), nullable=False),
        sa.Column("stop_atr_multiplier", sa.Numeric(6, 2), nullable=False),
        sa.Column("target_atr_multiplier", sa.Numeric(6, 2), nullable=False),
        sa.Column("max_holding_days", sa.Integer(), nullable=False),
        sa.Column("execution_model", _EXECUTION_MODEL, nullable=False),
        sa.Column("indicator_version", sa.String(length=32), nullable=False),
        sa.Column("score_version", sa.String(length=32), nullable=False),
        sa.Column("status", _BACKTEST_STATUS, nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("backtest_run_id", sa.Uuid(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("setup_type", _SETUP_TYPE, nullable=False),
        sa.Column("signal_date", sa.Date(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("stop_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("target_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("exit_date", sa.Date(), nullable=True),
        sa.Column("exit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("exit_reason", _EXIT_REASON, nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("fees_paid", sa.Numeric(18, 4), nullable=False),
        sa.Column("slippage_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("pnl", sa.Numeric(18, 4), nullable=True),
        sa.Column("r_multiple", sa.Numeric(9, 4), nullable=True),
        sa.Column("holding_days", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_backtest_trades_backtest_run_id", "backtest_trades", ["backtest_run_id"])
    op.create_index("ix_backtest_trades_instrument_id", "backtest_trades", ["instrument_id"])

    op.create_table(
        "backtest_equity_points",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("backtest_run_id", sa.Uuid(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("equity_value", sa.Numeric(18, 2), nullable=False),
        sa.UniqueConstraint(
            "backtest_run_id", "trade_date", name="uq_backtest_equity_point_identity"
        ),
    )
    op.create_index(
        "ix_backtest_equity_points_backtest_run_id", "backtest_equity_points", ["backtest_run_id"]
    )
    op.create_index(
        "ix_backtest_equity_points_trade_date", "backtest_equity_points", ["trade_date"]
    )

    op.create_table(
        "backtest_metrics",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "backtest_run_id",
            sa.Uuid(),
            sa.ForeignKey("backtest_runs.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("total_return_pct", sa.Numeric(9, 4), nullable=False),
        sa.Column("cagr_pct", sa.Numeric(9, 4), nullable=True),
        sa.Column("win_rate_pct", sa.Numeric(6, 2), nullable=False),
        sa.Column("avg_win", sa.Numeric(18, 4), nullable=True),
        sa.Column("avg_loss", sa.Numeric(18, 4), nullable=True),
        sa.Column("expectancy", sa.Numeric(18, 4), nullable=True),
        sa.Column("profit_factor", sa.Numeric(9, 4), nullable=True),
        sa.Column("max_drawdown_pct", sa.Numeric(9, 4), nullable=False),
        sa.Column("sharpe_ratio", sa.Numeric(9, 4), nullable=True),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("avg_holding_days", sa.Numeric(9, 2), nullable=True),
        sa.Column("r_distribution", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_backtest_metrics_backtest_run_id", "backtest_metrics", ["backtest_run_id"])


def downgrade() -> None:
    op.drop_index("ix_backtest_metrics_backtest_run_id", table_name="backtest_metrics")
    op.drop_table("backtest_metrics")
    op.drop_index("ix_backtest_equity_points_trade_date", table_name="backtest_equity_points")
    op.drop_index("ix_backtest_equity_points_backtest_run_id", table_name="backtest_equity_points")
    op.drop_table("backtest_equity_points")
    op.drop_index("ix_backtest_trades_instrument_id", table_name="backtest_trades")
    op.drop_index("ix_backtest_trades_backtest_run_id", table_name="backtest_trades")
    op.drop_table("backtest_trades")
    op.drop_table("backtest_runs")
