from app.backtesting.sizing import compute_position_size


def test_sizing_known_value() -> None:
    # risk 1% of 100,000,000 = 1,000,000; stop distance = 100 -> 10,000 shares
    # -> rounded down to lot=100 -> 10,000 shares (already a multiple of 100)
    qty = compute_position_size(
        equity=100_000_000, entry_price=1000, stop_price=900, risk_per_trade_pct=0.01
    )
    assert qty == 10_000


def test_sizing_rounds_down_to_lot_size() -> None:
    # risk_amount = 100,000 * 0.01 = 1,000; stop_distance=3 -> raw=333.33 shares
    # -> 3 lots of 100 = 300 shares (not 333)
    qty = compute_position_size(
        equity=100_000, entry_price=100, stop_price=97, risk_per_trade_pct=0.01
    )
    assert qty == 300
    assert qty % 100 == 0


def test_sizing_zero_when_stop_above_entry() -> None:
    assert compute_position_size(100_000, 100, 105, 0.01) == 0


def test_sizing_zero_when_stop_equals_entry() -> None:
    assert compute_position_size(100_000, 100, 100, 0.01) == 0


def test_sizing_zero_when_equity_non_positive() -> None:
    assert compute_position_size(0, 100, 90, 0.01) == 0
    assert compute_position_size(-100, 100, 90, 0.01) == 0


def test_sizing_zero_when_insufficient_capital_for_one_lot() -> None:
    # entry price so high that even 100 shares exceeds equity
    qty = compute_position_size(equity=1000, entry_price=100, stop_price=90, risk_per_trade_pct=1.0)
    assert qty == 0


def test_sizing_capped_by_affordability_not_just_risk() -> None:
    # huge risk_pct would size very large by risk formula, but equity can't afford it
    qty = compute_position_size(
        equity=10_000, entry_price=100, stop_price=99, risk_per_trade_pct=1.0
    )
    # afford at most 100 shares (1 lot) at equity=10,000, price=100
    assert qty <= 100
