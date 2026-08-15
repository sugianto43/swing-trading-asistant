import math

from app.indicators.calculations import (
    atr,
    bollinger_bands,
    ema,
    macd,
    relative_volume,
    returns,
    rolling_high,
    rolling_low,
    rsi,
    sma,
    volatility,
)


def test_sma_known_values() -> None:
    assert sma([1.0, 2.0, 3.0, 4.0, 5.0], 3) == [None, None, 2.0, 3.0, 4.0]


def test_sma_insufficient_data_all_none() -> None:
    assert sma([1.0, 2.0], 5) == [None, None]


def test_sma_empty_input() -> None:
    assert sma([], 3) == []


def test_sma_exact_boundary_window_minus_one_is_none() -> None:
    # exactly window-1 values: not enough for even one output
    assert sma([1.0, 2.0], 3) == [None, None]


def test_sma_exact_boundary_window_produces_one_value() -> None:
    # exactly `window` values: the last index (and only it) is populated
    assert sma([1.0, 2.0, 3.0], 3) == [None, None, 2.0]


def test_ema_seeded_by_sma_of_first_window() -> None:
    # constant series: EMA of a constant is that constant, once seeded
    values = [10.0] * 10
    result = ema(values, 3)
    assert result[:2] == [None, None]
    assert all(v == 10.0 for v in result[2:])


def test_ema_known_value_hand_computed() -> None:
    # window=2 -> k = 2/3
    values = [1.0, 2.0, 3.0]
    result = ema(values, 2)
    assert result[0] is None
    assert result[1] == 1.5  # SMA seed of [1,2]
    assert math.isclose(result[2], 3.0 * (2 / 3) + 1.5 * (1 / 3))


def test_rsi_warm_up_length() -> None:
    closes = [float(i) for i in range(1, 20)]  # steadily rising, no losses
    result = rsi(closes, window=14)
    assert all(v is None for v in result[:14])
    assert result[14] is not None


def test_rsi_exact_boundary_window_closes_is_all_none() -> None:
    # exactly `window` closes -> only window-1 diffs, not enough for RSI
    closes = [float(i) for i in range(14)]
    assert rsi(closes, window=14) == [None] * 14


def test_rsi_exact_boundary_window_plus_one_closes_produces_one_value() -> None:
    closes = [float(i) for i in range(15)]
    result = rsi(closes, window=14)
    assert result[:14] == [None] * 14
    assert result[14] is not None


def test_rsi_all_gains_is_100() -> None:
    closes = [float(i) for i in range(1, 20)]  # strictly increasing
    result = rsi(closes, window=14)
    assert result[14] == 100.0


def test_rsi_all_losses_is_0() -> None:
    closes = [float(i) for i in range(20, 1, -1)]  # strictly decreasing
    result = rsi(closes, window=14)
    assert result[14] == 0.0


def test_atr_warm_up_and_positive() -> None:
    highs = [10.0 + i for i in range(20)]
    lows = [9.0 + i for i in range(20)]
    closes = [9.5 + i for i in range(20)]
    result = atr(highs, lows, closes, window=14)
    assert all(v is None for v in result[:13])
    assert result[13] is not None
    assert result[13] > 0


def test_macd_warm_up_length() -> None:
    closes = [float(100 + i) for i in range(60)]
    macd_line, signal_line, hist = macd(closes, fast=12, slow=26, signal=9)
    assert macd_line[24] is None
    assert macd_line[25] is not None  # slow EMA (window 26) warms up at index 25
    # signal needs 9 consecutive macd values after index 25 -> warms up at 25+8=33
    assert signal_line[32] is None
    assert signal_line[33] is not None
    assert hist[33] == macd_line[33] - signal_line[33]


def test_bollinger_bands_middle_equals_sma() -> None:
    closes = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    upper, middle, lower = bollinger_bands(closes, window=5, num_std=2.0)
    assert middle == sma(closes, 5)
    for i in range(4, len(closes)):
        assert upper[i] > middle[i] > lower[i]


def test_bollinger_bands_zero_variance_bands_equal_middle() -> None:
    closes = [5.0] * 10
    upper, middle, lower = bollinger_bands(closes, window=5, num_std=2.0)
    assert upper[4] == middle[4] == lower[4] == 5.0


def test_rolling_high_low() -> None:
    highs = [1.0, 5.0, 3.0, 8.0, 2.0]
    lows = [0.5, 2.0, 1.0, 4.0, 1.5]
    assert rolling_high(highs, 3) == [None, None, 5.0, 8.0, 8.0]
    assert rolling_low(lows, 3) == [None, None, 0.5, 1.0, 1.0]


def test_returns_known_values() -> None:
    closes = [100.0, 110.0, 99.0]
    result = returns(closes, period=1)
    assert result[0] is None
    assert math.isclose(result[1], 0.10)
    assert math.isclose(result[2], -0.1)


def test_returns_zero_prior_price_is_none_not_crash() -> None:
    closes = [0.0, 10.0]
    assert returns(closes, period=1) == [None, None]


def test_volatility_constant_series_is_zero() -> None:
    closes = [10.0] * 25
    result = volatility(closes, window=20)
    assert result[20] == 0.0


def test_volatility_warm_up() -> None:
    closes = [float(100 + i) for i in range(25)]
    result = volatility(closes, window=20)
    assert all(v is None for v in result[:20])
    assert result[20] is not None


def test_relative_volume_excludes_current_day() -> None:
    # prior 20 days constant at 1000, current day spikes to 5000
    volumes = [1000] * 20 + [5000]
    result = relative_volume(volumes, window=20)
    assert result[20] == 5.0


def test_relative_volume_warm_up() -> None:
    volumes = [1000] * 10
    result = relative_volume(volumes, window=20)
    assert all(v is None for v in result)
