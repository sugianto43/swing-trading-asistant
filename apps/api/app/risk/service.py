import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.enums import SetupType, TradePlanStatus
from app.db.models import (
    CorporateAction,
    IndicatorSnapshot,
    Instrument,
    PriceBar,
    ScanCandidate,
    TradePlan,
)
from app.indicators.versioning import INDICATOR_VERSION
from app.risk.config import RiskConfig
from app.risk.engine import PortfolioPosition, TradePlanInput, TradePlanResult, build_trade_plan
from app.scanner.context import build_scan_points
from app.scanner.scoring_config import SCORE_VERSION

DEFAULT_LOOKBACK_DAYS = 400  # enough history to join the plan_date's indicator snapshot


class RiskService:
    """Builds and idempotently persists a TradePlan for one instrument's
    qualifying scan candidate on one date. A trade plan, unlike a
    BacktestRun, is data to keep in sync (upsert by natural key), not an
    experiment — re-running for the same (instrument, plan_date,
    setup_type, risk_version) updates the existing row."""

    def __init__(self, session: Session):
        self.session = session

    def build_plan(
        self,
        symbol: str,
        setup_type: SetupType,
        plan_date: date,
        capital: float,
        existing_positions: list[PortfolioPosition] | None = None,
        config: RiskConfig | None = None,
    ) -> TradePlan:
        config = config or RiskConfig()
        existing_positions = existing_positions or []

        instrument = self.session.scalar(select(Instrument).where(Instrument.symbol == symbol))
        if instrument is None:
            raise ValueError(f"instrument not seeded: {symbol!r}")

        candidate = self.session.scalar(
            select(ScanCandidate).where(
                ScanCandidate.instrument_id == instrument.id,
                ScanCandidate.scan_date == plan_date,
                ScanCandidate.setup_type == setup_type,
                ScanCandidate.score_version == SCORE_VERSION,
            )
        )

        lookback_start = plan_date - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        bars = self.session.scalars(
            select(PriceBar).where(
                PriceBar.instrument_id == instrument.id,
                PriceBar.trade_date >= lookback_start,
                PriceBar.trade_date <= plan_date,
            )
        ).all()
        corporate_actions = self.session.scalars(
            select(CorporateAction).where(
                CorporateAction.instrument_id == instrument.id,
                CorporateAction.ex_date <= plan_date,
            )
        ).all()
        indicator_snapshots = self.session.scalars(
            select(IndicatorSnapshot).where(
                IndicatorSnapshot.instrument_id == instrument.id,
                IndicatorSnapshot.indicator_version == INDICATOR_VERSION,
                IndicatorSnapshot.trade_date >= lookback_start,
                IndicatorSnapshot.trade_date <= plan_date,
            )
        ).all()
        points = build_scan_points(list(bars), list(corporate_actions), list(indicator_snapshots))
        point = next((p for p in points if p.trade_date == plan_date), None)

        assumptions = {"capital": capital, "config": _config_snapshot(config)}

        if candidate is None or point is None:
            reasons = []
            if candidate is None:
                reasons.append("no qualifying scan candidate for this instrument/setup/date")
            if point is None:
                reasons.append("no price/indicator data available for this date")
            result = TradePlanResult(valid=False, rejection_reasons=reasons)
            return self._persist(
                instrument.id,
                None,
                setup_type,
                plan_date,
                config,
                result,
                score_version=None,
                indicator_version=None,
                assumptions=assumptions,
                invalidation_conditions=[],
            )

        plan_input = TradePlanInput(
            symbol=symbol,
            sector=instrument.sector,
            close=point.close,
            atr_14=point.atr_14,
            volume_sma_20=point.volume_sma_20,
            capital=capital,
        )
        result = build_trade_plan(plan_input, existing_positions, config)

        return self._persist(
            instrument.id,
            candidate.id,
            setup_type,
            plan_date,
            config,
            result,
            score_version=SCORE_VERSION,
            indicator_version=INDICATOR_VERSION,
            assumptions=assumptions,
            invalidation_conditions=candidate.invalidation_conditions,
        )

    def _persist(
        self,
        instrument_id: uuid.UUID,
        scan_candidate_id: uuid.UUID | None,
        setup_type: SetupType,
        plan_date: date,
        config: RiskConfig,
        result: TradePlanResult,
        *,
        score_version: str | None,
        indicator_version: str | None,
        assumptions: dict[str, object],
        invalidation_conditions: list[str],
    ) -> TradePlan:
        existing = self.session.scalar(
            select(TradePlan).where(
                TradePlan.instrument_id == instrument_id,
                TradePlan.plan_date == plan_date,
                TradePlan.setup_type == setup_type,
                TradePlan.risk_version == config.risk_version,
            )
        )
        values = {
            "scan_candidate_id": scan_candidate_id,
            "score_version": score_version,
            "indicator_version": indicator_version,
            "status": TradePlanStatus.VALID if result.valid else TradePlanStatus.REJECTED,
            "rejection_reasons": result.rejection_reasons,
            "entry_price": result.entry_price,
            "stop_price": result.stop_price,
            "target_prices": result.target_prices,
            "quantity": result.quantity,
            "allocation_amount": result.allocation_amount,
            "allocation_pct": result.allocation_pct,
            "max_loss_amount": result.max_loss_amount,
            "risk_reward_ratio": result.risk_reward_ratio,
            "assumptions": assumptions,
            "invalidation_conditions": invalidation_conditions,
        }
        if existing is None:
            plan = TradePlan(
                instrument_id=instrument_id,
                plan_date=plan_date,
                setup_type=setup_type,
                risk_version=config.risk_version,
                **values,
            )
            self.session.add(plan)
            try:
                self.session.commit()
            except IntegrityError:
                # a concurrent request for the same natural key committed
                # first (e.g. a double-submitted POST) — the unique
                # constraint caught it, so fall back to updating that
                # row instead of surfacing a raw 500.
                self.session.rollback()
                existing = self.session.scalar(
                    select(TradePlan).where(
                        TradePlan.instrument_id == instrument_id,
                        TradePlan.plan_date == plan_date,
                        TradePlan.setup_type == setup_type,
                        TradePlan.risk_version == config.risk_version,
                    )
                )
                if existing is None:
                    # the constraint violation guarantees a matching row
                    # exists; a miss here would mean the schema's unique
                    # constraint no longer matches this natural key.
                    raise
                for field, value in values.items():
                    setattr(existing, field, value)
                self.session.commit()
                plan = existing
        else:
            for field, value in values.items():
                setattr(existing, field, value)
            plan = existing
            self.session.commit()
        self.session.refresh(plan)
        return plan


def _config_snapshot(config: RiskConfig) -> dict[str, object]:
    return {
        "risk_version": config.risk_version,
        "risk_per_trade_pct": config.risk_per_trade_pct,
        "max_portfolio_exposure_pct": config.max_portfolio_exposure_pct,
        "max_position_allocation_pct": config.max_position_allocation_pct,
        "max_sector_exposure_pct": config.max_sector_exposure_pct,
        "min_risk_reward": config.min_risk_reward,
        "min_liquidity_volume": config.min_liquidity_volume,
        "max_concurrent_positions": config.max_concurrent_positions,
        "fee_bps": config.fee_bps,
        "slippage_bps": config.slippage_bps,
        "stop_atr_multiplier": config.stop_atr_multiplier,
        "target_atr_multiplier": config.target_atr_multiplier,
        "lot_size": config.lot_size,
    }
