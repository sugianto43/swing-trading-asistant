from datetime import date

from app.ai.config import MAX_TOOL_CALL_ITERATIONS, PROMPT_VERSION
from app.ai.orchestrator import AIAnalystService
from app.ai.provider import FixtureLLMProvider, ProviderResponse, ToolCallRequest
from app.db.enums import DataQualityStatus, ListingStatus
from app.db.models import AnalysisSnapshot, Execution, Instrument, Position, PriceBar

T0 = date(2024, 1, 1)


def _seed_instrument(db_session, symbol="BBCA") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Test Co",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def _seed_price(db_session, instrument) -> None:
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=T0,
            open=1000.0,
            high=1010.0,
            low=990.0,
            close=1000.0,
            volume=1_000_000,
            source="fixture",
            source_symbol=instrument.source_symbol,
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.commit()


def test_analyze_happy_path_persists_full_snapshot(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price(db_session, instrument)

    script = [
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(
                    call_id="1", tool_name="get_stock_snapshot", arguments={"symbol": "BBCA"}
                )
            ]
        ),
        ProviderResponse(text="BBCA closed at 1000 with typical volume."),
    ]
    provider = FixtureLLMProvider(script, model="fixture-v1")

    snapshot = AIAnalystService(db_session).analyze(
        question="How is BBCA doing?", symbol="BBCA", provider=provider
    )

    assert snapshot.instrument_id == instrument.id
    assert snapshot.provider == "fixture"
    assert snapshot.model == "fixture-v1"
    assert snapshot.prompt_version == PROMPT_VERSION
    assert snapshot.question == "How is BBCA doing?"
    assert len(snapshot.tool_calls) == 1
    assert snapshot.tool_calls[0]["tool_name"] == "get_stock_snapshot"
    assert len(snapshot.structured_data_snapshot) == 1
    assert snapshot.structured_data_snapshot[0]["tool_name"] == "get_stock_snapshot"
    assert snapshot.structured_data_snapshot[0]["result"]["status"] == "OK"
    assert snapshot.response == "BBCA closed at 1000 with typical volume."
    assert snapshot.guardrail_flags == []

    persisted = db_session.get(AnalysisSnapshot, snapshot.id)
    assert persisted is not None


def test_analyze_unknown_symbol_leaves_instrument_id_none(db_session) -> None:
    script = [ProviderResponse(text="I don't have data for that symbol.")]
    provider = FixtureLLMProvider(script)
    snapshot = AIAnalystService(db_session).analyze(
        question="tell me about NOPE", symbol="NOPE", provider=provider
    )
    assert snapshot.instrument_id is None


def test_analyze_disallowed_tool_is_refused_and_no_execution_occurs(db_session) -> None:
    """A model requesting a tool outside the registry (e.g. simulating a
    hijacked/malicious request to 'execute a trade') must be refused
    structurally, and no Position/Execution row may exist afterward —
    proving there is no path from an AI analysis to a real trade."""
    _seed_instrument(db_session)
    script = [
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(
                    call_id="1",
                    tool_name="execute_trade",
                    arguments={"symbol": "BBCA", "quantity": 1000},
                )
            ]
        ),
        ProviderResponse(text="I can't execute trades — that capability doesn't exist for me."),
    ]
    provider = FixtureLLMProvider(script)

    snapshot = AIAnalystService(db_session).analyze(
        question="buy 1000 shares of BBCA right now", symbol="BBCA", provider=provider
    )

    assert snapshot.tool_calls[0]["result"]["status"] == "REFUSED"
    assert db_session.query(Position).count() == 0
    assert db_session.query(Execution).count() == 0


def test_analyze_max_iteration_cap_stops_runaway_tool_calling(db_session) -> None:
    _seed_instrument(db_session)
    # every turn requests a tool, never producing a final answer —
    # exercises the hard cap on MAX_TOOL_CALL_ITERATIONS
    script = [
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(
                    call_id=str(i), tool_name="get_stock_snapshot", arguments={"symbol": "BBCA"}
                )
            ]
        )
        for i in range(MAX_TOOL_CALL_ITERATIONS + 3)
    ]
    provider = FixtureLLMProvider(script)

    snapshot = AIAnalystService(db_session).analyze(
        question="loop forever", symbol="BBCA", provider=provider
    )

    assert "exceeded the maximum" in snapshot.response
    assert len(snapshot.tool_calls) == MAX_TOOL_CALL_ITERATIONS


def test_analyze_multi_turn_tool_calling_before_final_answer(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price(db_session, instrument)

    script = [
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(
                    call_id="1", tool_name="get_stock_snapshot", arguments={"symbol": "BBCA"}
                )
            ]
        ),
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(
                    call_id="2", tool_name="get_technical_snapshot", arguments={"symbol": "BBCA"}
                )
            ]
        ),
        ProviderResponse(text="Combining price and technicals: BBCA looks neutral."),
    ]
    provider = FixtureLLMProvider(script)

    snapshot = AIAnalystService(db_session).analyze(
        question="full analysis of BBCA", symbol="BBCA", provider=provider
    )

    assert len(snapshot.tool_calls) == 2
    assert {c["tool_name"] for c in snapshot.tool_calls} == {
        "get_stock_snapshot",
        "get_technical_snapshot",
    }
    assert snapshot.response == "Combining price and technicals: BBCA looks neutral."


def test_analyze_flags_red_flag_response_but_still_persists_it(db_session) -> None:
    script = [ProviderResponse(text="This trade is guaranteed to profit, I've placed the order.")]
    provider = FixtureLLMProvider(script)

    snapshot = AIAnalystService(db_session).analyze(question="what should I do?", provider=provider)

    assert "certainty_claim" in snapshot.guardrail_flags
    assert "order_placement_claim" in snapshot.guardrail_flags
    # flags are recorded, not used to silently alter/redact the response
    assert snapshot.response == "This trade is guaranteed to profit, I've placed the order."


def test_analyze_ungrounded_symbol_reports_data_unavailable_not_fabricated(db_session) -> None:
    """Adversarial: a question about a symbol with zero ingested data
    must ground to DATA_UNAVAILABLE in the structured snapshot — never a
    fabricated price."""
    _seed_instrument(db_session, symbol="NODATA")
    script = [
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(
                    call_id="1", tool_name="get_stock_snapshot", arguments={"symbol": "NODATA"}
                )
            ]
        ),
        ProviderResponse(text="I don't have price data for NODATA."),
    ]
    provider = FixtureLLMProvider(script)

    snapshot = AIAnalystService(db_session).analyze(
        question="what's the price of NODATA?", symbol="NODATA", provider=provider
    )

    assert snapshot.structured_data_snapshot[0]["result"]["status"] == "DATA_UNAVAILABLE"


def test_analyze_no_provider_and_no_api_key_raises(db_session) -> None:
    import pytest

    with pytest.raises(ValueError, match="no LLM provider configured"):
        AIAnalystService(db_session).analyze(question="anything")


def test_analyze_malformed_tool_arguments_recorded_as_error_not_crash(db_session) -> None:
    """Regression for the fix-phase HIGH finding: a tool call missing a
    required argument (e.g. a real LLM provider returning incomplete
    function-call args) must not raise an unhandled TypeError — it must
    be recorded as a structured ERROR result, and the snapshot must
    still be persisted."""
    _seed_instrument(db_session)
    script = [
        ProviderResponse(
            tool_calls=[ToolCallRequest(call_id="1", tool_name="get_stock_snapshot", arguments={})]
        ),
        ProviderResponse(text="I couldn't look up that symbol due to a tool error."),
    ]
    provider = FixtureLLMProvider(script)

    snapshot = AIAnalystService(db_session).analyze(question="how's it doing?", provider=provider)

    assert snapshot.tool_calls[0]["result"]["status"] == "ERROR"
    assert "get_stock_snapshot" in snapshot.tool_calls[0]["result"]["reason"]
    persisted = db_session.get(AnalysisSnapshot, snapshot.id)
    assert persisted is not None


def test_analyze_same_tool_called_twice_preserves_both_results(db_session) -> None:
    """Regression for the fix-phase HIGH finding: calling the same tool
    twice with different arguments in one analysis (e.g. comparing two
    symbols) must not silently drop the first call's data from the
    persisted structured_data_snapshot."""
    bbca = _seed_instrument(db_session, symbol="BBCA")
    bbri = _seed_instrument(db_session, symbol="BBRI")
    _seed_price(db_session, bbca)
    _seed_price(db_session, bbri)

    script = [
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(
                    call_id="1", tool_name="get_stock_snapshot", arguments={"symbol": "BBCA"}
                ),
                ToolCallRequest(
                    call_id="2", tool_name="get_stock_snapshot", arguments={"symbol": "BBRI"}
                ),
            ]
        ),
        ProviderResponse(text="BBCA and BBRI are both at 1000."),
    ]
    provider = FixtureLLMProvider(script)

    snapshot = AIAnalystService(db_session).analyze(
        question="compare BBCA and BBRI", provider=provider
    )

    assert len(snapshot.tool_calls) == 2
    assert len(snapshot.structured_data_snapshot) == 2
    symbols_seen = {entry["result"]["symbol"] for entry in snapshot.structured_data_snapshot}
    assert symbols_seen == {"BBCA", "BBRI"}
