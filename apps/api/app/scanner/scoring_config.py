"""Canonical scoring/setup parameter set.

Bump SCORE_VERSION whenever any threshold or weight below changes, so
historical scan_candidates rows stay traceable to the exact configuration
that produced them (MASTER-PRD §21), mirroring indicator_version.

Market context/regime is deliberately absent from both the setups and the
scoring weights below — no market-wide/breadth data source exists yet
(that is Phase 9 scope). Omitting it is a documented gap, not a silent
one; fabricating a placeholder signal from nothing would violate the
"never invent market data" principle.
"""

SCORE_VERSION = "v1"

# --- setup thresholds ---
BREAKOUT_MIN_RELATIVE_VOLUME = 1.5

PULLBACK_TOLERANCE_PCT = 0.03
PULLBACK_RSI_MIN = 40.0
PULLBACK_RSI_MAX = 60.0

MOMENTUM_RSI_MIN = 50.0
MOMENTUM_RSI_MAX = 70.0

MA_RECLAIM_MIN_RELATIVE_VOLUME = 1.0

SQUEEZE_LOOKBACK = 60
SQUEEZE_PERCENTILE = 0.20  # prior bar's BB width must be in the tightest 20% of the lookback
SQUEEZE_MIN_RELATIVE_VOLUME = 1.3

# --- scoring formula constants ---
VOLUME_SCORE_SCALE = 50.0  # relative_volume * this, capped at 100

RISK_REWARD_ATR_STOP_MULTIPLIER = 1.5
RISK_REWARD_ATR_TARGET_MULTIPLIER = 3.0
RISK_REWARD_SCORE_SCALE = 25.0  # R:R ratio * this, capped at 100

# volatility_score prefers a moderate ATR/close band — too low reads as
# illiquid/dead, too high reads as excessively risky for a weekly-swing hold
VOLATILITY_LOW_BAND = 0.01
VOLATILITY_HIGH_BAND = 0.05

# composite = sum(component * weight); weights sum to 1.0
SCORE_WEIGHTS = {
    "trend_score": 0.20,
    "momentum_score": 0.15,
    "volume_score": 0.15,
    "price_structure_score": 0.15,
    "volatility_score": 0.10,
    "setup_quality_score": 0.15,
    "risk_reward_score": 0.10,
}
