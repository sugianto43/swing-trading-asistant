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
from app.db.enums import CorporateActionType, DataQualityStatus, IngestionStatus, ListingStatus


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
