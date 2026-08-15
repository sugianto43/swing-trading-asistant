"""Canonical indicator parameter set.

Bump INDICATOR_VERSION whenever any formula or parameter below changes, so
historical indicator_snapshots rows stay traceable to the exact
configuration that produced them (MASTER-PRD §21). Never mutate the
meaning of an existing version string in place.
"""

INDICATOR_VERSION = "v1"

SMA_WINDOW_20 = 20
SMA_WINDOW_50 = 50
SMA_WINDOW_200 = 200
EMA_WINDOW_20 = 20
EMA_WINDOW_50 = 50
RSI_WINDOW = 14
ATR_WINDOW = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_WINDOW = 20
BOLLINGER_NUM_STD = 2.0
VOLUME_SMA_WINDOW = 20
RELATIVE_VOLUME_WINDOW = 20
ROLLING_HIGH_LOW_WINDOW = 20
VOLATILITY_WINDOW = 20
