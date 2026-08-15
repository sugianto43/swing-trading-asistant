import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import SetupType, TradePlanStatus

MAX_CAPITAL = 1e15  # generous ceiling (IDR), just a defense-in-depth sanity bound
MAX_EXISTING_POSITIONS = 1000  # a personal-use portfolio never realistically exceeds this


class PortfolioPositionIn(BaseModel):
    symbol: str
    sector: str | None = None
    allocation_amount: float = Field(ge=0, le=MAX_CAPITAL)


class TradePlanCreate(BaseModel):
    symbol: str
    setup_type: SetupType
    plan_date: date
    capital: float = Field(gt=0, le=MAX_CAPITAL)
    existing_positions: list[PortfolioPositionIn] = Field(
        default_factory=list, max_length=MAX_EXISTING_POSITIONS
    )


class TradePlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instrument_id: uuid.UUID
    scan_candidate_id: uuid.UUID | None
    setup_type: SetupType
    plan_date: date
    risk_version: str
    score_version: str | None
    indicator_version: str | None
    status: TradePlanStatus
    rejection_reasons: list[str]
    entry_price: float | None
    stop_price: float | None
    target_prices: list[float]
    quantity: int
    allocation_amount: float
    allocation_pct: float
    max_loss_amount: float
    risk_reward_ratio: float | None
    assumptions: dict[str, object]
    invalidation_conditions: list[str]
    created_at: datetime
    updated_at: datetime
