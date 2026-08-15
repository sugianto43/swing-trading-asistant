from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.backtesting.config import BacktestConfig
from app.backtesting.service import BacktestService
from app.db.enums import (
    BacktestStatus,
    CorporateActionType,
    DataQualityStatus,
    ListingStatus,
    SetupType,
)
from app.db.models import (
    BacktestEquityPoint,
    BacktestMetrics,
    BacktestRun,
    BacktestTrade,
    CorporateAction,
    IndicatorSnapshot,
    Instrument,
    InstrumentStatusHistory,
    PriceBar,
    ScanCandidate,
)

START = date(2024, 1, 1)
END = date(2024, 1, 20)


def _seed_instrument(db_session, symbol: str = "BBCA") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Bank Central Asia Tbk",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.flush()  # populate instrument.id (client-side default) before referencing it
    db_session.add(
        InstrumentStatusHistory(
            instrument_id=instrument.id,
            status=ListingStatus.ACTIVE,
            effective_from=datetime(2020, 1, 1, tzinfo=UTC),
            source="fixture",
        )
    )
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def _seed_tradeable_scenario(db_session, instrument: Instrument) -> None:
    for i in range(20):
        trade_date = START + timedelta(days=i)
        close = 1065.0 if i == 3 else 1000.0
        high = 1070.0 if i == 3 else 1000.0
        low = 1060.0 if i == 3 else 1000.0
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=close,
                high=high,
                low=low,
                close=close,
                volume=1_000_000,
                source="fixture",
                source_symbol=instrument.source_symbol,
                quality_status=DataQualityStatus.VALID,
            )
        )
        db_session.add(
            IndicatorSnapshot(
                instrument_id=instrument.id,
                trade_date=trade_date,
                indicator_version="v1",
                atr_14=20.0,
            )
        )
    db_session.add(
        ScanCandidate(
            instrument_id=instrument.id,
            scan_date=START + timedelta(days=1),
            setup_type=SetupType.BREAKOUT,
            indicator_version="v1",
            score_version="v1",
            composite_score=80.0,
            trend_score=0,
            momentum_score=0,
            volume_score=0,
            price_structure_score=0,
            volatility_score=0,
            setup_quality_score=0,
            risk_reward_score=0,
            qualifying_conditions=["test"],
            invalidation_conditions=["test"],
        )
    )
    db_session.commit()


def test_run_persists_backtest_with_trade(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_tradeable_scenario(db_session, instrument)

    config = BacktestConfig(setup_type=SetupType.BREAKOUT, start_date=START, end_date=END)
    run = BacktestService(db_session).run(config)

    assert run.status == BacktestStatus.SUCCEEDED
    assert run.finished_at is not None

    persisted_run = db_session.scalar(select(BacktestRun).where(BacktestRun.id == run.id))
    assert persisted_run is not None

    trades = db_session.scalars(
        select(BacktestTrade).where(BacktestTrade.backtest_run_id == run.id)
    ).all()
    assert len(trades) == 1
    assert trades[0].instrument_id == instrument.id

    equity_points = db_session.scalars(
        select(BacktestEquityPoint).where(BacktestEquityPoint.backtest_run_id == run.id)
    ).all()
    assert len(equity_points) > 0

    metrics = db_session.scalar(
        select(BacktestMetrics).where(BacktestMetrics.backtest_run_id == run.id)
    )
    assert metrics is not None
    assert metrics.trade_count == 1


def test_run_with_no_data_succeeds_with_zero_trades(db_session) -> None:
    config = BacktestConfig(setup_type=SetupType.BREAKOUT, start_date=START, end_date=END)
    run = BacktestService(db_session).run(config)

    assert run.status == BacktestStatus.SUCCEEDED
    metrics = db_session.scalar(
        select(BacktestMetrics).where(BacktestMetrics.backtest_run_id == run.id)
    )
    assert metrics.trade_count == 0


def test_run_each_invocation_creates_a_new_run_not_upsert(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_tradeable_scenario(db_session, instrument)
    config = BacktestConfig(setup_type=SetupType.BREAKOUT, start_date=START, end_date=END)
    service = BacktestService(db_session)

    run1 = service.run(config)
    run2 = service.run(config)

    assert run1.id != run2.id
    all_runs = db_session.scalars(select(BacktestRun)).all()
    assert len(all_runs) == 2


def test_run_is_reproducible_across_separate_runs(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_tradeable_scenario(db_session, instrument)
    config = BacktestConfig(setup_type=SetupType.BREAKOUT, start_date=START, end_date=END)
    service = BacktestService(db_session)

    run1 = service.run(config)
    run2 = service.run(config)

    metrics1 = db_session.scalar(
        select(BacktestMetrics).where(BacktestMetrics.backtest_run_id == run1.id)
    )
    metrics2 = db_session.scalar(
        select(BacktestMetrics).where(BacktestMetrics.backtest_run_id == run2.id)
    )
    assert float(metrics1.total_return_pct) == float(metrics2.total_return_pct)
    assert metrics1.trade_count == metrics2.trade_count


def test_run_marks_failed_on_unexpected_exception(db_session, monkeypatch) -> None:
    instrument = _seed_instrument(db_session)
    _seed_tradeable_scenario(db_session, instrument)

    import app.backtesting.service as service_module

    def _broken_simulation(*args, **kwargs):
        raise RuntimeError("simulated engine failure")

    monkeypatch.setattr(service_module, "run_simulation", _broken_simulation)

    config = BacktestConfig(setup_type=SetupType.BREAKOUT, start_date=START, end_date=END)
    import pytest

    with pytest.raises(RuntimeError, match="simulated engine failure"):
        BacktestService(db_session).run(config)

    run = db_session.scalar(select(BacktestRun))
    assert run is not None
    assert run.status == BacktestStatus.FAILED
    assert run.error_message == "simulated engine failure"


def test_split_mid_trade_does_not_create_fake_pnl(db_session) -> None:
    # Raw prices show a 50% "crash" at the split date (2000 -> 1000), but
    # after split-adjustment the whole series is flat at 1000 — a
    # correctly-adjusted trade held across the split must show pnl close
    # to zero (just fees/slippage), never a ~50% swing.
    instrument = _seed_instrument(db_session)
    split_ex_date = START + timedelta(days=5)
    for i in range(20):
        trade_date = START + timedelta(days=i)
        raw_price = 2000.0 if trade_date < split_ex_date else 1000.0
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=raw_price,
                high=raw_price,
                low=raw_price,
                close=raw_price,
                volume=1_000_000,
                source="fixture",
                source_symbol=instrument.source_symbol,
                quality_status=DataQualityStatus.VALID,
            )
        )
        db_session.add(
            IndicatorSnapshot(
                instrument_id=instrument.id,
                trade_date=trade_date,
                indicator_version="v1",
                atr_14=20.0,
            )
        )
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=split_ex_date,
            source="fixture",
            source_symbol=instrument.source_symbol,
            ratio=2.0,
        )
    )
    db_session.add(
        ScanCandidate(
            instrument_id=instrument.id,
            scan_date=START,
            setup_type=SetupType.BREAKOUT,
            indicator_version="v1",
            score_version="v1",
            composite_score=80.0,
            trend_score=0,
            momentum_score=0,
            volume_score=0,
            price_structure_score=0,
            volatility_score=0,
            setup_quality_score=0,
            risk_reward_score=0,
            qualifying_conditions=["test"],
            invalidation_conditions=["test"],
        )
    )
    db_session.commit()

    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT,
        start_date=START,
        end_date=START + timedelta(days=19),
        fee_bps=0.0,
        slippage_bps=0.0,
    )
    run = BacktestService(db_session).run(config)
    assert run.status == BacktestStatus.SUCCEEDED

    trade = db_session.scalar(select(BacktestTrade).where(BacktestTrade.backtest_run_id == run.id))
    assert trade is not None
    # flat adjusted series -> pnl should be exactly zero (zero cost config),
    # not the ~-50% (-1000/share) a fake unadjusted crash would produce
    assert float(trade.pnl) == 0.0


def test_split_after_end_date_is_not_applied(db_session) -> None:
    # Mirrors Phase 3's corporate-action look-ahead fix: a split ingested
    # with ex_date after the backtest's end_date must not retroactively
    # adjust prices used within the backtest window.
    instrument = _seed_instrument(db_session)
    for i in range(10):
        trade_date = START + timedelta(days=i)
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=1000.0,
                high=1000.0,
                low=1000.0,
                close=1000.0,
                volume=1_000_000,
                source="fixture",
                source_symbol=instrument.source_symbol,
                quality_status=DataQualityStatus.VALID,
            )
        )
        db_session.add(
            IndicatorSnapshot(
                instrument_id=instrument.id,
                trade_date=trade_date,
                indicator_version="v1",
                atr_14=20.0,
            )
        )
    backtest_end = START + timedelta(days=9)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=backtest_end + timedelta(days=30),  # well after end_date
            source="fixture",
            source_symbol=instrument.source_symbol,
            ratio=2.0,
        )
    )
    db_session.add(
        ScanCandidate(
            instrument_id=instrument.id,
            scan_date=START,
            setup_type=SetupType.BREAKOUT,
            indicator_version="v1",
            score_version="v1",
            composite_score=80.0,
            trend_score=0,
            momentum_score=0,
            volume_score=0,
            price_structure_score=0,
            volatility_score=0,
            setup_quality_score=0,
            risk_reward_score=0,
            qualifying_conditions=["test"],
            invalidation_conditions=["test"],
        )
    )
    db_session.commit()

    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT,
        start_date=START,
        end_date=backtest_end,
        fee_bps=0.0,
        slippage_bps=0.0,
    )
    run = BacktestService(db_session).run(config)

    trade = db_session.scalar(select(BacktestTrade).where(BacktestTrade.backtest_run_id == run.id))
    assert trade is not None
    # unadjusted: entry price still 1000, not retroactively halved to 500
    assert float(trade.entry_price) == 1000.0


def test_zero_cost_config_pnl_matches_raw_price_movement(db_session) -> None:
    instrument = _seed_instrument(db_session)
    for i in range(10):
        trade_date = START + timedelta(days=i)
        price = 1000.0 if i < 3 else 1100.0  # jumps up on day 3, then flat
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=1_000_000,
                source="fixture",
                source_symbol=instrument.source_symbol,
                quality_status=DataQualityStatus.VALID,
            )
        )
        db_session.add(
            IndicatorSnapshot(
                instrument_id=instrument.id,
                trade_date=trade_date,
                indicator_version="v1",
                atr_14=200.0,  # wide enough that stop/target aren't hit
            )
        )
    db_session.add(
        ScanCandidate(
            instrument_id=instrument.id,
            scan_date=START,
            setup_type=SetupType.BREAKOUT,
            indicator_version="v1",
            score_version="v1",
            composite_score=80.0,
            trend_score=0,
            momentum_score=0,
            volume_score=0,
            price_structure_score=0,
            volatility_score=0,
            setup_quality_score=0,
            risk_reward_score=0,
            qualifying_conditions=["test"],
            invalidation_conditions=["test"],
        )
    )
    db_session.commit()

    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT,
        start_date=START,
        end_date=START + timedelta(days=9),
        fee_bps=0.0,
        slippage_bps=0.0,
        max_holding_days=100,
    )
    run = BacktestService(db_session).run(config)
    trade = db_session.scalar(select(BacktestTrade).where(BacktestTrade.backtest_run_id == run.id))
    assert trade is not None
    assert trade.fees_paid == 0.0
    assert trade.slippage_cost == 0.0
    expected_pnl = (float(trade.exit_price) - float(trade.entry_price)) * trade.quantity
    assert float(trade.pnl) == expected_pnl


def test_reproducibility_matches_full_trade_sequence_not_just_metrics(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_tradeable_scenario(db_session, instrument)
    config = BacktestConfig(setup_type=SetupType.BREAKOUT, start_date=START, end_date=END)
    service = BacktestService(db_session)

    run1 = service.run(config)
    run2 = service.run(config)

    def _trade_tuples(run_id):
        rows = db_session.scalars(
            select(BacktestTrade)
            .where(BacktestTrade.backtest_run_id == run_id)
            .order_by(BacktestTrade.entry_date)
        ).all()
        return [
            (
                r.instrument_id,
                r.entry_date,
                float(r.entry_price),
                r.exit_date,
                float(r.exit_price) if r.exit_price is not None else None,
                r.exit_reason,
                r.quantity,
                float(r.pnl) if r.pnl is not None else None,
            )
            for r in rows
        ]

    assert _trade_tuples(run1.id) == _trade_tuples(run2.id)


def test_invalid_quality_bar_defers_entry_to_next_good_day(db_session) -> None:
    instrument = _seed_instrument(db_session)
    entry_date = START + timedelta(days=1)
    for i in range(10):
        trade_date = START + timedelta(days=i)
        is_entry_day = trade_date == entry_date
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=1000.0,
                high=1000.0,
                low=-1.0 if is_entry_day else 1000.0,  # impossible price -> INVALID
                close=1000.0,
                volume=1_000_000,
                source="fixture",
                source_symbol=instrument.source_symbol,
                quality_status=DataQualityStatus.INVALID
                if is_entry_day
                else DataQualityStatus.VALID,
            )
        )
        # matches Phase 3 behavior: no IndicatorSnapshot is ever computed
        # for an INVALID bar's date
        if not is_entry_day:
            db_session.add(
                IndicatorSnapshot(
                    instrument_id=instrument.id,
                    trade_date=trade_date,
                    indicator_version="v1",
                    atr_14=20.0,
                )
            )
    db_session.add(
        ScanCandidate(
            instrument_id=instrument.id,
            scan_date=START,
            setup_type=SetupType.BREAKOUT,
            indicator_version="v1",
            score_version="v1",
            composite_score=80.0,
            trend_score=0,
            momentum_score=0,
            volume_score=0,
            price_structure_score=0,
            volatility_score=0,
            setup_quality_score=0,
            risk_reward_score=0,
            qualifying_conditions=["test"],
            invalidation_conditions=["test"],
        )
    )
    db_session.commit()

    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=START, end_date=START + timedelta(days=9)
    )
    run = BacktestService(db_session).run(config)

    trades = db_session.scalars(
        select(BacktestTrade).where(BacktestTrade.backtest_run_id == run.id)
    ).all()
    # the INVALID day is excluded entirely (no ScanPoint), so the signal
    # is NOT lost — it fills at the next available good day's open,
    # never on the bad-quality day itself. This is graceful degradation,
    # not a look-ahead violation: the fill still only ever uses a price
    # that was genuinely knowable/actionable at that later date.
    assert len(trades) == 1
    assert trades[0].entry_date == entry_date + timedelta(days=1)
