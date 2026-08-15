import math

from app.backtesting.costs import apply_slippage_to_price, compute_fee


def test_compute_fee_known_value() -> None:
    assert compute_fee(1_000_000, 15.0) == 1500.0


def test_compute_fee_zero_bps() -> None:
    assert compute_fee(1_000_000, 0.0) == 0.0


def test_slippage_buy_increases_price() -> None:
    price = apply_slippage_to_price(1000.0, 10.0, is_buy=True)
    assert price > 1000.0
    assert math.isclose(price, 1001.0)


def test_slippage_sell_decreases_price() -> None:
    price = apply_slippage_to_price(1000.0, 10.0, is_buy=False)
    assert price < 1000.0
    assert math.isclose(price, 999.0)


def test_slippage_zero_bps_no_change() -> None:
    assert apply_slippage_to_price(1000.0, 0.0, is_buy=True) == 1000.0
    assert apply_slippage_to_price(1000.0, 0.0, is_buy=False) == 1000.0
