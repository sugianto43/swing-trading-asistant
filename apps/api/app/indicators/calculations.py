"""Pure, deterministic indicator formulas.

Plain Python, not pandas/numpy — indicator math stays maximally auditable
and immune to library default-parameter surprises (e.g. pandas' `ewm`
`adjust=True` vs `False` producing different EMAs). Each function only
ever looks at values at or before the current index — no centered windows,
no future data (MASTER-PRD §8, QUANT-TRADING-RULES).

Every function returns a list the same length as its input, with `None`
for indices that don't yet have enough history (explicit warm-up, per
Phase 3 TDD).
"""

import math


def sma(values: list[float], window: int) -> list[float | None]:
    """Simple moving average over a trailing window (inclusive of current)."""
    result: list[float | None] = [None] * len(values)
    for i in range(len(values)):
        if i < window - 1:
            continue
        window_slice = values[i - window + 1 : i + 1]
        result[i] = sum(window_slice) / window
    return result


def ema(values: list[float], window: int) -> list[float | None]:
    """Exponential moving average, seeded by the SMA of the first `window` values."""
    result: list[float | None] = [None] * len(values)
    if len(values) < window:
        return result

    seed = sum(values[:window]) / window
    result[window - 1] = seed
    k = 2 / (window + 1)
    prev = seed
    for i in range(window, len(values)):
        prev = values[i] * k + prev * (1 - k)
        result[i] = prev
    return result


def _ema_skip_leading_none(values: list[float | None], window: int) -> list[float | None]:
    """EMA over a list that has leading Nones (e.g. MACD line before its
    slow EMA warms up) but no gaps once it starts. Returns a full-length
    list, None-padded to match the input's leading gap."""
    first_valid = next((i for i, v in enumerate(values) if v is not None), None)
    if first_valid is None:
        return [None] * len(values)

    trimmed = [v for v in values[first_valid:] if v is not None]
    trimmed_ema = ema(trimmed, window)
    return [None] * first_valid + trimmed_ema


def rsi(closes: list[float], window: int = 14) -> list[float | None]:
    """Wilder's RSI. First value appears at index `window` (needs `window`
    price changes, i.e. `window + 1` closes)."""
    n = len(closes)
    result: list[float | None] = [None] * n
    if n <= window:
        return result

    diffs = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [max(d, 0.0) for d in diffs]
    losses = [max(-d, 0.0) for d in diffs]

    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window
    result[window] = _rsi_from_averages(avg_gain, avg_loss)

    for i in range(window, len(diffs)):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window
        result[i + 1] = _rsi_from_averages(avg_gain, avg_loss)

    return result


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(
    highs: list[float], lows: list[float], closes: list[float], window: int = 14
) -> list[float | None]:
    """Wilder's Average True Range."""
    n = len(highs)
    result: list[float | None] = [None] * n
    if n < window:
        return result

    true_ranges: list[float] = [highs[0] - lows[0]]
    for i in range(1, n):
        true_ranges.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )

    prev_atr = sum(true_ranges[:window]) / window
    result[window - 1] = prev_atr
    for i in range(window, n):
        prev_atr = (prev_atr * (window - 1) + true_ranges[i]) / window
        result[i] = prev_atr

    return result


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line: list[float | None] = [
        None if (f is None or s is None) else f - s for f, s in zip(ema_fast, ema_slow, strict=True)
    ]
    signal_line = _ema_skip_leading_none(macd_line, signal)
    histogram: list[float | None] = [
        None if (m is None or s is None) else m - s
        for m, s in zip(macd_line, signal_line, strict=True)
    ]
    return macd_line, signal_line, histogram


def _stdev(values: list[float]) -> float:
    """Population standard deviation (ddof=0) — canonical Bollinger Bands convention."""
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def bollinger_bands(
    closes: list[float], window: int = 20, num_std: float = 2.0
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Returns (upper, middle, lower)."""
    middle = sma(closes, window)
    upper: list[float | None] = [None] * len(closes)
    lower: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        middle_value = middle[i]
        if middle_value is None:
            continue
        band = num_std * _stdev(closes[i - window + 1 : i + 1])
        upper[i] = middle_value + band
        lower[i] = middle_value - band
    return upper, middle, lower


def rolling_high(highs: list[float], window: int) -> list[float | None]:
    result: list[float | None] = [None] * len(highs)
    for i in range(len(highs)):
        if i < window - 1:
            continue
        result[i] = max(highs[i - window + 1 : i + 1])
    return result


def rolling_low(lows: list[float], window: int) -> list[float | None]:
    result: list[float | None] = [None] * len(lows)
    for i in range(len(lows)):
        if i < window - 1:
            continue
        result[i] = min(lows[i - window + 1 : i + 1])
    return result


def returns(closes: list[float], period: int = 1) -> list[float | None]:
    result: list[float | None] = [None] * len(closes)
    for i in range(period, len(closes)):
        prior = closes[i - period]
        if prior == 0:
            continue
        result[i] = (closes[i] - prior) / prior
    return result


def volatility(closes: list[float], window: int = 20) -> list[float | None]:
    """Population stdev of 1-day returns over a trailing window."""
    daily_returns = returns(closes, period=1)
    result: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        window_returns = daily_returns[i - window + 1 : i + 1] if i >= window else None
        if not window_returns or any(r is None for r in window_returns):
            continue
        result[i] = _stdev([r for r in window_returns if r is not None])
    return result


def relative_volume(volumes: list[int], window: int = 20) -> list[float | None]:
    """Current volume vs the average of the PRIOR `window` days (excluding
    today) — causal by construction, no self-reference."""
    result: list[float | None] = [None] * len(volumes)
    for i in range(window, len(volumes)):
        prior_avg = sum(volumes[i - window : i]) / window
        if prior_avg == 0:
            continue
        result[i] = volumes[i] / prior_avg
    return result
