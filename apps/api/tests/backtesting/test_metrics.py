import math
import uuid
from datetime import date

from app.backtesting.metrics import (
    avg_holding_days,
    avg_loss,
    avg_win,
    cagr_pct,
    compute_metrics,
    expectancy,
    max_drawdown_pct,
    profit_factor,
    sharpe_ratio,
    total_return_pct,
    win_rate_pct,
)
from app.backtesting.simulator import TradeResult
from app.db.enums import ExitReason, SetupType


def _trade(pnl: float, r_multiple: float = 1.0, holding_days: int = 5) -> TradeResult:
    return TradeResult(
        instrument_id=uuid.uuid4(),
        setup_type=SetupType.BREAKOUT,
        signal_date=date(2024, 1, 1),
        entry_date=date(2024, 1, 2),
        entry_price=100.0,
        stop_price=95.0,
        target_price=110.0,
        exit_date=date(2024, 1, 7),
        exit_price=100.0 + pnl / 100,
        exit_reason=ExitReason.TARGET,
        quantity=100,
        fees_paid=10.0,
        slippage_cost=5.0,
        pnl=pnl,
        r_multiple=r_multiple,
        holding_days=holding_days,
    )


def test_total_return_pct_known_value() -> None:
    assert total_return_pct(100_000, 110_000) == 10.0


def test_total_return_pct_negative() -> None:
    assert total_return_pct(100_000, 90_000) == -10.0


def test_total_return_pct_zero_capital_safe() -> None:
    assert total_return_pct(0, 100) == 0.0


def test_cagr_known_value_one_year() -> None:
    result = cagr_pct(100_000, 110_000, date(2024, 1, 1), date(2025, 1, 1))
    assert result is not None
    assert math.isclose(result, 10.0, rel_tol=0.01)


def test_cagr_none_for_short_window() -> None:
    assert cagr_pct(100_000, 105_000, date(2024, 1, 1), date(2024, 1, 10)) is None


def test_win_rate_pct_known_value() -> None:
    trades = [_trade(100), _trade(-50), _trade(200), _trade(-30)]
    assert win_rate_pct(trades) == 50.0


def test_win_rate_pct_empty_is_zero() -> None:
    assert win_rate_pct([]) == 0.0


def test_avg_win_and_avg_loss() -> None:
    trades = [_trade(100), _trade(-50), _trade(200), _trade(-30)]
    assert avg_win(trades) == 150.0
    assert avg_loss(trades) == -40.0


def test_avg_win_none_when_no_wins() -> None:
    assert avg_win([_trade(-10), _trade(-20)]) is None


def test_avg_loss_none_when_no_losses() -> None:
    assert avg_loss([_trade(10), _trade(20)]) is None


def test_expectancy_known_value() -> None:
    trades = [_trade(100), _trade(-50)]
    assert expectancy(trades) == 25.0


def test_expectancy_none_when_no_trades() -> None:
    assert expectancy([]) is None


def test_profit_factor_known_value() -> None:
    trades = [_trade(100), _trade(-50)]
    assert profit_factor(trades) == 2.0


def test_profit_factor_none_when_no_losses() -> None:
    assert profit_factor([_trade(100), _trade(50)]) is None


def test_max_drawdown_pct_known_value() -> None:
    curve = [
        (date(2024, 1, 1), 100_000),
        (date(2024, 1, 2), 120_000),  # new peak
        (date(2024, 1, 3), 90_000),  # drawdown from peak: (120000-90000)/120000=25%
        (date(2024, 1, 4), 110_000),
    ]
    assert max_drawdown_pct(curve) == 25.0


def test_max_drawdown_pct_empty_curve() -> None:
    assert max_drawdown_pct([]) == 0.0


def test_max_drawdown_pct_monotonic_up_is_zero() -> None:
    curve = [(date(2024, 1, 1), 100), (date(2024, 1, 2), 110), (date(2024, 1, 3), 120)]
    assert max_drawdown_pct(curve) == 0.0


def test_sharpe_ratio_none_for_short_curve() -> None:
    curve = [(date(2024, 1, 1), 100_000), (date(2024, 1, 2), 101_000)]
    assert sharpe_ratio(curve) is None


def test_sharpe_ratio_none_for_zero_variance() -> None:
    curve = [(date(2024, 1, i), 100_000) for i in range(1, 6)]
    assert sharpe_ratio(curve) is None


def test_sharpe_ratio_positive_for_uptrend() -> None:
    curve = [(date(2024, 1, i), 100_000 * (1.001**i)) for i in range(1, 30)]
    result = sharpe_ratio(curve)
    assert result is not None
    assert result > 0


def test_avg_holding_days_known_value() -> None:
    trades = [_trade(10, holding_days=5), _trade(20, holding_days=15)]
    assert avg_holding_days(trades) == 10.0


def test_avg_holding_days_none_when_empty() -> None:
    assert avg_holding_days([]) is None


def test_compute_metrics_zero_trades() -> None:
    result = compute_metrics([], [], 100_000, date(2024, 1, 1), date(2024, 12, 31))
    assert result.trade_count == 0
    assert result.win_rate_pct == 0.0
    assert result.total_return_pct == 0.0
    assert result.r_distribution == []


def test_compute_metrics_uses_final_equity_curve_value() -> None:
    curve = [(date(2024, 1, 1), 100_000), (date(2024, 12, 31), 120_000)]
    result = compute_metrics([_trade(20_000)], curve, 100_000, date(2024, 1, 1), date(2024, 12, 31))
    assert result.total_return_pct == 20.0
