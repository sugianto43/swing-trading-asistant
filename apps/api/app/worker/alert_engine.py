"""Pure alert-trigger evaluation — no DB access, same discipline as
every other *_engine.py module in this codebase. Each function takes
already-fetched plain data and returns zero or more AlertCandidate
values; persistence/deduplication is alert_service.py's job.

SETUP_INVALIDATED is deliberately not implemented here — Phase 4's
ScanCandidate.invalidation_conditions is a list of human-readable
description strings, not a re-evaluatable predicate, so mechanically
detecting "this setup is now invalidated" isn't possible without new
setup-detector-level logic that doesn't exist. Documented gap, not
fabricated.
"""

import uuid
from dataclasses import dataclass, field

from app.db.enums import AlertType
from app.worker.alert_config import AlertConfig


@dataclass(frozen=True, slots=True)
class AlertCandidate:
    alert_type: AlertType
    instrument_id: uuid.UUID
    message: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SetupSignal:
    instrument_id: uuid.UUID
    symbol: str
    setup_type: str
    composite_score: float


def evaluate_setup_alerts(signals: list[SetupSignal]) -> list[AlertCandidate]:
    """Every qualifying setup detected today produces a SETUP_DETECTED
    alert; a setup_type of BREAKOUT additionally produces a BREAKOUT
    alert — both mechanically derived from the ScanCandidate row that
    already exists, nothing inferred."""
    candidates: list[AlertCandidate] = []
    for signal in signals:
        candidates.append(
            AlertCandidate(
                alert_type=AlertType.SETUP_DETECTED,
                instrument_id=signal.instrument_id,
                message=f"{signal.symbol}: {signal.setup_type} setup detected "
                f"(score {signal.composite_score:.1f})",
                details={
                    "setup_type": signal.setup_type,
                    "composite_score": signal.composite_score,
                },
            )
        )
        if signal.setup_type == "BREAKOUT":
            candidates.append(
                AlertCandidate(
                    alert_type=AlertType.BREAKOUT,
                    instrument_id=signal.instrument_id,
                    message=f"{signal.symbol}: breakout setup detected",
                    details={"composite_score": signal.composite_score},
                )
            )
    return candidates


@dataclass(frozen=True, slots=True)
class PricePlanSignal:
    instrument_id: uuid.UUID
    symbol: str
    current_price: float
    entry_price: float | None
    stop_price: float | None
    target_price: float | None  # the full (final) target, if any


def _is_near(current: float, level: float, threshold_pct: float) -> bool:
    if level <= 0:
        return False
    return abs(current - level) / level <= threshold_pct


def evaluate_price_proximity_alerts(
    signals: list[PricePlanSignal], config: AlertConfig
) -> list[AlertCandidate]:
    """PRICE_NEAR_ENTRY/STOP/TARGET — current price within
    config.near_price_threshold_pct of a VALID TradePlan's stated
    level."""
    candidates: list[AlertCandidate] = []
    for signal in signals:
        if signal.entry_price is not None and _is_near(
            signal.current_price, signal.entry_price, config.near_price_threshold_pct
        ):
            candidates.append(
                AlertCandidate(
                    alert_type=AlertType.PRICE_NEAR_ENTRY,
                    instrument_id=signal.instrument_id,
                    message=f"{signal.symbol}: price {signal.current_price} near entry "
                    f"{signal.entry_price}",
                    details={
                        "current_price": signal.current_price,
                        "entry_price": signal.entry_price,
                    },
                )
            )
        if signal.stop_price is not None and _is_near(
            signal.current_price, signal.stop_price, config.near_price_threshold_pct
        ):
            candidates.append(
                AlertCandidate(
                    alert_type=AlertType.PRICE_NEAR_STOP,
                    instrument_id=signal.instrument_id,
                    message=f"{signal.symbol}: price {signal.current_price} near stop "
                    f"{signal.stop_price}",
                    details={
                        "current_price": signal.current_price,
                        "stop_price": signal.stop_price,
                    },
                )
            )
        if signal.target_price is not None and _is_near(
            signal.current_price, signal.target_price, config.near_price_threshold_pct
        ):
            candidates.append(
                AlertCandidate(
                    alert_type=AlertType.PRICE_NEAR_TARGET,
                    instrument_id=signal.instrument_id,
                    message=f"{signal.symbol}: price {signal.current_price} near target "
                    f"{signal.target_price}",
                    details={
                        "current_price": signal.current_price,
                        "target_price": signal.target_price,
                    },
                )
            )
    return candidates


@dataclass(frozen=True, slots=True)
class VolumeSignal:
    instrument_id: uuid.UUID
    symbol: str
    relative_volume: float | None


def evaluate_volume_alerts(
    signals: list[VolumeSignal], config: AlertConfig
) -> list[AlertCandidate]:
    candidates: list[AlertCandidate] = []
    for signal in signals:
        if (
            signal.relative_volume is not None
            and signal.relative_volume >= config.unusual_volume_relative_threshold
        ):
            candidates.append(
                AlertCandidate(
                    alert_type=AlertType.UNUSUAL_VOLUME,
                    instrument_id=signal.instrument_id,
                    message=f"{signal.symbol}: unusual volume "
                    f"({signal.relative_volume:.1f}x average)",
                    details={"relative_volume": signal.relative_volume},
                )
            )
    return candidates


def evaluate_stale_data_alert(instrument_id: uuid.UUID, symbol: str) -> AlertCandidate:
    """Called explicitly by the job wrapper when staleness is detected
    (MASTER-PRD §20: 'DO NOT generate a fresh trading signal' when data
    is stale) — makes that suppression visible instead of only
    internally silent."""
    return AlertCandidate(
        alert_type=AlertType.STALE_DATA,
        instrument_id=instrument_id,
        message=f"{symbol}: price data is stale — no fresh signal generated",
        details={"symbol": symbol},
    )


@dataclass(frozen=True, slots=True)
class EventSignal:
    instrument_id: uuid.UUID
    symbol: str
    event_type: str
    description: str


def evaluate_important_event_alerts(signals: list[EventSignal]) -> list[AlertCandidate]:
    """An IMPORTANT_EVENT alert for each Phase 9 corporate-action event
    newly announced today for a tracked instrument."""
    return [
        AlertCandidate(
            alert_type=AlertType.IMPORTANT_EVENT,
            instrument_id=signal.instrument_id,
            message=f"{signal.symbol}: {signal.description}",
            details={"event_type": signal.event_type},
        )
        for signal in signals
    ]
