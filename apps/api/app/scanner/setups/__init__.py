from dataclasses import dataclass

from app.db.enums import SetupType


@dataclass(frozen=True, slots=True)
class SetupResult:
    """Returned only when a setup's qualifying conditions are met — a
    detector returns None rather than a "qualifies=False" result, so
    callers never need to distinguish "not evaluated" from "evaluated and
    failed" (MASTER-PRD FR-005: prerequisites/qualifying/invalidation
    conditions must be explicit)."""

    setup_type: SetupType
    reasons: list[str]
    invalidation_conditions: list[str]
    setup_quality_score: float
