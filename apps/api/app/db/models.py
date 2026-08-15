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
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import (
    CorporateActionType,
    DataQualityStatus,
    IngestionStatus,
    ListingStatus,
    ScanStatus,
    SetupType,
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
