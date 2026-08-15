import uuid

from app.db.enums import ListingStatus
from app.db.models import AnalysisSnapshot, Instrument


def _instrument() -> Instrument:
    return Instrument(
        symbol=f"T{uuid.uuid4().hex[:8]}",
        company_name="Test Co",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol="TEST.JK",
    )


def test_analysis_snapshot_persists_with_null_instrument(db_session) -> None:
    snapshot = AnalysisSnapshot(
        instrument_id=None,
        provider="fixture",
        model="fixture-v1",
        prompt_version="v1",
        question="general question",
        tool_calls=[],
        structured_data_snapshot=[],
        response="a general answer",
        guardrail_flags=[],
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    assert snapshot.id is not None
    assert snapshot.instrument_id is None


def test_analysis_snapshot_json_fields_round_trip(db_session) -> None:
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()

    snapshot = AnalysisSnapshot(
        instrument_id=instrument.id,
        provider="fixture",
        model="fixture-v1",
        prompt_version="v1",
        question="q",
        tool_calls=[{"tool_name": "get_stock_snapshot", "arguments": {"symbol": "BBCA"}}],
        structured_data_snapshot=[
            {"tool_name": "get_stock_snapshot", "result": {"status": "OK", "close": 1000.0}}
        ],
        response="r",
        guardrail_flags=["certainty_claim"],
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    assert snapshot.tool_calls == [
        {"tool_name": "get_stock_snapshot", "arguments": {"symbol": "BBCA"}}
    ]
    assert snapshot.structured_data_snapshot == [
        {"tool_name": "get_stock_snapshot", "result": {"status": "OK", "close": 1000.0}}
    ]
    assert snapshot.guardrail_flags == ["certainty_claim"]


def test_multiple_snapshots_allowed_no_unique_constraint(db_session) -> None:
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()

    for _ in range(3):
        db_session.add(
            AnalysisSnapshot(
                instrument_id=instrument.id,
                provider="fixture",
                model="fixture-v1",
                prompt_version="v1",
                question="q",
                tool_calls=[],
                structured_data_snapshot=[],
                response="r",
                guardrail_flags=[],
            )
        )
    db_session.commit()  # must not raise — an append-only log, not upserted
