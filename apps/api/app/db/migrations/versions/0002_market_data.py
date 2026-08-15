"""create market data tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LISTING_STATUS = sa.Enum(
    "ACTIVE", "SUSPENDED", "DELISTED", name="listing_status", native_enum=False
)
_QUALITY_STATUS = sa.Enum(
    "VALID", "INVALID", "STALE", "SUSPECT", name="data_quality_status", native_enum=False
)
_ACTION_TYPE = sa.Enum(
    "SPLIT",
    "REVERSE_SPLIT",
    "CASH_DIVIDEND",
    "STOCK_DIVIDEND",
    "BONUS_ISSUE",
    "RIGHTS_ISSUE",
    "OTHER",
    name="corporate_action_type",
    native_enum=False,
)
_INGESTION_STATUS = sa.Enum(
    "RUNNING", "SUCCEEDED", "FAILED", "PARTIAL", name="ingestion_status", native_enum=False
)


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("exchange", sa.String(length=16), nullable=False),
        sa.Column("mic", sa.String(length=16), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("security_type", sa.String(length=32), nullable=False),
        sa.Column("sector", sa.String(length=128), nullable=True),
        sa.Column("subsector", sa.String(length=128), nullable=True),
        sa.Column("listing_date", sa.Date(), nullable=True),
        sa.Column("delisting_date", sa.Date(), nullable=True),
        sa.Column("status", _LISTING_STATUS, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_symbol", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_instruments_symbol", "instruments", ["symbol"], unique=True)

    op.create_table(
        "instrument_status_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("status", _LISTING_STATUS, nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_instrument_status_history_instrument_id",
        "instrument_status_history",
        ["instrument_id"],
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", _INGESTION_STATUS, nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("records_flagged", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "price_bars",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4), nullable=False),
        sa.Column("high", sa.Numeric(18, 4), nullable=False),
        sa.Column("low", sa.Numeric(18, 4), nullable=False),
        sa.Column("close", sa.Numeric(18, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("previous_close", sa.Numeric(18, 4), nullable=True),
        sa.Column("change", sa.Numeric(18, 4), nullable=True),
        sa.Column("change_percent", sa.Numeric(9, 4), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_symbol", sa.String(length=32), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), sa.ForeignKey("ingestion_runs.id"), nullable=True),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("quality_status", _QUALITY_STATUS, nullable=False),
        sa.Column("quality_notes", sa.JSON(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.UniqueConstraint("instrument_id", "trade_date", "source", name="uq_price_bar_identity"),
    )
    op.create_index("ix_price_bars_instrument_id", "price_bars", ["instrument_id"])
    op.create_index("ix_price_bars_trade_date", "price_bars", ["trade_date"])

    op.create_table(
        "corporate_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("action_type", _ACTION_TYPE, nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ratio", sa.Numeric(12, 6), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_symbol", sa.String(length=32), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), sa.ForeignKey("ingestion_runs.id"), nullable=True),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.UniqueConstraint(
            "instrument_id",
            "action_type",
            "ex_date",
            "source",
            name="uq_corporate_action_identity",
        ),
    )
    op.create_index("ix_corporate_actions_instrument_id", "corporate_actions", ["instrument_id"])
    op.create_index("ix_corporate_actions_ex_date", "corporate_actions", ["ex_date"])

    op.create_table(
        "trading_calendar",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_trading_day", sa.Boolean(), nullable=False),
        sa.Column("session_open", sa.Time(), nullable=True),
        sa.Column("session_close", sa.Time(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_trading_calendar_date", "trading_calendar", ["date"], unique=True)


def downgrade() -> None:
    op.drop_table("trading_calendar")
    op.drop_index("ix_corporate_actions_ex_date", table_name="corporate_actions")
    op.drop_index("ix_corporate_actions_instrument_id", table_name="corporate_actions")
    op.drop_table("corporate_actions")
    op.drop_index("ix_price_bars_trade_date", table_name="price_bars")
    op.drop_index("ix_price_bars_instrument_id", table_name="price_bars")
    op.drop_table("price_bars")
    op.drop_table("ingestion_runs")
    op.drop_index(
        "ix_instrument_status_history_instrument_id", table_name="instrument_status_history"
    )
    op.drop_table("instrument_status_history")
    op.drop_index("ix_instruments_symbol", table_name="instruments")
    op.drop_table("instruments")
