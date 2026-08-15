import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    JSON as SqlJSON,
)
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import (
    AlertType,
    BacktestStatus,
    CorporateActionType,
    DataQualityStatus,
    ExecutionModel,
    ExecutionSide,
    ExitReason,
    IngestionStatus,
    JobStatus,
    JobType,
    ListingStatus,
    MarketRegime,
    PositionStatus,
    ScanStatus,
    SetupType,
    TradePlanStatus,
)


class User(Base):
    """Auth-ready user record. No auth vendor coupling in this phase."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Instrument(Base):
    """Canonical IDX instrument master record.

    Vendor-specific identifiers live in source/source_symbol; symbol is the
    application-canonical ticker used everywhere else in the domain.
    """

    __tablename__ = "instruments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    exchange: Mapped[str] = mapped_column(String(16), default="IDX")
    mic: Mapped[str | None] = mapped_column(String(16), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="IDR")
    security_type: Mapped[str] = mapped_column(String(32), default="EQUITY")
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subsector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delisting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ListingStatus] = mapped_column(
        SqlEnum(ListingStatus, native_enum=False), default=ListingStatus.ACTIVE
    )
    source: Mapped[str] = mapped_column(String(64))
    source_symbol: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InstrumentStatusHistory(Base):
    """Timestamp-aware universe membership, so historical research can
    reconstruct which instruments were active/suspended/delisted as of a
    given date (avoids survivorship bias)."""

    __tablename__ = "instrument_status_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    status: Mapped[ListingStatus] = mapped_column(SqlEnum(ListingStatus, native_enum=False))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PriceBar(Base):
    """Raw (unadjusted) daily OHLCV. Adjusted series are computed on read
    from CorporateAction records, never persisted as a second table."""

    __tablename__ = "price_bars"
    __table_args__ = (
        UniqueConstraint("instrument_id", "trade_date", "source", name="uq_price_bar_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Numeric(18, 4))
    high: Mapped[float] = mapped_column(Numeric(18, 4))
    low: Mapped[float] = mapped_column(Numeric(18, 4))
    close: Mapped[float] = mapped_column(Numeric(18, 4))
    volume: Mapped[int] = mapped_column(BigInteger)
    previous_close: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    change_percent: Mapped[float | None] = mapped_column(Numeric(9, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    source_symbol: Mapped[str] = mapped_column(String(32))
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    quality_status: Mapped[DataQualityStatus] = mapped_column(
        SqlEnum(DataQualityStatus, native_enum=False), default=DataQualityStatus.VALID
    )
    quality_notes: Mapped[list[str] | None] = mapped_column(SqlJSON, nullable=True)
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(SqlJSON, nullable=True)


class CorporateAction(Base):
    """Raw corporate action record. Split/dividend ratios drive on-read
    price adjustment; announced_at/effective_date are kept distinct per
    QUANT-TRADING-RULES (publication timestamp vs effective date)."""

    __tablename__ = "corporate_actions"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "action_type", "ex_date", "source", name="uq_corporate_action_identity"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    action_type: Mapped[CorporateActionType] = mapped_column(
        SqlEnum(CorporateActionType, native_enum=False)
    )
    ex_date: Mapped[date] = mapped_column(Date, index=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    announced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ratio: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    source_symbol: Mapped[str] = mapped_column(String(32))
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(SqlJSON, nullable=True)


class TradingCalendarDay(Base):
    """Trading calendar, populated incrementally from observed trading
    days in ingested bars (no holiday-calendar API is available from the
    current provider). This is a documented limitation, not a silent gap."""

    __tablename__ = "trading_calendar"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    is_trading_day: Mapped[bool] = mapped_column(default=True)
    session_open: Mapped[time | None] = mapped_column(Time, nullable=True)
    session_close: Mapped[time | None] = mapped_column(Time, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="observed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IndicatorSnapshot(Base):
    """Canonical technical-indicator values for one instrument/date, tied
    to the formula/parameter set that produced them (indicator_version) so
    historical results stay traceable to their exact configuration
    (MASTER-PRD §21). Computed from split-adjusted VALID price bars only —
    see app/indicators/engine.py."""

    __tablename__ = "indicator_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "trade_date",
            "indicator_version",
            name="uq_indicator_snapshot_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    indicator_version: Mapped[str] = mapped_column(String(32))

    sma_20: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    sma_50: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    sma_200: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    ema_20: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    ema_50: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    rsi_14: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    atr_14: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    macd: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    macd_histogram: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    bb_upper: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    bb_middle: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    bb_lower: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    volume_sma_20: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    relative_volume: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    rolling_high_20: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    rolling_low_20: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    return_1d: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    volatility_20: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class IngestionRun(Base):
    """Audit/lineage trail for each ingestion batch."""

    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_name: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[IngestionStatus] = mapped_column(
        SqlEnum(IngestionStatus, native_enum=False), default=IngestionStatus.RUNNING
    )
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_flagged: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScanCandidate(Base):
    """One qualifying setup for one instrument on one scan date.

    Only persisted when the setup's qualifying conditions are actually
    met — a symbol with no qualifying setup on a given date simply has no
    row, it is not represented as a zero-score candidate. Score/version
    fields make results traceable to the exact scoring configuration that
    produced them (MASTER-PRD §21), mirroring indicator_version.
    """

    __tablename__ = "scan_candidates"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "scan_date",
            "setup_type",
            "indicator_version",
            "score_version",
            name="uq_scan_candidate_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    scan_date: Mapped[date] = mapped_column(Date, index=True)
    setup_type: Mapped[SetupType] = mapped_column(SqlEnum(SetupType, native_enum=False))
    indicator_version: Mapped[str] = mapped_column(String(32))
    score_version: Mapped[str] = mapped_column(String(32))

    composite_score: Mapped[float] = mapped_column(Numeric(6, 2))
    trend_score: Mapped[float] = mapped_column(Numeric(6, 2))
    momentum_score: Mapped[float] = mapped_column(Numeric(6, 2))
    volume_score: Mapped[float] = mapped_column(Numeric(6, 2))
    price_structure_score: Mapped[float] = mapped_column(Numeric(6, 2))
    volatility_score: Mapped[float] = mapped_column(Numeric(6, 2))
    setup_quality_score: Mapped[float] = mapped_column(Numeric(6, 2))
    risk_reward_score: Mapped[float] = mapped_column(Numeric(6, 2))

    qualifying_conditions: Mapped[list[str]] = mapped_column(SqlJSON)
    invalidation_conditions: Mapped[list[str]] = mapped_column(SqlJSON)

    scan_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scan_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScanRun(Base):
    """Audit/lineage trail for each scan batch, same pattern as
    IngestionRun. Records how many symbols were skipped due to stale data
    so that gate is traceable, not silently invisible (MASTER-PRD §20)."""

    __tablename__ = "scan_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scan_date: Mapped[date] = mapped_column(Date, index=True)
    score_version: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ScanStatus] = mapped_column(
        SqlEnum(ScanStatus, native_enum=False), default=ScanStatus.RUNNING
    )
    symbols_scanned: Mapped[int] = mapped_column(Integer, default=0)
    symbols_skipped_stale: Mapped[int] = mapped_column(Integer, default=0)
    candidates_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BacktestRun(Base):
    """One backtest experiment. Unlike ingestion/indicator/scan runs, a
    backtest is not idempotently upserted — each invocation creates a new
    row, since users legitimately want to compare multiple runs (same
    config re-run for reproducibility, or different configs side by
    side). All config fields are captured so a historical run stays
    traceable to the exact parameters that produced it (MASTER-PRD §21).

    Reproducibility here means: identical config + identical underlying
    DB state -> identical results. There is no separate frozen dataset
    snapshot system (an open MASTER-PRD decision) — this is a documented
    limitation, not a silent gap.
    """

    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    strategy_version: Mapped[str] = mapped_column(String(32))
    setup_type: Mapped[SetupType] = mapped_column(SqlEnum(SetupType, native_enum=False))
    min_score: Mapped[float] = mapped_column(Numeric(6, 2))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    initial_capital: Mapped[float] = mapped_column(Numeric(18, 2))
    risk_per_trade_pct: Mapped[float] = mapped_column(Numeric(6, 4))
    max_concurrent_positions: Mapped[int] = mapped_column(Integer)
    fee_bps: Mapped[float] = mapped_column(Numeric(9, 4))
    slippage_bps: Mapped[float] = mapped_column(Numeric(9, 4))
    stop_atr_multiplier: Mapped[float] = mapped_column(Numeric(6, 2))
    target_atr_multiplier: Mapped[float] = mapped_column(Numeric(6, 2))
    max_holding_days: Mapped[int] = mapped_column(Integer)
    execution_model: Mapped[ExecutionModel] = mapped_column(
        SqlEnum(ExecutionModel, native_enum=False)
    )
    indicator_version: Mapped[str] = mapped_column(String(32))
    score_version: Mapped[str] = mapped_column(String(32))

    status: Mapped[BacktestStatus] = mapped_column(
        SqlEnum(BacktestStatus, native_enum=False), default=BacktestStatus.RUNNING
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BacktestTrade(Base):
    """One simulated round-trip trade within a backtest run."""

    __tablename__ = "backtest_trades"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    backtest_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backtest_runs.id"), index=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    setup_type: Mapped[SetupType] = mapped_column(SqlEnum(SetupType, native_enum=False))
    signal_date: Mapped[date] = mapped_column(Date)
    entry_date: Mapped[date] = mapped_column(Date)
    entry_price: Mapped[float] = mapped_column(Numeric(18, 4))
    stop_price: Mapped[float] = mapped_column(Numeric(18, 4))
    target_price: Mapped[float] = mapped_column(Numeric(18, 4))
    exit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    exit_reason: Mapped[ExitReason | None] = mapped_column(
        SqlEnum(ExitReason, native_enum=False), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    fees_paid: Mapped[float] = mapped_column(Numeric(18, 4))
    slippage_cost: Mapped[float] = mapped_column(Numeric(18, 4))
    pnl: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    r_multiple: Mapped[float | None] = mapped_column(Numeric(9, 4), nullable=True)
    holding_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BacktestEquityPoint(Base):
    """Daily mark-to-market equity value for a backtest run's equity
    curve/drawdown calculation."""

    __tablename__ = "backtest_equity_points"
    __table_args__ = (
        UniqueConstraint("backtest_run_id", "trade_date", name="uq_backtest_equity_point_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    backtest_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backtest_runs.id"), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    equity_value: Mapped[float] = mapped_column(Numeric(18, 2))


class BacktestMetrics(Base):
    """Performance metrics computed once at run completion (MASTER-PRD
    FR-012). One row per backtest run."""

    __tablename__ = "backtest_metrics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("backtest_runs.id"), unique=True, index=True
    )
    total_return_pct: Mapped[float] = mapped_column(Numeric(9, 4))
    cagr_pct: Mapped[float | None] = mapped_column(Numeric(9, 4), nullable=True)
    win_rate_pct: Mapped[float] = mapped_column(Numeric(6, 2))
    avg_win: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    avg_loss: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    expectancy: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    profit_factor: Mapped[float | None] = mapped_column(Numeric(9, 4), nullable=True)
    max_drawdown_pct: Mapped[float] = mapped_column(Numeric(9, 4))
    sharpe_ratio: Mapped[float | None] = mapped_column(Numeric(9, 4), nullable=True)
    trade_count: Mapped[int] = mapped_column(Integer)
    avg_holding_days: Mapped[float | None] = mapped_column(Numeric(9, 2), nullable=True)
    r_distribution: Mapped[list[float]] = mapped_column(SqlJSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TradePlan(Base):
    """One deterministic risk-engine output for one instrument/setup/day.

    Unlike BacktestRun (an experiment, never upserted), a trade plan for
    a given (instrument, plan_date, setup_type, risk_version) IS data to
    keep in sync — re-running the plan for the same day/config should
    update the existing row, same idempotent-upsert-by-natural-key
    pattern as ingestion/indicators/scanner. Invalid plans are persisted
    with status=REJECTED and populated rejection_reasons rather than
    being dropped, so every risk decision stays auditable (MASTER-PRD
    §21, FR-011).
    """

    __tablename__ = "trade_plans"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "plan_date",
            "setup_type",
            "risk_version",
            name="uq_trade_plan_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    scan_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scan_candidates.id"), nullable=True
    )
    setup_type: Mapped[SetupType] = mapped_column(SqlEnum(SetupType, native_enum=False))
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    risk_version: Mapped[str] = mapped_column(String(32))
    score_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    indicator_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    status: Mapped[TradePlanStatus] = mapped_column(SqlEnum(TradePlanStatus, native_enum=False))
    rejection_reasons: Mapped[list[str]] = mapped_column(SqlJSON, default=list)

    entry_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    stop_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    target_prices: Mapped[list[float]] = mapped_column(SqlJSON, default=list)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    allocation_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    allocation_pct: Mapped[float] = mapped_column(Numeric(9, 4), default=0)
    max_loss_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    risk_reward_ratio: Mapped[float | None] = mapped_column(Numeric(9, 4), nullable=True)

    assumptions: Mapped[dict[str, object]] = mapped_column(SqlJSON)
    invalidation_conditions: Mapped[list[str]] = mapped_column(SqlJSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Position(Base):
    """Derived/materialized position state for one instrument's
    open-through-close lifecycle. Never independently mutated via API —
    ExecutionService recomputes it inside the same transaction as every
    new Execution insert, so Execution is the source of truth and
    Position is a queryable summary of it. Reopening after CLOSED/
    CANCELLED creates a new Position row rather than reusing this one.

    uq_positions_one_non_terminal_per_instrument is a partial unique
    index (not just an app-level check) enforcing "at most one
    PLANNED/OPEN/PARTIALLY_CLOSED position per instrument" at the DB
    level — a prior version relied on ExecutionService's check-then-insert
    alone, which a race between two concurrent requests could silently
    slip past (both see "no existing position", both insert). The index
    makes the second insert fail loudly (IntegrityError, caught and
    turned into the same ValueError the app-level check already raises)
    instead of leaving two open positions for one instrument.
    """

    __tablename__ = "positions"
    __table_args__ = (
        Index(
            "uq_positions_one_non_terminal_per_instrument",
            "instrument_id",
            unique=True,
            postgresql_where=text("status IN ('PLANNED', 'OPEN', 'PARTIALLY_CLOSED')"),
            sqlite_where=text("status IN ('PLANNED', 'OPEN', 'PARTIALLY_CLOSED')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    trade_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trade_plans.id"), nullable=True
    )
    status: Mapped[PositionStatus] = mapped_column(
        SqlEnum(PositionStatus, native_enum=False), index=True
    )
    quantity_open: Mapped[int] = mapped_column(Integer, default=0)
    avg_entry_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    avg_entry_fee_per_share: Mapped[float] = mapped_column(Numeric(18, 6), default=0)
    cumulative_quantity_bought: Mapped[int] = mapped_column(Integer, default=0)
    cumulative_entry_fees: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    cumulative_exit_fees: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    realized_pnl: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Execution(Base):
    """Append-only manual-execution ledger row. No update/delete path
    exists anywhere in the API — a recording mistake is corrected by
    entering a new offsetting execution, an explicit adjustment rather
    than an edit to history (MASTER-TDD Phase 7: "execution records
    append-only/auditable; corrections are explicit adjustments").
    Long-only: side BUY opens/adds, SELL reduces/closes — no short model.
    realized_pnl_impact is populated only for SELL rows (None for BUY),
    denormalized here (rather than only on Position) so performance
    aggregation can query the ledger directly without replaying history.
    """

    __tablename__ = "executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    position_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("positions.id"), index=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), index=True)
    trade_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trade_plans.id"), nullable=True
    )
    side: Mapped[ExecutionSide] = mapped_column(SqlEnum(ExecutionSide, native_enum=False))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Numeric(18, 4))
    fee: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    realized_pnl_impact: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JournalEntry(Base):
    """User reflection tied to one position — ordinary mutable CRUD
    (unlike Execution), since a journal is meant to be refined as the
    trader's thinking evolves. One entry per position (create-or-update
    semantics in JournalService). reference_urls holds external links
    only (e.g. a chart screenshot hosted elsewhere) — no file upload or
    storage infra exists in this phase, so attachments are references,
    never uploaded content."""

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    position_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("positions.id"), unique=True, index=True
    )
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_quality: Mapped[str | None] = mapped_column(Text, nullable=True)
    behavioral_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_adherence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    mistakes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_urls: Mapped[list[str]] = mapped_column(SqlJSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AnalysisSnapshot(Base):
    """One AI-analyst invocation, fully auditable (MASTER-PRD §21:
    "important AI analyses should persist the model/provider, prompt/
    version, tool inputs, structured data snapshot, response, and
    timestamp"). Append-only — no update/delete path exists, same
    discipline as Execution, since this is an audit trail of what the
    model was told and what it said, not editable state."""

    __tablename__ = "analysis_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("instruments.id"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    question: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[list[dict[str, object]]] = mapped_column(SqlJSON, default=list)
    structured_data_snapshot: Mapped[list[dict[str, object]]] = mapped_column(SqlJSON, default=list)
    response: Mapped[str] = mapped_column(Text)
    guardrail_flags: Mapped[list[str]] = mapped_column(SqlJSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BreadthSnapshot(Base):
    """One day's market-breadth/regime computation over the local
    ingested universe (MASTER-PRD §12). A proxy for the whole IDX
    market only to the extent the ingested universe is representative —
    documented, not silently overstated. Idempotent-upsert-by-natural-key
    (as_of, breadth_version), same pattern as indicators/scanner/trade
    plans — this is data to keep in sync for a given day/config, not an
    experiment."""

    __tablename__ = "breadth_snapshots"
    __table_args__ = (
        UniqueConstraint("as_of", "breadth_version", name="uq_breadth_snapshot_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    breadth_version: Mapped[str] = mapped_column(String(32))
    universe_size: Mapped[int] = mapped_column(Integer)
    pct_above_sma50: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    pct_above_sma200: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    advancers: Mapped[int] = mapped_column(Integer)
    decliners: Mapped[int] = mapped_column(Integer)
    unchanged: Mapped[int] = mapped_column(Integer)
    new_highs_20: Mapped[int] = mapped_column(Integer)
    new_lows_20: Mapped[int] = mapped_column(Integer)
    regime: Mapped[MarketRegime] = mapped_column(SqlEnum(MarketRegime, native_enum=False))
    regime_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobRun(Base):
    """Audit trail for one scheduled/worker-invoked pipeline stage — same
    RUNNING -> SUCCEEDED/FAILED/PARTIAL shape as IngestionRun/ScanRun/
    BacktestRun, just applied to the Phase 10 scheduler's own
    invocations rather than a single domain operation. This is what
    backs the 'worker health' / 'error rates' observability
    requirement (MASTER-PRD §20) without needing a separate metrics
    stack."""

    __tablename__ = "job_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_type: Mapped[JobType] = mapped_column(SqlEnum(JobType, native_enum=False), index=True)
    run_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[JobStatus] = mapped_column(
        SqlEnum(JobStatus, native_enum=False), default=JobStatus.RUNNING
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    """One deduplicated alert (MASTER-PRD §16: 'Alerts must be
    deduplicated'). The unique constraint on (alert_type, instrument_id,
    trigger_date) is the dedup key, enforced at the DB level from day
    one — a lesson from Phase 7/9's fix-phase findings, where an
    app-level-only check-then-insert wasn't enough on its own.

    instrument_id is intentionally NOT NULL: every alert type this phase
    implements is instrument-scoped, and SQL unique constraints don't
    dedupe NULLs against each other (NULL != NULL) — a nullable column
    here would silently defeat the dedup guarantee for any future
    market-wide alert type. Add a functional/partial unique index at that
    point instead of relaxing this back to nullable."""

    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("alert_type", "instrument_id", "trigger_date", name="uq_alert_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    alert_type: Mapped[AlertType] = mapped_column(SqlEnum(AlertType, native_enum=False), index=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id"), nullable=False, index=True
    )
    trigger_date: Mapped[date] = mapped_column(Date, index=True)
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, object]] = mapped_column(SqlJSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
