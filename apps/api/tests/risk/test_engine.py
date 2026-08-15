from app.risk.config import RiskConfig
from app.risk.engine import (
    PortfolioPosition,
    TradePlanInput,
    build_trade_plan,
    check_risk_limits,
    compute_entry_stop_targets,
    compute_position_size,
)

BASE_CONFIG = RiskConfig()


def test_entry_stop_targets_derived_from_atr() -> None:
    entry_price, stop, targets = compute_entry_stop_targets(1000.0, 20.0, BASE_CONFIG)
    assert entry_price == 1000.0
    assert stop == 1000.0 - BASE_CONFIG.stop_atr_multiplier * 20.0
    assert len(targets) == 2
    assert targets[0] == 1000.0 + BASE_CONFIG.stop_atr_multiplier * 20.0  # 1R partial
    assert targets[1] == 1000.0 + BASE_CONFIG.target_atr_multiplier * 20.0  # full target
    assert targets[1] > targets[0]


def test_position_size_zero_on_invalid_stop() -> None:
    assert compute_position_size(100_000_000.0, 1000.0, 1000.0, BASE_CONFIG) == 0
    assert (
        compute_position_size(100_000_000.0, 1000.0, 1050.0, BASE_CONFIG) == 0
    )  # stop above entry


def test_position_size_zero_on_insufficient_capital() -> None:
    assert compute_position_size(1000.0, 1000.0, 970.0, BASE_CONFIG) == 0


def test_position_size_respects_minimum_lot_boundary() -> None:
    # risk budget affords well under one lot (100 shares) at this stop distance
    config = RiskConfig(risk_per_trade_pct=0.00001)
    qty = compute_position_size(100_000_000.0, 1000.0, 970.0, config)
    assert qty == 0


def test_position_size_deterministic_and_lot_aware() -> None:
    qty = compute_position_size(100_000_000.0, 1000.0, 970.0, BASE_CONFIG)
    assert qty % BASE_CONFIG.lot_size == 0
    assert qty > 0
    # same inputs, same output
    assert qty == compute_position_size(100_000_000.0, 1000.0, 970.0, BASE_CONFIG)


def test_position_size_lower_with_higher_fees() -> None:
    cheap = RiskConfig(fee_bps=0.0)
    expensive = RiskConfig(fee_bps=500.0)  # 5%, deliberately large to force a visible effect
    qty_cheap = compute_position_size(1_000_000.0, 1000.0, 970.0, cheap)
    qty_expensive = compute_position_size(1_000_000.0, 1000.0, 970.0, expensive)
    assert qty_expensive <= qty_cheap


def test_check_risk_limits_rejects_negative_risk_reward() -> None:
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[990.0],  # target below entry: negative R:R
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=[],
        config=BASE_CONFIG,
    )
    assert any("risk/reward" in r for r in reasons)


def test_check_risk_limits_rejects_low_liquidity() -> None:
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=1.0,
        existing_positions=[],
        config=BASE_CONFIG,
    )
    assert any("liquidity" in r for r in reasons)


def test_check_risk_limits_rejects_missing_liquidity_data() -> None:
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=None,
        existing_positions=[],
        config=BASE_CONFIG,
    )
    assert any("liquidity unknown" in r for r in reasons)


def test_check_risk_limits_rejects_position_over_max_allocation() -> None:
    config = RiskConfig(max_position_allocation_pct=0.01)
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=10_000,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=[],
        config=config,
    )
    assert any("position allocation" in r for r in reasons)


def test_check_risk_limits_rejects_portfolio_exposure_over_max() -> None:
    config = RiskConfig(max_portfolio_exposure_pct=0.10)
    existing = [PortfolioPosition(symbol="OTHER", sector=None, allocation_amount=95_000_000.0)]
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=existing,
        config=config,
    )
    assert any("portfolio exposure" in r for r in reasons)


def test_check_risk_limits_rejects_sector_concentration() -> None:
    config = RiskConfig(max_sector_exposure_pct=0.10)
    existing = [PortfolioPosition(symbol="OTHER", sector="Banking", allocation_amount=50_000_000.0)]
    reasons = check_risk_limits(
        symbol="TEST",
        sector="Banking",
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=1000,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=existing,
        config=config,
    )
    assert any("sector exposure" in r for r in reasons)


def test_check_risk_limits_allows_unrelated_sector() -> None:
    config = RiskConfig(max_sector_exposure_pct=0.10)
    existing = [
        PortfolioPosition(symbol="OTHER", sector="Consumer", allocation_amount=95_000_000.0)
    ]
    reasons = check_risk_limits(
        symbol="TEST",
        sector="Banking",
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=existing,
        config=config,
    )
    assert not any("sector exposure" in r for r in reasons)


def test_check_risk_limits_rejects_max_concurrent_positions() -> None:
    config = RiskConfig(max_concurrent_positions=1)
    existing = [PortfolioPosition(symbol="OTHER", sector=None, allocation_amount=1_000_000.0)]
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=existing,
        config=config,
    )
    assert any("concurrent positions" in r for r in reasons)


def test_check_risk_limits_reports_all_violations_not_just_first() -> None:
    config = RiskConfig(
        max_position_allocation_pct=0.001,
        max_portfolio_exposure_pct=0.001,
        min_risk_reward=100.0,
    )
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=1000,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=[],
        config=config,
    )
    assert len(reasons) >= 3


def test_check_risk_limits_boundary_risk_reward_exactly_at_minimum_passes() -> None:
    config = RiskConfig(min_risk_reward=2.0)
    # stop_distance=30, target_distance=60 -> R:R exactly 2.0
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1060.0],
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=[],
        config=config,
    )
    assert not any("risk/reward" in r for r in reasons)


def test_check_risk_limits_boundary_position_allocation_exactly_at_maximum_passes() -> None:
    config = RiskConfig(max_position_allocation_pct=0.20)
    # allocation_amount = 1000*20000 = 20,000,000 -> exactly 20% of 100,000,000
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=20_000,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=[],
        config=config,
    )
    assert not any("position allocation" in r for r in reasons)


def test_check_risk_limits_boundary_concurrent_positions_exactly_at_maximum_passes() -> None:
    config = RiskConfig(max_concurrent_positions=2)
    existing = [PortfolioPosition(symbol="OTHER", sector=None, allocation_amount=1_000_000.0)]
    reasons = check_risk_limits(
        symbol="NEW",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=existing,
        config=config,
    )
    assert not any("concurrent positions" in r for r in reasons)


def test_check_risk_limits_existing_position_for_same_symbol_not_double_counted() -> None:
    """Re-planning a symbol that already has an open position must count
    as one concurrent slot, not two — the new plan replaces/refreshes the
    same symbol's position rather than adding a second one."""
    config = RiskConfig(max_concurrent_positions=1)
    existing = [PortfolioPosition(symbol="TEST", sector=None, allocation_amount=1_000_000.0)]
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=existing,
        config=config,
    )
    assert not any("concurrent positions" in r for r in reasons)


def test_check_risk_limits_sector_none_on_new_symbol_skips_sector_check() -> None:
    config = RiskConfig(max_sector_exposure_pct=0.01)
    existing = [PortfolioPosition(symbol="OTHER", sector="Banking", allocation_amount=90_000_000.0)]
    reasons = check_risk_limits(
        symbol="TEST",
        sector=None,  # unknown sector for the candidate itself
        entry_price=1000.0,
        stop_price=970.0,
        target_prices=[1090.0],
        quantity=100,
        capital=100_000_000.0,
        volume_sma_20=1_000_000.0,
        existing_positions=existing,
        config=config,
    )
    assert not any("sector exposure" in r for r in reasons)


def test_build_trade_plan_valid_happy_path() -> None:
    # 2% ATR/price is a typical setup — default config is tuned so this
    # sizes to comfortably under max_position_allocation_pct.
    plan_input = TradePlanInput(
        symbol="BBCA",
        sector="Banking",
        close=1000.0,
        atr_14=20.0,
        volume_sma_20=1_000_000.0,
        capital=100_000_000.0,
    )
    result = build_trade_plan(plan_input, [], BASE_CONFIG)
    assert result.valid is True
    assert result.rejection_reasons == []
    assert result.quantity > 0
    assert result.stop_price is not None
    assert result.stop_price < result.entry_price  # type: ignore[operator]
    assert result.risk_reward_ratio is not None
    assert result.risk_reward_ratio >= BASE_CONFIG.min_risk_reward


def test_build_trade_plan_rejected_when_atr_missing() -> None:
    plan_input = TradePlanInput(
        symbol="BBCA",
        sector=None,
        close=1000.0,
        atr_14=None,
        volume_sma_20=1_000_000.0,
        capital=100_000_000.0,
    )
    result = build_trade_plan(plan_input, [], BASE_CONFIG)
    assert result.valid is False
    assert any("ATR" in r for r in result.rejection_reasons)


def test_build_trade_plan_rejected_when_atr_non_positive() -> None:
    plan_input = TradePlanInput(
        symbol="BBCA",
        sector=None,
        close=1000.0,
        atr_14=0.0,
        volume_sma_20=1_000_000.0,
        capital=100_000_000.0,
    )
    result = build_trade_plan(plan_input, [], BASE_CONFIG)
    assert result.valid is False


def test_build_trade_plan_deterministic_reproducible() -> None:
    plan_input = TradePlanInput(
        symbol="BBCA",
        sector="Banking",
        close=1000.0,
        atr_14=20.0,
        volume_sma_20=1_000_000.0,
        capital=100_000_000.0,
    )
    r1 = build_trade_plan(plan_input, [], BASE_CONFIG)
    r2 = build_trade_plan(plan_input, [], BASE_CONFIG)
    assert r1 == r2
