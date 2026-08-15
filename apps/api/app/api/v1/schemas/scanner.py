from datetime import date

from pydantic import BaseModel, ConfigDict

from app.db.enums import SetupType


class ScanCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    scan_date: date
    setup_type: SetupType
    indicator_version: str
    score_version: str
    composite_score: float
    trend_score: float
    momentum_score: float
    volume_score: float
    price_structure_score: float
    volatility_score: float
    setup_quality_score: float
    risk_reward_score: float
    qualifying_conditions: list[str]
    invalidation_conditions: list[str]
