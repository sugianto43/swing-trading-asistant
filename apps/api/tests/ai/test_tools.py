import uuid
from datetime import UTC, date, datetime

from app.ai import tools
from app.db.enums import (
    BacktestStatus,
    DataQualityStatus,
    ExecutionModel,
    ExecutionSide,
    ListingStatus,
    PositionStatus,
    SetupType,
    TradePlanStatus,
)
from app.db.models import (
    BacktestMetrics,
    BacktestRun,
    Execution,
    IndicatorSnapshot,
    Instrument,
    Position,
    PriceBar,
    ScanCandidate,
    TradePlan,
)

T0 = date(2024, 1, 1)


def _seed_instrument(db_session, symbol="BBCA", sector="Banking") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Test Co",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        sector=sector,
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def test_get_stock_snapshot_unknown_symbol_unavailable(db_session) -> None:
    result = tools.get_stock_snapshot(db_session, symbol="NOPE")
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_stock_snapshot_no_price_data_unavailable(db_session) -> None:
    _seed_instrument(db_session)
    result = tools.get_stock_snapshot(db_session, symbol="BBCA")
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_stock_snapshot_happy_path(db_session) -> None:
    instrument = _seed_instrument(db_session)
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

    result = tools.get_stock_snapshot(db_session, symbol="bbca")  # lowercase input
    assert result["status"] == "OK"
    assert result["symbol"] == "BBCA"
    assert result["close"] == 1000.0
    assert result["is_stale"] is True  # T0 is far in the past relative to "now"


def test_get_stock_snapshot_fresh_data_not_flagged_stale(db_session) -> None:
    instrument = _seed_instrument(db_session)
    recent_date = datetime.now(UTC).date()
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=recent_date,
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

    result = tools.get_stock_snapshot(db_session, symbol="BBCA")
    assert result["status"] == "OK"
    assert result["is_stale"] is False


def test_get_technical_snapshot_no_snapshot_unavailable(db_session) -> None:
    _seed_instrument(db_session)
    result = tools.get_technical_snapshot(db_session, symbol="BBCA")
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_technical_snapshot_happy_path(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id,
            trade_date=T0,
            indicator_version="v1",
            rsi_14=55.5,
            atr_14=20.0,
        )
    )
    db_session.commit()

    result = tools.get_technical_snapshot(db_session, symbol="BBCA")
    assert result["status"] == "OK"
    assert result["rsi_14"] == 55.5
    assert result["atr_14"] == 20.0
    assert result["sma_20"] is None  # never fabricated


def test_get_setup_no_candidate_unavailable(db_session) -> None:
    _seed_instrument(db_session)
    result = tools.get_setup(db_session, symbol="BBCA")
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_setup_happy_path(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        ScanCandidate(
            instrument_id=instrument.id,
            scan_date=T0,
            setup_type=SetupType.BREAKOUT,
            indicator_version="v1",
            score_version="v1",
            composite_score=75.0,
            trend_score=0,
            momentum_score=0,
            volume_score=0,
            price_structure_score=0,
            volatility_score=0,
            setup_quality_score=0,
            risk_reward_score=0,
            qualifying_conditions=["breakout above resistance"],
            invalidation_conditions=["close below breakout level"],
        )
    )
    db_session.commit()

    result = tools.get_setup(db_session, symbol="BBCA")
    assert result["status"] == "OK"
    assert result["setups"][0]["setup_type"] == "BREAKOUT"
    assert result["setups"][0]["composite_score"] == 75.0


def test_get_setup_boundary_returns_at_most_five_most_recent(db_session) -> None:
    instrument = _seed_instrument(db_session)
    for i in range(7):
        db_session.add(
            ScanCandidate(
                instrument_id=instrument.id,
                scan_date=date(2024, 1, 1 + i),
                setup_type=SetupType.BREAKOUT,
                indicator_version="v1",
                score_version="v1",
                composite_score=float(60 + i),
                trend_score=0,
                momentum_score=0,
                volume_score=0,
                price_structure_score=0,
                volatility_score=0,
                setup_quality_score=0,
                risk_reward_score=0,
                qualifying_conditions=["test"],
                invalidation_conditions=[],
            )
        )
    db_session.commit()

    result = tools.get_setup(db_session, symbol="BBCA")
    assert result["status"] == "OK"
    assert len(result["setups"]) == 5
    # most recent scan_date first (2024-01-07, the 7th seeded day)
    assert result["setups"][0]["scan_date"] == "2024-01-07"


def test_get_trade_plan_none_unavailable(db_session) -> None:
    _seed_instrument(db_session)
    result = tools.get_trade_plan(db_session, symbol="BBCA")
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_trade_plan_happy_path(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        TradePlan(
            instrument_id=instrument.id,
            setup_type=SetupType.BREAKOUT,
            plan_date=T0,
            risk_version="v1",
            status=TradePlanStatus.VALID,
            rejection_reasons=[],
            entry_price=1000.0,
            stop_price=950.0,
            target_prices=[1100.0],
            quantity=100,
            allocation_amount=100_000.0,
            allocation_pct=0.1,
            max_loss_amount=5_000.0,
            assumptions={"capital": 1_000_000.0},
            invalidation_conditions=[],
        )
    )
    db_session.commit()

    result = tools.get_trade_plan(db_session, symbol="BBCA")
    assert result["status"] == "OK"
    assert result["entry_price"] == 1000.0
    assert result["stop_price"] == 950.0


def test_get_backtest_invalid_id_unavailable(db_session) -> None:
    result = tools.get_backtest(db_session, backtest_id="not-a-uuid")
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_backtest_unknown_id_unavailable(db_session) -> None:
    result = tools.get_backtest(db_session, backtest_id=str(uuid.uuid4()))
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_backtest_happy_path(db_session) -> None:
    run = BacktestRun(
        strategy_version="v1",
        setup_type=SetupType.BREAKOUT,
        min_score=60.0,
        start_date=T0,
        end_date=date(2024, 6, 30),
        initial_capital=100_000_000.0,
        risk_per_trade_pct=0.01,
        max_concurrent_positions=5,
        fee_bps=15.0,
        slippage_bps=10.0,
        stop_atr_multiplier=1.5,
        target_atr_multiplier=3.0,
        max_holding_days=20,
        execution_model=ExecutionModel.NEXT_OPEN,
        indicator_version="v1",
        score_version="v1",
        status=BacktestStatus.SUCCEEDED,
    )
    db_session.add(run)
    db_session.commit()
    db_session.add(
        BacktestMetrics(
            backtest_run_id=run.id,
            total_return_pct=12.5,
            win_rate_pct=60.0,
            max_drawdown_pct=8.0,
            trade_count=10,
            r_distribution=[1.0, -1.0],
        )
    )
    db_session.commit()

    result = tools.get_backtest(db_session, backtest_id=str(run.id))
    assert result["status"] == "OK"
    assert result["total_return_pct"] == 12.5
    assert result["trade_count"] == 10


def test_get_backtest_still_running_without_metrics_yet(db_session) -> None:
    """A RUNNING backtest has no BacktestMetrics row yet — metrics fields
    must be None (not fabricated), never a crash on the missing join."""
    run = BacktestRun(
        strategy_version="v1",
        setup_type=SetupType.BREAKOUT,
        min_score=60.0,
        start_date=T0,
        end_date=date(2024, 6, 30),
        initial_capital=100_000_000.0,
        risk_per_trade_pct=0.01,
        max_concurrent_positions=5,
        fee_bps=15.0,
        slippage_bps=10.0,
        stop_atr_multiplier=1.5,
        target_atr_multiplier=3.0,
        max_holding_days=20,
        execution_model=ExecutionModel.NEXT_OPEN,
        indicator_version="v1",
        score_version="v1",
        status=BacktestStatus.RUNNING,
    )
    db_session.add(run)
    db_session.commit()

    result = tools.get_backtest(db_session, backtest_id=str(run.id))
    assert result["status"] == "OK"
    assert result["backtest_status"] == "RUNNING"
    assert result["total_return_pct"] is None
    assert result["trade_count"] is None


def test_get_position_none_unavailable(db_session) -> None:
    _seed_instrument(db_session)
    result = tools.get_position(db_session, symbol="BBCA")
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_position_happy_path(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        Position(
            instrument_id=instrument.id,
            status=PositionStatus.OPEN,
            quantity_open=100,
            avg_entry_price=1000.0,
            avg_entry_fee_per_share=1.0,
            cumulative_quantity_bought=100,
            cumulative_entry_fees=100.0,
            cumulative_exit_fees=0.0,
            realized_pnl=0.0,
            opened_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
    )
    db_session.commit()

    result = tools.get_position(db_session, symbol="BBCA")
    assert result["status"] == "OK"
    assert result["quantity_open"] == 100


def test_get_portfolio_risk_empty(db_session) -> None:
    result = tools.get_portfolio_risk(db_session)
    assert result["status"] == "OK"
    assert result["closed_position_count"] == 0


def test_get_portfolio_risk_reflects_closed_trade(db_session) -> None:
    instrument = _seed_instrument(db_session)
    position = Position(
        instrument_id=instrument.id,
        status=PositionStatus.CLOSED,
        quantity_open=0,
        avg_entry_price=1000.0,
        avg_entry_fee_per_share=0.0,
        cumulative_quantity_bought=100,
        cumulative_entry_fees=0.0,
        cumulative_exit_fees=0.0,
        realized_pnl=10_000.0,
        opened_at=datetime(2024, 1, 1, tzinfo=UTC),
        closed_at=datetime(2024, 1, 10, tzinfo=UTC),
    )
    db_session.add(position)
    db_session.commit()
    db_session.add(
        Execution(
            position_id=position.id,
            instrument_id=instrument.id,
            side=ExecutionSide.SELL,
            quantity=100,
            price=1100.0,
            fee=0.0,
            realized_pnl_impact=10_000.0,
            executed_at=datetime(2024, 1, 10, tzinfo=UTC),
        )
    )
    db_session.commit()

    result = tools.get_portfolio_risk(db_session)
    assert result["status"] == "OK"
    assert result["closed_position_count"] == 1
    assert result["total_realized_pnl"] == 10_000.0


def test_get_market_regime_unavailable_when_no_snapshot_computed(db_session) -> None:
    result = tools.get_market_regime(db_session)
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_market_regime_happy_path(db_session) -> None:
    from datetime import date

    from app.db.enums import MarketRegime
    from app.db.models import BreadthSnapshot

    db_session.add(
        BreadthSnapshot(
            as_of=date(2024, 3, 1),
            breadth_version="v1",
            universe_size=10,
            pct_above_sma50=0.7,
            pct_above_sma200=0.6,
            advancers=8,
            decliners=2,
            unchanged=0,
            new_highs_20=1,
            new_lows_20=0,
            regime=MarketRegime.RISK_ON,
            regime_version="v1",
        )
    )
    db_session.commit()

    result = tools.get_market_regime(db_session)
    assert result["status"] == "OK"
    assert result["regime"] == "RISK_ON"
    assert "proxy" in result["note"]


def test_get_market_events_unavailable_when_no_corporate_actions(db_session) -> None:
    _seed_instrument(db_session)
    result = tools.get_market_events(db_session, symbol="BBCA")
    assert result["status"] == "DATA_UNAVAILABLE"


def test_get_market_events_happy_path(db_session) -> None:
    from datetime import UTC, date, datetime

    from app.db.enums import CorporateActionType
    from app.db.models import CorporateAction

    instrument = _seed_instrument(db_session)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=date(2024, 3, 1),
            announced_at=datetime(2024, 2, 1, tzinfo=UTC),
            ratio=2.0,
            source="fixture",
            source_symbol=instrument.source_symbol,
        )
    )
    db_session.commit()

    result = tools.get_market_events(db_session, symbol="BBCA")
    assert result["status"] == "OK"
    assert result["events"][0]["event_type"] == "SPLIT"
    assert "news" in result["note"]


def test_tool_registry_has_no_writing_or_execution_capable_tools() -> None:
    """Structural guardrail check: the registry must never contain a tool
    whose name suggests it could execute a trade, modify risk limits, or
    run arbitrary SQL — the forbidden-action guardrail is that no such
    capability exists at all, not that the model is merely told not to."""
    forbidden_substrings = ("execute", "order", "sql", "delete", "update_risk", "place")
    for name in tools.TOOL_REGISTRY:
        lowered = name.lower()
        assert not any(bad in lowered for bad in forbidden_substrings), name
