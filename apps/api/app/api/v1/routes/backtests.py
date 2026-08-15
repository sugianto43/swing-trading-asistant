import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.backtests import (
    BacktestMetricsOut,
    BacktestRunDetailOut,
    BacktestRunOut,
    BacktestTradeOut,
    EquityPointOut,
)
from app.db.models import (
    BacktestEquityPoint,
    BacktestMetrics,
    BacktestRun,
    BacktestTrade,
    Instrument,
)
from app.db.session import get_db

router = APIRouter()


def _get_run_or_404(db: Session, backtest_run_id: uuid.UUID) -> BacktestRun:
    run = db.scalar(select(BacktestRun).where(BacktestRun.id == backtest_run_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest run not found")
    return run


@router.get("/backtests", response_model=Page[BacktestRunOut])
def list_backtest_runs(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[BacktestRunOut]:
    query = select(BacktestRun)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(BacktestRun.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[BacktestRunOut](
        items=[BacktestRunOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/backtests/{backtest_run_id}", response_model=BacktestRunDetailOut)
def get_backtest_run(
    backtest_run_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> BacktestRunDetailOut:
    run = _get_run_or_404(db, backtest_run_id)
    metrics_row = db.scalar(
        select(BacktestMetrics).where(BacktestMetrics.backtest_run_id == run.id)
    )
    metrics = BacktestMetricsOut.model_validate(metrics_row) if metrics_row else None
    return BacktestRunDetailOut(**BacktestRunOut.model_validate(run).model_dump(), metrics=metrics)


@router.get("/backtests/{backtest_run_id}/trades", response_model=Page[BacktestTradeOut])
def list_backtest_trades(
    backtest_run_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[BacktestTradeOut]:
    _get_run_or_404(db, backtest_run_id)
    query = (
        select(BacktestTrade, Instrument.symbol)
        .join(Instrument, BacktestTrade.instrument_id == Instrument.id)
        .where(BacktestTrade.backtest_run_id == backtest_run_id)
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(BacktestTrade.entry_date).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [
        BacktestTradeOut(
            symbol=symbol,
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
        for trade, symbol in rows
    ]
    return Page[BacktestTradeOut](items=items, page=page, page_size=page_size, total=total)


@router.get("/backtests/{backtest_run_id}/equity-curve", response_model=Page[EquityPointOut])
def list_backtest_equity_curve(
    backtest_run_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[EquityPointOut]:
    _get_run_or_404(db, backtest_run_id)
    query = select(BacktestEquityPoint).where(
        BacktestEquityPoint.backtest_run_id == backtest_run_id
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(BacktestEquityPoint.trade_date)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[EquityPointOut](
        items=[EquityPointOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
