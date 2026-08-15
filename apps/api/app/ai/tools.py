"""Typed domain tools (MASTER-PRD §13). Every tool is a plain, read-only
function over the existing Phase 2-7 domain models — no new business
logic, no writes, no raw SQL exposed to the model. A tool that has
nothing to report returns `{"status": "DATA_UNAVAILABLE", "reason": ...}`
rather than fabricating a value (AI-GUARDRAILS.md "Unsupported Data").

get_market_regime is backed by Phase 9's breadth/regime computation
(a proxy for the locally-ingested universe, not the whole IDX market —
see app/intelligence/breadth_engine.py). get_market_events is backed by
Phase 9's canonicalized corporate-action events (splits, dividends,
rights issues, etc.) — it still does NOT cover news/earnings-calendar/
macro/regulatory events, since no viable free data source exists for
those on IDX tickers (documented gap, not silently invented — see
DECISION-LOG.md and app/intelligence/event_mapper.py).

There is deliberately no tool here that writes anything, places an
order, or runs arbitrary SQL — the guardrail against those is structural
(the capability doesn't exist), not just a prompt instruction.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import ToolSpec
from app.db.enums import PositionStatus
from app.db.models import (
    BacktestMetrics,
    BacktestRun,
    IndicatorSnapshot,
    Instrument,
    Position,
    PriceBar,
    ScanCandidate,
    TradePlan,
)
from app.intelligence.service import MarketIntelligenceService
from app.marketdata.validation import is_stale
from app.positions.performance_service import PerformanceService


def _unavailable(reason: str) -> dict[str, object]:
    return {"status": "DATA_UNAVAILABLE", "reason": reason}


def _ok(data: dict[str, object]) -> dict[str, object]:
    # "status" is the envelope's own key (OK/DATA_UNAVAILABLE) — a domain
    # field also named "status" would silently overwrite it via dict
    # unpacking, so callers must use a qualified name instead
    # (plan_status, backtest_status, position_status, ...).
    if "status" in data:
        raise ValueError(f"tool result data must not use the reserved key 'status': {data!r}")
    return {"status": "OK", **data}


def get_stock_snapshot(session: Session, symbol: str) -> dict[str, object]:
    instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol.upper()))
    if instrument is None:
        return _unavailable(f"instrument not seeded: {symbol!r}")

    latest_bar = session.scalar(
        select(PriceBar)
        .where(PriceBar.instrument_id == instrument.id)
        .order_by(PriceBar.trade_date.desc())
        .limit(1)
    )
    if latest_bar is None:
        return _unavailable(f"no price data ingested for {symbol!r}")

    stale = is_stale(latest_bar.trade_date, datetime.now(UTC).date())
    return _ok(
        {
            "symbol": instrument.symbol,
            "company_name": instrument.company_name,
            "sector": instrument.sector,
            "as_of_date": latest_bar.trade_date.isoformat(),
            "close": float(latest_bar.close),
            "volume": latest_bar.volume,
            "is_stale": stale,
        }
    )


def get_technical_snapshot(session: Session, symbol: str) -> dict[str, object]:
    instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol.upper()))
    if instrument is None:
        return _unavailable(f"instrument not seeded: {symbol!r}")

    snapshot = session.scalar(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.instrument_id == instrument.id)
        .order_by(IndicatorSnapshot.trade_date.desc())
        .limit(1)
    )
    if snapshot is None:
        return _unavailable(f"no indicator snapshot computed for {symbol!r}")

    def _f(value: float | None) -> float | None:
        return None if value is None else float(value)

    return _ok(
        {
            "symbol": instrument.symbol,
            "as_of_date": snapshot.trade_date.isoformat(),
            "sma_20": _f(snapshot.sma_20),
            "sma_50": _f(snapshot.sma_50),
            "sma_200": _f(snapshot.sma_200),
            "rsi_14": _f(snapshot.rsi_14),
            "atr_14": _f(snapshot.atr_14),
            "macd": _f(snapshot.macd),
            "relative_volume": _f(snapshot.relative_volume),
        }
    )


def get_setup(session: Session, symbol: str) -> dict[str, object]:
    instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol.upper()))
    if instrument is None:
        return _unavailable(f"instrument not seeded: {symbol!r}")

    candidates = session.scalars(
        select(ScanCandidate)
        .where(ScanCandidate.instrument_id == instrument.id)
        .order_by(ScanCandidate.scan_date.desc())
        .limit(5)
    ).all()
    if not candidates:
        return _unavailable(f"no qualifying setup found for {symbol!r}")

    return _ok(
        {
            "symbol": instrument.symbol,
            "setups": [
                {
                    "scan_date": c.scan_date.isoformat(),
                    "setup_type": c.setup_type.value,
                    "composite_score": float(c.composite_score),
                    "qualifying_conditions": c.qualifying_conditions,
                    "invalidation_conditions": c.invalidation_conditions,
                }
                for c in candidates
            ],
        }
    )


def get_trade_plan(session: Session, symbol: str) -> dict[str, object]:
    instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol.upper()))
    if instrument is None:
        return _unavailable(f"instrument not seeded: {symbol!r}")

    plan = session.scalar(
        select(TradePlan)
        .where(TradePlan.instrument_id == instrument.id)
        .order_by(TradePlan.plan_date.desc())
        .limit(1)
    )
    if plan is None:
        return _unavailable(f"no trade plan exists for {symbol!r}")

    return _ok(
        {
            "symbol": instrument.symbol,
            "plan_date": plan.plan_date.isoformat(),
            "setup_type": plan.setup_type.value,
            "plan_status": plan.status.value,
            "rejection_reasons": plan.rejection_reasons,
            "entry_price": float(plan.entry_price) if plan.entry_price is not None else None,
            "stop_price": float(plan.stop_price) if plan.stop_price is not None else None,
            "target_prices": [float(t) for t in plan.target_prices],
            "quantity": plan.quantity,
            "risk_reward_ratio": float(plan.risk_reward_ratio)
            if plan.risk_reward_ratio is not None
            else None,
        }
    )


def get_backtest(session: Session, backtest_id: str) -> dict[str, object]:
    try:
        run_id = uuid.UUID(backtest_id)
    except ValueError:
        return _unavailable(f"invalid backtest_id: {backtest_id!r}")

    run = session.scalar(select(BacktestRun).where(BacktestRun.id == run_id))
    if run is None:
        return _unavailable(f"no backtest found with id {backtest_id!r}")

    metrics = session.scalar(
        select(BacktestMetrics).where(BacktestMetrics.backtest_run_id == run.id)
    )
    return _ok(
        {
            "backtest_id": str(run.id),
            "setup_type": run.setup_type.value,
            "backtest_status": run.status.value,
            "start_date": run.start_date.isoformat(),
            "end_date": run.end_date.isoformat(),
            "total_return_pct": float(metrics.total_return_pct) if metrics else None,
            "win_rate_pct": float(metrics.win_rate_pct) if metrics else None,
            "max_drawdown_pct": float(metrics.max_drawdown_pct) if metrics else None,
            "trade_count": metrics.trade_count if metrics else None,
        }
    )


def get_position(session: Session, symbol: str) -> dict[str, object]:
    instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol.upper()))
    if instrument is None:
        return _unavailable(f"instrument not seeded: {symbol!r}")

    position = session.scalar(
        select(Position).where(
            Position.instrument_id == instrument.id,
            Position.status.in_(
                (PositionStatus.PLANNED, PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED)
            ),
        )
    )
    if position is None:
        return _unavailable(f"no open position for {symbol!r}")

    return _ok(
        {
            "symbol": instrument.symbol,
            "position_status": position.status.value,
            "quantity_open": position.quantity_open,
            "avg_entry_price": float(position.avg_entry_price)
            if position.avg_entry_price is not None
            else None,
            "realized_pnl": float(position.realized_pnl),
            "opened_at": position.opened_at.isoformat() if position.opened_at else None,
        }
    )


def get_portfolio_risk(session: Session) -> dict[str, object]:
    summary = PerformanceService(session).summary()
    return _ok(
        {
            "closed_position_count": summary.closed_position_count,
            "win_rate_pct": summary.win_rate_pct,
            "total_realized_pnl": summary.total_realized_pnl,
            "unrealized_pnl": summary.unrealized_pnl,
            "exposure": summary.exposure,
            "max_drawdown_pct": summary.max_drawdown_pct,
        }
    )


def get_market_regime(session: Session, symbol: str | None = None) -> dict[str, object]:
    snapshot = MarketIntelligenceService(session).get_breadth_snapshot()
    if snapshot is None:
        return _unavailable("no breadth/regime snapshot has been computed yet")
    return _ok(
        {
            "as_of": snapshot.as_of.isoformat(),
            "regime": snapshot.regime.value,
            "universe_size": snapshot.universe_size,
            "pct_above_sma50": float(snapshot.pct_above_sma50)
            if snapshot.pct_above_sma50 is not None
            else None,
            "advancers": snapshot.advancers,
            "decliners": snapshot.decliners,
            "note": "proxy for the locally-ingested universe, not the whole IDX market",
        }
    )


def get_market_events(session: Session, symbol: str) -> dict[str, object]:
    events = MarketIntelligenceService(session).get_events(symbol=symbol, as_of=None)
    if not events:
        return _unavailable(f"no known corporate-action events for {symbol!r}")
    return _ok(
        {
            "symbol": symbol.upper(),
            "events": [
                {
                    "event_type": e.event_type,
                    "announced_at": e.announced_at.isoformat(),
                    "availability_is_estimated": e.availability_is_estimated,
                    "ex_date": e.ex_date.isoformat(),
                    "description": e.description,
                }
                for e in events[:10]
            ],
            "note": "corporate-action events only — news/earnings-calendar/macro/regulatory "
            "events are not available yet (no viable free data source for IDX tickers)",
        }
    )


TOOL_REGISTRY: dict[str, Callable[..., dict[str, object]]] = {
    "get_stock_snapshot": get_stock_snapshot,
    "get_technical_snapshot": get_technical_snapshot,
    "get_setup": get_setup,
    "get_trade_plan": get_trade_plan,
    "get_backtest": get_backtest,
    "get_position": get_position,
    "get_portfolio_risk": get_portfolio_risk,
    "get_market_regime": get_market_regime,
    "get_market_events": get_market_events,
}

TOOL_SPECS = [
    ToolSpec(
        name="get_stock_snapshot",
        description="Latest price snapshot for a symbol (close, volume, staleness).",
        parameters_schema={
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    ),
    ToolSpec(
        name="get_technical_snapshot",
        description="Latest computed technical indicators for a symbol.",
        parameters_schema={
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    ),
    ToolSpec(
        name="get_setup",
        description="Recent qualifying swing setups (scanner candidates) for a symbol.",
        parameters_schema={
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    ),
    ToolSpec(
        name="get_trade_plan",
        description="Most recent risk-engine trade plan for a symbol.",
        parameters_schema={
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    ),
    ToolSpec(
        name="get_backtest",
        description="Backtest run summary and metrics by backtest id.",
        parameters_schema={
            "type": "object",
            "properties": {"backtest_id": {"type": "string"}},
            "required": ["backtest_id"],
        },
    ),
    ToolSpec(
        name="get_position",
        description="Current open/planned position for a symbol, if any.",
        parameters_schema={
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    ),
    ToolSpec(
        name="get_portfolio_risk",
        description="Portfolio-level performance/exposure summary across all positions.",
        parameters_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="get_market_regime",
        description="Breadth/regime context for the locally-ingested universe (not the whole "
        "market), if a snapshot has been computed.",
        parameters_schema={
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
        },
    ),
    ToolSpec(
        name="get_market_events",
        description="Known corporate-action events (splits, dividends, rights issues, etc.) "
        "for a symbol. Does not include news/earnings-calendar/macro/regulatory events.",
        parameters_schema={
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    ),
]
