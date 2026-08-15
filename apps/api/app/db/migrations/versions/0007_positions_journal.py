"""create positions, executions, journal_entries

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_POSITION_STATUS = sa.Enum(
    "PLANNED",
    "OPEN",
    "PARTIALLY_CLOSED",
    "CLOSED",
    "CANCELLED",
    name="position_status",
    native_enum=False,
)
_EXECUTION_SIDE = sa.Enum("BUY", "SELL", name="execution_side", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "positions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("trade_plan_id", sa.Uuid(), sa.ForeignKey("trade_plans.id"), nullable=True),
        sa.Column("status", _POSITION_STATUS, nullable=False),
        sa.Column("quantity_open", sa.Integer(), nullable=False),
        sa.Column("avg_entry_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("avg_entry_fee_per_share", sa.Numeric(18, 6), nullable=False),
        sa.Column("cumulative_quantity_bought", sa.Integer(), nullable=False),
        sa.Column("cumulative_entry_fees", sa.Numeric(18, 4), nullable=False),
        sa.Column("cumulative_exit_fees", sa.Numeric(18, 4), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(18, 4), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_positions_instrument_id", "positions", ["instrument_id"])
    op.create_index("ix_positions_status", "positions", ["status"])
    # partial unique index: at most one PLANNED/OPEN/PARTIALLY_CLOSED
    # position per instrument, enforced at the DB level (not just by
    # ExecutionService's check-then-insert, which a race between two
    # concurrent requests could otherwise slip past silently).
    op.create_index(
        "uq_positions_one_non_terminal_per_instrument",
        "positions",
        ["instrument_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PLANNED', 'OPEN', 'PARTIALLY_CLOSED')"),
        sqlite_where=sa.text("status IN ('PLANNED', 'OPEN', 'PARTIALLY_CLOSED')"),
    )

    op.create_table(
        "executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("position_id", sa.Uuid(), sa.ForeignKey("positions.id"), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("trade_plan_id", sa.Uuid(), sa.ForeignKey("trade_plans.id"), nullable=True),
        sa.Column("side", _EXECUTION_SIDE, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=False),
        sa.Column("fee", sa.Numeric(18, 4), nullable=False),
        sa.Column("realized_pnl_impact", sa.Numeric(18, 4), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_executions_position_id", "executions", ["position_id"])
    op.create_index("ix_executions_instrument_id", "executions", ["instrument_id"])
    op.create_index("ix_executions_executed_at", "executions", ["executed_at"])

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "position_id",
            sa.Uuid(),
            sa.ForeignKey("positions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("thesis", sa.Text(), nullable=True),
        sa.Column("market_context", sa.Text(), nullable=True),
        sa.Column("execution_quality", sa.Text(), nullable=True),
        sa.Column("behavioral_notes", sa.Text(), nullable=True),
        sa.Column("plan_adherence_notes", sa.Text(), nullable=True),
        sa.Column("mistakes", sa.Text(), nullable=True),
        sa.Column("lessons", sa.Text(), nullable=True),
        sa.Column("reference_urls", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_journal_entries_position_id", "journal_entries", ["position_id"])


def downgrade() -> None:
    op.drop_index("ix_journal_entries_position_id", table_name="journal_entries")
    op.drop_table("journal_entries")
    op.drop_index("ix_executions_executed_at", table_name="executions")
    op.drop_index("ix_executions_instrument_id", table_name="executions")
    op.drop_index("ix_executions_position_id", table_name="executions")
    op.drop_table("executions")
    op.drop_index("uq_positions_one_non_terminal_per_instrument", table_name="positions")
    op.drop_index("ix_positions_status", table_name="positions")
    op.drop_index("ix_positions_instrument_id", table_name="positions")
    op.drop_table("positions")
