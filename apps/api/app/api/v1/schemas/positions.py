import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import ExecutionSide, PositionStatus

MAX_PRICE = 1e12  # defense-in-depth sanity bound, mirrors risk schema's MAX_CAPITAL


class ExecutionCreate(BaseModel):
    symbol: str
    side: ExecutionSide
    quantity: int = Field(gt=0)
    price: float = Field(gt=0, le=MAX_PRICE)
    fee: float = Field(ge=0, le=MAX_PRICE)
    executed_at: datetime
    trade_plan_id: uuid.UUID | None = None
    notes: str | None = None


class ExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position_id: uuid.UUID
    instrument_id: uuid.UUID
    trade_plan_id: uuid.UUID | None
    side: ExecutionSide
    quantity: int
    price: float
    fee: float
    realized_pnl_impact: float | None
    executed_at: datetime
    notes: str | None
    created_at: datetime


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instrument_id: uuid.UUID
    trade_plan_id: uuid.UUID | None
    status: PositionStatus
    quantity_open: int
    avg_entry_price: float | None
    avg_entry_fee_per_share: float
    cumulative_quantity_bought: int
    cumulative_entry_fees: float
    cumulative_exit_fees: float
    realized_pnl: float
    opened_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PlannedPositionCreate(BaseModel):
    trade_plan_id: uuid.UUID


class JournalUpsert(BaseModel):
    thesis: str | None = None
    market_context: str | None = None
    execution_quality: str | None = None
    behavioral_notes: str | None = None
    plan_adherence_notes: str | None = None
    mistakes: str | None = None
    lessons: str | None = None
    reference_urls: list[str] = Field(default_factory=list, max_length=50)


class JournalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position_id: uuid.UUID
    thesis: str | None
    market_context: str | None
    execution_quality: str | None
    behavioral_notes: str | None
    plan_adherence_notes: str | None
    mistakes: str | None
    lessons: str | None
    reference_urls: list[str]
    created_at: datetime
    updated_at: datetime
