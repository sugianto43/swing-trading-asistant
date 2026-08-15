"""Deterministic risk engine: setup + portfolio state -> validated trade
plan. Pure functions only, no DB access, so every rule is unit-testable
in isolation (same discipline as app/backtesting/simulator.py).

Portfolio state is an explicit input (`existing_positions`), never read
from a database — Phase 7 (Position & Journal) has not been built yet,
so there is no persisted position table to query. An empty list is a
valid, non-fabricated "no open positions" case, not a placeholder.
"""

from dataclasses import dataclass, field

from app.backtesting.costs import apply_slippage_to_price, compute_fee
from app.risk.config import RiskConfig


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    """One caller-supplied existing exposure, used only to evaluate
    portfolio/sector/concentration limits for a new candidate plan."""

    symbol: str
    sector: str | None
    allocation_amount: float


@dataclass(frozen=True, slots=True)
class TradePlanInput:
    symbol: str
    sector: str | None
    close: float
    atr_14: float | None
    volume_sma_20: float | None
    capital: float


@dataclass(frozen=True, slots=True)
class TradePlanResult:
    valid: bool
    rejection_reasons: list[str]
    entry_price: float | None = None
    stop_price: float | None = None
    target_prices: list[float] = field(default_factory=list)
    quantity: int = 0
    allocation_amount: float = 0.0
    allocation_pct: float = 0.0
    max_loss_amount: float = 0.0
    risk_reward_ratio: float | None = None


def compute_entry_stop_targets(
    close: float, atr_14: float, config: RiskConfig
) -> tuple[float, float, list[float]]:
    """A single execution price (the last close) anchors stop/targets,
    using only the already-known ATR at plan time (no look-ahead is
    possible here since this is a forward-looking plan, not a historical
    replay — the plan is only ever built from the latest available bar).

    An earlier version also returned a buffered "entry zone high" for
    display, but no sizing/risk calculation ever used it — a fill
    anywhere above the stated entry price would silently understate the
    plan's real risk/R:R. Reporting one execution price keeps every
    persisted number (stop, targets, quantity, R:R) valid for the price
    the plan was actually built from.

    Two targets are returned: a partial-profit target at 1R and a full
    target at `target_atr_multiplier` R, so FR-009's plural "targets" is
    satisfied without fabricating extra unexplained levels.
    """
    stop_distance = config.stop_atr_multiplier * atr_14
    stop_price = close - stop_distance
    target_1r = close + stop_distance
    target_full = close + config.target_atr_multiplier * atr_14
    return close, stop_price, [target_1r, target_full]


def compute_position_size(
    capital: float, entry_price: float, stop_price: float, config: RiskConfig
) -> int:
    """Fixed-fractional sizing on total capital, lot-aware, rounded down.
    Entry price is slippage-adjusted (worse fill, same convention as
    app.backtesting.costs) before sizing, and affordability accounts for
    the entry fee — so a plan's stated quantity is never larger than what
    capital can actually cover once real trading costs are included.
    Returns 0 (never a fabricated minimum) when inputs are invalid or
    capital cannot afford even one lot."""
    if capital <= 0 or entry_price <= 0 or config.risk_per_trade_pct <= 0:
        return 0
    if stop_price >= entry_price:
        return 0

    filled_entry_price = apply_slippage_to_price(entry_price, config.slippage_bps, is_buy=True)
    if stop_price >= filled_entry_price:
        return 0

    risk_amount = capital * config.risk_per_trade_pct
    stop_distance = filled_entry_price - stop_price
    risk_based_lots = int((risk_amount / stop_distance) // config.lot_size)

    fee_factor = 1 + config.fee_bps / 10_000
    affordable_notional = capital / fee_factor
    max_affordable_lots = int((affordable_notional / filled_entry_price) // config.lot_size)

    lots = min(risk_based_lots, max_affordable_lots)
    return max(0, lots * config.lot_size)


def _portfolio_exposure(existing_positions: list[PortfolioPosition]) -> float:
    return sum(p.allocation_amount for p in existing_positions)


def _sector_exposure(existing_positions: list[PortfolioPosition], sector: str | None) -> float:
    if sector is None:
        return 0.0
    return sum(p.allocation_amount for p in existing_positions if p.sector == sector)


def check_risk_limits(
    *,
    symbol: str,
    sector: str | None,
    entry_price: float,
    stop_price: float,
    target_prices: list[float],
    quantity: int,
    capital: float,
    volume_sma_20: float | None,
    existing_positions: list[PortfolioPosition],
    config: RiskConfig,
) -> list[str]:
    """Returns a list of human-readable rejection reasons; empty means
    the plan passes every configured limit. Every violated rule is
    reported (not just the first), so a rejected plan is fully
    explainable rather than partially diagnosed."""
    reasons: list[str] = []

    if stop_price >= entry_price:
        reasons.append("stop price must be below entry price")

    if quantity <= 0:
        reasons.append("position size rounds to zero lots (insufficient capital or risk budget)")

    if entry_price > 0 and stop_price < entry_price:
        stop_distance = entry_price - stop_price
        reward_distance = (target_prices[-1] - entry_price) if target_prices else 0.0
        risk_reward = reward_distance / stop_distance if stop_distance > 0 else 0.0
        if risk_reward < config.min_risk_reward:
            reasons.append(
                f"risk/reward {risk_reward:.2f} below minimum {config.min_risk_reward:.2f}"
            )

    if volume_sma_20 is None:
        reasons.append(
            "liquidity unknown (missing volume_sma_20) — cannot verify minimum liquidity"
        )
    elif volume_sma_20 < config.min_liquidity_volume:
        reasons.append(
            f"liquidity {volume_sma_20:.0f} below minimum {config.min_liquidity_volume:.0f}"
        )

    allocation_amount = entry_price * quantity
    if capital > 0:
        allocation_pct = allocation_amount / capital
        if allocation_pct > config.max_position_allocation_pct:
            reasons.append(
                f"position allocation {allocation_pct:.2%} exceeds maximum "
                f"{config.max_position_allocation_pct:.2%}"
            )

        existing_exposure = _portfolio_exposure(existing_positions)
        portfolio_exposure_pct = (existing_exposure + allocation_amount) / capital
        if portfolio_exposure_pct > config.max_portfolio_exposure_pct:
            reasons.append(
                f"portfolio exposure {portfolio_exposure_pct:.2%} exceeds maximum "
                f"{config.max_portfolio_exposure_pct:.2%}"
            )

        if sector is not None:
            existing_sector_exposure = _sector_exposure(existing_positions, sector)
            sector_exposure_pct = (existing_sector_exposure + allocation_amount) / capital
            if sector_exposure_pct > config.max_sector_exposure_pct:
                reasons.append(
                    f"sector exposure {sector_exposure_pct:.2%} exceeds maximum "
                    f"{config.max_sector_exposure_pct:.2%}"
                )

    already_held_symbols = {p.symbol for p in existing_positions}
    concurrent_count = len(already_held_symbols - {symbol}) + 1
    if concurrent_count > config.max_concurrent_positions:
        reasons.append(
            f"concurrent positions {concurrent_count} exceeds maximum "
            f"{config.max_concurrent_positions}"
        )

    return reasons


def build_trade_plan(
    plan_input: TradePlanInput,
    existing_positions: list[PortfolioPosition],
    config: RiskConfig,
) -> TradePlanResult:
    """Orchestrates entry/stop/target derivation, sizing, and limit
    checks into one TradePlanResult. An invalid plan is still fully
    returned (with rejection_reasons populated) rather than raising or
    being silently dropped — callers persist it as REJECTED, matching
    FR-011's "invalid plans must be rejected" plus FR-009/§21's
    auditability requirement."""
    if plan_input.atr_14 is None or plan_input.atr_14 <= 0:
        return TradePlanResult(
            valid=False,
            rejection_reasons=["missing or non-positive ATR — cannot derive stop/targets"],
        )

    raw_entry_price, stop_price, target_prices = compute_entry_stop_targets(
        plan_input.close, plan_input.atr_14, config
    )
    # downstream allocation/loss/R:R math uses the same slippage-adjusted
    # fill price that sizing used, so a plan's stated numbers are
    # internally consistent rather than mixing a raw and a filled price.
    entry_price = apply_slippage_to_price(raw_entry_price, config.slippage_bps, is_buy=True)

    quantity = compute_position_size(plan_input.capital, raw_entry_price, stop_price, config)

    reasons = check_risk_limits(
        symbol=plan_input.symbol,
        sector=plan_input.sector,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices,
        quantity=quantity,
        capital=plan_input.capital,
        volume_sma_20=plan_input.volume_sma_20,
        existing_positions=existing_positions,
        config=config,
    )

    allocation_amount = entry_price * quantity
    allocation_pct = allocation_amount / plan_input.capital if plan_input.capital > 0 else 0.0
    stop_distance = entry_price - stop_price
    # max loss includes the known entry fee; the exit fee isn't included
    # since its notional depends on the (unknown) exit price.
    entry_fee = compute_fee(allocation_amount, config.fee_bps)
    max_loss_amount = stop_distance * quantity + entry_fee
    risk_reward_ratio = (
        (target_prices[-1] - entry_price) / stop_distance if stop_distance > 0 else None
    )

    return TradePlanResult(
        valid=len(reasons) == 0,
        rejection_reasons=reasons,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices,
        quantity=quantity,
        allocation_amount=allocation_amount,
        allocation_pct=allocation_pct,
        max_loss_amount=max_loss_amount,
        risk_reward_ratio=risk_reward_ratio,
    )
