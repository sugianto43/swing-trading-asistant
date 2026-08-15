"""Golden end-to-end journey (MASTER-PRD §24):

IDX Data -> Validation -> Indicators -> Market Context -> Scanner -> Ranking
-> Stock Analysis -> Risk -> Trade Plan -> AI Explanation -> Human Decision
-> Manual Execution -> Position -> Exit -> Journal -> Performance -> AI Review

Compute stages (ingestion, indicators, scanner) have no REST trigger by
design across every phase (CLI/worker-job only) — those steps run through
the real service layer, exactly as the CLI/worker would call them.
Breadth is the one exception: it does have a REST trigger
(POST /intelligence/breadth/compute) and runs through that. Every
user-actionable stage (trade plan, AI, executions, journal, performance)
goes through the real FastAPI routes via TestClient, against the same DB
session, so a schema/field mismatch between what one stage writes and
what the next stage reads would fail here even though every phase's own
isolated test suite passes.

The AI steps call AIAnalystService directly with an injected
FixtureLLMProvider — the HTTP route always resolves the real configured
provider (requires GEMINI_API_KEY) with no injection point, the same
constraint every other AI test in this codebase works within.
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.ai.orchestrator import AIAnalystService
from app.ai.provider import FixtureLLMProvider, ProviderResponse, ToolCallRequest
from app.db.enums import ExecutionSide, PositionStatus, SetupType, TradePlanStatus
from app.db.models import IndicatorSnapshot, Instrument, ScanCandidate
from app.indicators.service import IndicatorService
from app.indicators.versioning import INDICATOR_VERSION
from app.marketdata.fixture_provider import FixtureProvider
from app.marketdata.ingestion import IngestionService
from app.marketdata.provider import RawBar
from app.marketdata.validation import DEFAULT_MAX_STALENESS_DAYS
from app.risk.config import RISK_VERSION
from app.scanner.scoring_config import SCORE_VERSION
from app.scanner.service import ScannerService

SYMBOL = "BBCA"
SOURCE_SYMBOL = "BBCA.JK"
BASELINE_DAYS = 21  # indices 0..20: flat range, no breakout
BREAKOUT_INDEX = 21  # index 21: the 22nd bar — breaks above the prior rolling 20-day high
START = date(2024, 1, 1)


def _bars(future_days: int = 0) -> list[RawBar]:
    bars = []
    for i in range(BASELINE_DAYS):
        bars.append(
            RawBar(
                source_symbol=SOURCE_SYMBOL,
                trade_date=START + timedelta(days=i),
                open=1000.0,
                high=1020.0,
                low=980.0,
                close=1000.0,
                volume=1_000_000,
                source="fixture",
            )
        )
    bars.append(
        RawBar(
            source_symbol=SOURCE_SYMBOL,
            trade_date=START + timedelta(days=BREAKOUT_INDEX),
            open=1010.0,
            high=1075.0,
            low=1005.0,
            close=1050.0,
            volume=2_500_000,  # 2.5x the 20-day prior average volume
            source="fixture",
        )
    )
    # Deliberately extreme, easy-to-spot-if-leaked values for a no-look-
    # ahead check: if a computation "as of" the breakout day ever used
    # these, the resulting numbers would be obviously different.
    for j in range(future_days):
        bars.append(
            RawBar(
                source_symbol=SOURCE_SYMBOL,
                trade_date=START + timedelta(days=BREAKOUT_INDEX + 1 + j),
                open=2000.0,
                high=2100.0,
                low=1900.0,
                close=2000.0,
                volume=50_000_000,
                source="fixture",
            )
        )
    return bars


def _seed_market_data(
    db_session, future_days: int = 0, ingest_end: date | None = None
) -> tuple[Instrument, date]:
    """IDX Data -> Validation: real ingestion, exactly as the CLI/worker
    would call it (no REST trigger exists for this stage, by design)."""
    provider = FixtureProvider(bars={SOURCE_SYMBOL: _bars(future_days=future_days)})
    service = IngestionService(db_session, provider)
    service.sync_instruments()
    as_of = START + timedelta(days=BREAKOUT_INDEX)
    end = ingest_end or as_of
    service.ingest_prices(SYMBOL, START, end, as_of=end)

    instrument = db_session.query(Instrument).filter(Instrument.symbol == SYMBOL).one()
    return instrument, as_of


def _compute_indicators(db_session, as_of: date) -> None:
    """Indicators: real IndicatorService, no REST trigger by design."""
    IndicatorService(db_session).compute_and_persist(SYMBOL, persist_from=START, persist_to=as_of)


def _compute_breadth_via_api(client, as_of: date) -> dict:
    """Market Context: this stage DOES have a REST trigger."""
    response = client.post(
        "/api/v1/intelligence/breadth/compute", json={"as_of": as_of.isoformat()}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _run_scanner(db_session, as_of: date) -> None:
    """Scanner + Ranking: real ScannerService, no REST trigger by design."""
    ScannerService(db_session).scan_symbol(SYMBOL, as_of)


def test_golden_journey_happy_path(client, db_session) -> None:
    _, as_of = _seed_market_data(db_session)
    _compute_indicators(db_session, as_of)

    breadth = _compute_breadth_via_api(client, as_of)
    assert breadth["universe_size"] == 1

    _run_scanner(db_session, as_of)

    # Stock Analysis / Ranking — real GET, verifies the scanner's write is
    # readable through the same schema the API promises.
    candidates_response = client.get(f"/api/v1/instruments/{SYMBOL}/candidates")
    assert candidates_response.status_code == 200, candidates_response.text
    candidates = candidates_response.json()["items"]
    breakout_candidates = [c for c in candidates if c["setup_type"] == SetupType.BREAKOUT.value]
    assert len(breakout_candidates) == 1, (
        f"expected one BREAKOUT candidate from the synthetic breakout bar, got: {candidates}"
    )

    # Risk -> Trade Plan
    trade_plan_response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": SYMBOL,
            "setup_type": SetupType.BREAKOUT.value,
            "plan_date": as_of.isoformat(),
            "capital": 100_000_000.0,
        },
    )
    assert trade_plan_response.status_code == 201, trade_plan_response.text
    trade_plan = trade_plan_response.json()
    assert trade_plan["status"] == TradePlanStatus.VALID.value, trade_plan
    assert trade_plan["quantity"] > 0
    assert trade_plan["entry_price"] is not None

    # AI Explanation (pre-trade) — service-level, fixture-scripted, same
    # pattern as every other AI test in this codebase.
    explanation_script = [
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(
                    call_id="1", tool_name="get_trade_plan", arguments={"symbol": SYMBOL}
                )
            ]
        ),
        ProviderResponse(text="BBCA broke out above its 20-day high on strong volume."),
    ]
    explanation_snapshot = AIAnalystService(db_session).analyze(
        question="Should I take this BBCA breakout setup?",
        symbol=SYMBOL,
        provider=FixtureLLMProvider(explanation_script),
    )
    assert explanation_snapshot.response == "BBCA broke out above its 20-day high on strong volume."
    assert explanation_snapshot.guardrail_flags == []

    # Human Decision -> Manual Execution (entry)
    entry_execution_response = client.post(
        "/api/v1/executions",
        json={
            "symbol": SYMBOL,
            "side": ExecutionSide.BUY.value,
            "quantity": trade_plan["quantity"],
            "price": trade_plan["entry_price"],
            "fee": 0.0,
            "executed_at": datetime.combine(as_of, datetime.min.time(), tzinfo=UTC).isoformat(),
            "trade_plan_id": trade_plan["id"],
        },
    )
    assert entry_execution_response.status_code == 201, entry_execution_response.text
    position = entry_execution_response.json()
    assert position["status"] == PositionStatus.OPEN.value
    assert position["quantity_open"] == trade_plan["quantity"]

    # Journal
    journal_response = client.post(
        f"/api/v1/positions/{position['id']}/journal",
        json={"thesis": "Breakout above 20-day high with 2.5x volume confirmation."},
    )
    assert journal_response.status_code == 200, journal_response.text
    assert (
        journal_response.json()["thesis"]
        == "Breakout above 20-day high with 2.5x volume confirmation."
    )

    # Exit
    exit_price = trade_plan["entry_price"] * 1.05
    exit_at = as_of + timedelta(days=3)
    exit_execution_response = client.post(
        "/api/v1/executions",
        json={
            "symbol": SYMBOL,
            "side": ExecutionSide.SELL.value,
            "quantity": trade_plan["quantity"],
            "price": exit_price,
            "fee": 0.0,
            "executed_at": datetime.combine(exit_at, datetime.min.time(), tzinfo=UTC).isoformat(),
        },
    )
    assert exit_execution_response.status_code == 201, exit_execution_response.text
    closed_position = exit_execution_response.json()
    assert closed_position["id"] == position["id"]
    assert closed_position["status"] == PositionStatus.CLOSED.value
    assert closed_position["quantity_open"] == 0
    assert closed_position["realized_pnl"] > 0  # sold above entry

    # Performance
    performance_response = client.get(
        "/api/v1/performance/summary", params={"initial_capital": 100_000_000.0}
    )
    assert performance_response.status_code == 200, performance_response.text
    performance = performance_response.json()
    assert performance["closed_position_count"] == 1
    assert performance["total_realized_pnl"] > 0

    # AI Review (post-trade) — references the now-closed position.
    review_script = [
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(call_id="1", tool_name="get_position", arguments={"symbol": SYMBOL})
            ]
        ),
        ProviderResponse(text="The BBCA breakout trade closed profitably, exiting above entry."),
    ]
    review_snapshot = AIAnalystService(db_session).analyze(
        question="How did my BBCA trade go?",
        symbol=SYMBOL,
        provider=FixtureLLMProvider(review_script),
    )
    assert (
        review_snapshot.response
        == "The BBCA breakout trade closed profitably, exiting above entry."
    )
    assert review_snapshot.guardrail_flags == []


def test_execution_overselling_is_rejected_not_silently_capped(client, db_session) -> None:
    """Boundary/integration-defect focus: a SELL beyond the open quantity
    must 409, never silently oversell or crash the position state."""
    _, as_of = _seed_market_data(db_session)
    _compute_indicators(db_session, as_of)
    _run_scanner(db_session, as_of)

    trade_plan_response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": SYMBOL,
            "setup_type": SetupType.BREAKOUT.value,
            "plan_date": as_of.isoformat(),
            "capital": 100_000_000.0,
        },
    )
    trade_plan = trade_plan_response.json()

    entry_response = client.post(
        "/api/v1/executions",
        json={
            "symbol": SYMBOL,
            "side": ExecutionSide.BUY.value,
            "quantity": trade_plan["quantity"],
            "price": trade_plan["entry_price"],
            "fee": 0.0,
            "executed_at": datetime.combine(as_of, datetime.min.time(), tzinfo=UTC).isoformat(),
            "trade_plan_id": trade_plan["id"],
        },
    )
    position = entry_response.json()

    oversell_response = client.post(
        "/api/v1/executions",
        json={
            "symbol": SYMBOL,
            "side": ExecutionSide.SELL.value,
            "quantity": trade_plan["quantity"] * 2,
            "price": trade_plan["entry_price"],
            "fee": 0.0,
            "executed_at": datetime.combine(
                as_of + timedelta(days=1), datetime.min.time(), tzinfo=UTC
            ).isoformat(),
        },
    )
    assert oversell_response.status_code == 409, oversell_response.text

    still_open = client.get(f"/api/v1/positions/{position['id']}")
    assert still_open.json()["status"] == PositionStatus.OPEN.value
    assert still_open.json()["quantity_open"] == trade_plan["quantity"]


def test_trade_plan_rejected_for_setup_with_no_qualifying_candidate(client, db_session) -> None:
    """Boundary focus: requesting a trade plan for a setup type that has
    no qualifying ScanCandidate must surface as REJECTED with a reason,
    not a 500 or a silently-fabricated plan (AI-GUARDRAILS.md: never
    invent numerical facts)."""
    _, as_of = _seed_market_data(db_session)
    _compute_indicators(db_session, as_of)
    _run_scanner(db_session, as_of)  # only produces a BREAKOUT candidate

    response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": SYMBOL,
            "setup_type": SetupType.MA_RECLAIM.value,
            "plan_date": as_of.isoformat(),
            "capital": 100_000_000.0,
        },
    )
    assert response.status_code == 201, response.text
    plan = response.json()
    assert plan["status"] == TradePlanStatus.REJECTED.value
    assert len(plan["rejection_reasons"]) > 0


def test_stale_data_produces_no_fresh_signal_end_to_end(client, db_session) -> None:
    """MASTER-PRD §20: when data is stale, the system must not generate a
    fresh trading signal. Verified across the full chain, not just at the
    scanner: staleness must propagate through to the trade-plan stage too
    (no qualifying candidate means no VALID plan can ever be built)."""
    _, ingested_as_of = _seed_market_data(db_session)
    _compute_indicators(db_session, ingested_as_of)

    stale_as_of = ingested_as_of + timedelta(days=DEFAULT_MAX_STALENESS_DAYS + 1)
    ScannerService(db_session).scan_symbol(SYMBOL, stale_as_of)

    candidates_response = client.get(f"/api/v1/instruments/{SYMBOL}/candidates")
    assert candidates_response.status_code == 200, candidates_response.text
    assert candidates_response.json()["items"] == []

    plan_response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": SYMBOL,
            "setup_type": SetupType.BREAKOUT.value,
            "plan_date": stale_as_of.isoformat(),
            "capital": 100_000_000.0,
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan = plan_response.json()
    assert plan["status"] == TradePlanStatus.REJECTED.value


def test_future_bars_already_in_db_do_not_leak_into_past_computation(client, db_session) -> None:
    """No-look-ahead, verified end-to-end: PriceBar rows for dates AFTER
    as_of already exist in the DB (a realistic batch-ingestion scenario —
    ingestion isn't required to stop exactly at "today"), but indicator
    computation and scanning "as of" the breakout day must produce
    identical results whether or not those future rows exist."""
    ingest_end = START + timedelta(days=BREAKOUT_INDEX + 5)
    _, as_of = _seed_market_data(db_session, future_days=5, ingest_end=ingest_end)

    _compute_indicators(db_session, as_of)
    _run_scanner(db_session, as_of)

    # No IndicatorSnapshot or ScanCandidate row may exist beyond as_of —
    # proof persist_from/persist_to bounds actually held, not just that
    # the visible candidate happens to look right.
    future_snapshots = db_session.scalars(
        select(IndicatorSnapshot).where(IndicatorSnapshot.trade_date > as_of)
    ).all()
    assert future_snapshots == []
    future_candidates = db_session.scalars(
        select(ScanCandidate).where(ScanCandidate.scan_date > as_of)
    ).all()
    assert future_candidates == []

    candidates_response = client.get(f"/api/v1/instruments/{SYMBOL}/candidates")
    candidates = candidates_response.json()["items"]
    breakout_candidates = [c for c in candidates if c["setup_type"] == SetupType.BREAKOUT.value]
    assert len(breakout_candidates) == 1

    # The extreme future volume (50M) would blow relative_volume far past
    # the ~2.5x this setup actually has if the window leaked forward.
    instrument = db_session.scalars(select(Instrument).where(Instrument.symbol == SYMBOL)).one()
    snapshot = db_session.scalars(
        select(IndicatorSnapshot).where(
            IndicatorSnapshot.instrument_id == instrument.id,
            IndicatorSnapshot.trade_date == as_of,
        )
    ).one()
    assert snapshot.relative_volume is not None
    assert snapshot.relative_volume < 5.0  # nowhere near what a leaked 50M-volume day would cause


def test_version_lineage_persists_through_the_full_journey(client, db_session) -> None:
    """Data lineage (MASTER-PRD §21): every computed/scored/planned row
    carries the version tag of the logic that produced it, and that tag
    must still be the canonical current version by the time it's read
    back through the trade-plan API — not silently dropped or stale
    across the ingestion -> indicators -> scanner -> risk chain."""
    _, as_of = _seed_market_data(db_session)
    _compute_indicators(db_session, as_of)
    _run_scanner(db_session, as_of)

    trade_plan_response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": SYMBOL,
            "setup_type": SetupType.BREAKOUT.value,
            "plan_date": as_of.isoformat(),
            "capital": 100_000_000.0,
        },
    )
    plan = trade_plan_response.json()
    assert plan["status"] == TradePlanStatus.VALID.value
    assert plan["indicator_version"] == INDICATOR_VERSION
    assert plan["score_version"] == SCORE_VERSION
    assert plan["risk_version"] == RISK_VERSION
    assert plan["scan_candidate_id"] is not None  # traceable back to the exact candidate row


def test_ai_review_for_unseeded_symbol_returns_data_unavailable_not_fabricated(db_session) -> None:
    """AI-GUARDRAILS.md "Unsupported Data": for a symbol with no ingested
    data at all, the real get_stock_snapshot tool (executed for real
    against the real DB, not mocked) must return DATA_UNAVAILABLE, and
    that envelope must be what actually gets persisted in the snapshot's
    structured_data_snapshot — never a fabricated price/indicator."""
    script = [
        ProviderResponse(
            tool_calls=[
                ToolCallRequest(
                    call_id="1", tool_name="get_stock_snapshot", arguments={"symbol": "GOTO"}
                )
            ]
        ),
        ProviderResponse(text="I don't have any data for GOTO."),
    ]
    snapshot = AIAnalystService(db_session).analyze(
        question="How is GOTO doing?",
        symbol="GOTO",
        provider=FixtureLLMProvider(script),
    )

    assert snapshot.guardrail_flags == []
    assert any(
        isinstance(entry, dict) and entry.get("result", {}).get("status") == "DATA_UNAVAILABLE"
        for entry in snapshot.structured_data_snapshot
    ), snapshot.structured_data_snapshot
