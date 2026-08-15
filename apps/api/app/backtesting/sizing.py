from app.backtesting.config import IDX_LOT_SIZE


def compute_position_size(
    equity: float,
    entry_price: float,
    stop_price: float,
    risk_per_trade_pct: float,
    lot_size: int = IDX_LOT_SIZE,
) -> int:
    """Fixed-fractional position sizing, deterministic and lot-aware.

    Risks `risk_per_trade_pct` of total equity on the entry-to-stop
    distance, rounded DOWN to whole lots, further capped by what current
    equity can actually afford. Returns 0 (not a fabricated minimum
    position) whenever inputs are invalid or capital is insufficient for
    even one lot — this is a minimal backtest-internal sizing model, not
    Phase 6's full risk engine.
    """
    if equity <= 0 or entry_price <= 0 or risk_per_trade_pct <= 0:
        return 0
    if stop_price >= entry_price:
        return 0

    risk_amount = equity * risk_per_trade_pct
    stop_distance = entry_price - stop_price
    raw_shares = risk_amount / stop_distance
    risk_based_lots = int(raw_shares // lot_size)

    max_affordable_lots = int((equity // entry_price) // lot_size)

    lots = min(risk_based_lots, max_affordable_lots)
    return max(0, lots * lot_size)
