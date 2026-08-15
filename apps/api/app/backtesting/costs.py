def compute_fee(notional: float, fee_bps: float) -> float:
    return notional * (fee_bps / 10_000)


def apply_slippage_to_price(price: float, slippage_bps: float, *, is_buy: bool) -> float:
    """Slippage always moves the fill price against the trader: worse
    (higher) on a buy, worse (lower) on a sell. Applied directly to the
    fill price rather than tracked as a separate adjustment, so pnl
    computed from fill prices already reflects it without double-counting."""
    factor = slippage_bps / 10_000
    return price * (1 + factor) if is_buy else price * (1 - factor)
