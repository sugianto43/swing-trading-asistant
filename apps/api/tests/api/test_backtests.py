import uuid
from datetime import date

from app.db.enums import BacktestStatus, ExecutionModel, ExitReason, ListingStatus, SetupType
from app.db.models import (
    BacktestEquityPoint,
    BacktestMetrics,
    BacktestRun,
    BacktestTrade,
    Instrument,
)


def _seed_run(db_session, **overrides) -> BacktestRun:
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
    run = BacktestRun(**defaults)
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def _seed_instrument(db_session, symbol="BBCA") -> Instrument:
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
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def test_list_backtest_runs_empty(client) -> None:
    response = client.get("/api/v1/backtests")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_list_backtest_runs_returns_seeded_rows(client, db_session) -> None:
    _seed_run(db_session)
    response = client.get("/api/v1/backtests")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["setup_type"] == "BREAKOUT"


def test_get_backtest_run_404_for_unknown_id(client) -> None:
    response = client.get(f"/api/v1/backtests/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_backtest_run_detail_includes_metrics(client, db_session) -> None:
    run = _seed_run(db_session)
    db_session.add(
        BacktestMetrics(
            backtest_run_id=run.id,
            total_return_pct=12.5,
            win_rate_pct=60.0,
            max_drawdown_pct=8.0,
            trade_count=10,
            r_distribution=[1.0, -1.0, 2.0],
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/backtests/{run.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["total_return_pct"] == 12.5
    assert body["metrics"]["trade_count"] == 10


def test_get_backtest_run_detail_metrics_none_when_missing(client, db_session) -> None:
    run = _seed_run(db_session)
    response = client.get(f"/api/v1/backtests/{run.id}")
    assert response.status_code == 200
    assert response.json()["metrics"] is None


def test_list_backtest_trades_404_for_unknown_run(client) -> None:
    response = client.get(f"/api/v1/backtests/{uuid.uuid4()}/trades")
    assert response.status_code == 404


def test_list_backtest_trades_returns_seeded_rows(client, db_session) -> None:
    run = _seed_run(db_session)
    instrument = _seed_instrument(db_session)
    db_session.add(
        BacktestTrade(
            backtest_run_id=run.id,
            instrument_id=instrument.id,
            setup_type=SetupType.BREAKOUT,
            signal_date=date(2024, 1, 1),
            entry_date=date(2024, 1, 2),
            entry_price=1000.0,
            stop_price=970.0,
            target_price=1060.0,
            exit_date=date(2024, 1, 5),
            exit_price=1060.0,
            exit_reason=ExitReason.TARGET,
            quantity=100,
            fees_paid=15.0,
            slippage_cost=10.0,
            pnl=5975.0,
            r_multiple=2.0,
            holding_days=3,
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/backtests/{run.id}/trades")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "BBCA"
    assert body["items"][0]["exit_reason"] == "TARGET"


def test_list_backtest_equity_curve_404_for_unknown_run(client) -> None:
    response = client.get(f"/api/v1/backtests/{uuid.uuid4()}/equity-curve")
    assert response.status_code == 404


def test_list_backtest_equity_curve_returns_seeded_rows(client, db_session) -> None:
    run = _seed_run(db_session)
    db_session.add(
        BacktestEquityPoint(
            backtest_run_id=run.id, trade_date=date(2024, 1, 2), equity_value=100_500_000.0
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/backtests/{run.id}/equity-curve")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["equity_value"] == 100_500_000.0


def test_list_backtest_runs_rejects_page_below_one(client) -> None:
    response = client.get("/api/v1/backtests", params={"page": 0})
    assert response.status_code == 422


def test_list_backtest_trades_rejects_page_size_over_max(client, db_session) -> None:
    run = _seed_run(db_session)
    response = client.get(f"/api/v1/backtests/{run.id}/trades", params={"page_size": 10_000})
    assert response.status_code == 422


def test_get_backtest_run_rejects_malformed_uuid(client) -> None:
    response = client.get("/api/v1/backtests/not-a-uuid")
    assert response.status_code == 422
