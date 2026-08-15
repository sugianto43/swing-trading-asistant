"""create job_runs, alerts

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JOB_TYPE = sa.Enum(
    "INGESTION",
    "INDICATORS",
    "SCANNER",
    "RISK_PLANS",
    "BREADTH",
    "ALERTS",
    name="job_type",
    native_enum=False,
)
_JOB_STATUS = sa.Enum(
    "RUNNING", "SUCCEEDED", "FAILED", "PARTIAL", name="job_status", native_enum=False
)
_ALERT_TYPE = sa.Enum(
    "SETUP_DETECTED",
    "BREAKOUT",
    "PRICE_NEAR_ENTRY",
    "PRICE_NEAR_STOP",
    "PRICE_NEAR_TARGET",
    "UNUSUAL_VOLUME",
    "STALE_DATA",
    "IMPORTANT_EVENT",
    name="alert_type",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "job_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_type", _JOB_TYPE, nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("status", _JOB_STATUS, nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_job_runs_job_type", "job_runs", ["job_type"])
    op.create_index("ix_job_runs_run_date", "job_runs", ["run_date"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("alert_type", _ALERT_TYPE, nullable=False),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("trigger_date", sa.Date(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "alert_type", "instrument_id", "trigger_date", name="uq_alert_identity"
        ),
    )
    op.create_index("ix_alerts_alert_type", "alerts", ["alert_type"])
    op.create_index("ix_alerts_instrument_id", "alerts", ["instrument_id"])
    op.create_index("ix_alerts_trigger_date", "alerts", ["trigger_date"])


def downgrade() -> None:
    op.drop_index("ix_alerts_trigger_date", table_name="alerts")
    op.drop_index("ix_alerts_instrument_id", table_name="alerts")
    op.drop_index("ix_alerts_alert_type", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_job_runs_run_date", table_name="job_runs")
    op.drop_index("ix_job_runs_job_type", table_name="job_runs")
    op.drop_table("job_runs")
