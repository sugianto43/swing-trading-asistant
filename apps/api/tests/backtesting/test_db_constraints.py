from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import BacktestStatus, ExecutionModel, SetupType
from app.db.models import BacktestEquityPoint, BacktestRun


def _run(**overrides) -> BacktestRun:
    defaults = {
        "strategy_version": "v1",
        "setup_type": SetupType.BREAKOUT,
        "min_score": 60.0,
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
        "initial_capital": 100_000_000.0,
        "risk_per_trade_pct": 0.01,
        "max_concurrent_positions": 5,
        "fee_bps": 15.0,
        "slippage_bps": 10.0,
        "stop_atr_multiplier": 1.5,
        "target_atr_multiplier": 3.0,
        "max_holding_days": 20,
        "execution_model": ExecutionModel.NEXT_OPEN,
        "indicator_version": "v1",
        "score_version": "v1",
        "status": BacktestStatus.SUCCEEDED,
    }
    defaults.update(overrides)
    return BacktestRun(**defaults)


def test_duplicate_equity_point_violates_unique_constraint(db_session) -> None:
    run = _run()
    db_session.add(run)
    db_session.commit()

    db_session.add(
        BacktestEquityPoint(
            backtest_run_id=run.id, trade_date=date(2024, 1, 2), equity_value=100_000_000.0
        )
    )
    db_session.commit()

    db_session.add(
        BacktestEquityPoint(backtest_run_id=run.id, trade_date=date(2024, 1, 2), equity_value=999.0)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_different_backtest_run_same_date_is_allowed(db_session) -> None:
    run1 = _run()
    run2 = _run()
    db_session.add(run1)
    db_session.add(run2)
    db_session.commit()

    db_session.add(
        BacktestEquityPoint(
            backtest_run_id=run1.id, trade_date=date(2024, 1, 2), equity_value=100.0
        )
    )
    db_session.add(
        BacktestEquityPoint(
            backtest_run_id=run2.id, trade_date=date(2024, 1, 2), equity_value=100.0
        )
    )
    db_session.commit()  # must not raise — different backtest_run_id


def test_backtest_metrics_unique_per_run(db_session) -> None:
    from app.db.models import BacktestMetrics

    run = _run()
    db_session.add(run)
    db_session.commit()

    db_session.add(
        BacktestMetrics(
            backtest_run_id=run.id,
            total_return_pct=10.0,
            win_rate_pct=50.0,
            max_drawdown_pct=5.0,
            trade_count=1,
            r_distribution=[1.0],
        )
    )
    db_session.commit()

    db_session.add(
        BacktestMetrics(
            backtest_run_id=run.id,
            total_return_pct=999.0,
            win_rate_pct=50.0,
            max_drawdown_pct=5.0,
            trade_count=1,
            r_distribution=[1.0],
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
