import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtesting.config import BacktestConfig
from app.backtesting.metrics import compute_metrics
from app.backtesting.simulator import EntrySignal, run_simulation
from app.backtesting.universe import is_active_as_of
from app.db.enums import BacktestStatus
from app.db.models import (
    BacktestEquityPoint,
    BacktestMetrics,
    BacktestRun,
    BacktestTrade,
    CorporateAction,
    IndicatorSnapshot,
    Instrument,
    InstrumentStatusHistory,
    PriceBar,
    ScanCandidate,
)
from app.indicators.versioning import INDICATOR_VERSION
from app.scanner.context import ScanPoint, build_scan_points
from app.scanner.scoring_config import SCORE_VERSION


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BacktestService:
    """Orchestrates fetch -> simulate -> persist for one backtest
    experiment. Each invocation creates a NEW BacktestRun row — a
    backtest is an experiment to compare, not data to keep in sync
    (unlike ingestion/indicators/scanner, which upsert)."""

    def __init__(self, session: Session):
        self.session = session

    def run(self, config: BacktestConfig) -> BacktestRun:
        run = BacktestRun(
            strategy_version=config.strategy_version,
            setup_type=config.setup_type,
            min_score=config.min_score,
            start_date=config.start_date,
            end_date=config.end_date,
            initial_capital=config.initial_capital,
            risk_per_trade_pct=config.risk_per_trade_pct,
            max_concurrent_positions=config.max_concurrent_positions,
            fee_bps=config.fee_bps,
            slippage_bps=config.slippage_bps,
            stop_atr_multiplier=config.stop_atr_multiplier,
            target_atr_multiplier=config.target_atr_multiplier,
            max_holding_days=config.max_holding_days,
            execution_model=config.execution_model,
            indicator_version=INDICATOR_VERSION,
            score_version=SCORE_VERSION,
            status=BacktestStatus.RUNNING,
        )
        self.session.add(run)
        self.session.commit()

        try:
            instruments = self.session.scalars(select(Instrument)).all()

            points_by_instrument: dict[uuid.UUID, list[ScanPoint]] = {}
            instruments_by_id: dict[uuid.UUID, Instrument] = {}
            status_history_by_instrument: dict[uuid.UUID, list[InstrumentStatusHistory]] = {}
            for instrument in instruments:
                instruments_by_id[instrument.id] = instrument
                bars = self.session.scalars(
                    select(PriceBar).where(
                        PriceBar.instrument_id == instrument.id,
                        PriceBar.trade_date <= config.end_date,
                    )
                ).all()
                corporate_actions = self.session.scalars(
                    select(CorporateAction).where(
                        CorporateAction.instrument_id == instrument.id,
                        CorporateAction.ex_date <= config.end_date,
                    )
                ).all()
                indicator_snapshots = self.session.scalars(
                    select(IndicatorSnapshot).where(
                        IndicatorSnapshot.instrument_id == instrument.id,
                        IndicatorSnapshot.indicator_version == INDICATOR_VERSION,
                        IndicatorSnapshot.trade_date <= config.end_date,
                    )
                ).all()
                points_by_instrument[instrument.id] = build_scan_points(
                    list(bars), list(corporate_actions), list(indicator_snapshots)
                )
                status_history_by_instrument[instrument.id] = list(
                    self.session.scalars(
                        select(InstrumentStatusHistory).where(
                            InstrumentStatusHistory.instrument_id == instrument.id
                        )
                    ).all()
                )

            candidates = self.session.scalars(
                select(ScanCandidate).where(
                    ScanCandidate.setup_type == config.setup_type,
                    ScanCandidate.score_version == SCORE_VERSION,
                    ScanCandidate.composite_score >= config.min_score,
                    ScanCandidate.scan_date >= config.start_date,
                    ScanCandidate.scan_date <= config.end_date,
                )
            ).all()
            signals = [
                EntrySignal(
                    instrument_id=c.instrument_id,
                    setup_type=c.setup_type,
                    signal_date=c.scan_date,
                    score=float(c.composite_score),
                )
                for c in candidates
            ]

            def is_eligible(instrument_id: uuid.UUID, as_of: date) -> bool:
                instrument = instruments_by_id.get(instrument_id)
                if instrument is None:
                    return False
                return is_active_as_of(
                    instrument, status_history_by_instrument.get(instrument_id, []), as_of
                )

            result = run_simulation(config, points_by_instrument, signals, is_eligible)

            for trade in result.trades:
                self.session.add(
                    BacktestTrade(
                        backtest_run_id=run.id,
                        instrument_id=trade.instrument_id,
                        setup_type=trade.setup_type,
                        signal_date=trade.signal_date,
                        entry_date=trade.entry_date,
                        entry_price=trade.entry_price,
                        stop_price=trade.stop_price,
                        target_price=trade.target_price,
                        exit_date=trade.exit_date,
                        exit_price=trade.exit_price,
                        exit_reason=trade.exit_reason,
                        quantity=trade.quantity,
                        fees_paid=trade.fees_paid,
                        slippage_cost=trade.slippage_cost,
                        pnl=trade.pnl,
                        r_multiple=trade.r_multiple,
                        holding_days=trade.holding_days,
                    )
                )
            for trade_date, equity_value in result.equity_curve:
                self.session.add(
                    BacktestEquityPoint(
                        backtest_run_id=run.id, trade_date=trade_date, equity_value=equity_value
                    )
                )

            metrics = compute_metrics(
                result.trades,
                result.equity_curve,
                config.initial_capital,
                config.start_date,
                config.end_date,
            )
            self.session.add(
                BacktestMetrics(
                    backtest_run_id=run.id,
                    total_return_pct=metrics.total_return_pct,
                    cagr_pct=metrics.cagr_pct,
                    win_rate_pct=metrics.win_rate_pct,
                    avg_win=metrics.avg_win,
                    avg_loss=metrics.avg_loss,
                    expectancy=metrics.expectancy,
                    profit_factor=metrics.profit_factor,
                    max_drawdown_pct=metrics.max_drawdown_pct,
                    sharpe_ratio=metrics.sharpe_ratio,
                    trade_count=metrics.trade_count,
                    avg_holding_days=metrics.avg_holding_days,
                    r_distribution=metrics.r_distribution,
                )
            )

            run.status = BacktestStatus.SUCCEEDED
            run.finished_at = _utcnow()
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            run.status = BacktestStatus.FAILED
            run.finished_at = _utcnow()
            run.error_message = str(exc)
            self.session.add(run)
            self.session.commit()
            raise

        return run
