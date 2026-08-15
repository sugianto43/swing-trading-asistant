import uuid

from app.db.enums import AlertType
from app.worker.alert_config import AlertConfig
from app.worker.alert_engine import (
    EventSignal,
    PricePlanSignal,
    SetupSignal,
    VolumeSignal,
    evaluate_important_event_alerts,
    evaluate_price_proximity_alerts,
    evaluate_setup_alerts,
    evaluate_stale_data_alert,
    evaluate_volume_alerts,
)

CONFIG = AlertConfig(near_price_threshold_pct=0.02, unusual_volume_relative_threshold=2.0)


def test_evaluate_setup_alerts_generic_setup() -> None:
    iid = uuid.uuid4()
    signals = [
        SetupSignal(instrument_id=iid, symbol="BBCA", setup_type="MA_RECLAIM", composite_score=75.0)
    ]
    result = evaluate_setup_alerts(signals)
    assert len(result) == 1
    assert result[0].alert_type == AlertType.SETUP_DETECTED


def test_evaluate_setup_alerts_breakout_produces_two_alerts() -> None:
    iid = uuid.uuid4()
    signals = [
        SetupSignal(instrument_id=iid, symbol="BBCA", setup_type="BREAKOUT", composite_score=80.0)
    ]
    result = evaluate_setup_alerts(signals)
    types = {c.alert_type for c in result}
    assert types == {AlertType.SETUP_DETECTED, AlertType.BREAKOUT}


def test_evaluate_setup_alerts_empty() -> None:
    assert evaluate_setup_alerts([]) == []


def test_price_near_entry_triggers_within_threshold() -> None:
    iid = uuid.uuid4()
    signals = [
        PricePlanSignal(
            instrument_id=iid,
            symbol="BBCA",
            current_price=1010.0,
            entry_price=1000.0,
            stop_price=None,
            target_price=None,
        )
    ]
    result = evaluate_price_proximity_alerts(signals, CONFIG)
    assert len(result) == 1
    assert result[0].alert_type == AlertType.PRICE_NEAR_ENTRY


def test_price_near_entry_boundary_exactly_at_threshold() -> None:
    iid = uuid.uuid4()
    signals = [
        PricePlanSignal(
            instrument_id=iid,
            symbol="BBCA",
            current_price=1020.0,
            entry_price=1000.0,
            stop_price=None,
            target_price=None,
        )
    ]
    result = evaluate_price_proximity_alerts(signals, CONFIG)
    assert len(result) == 1  # exactly 2% away — inclusive boundary


def test_price_near_entry_no_trigger_outside_threshold() -> None:
    iid = uuid.uuid4()
    signals = [
        PricePlanSignal(
            instrument_id=iid,
            symbol="BBCA",
            current_price=1100.0,
            entry_price=1000.0,
            stop_price=None,
            target_price=None,
        )
    ]
    result = evaluate_price_proximity_alerts(signals, CONFIG)
    assert result == []


def test_price_near_stop_and_target_can_both_trigger_independently() -> None:
    iid = uuid.uuid4()
    signals = [
        PricePlanSignal(
            instrument_id=iid,
            symbol="BBCA",
            current_price=970.0,
            entry_price=1000.0,
            stop_price=970.0,
            target_price=1100.0,
        )
    ]
    result = evaluate_price_proximity_alerts(signals, CONFIG)
    types = {c.alert_type for c in result}
    assert AlertType.PRICE_NEAR_STOP in types
    assert AlertType.PRICE_NEAR_ENTRY not in types  # 3% away from entry, outside 2% threshold


def test_price_proximity_no_plan_levels_no_alerts() -> None:
    iid = uuid.uuid4()
    signals = [
        PricePlanSignal(
            instrument_id=iid,
            symbol="BBCA",
            current_price=1000.0,
            entry_price=None,
            stop_price=None,
            target_price=None,
        )
    ]
    assert evaluate_price_proximity_alerts(signals, CONFIG) == []


def test_unusual_volume_triggers_at_or_above_threshold() -> None:
    iid = uuid.uuid4()
    signals = [VolumeSignal(instrument_id=iid, symbol="BBCA", relative_volume=2.0)]
    result = evaluate_volume_alerts(signals, CONFIG)
    assert len(result) == 1
    assert result[0].alert_type == AlertType.UNUSUAL_VOLUME


def test_unusual_volume_no_trigger_below_threshold() -> None:
    iid = uuid.uuid4()
    signals = [VolumeSignal(instrument_id=iid, symbol="BBCA", relative_volume=1.9)]
    assert evaluate_volume_alerts(signals, CONFIG) == []


def test_unusual_volume_missing_data_no_trigger_not_fabricated() -> None:
    iid = uuid.uuid4()
    signals = [VolumeSignal(instrument_id=iid, symbol="BBCA", relative_volume=None)]
    assert evaluate_volume_alerts(signals, CONFIG) == []


def test_evaluate_stale_data_alert() -> None:
    iid = uuid.uuid4()
    candidate = evaluate_stale_data_alert(iid, "BBCA")
    assert candidate.alert_type == AlertType.STALE_DATA
    assert candidate.instrument_id == iid


def test_evaluate_important_event_alerts() -> None:
    iid = uuid.uuid4()
    signals = [
        EventSignal(
            instrument_id=iid, symbol="BBCA", event_type="SPLIT", description="SPLIT ratio=2.0"
        )
    ]
    result = evaluate_important_event_alerts(signals)
    assert len(result) == 1
    assert result[0].alert_type == AlertType.IMPORTANT_EVENT


def test_evaluate_important_event_alerts_empty() -> None:
    assert evaluate_important_event_alerts([]) == []
