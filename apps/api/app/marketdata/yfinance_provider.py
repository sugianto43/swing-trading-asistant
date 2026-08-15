from datetime import UTC, date, datetime

import pandas as pd

from app.db.enums import CorporateActionType
from app.marketdata.provider import (
    ProviderError,
    RawBar,
    RawCalendarDay,
    RawCorporateAction,
    RawInstrument,
)
from app.marketdata.seed import load_seed_instruments

YFINANCE_SOURCE = "yfinance"
CANONICAL_TIMEZONE = "Asia/Jakarta"  # docs/data/DATA-VENDOR-REQUIREMENTS.md §7


def _to_canonical_trade_date(timestamp: pd.Timestamp) -> date:
    """Extract the exchange-local session date.

    yfinance returns its history index already localized to the exchange's
    own timezone (Asia/Jakarta for .JK tickers) rather than UTC. This makes
    that assumption explicit and converts defensively if a tz-aware
    timestamp in a different zone is ever encountered, instead of silently
    trusting whatever `.date()` on the raw timestamp happens to return.
    """
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(CANONICAL_TIMEZONE)
    return date(timestamp.year, timestamp.month, timestamp.day)


class YfinanceProvider:
    """Adapter over the unofficial `yfinance` package.

    Personal/non-commercial use only (docs/data/VENDOR-EVALUATION.md).
    yfinance exposes no IDX instrument-master or trading-calendar API, so
    those are backed by the local seed / observed bars respectively — see
    get_instruments() and get_calendar() docstrings below.
    """

    name = YFINANCE_SOURCE

    def get_instruments(self) -> list[RawInstrument]:
        # yfinance has no listing endpoint; the universe is the local IDX
        # seed (see app/marketdata/seed.py), not vendor-sourced data.
        return load_seed_instruments()

    def get_daily_bars(self, source_symbol: str, start: date, end: date) -> list[RawBar]:
        import yfinance as yf

        try:
            history = yf.Ticker(source_symbol).history(
                start=start, end=end, interval="1d", auto_adjust=False, actions=False
            )
        except Exception as exc:  # yfinance has no stable exception hierarchy to narrow to
            raise ProviderError(
                f"yfinance history fetch failed for {source_symbol}: {exc}"
            ) from exc

        bars: list[RawBar] = []
        previous_close: float | None = None
        for trade_timestamp, row in history.iterrows():
            trade_date = _to_canonical_trade_date(trade_timestamp)
            close = float(row["Close"])
            bars.append(
                RawBar(
                    source_symbol=source_symbol,
                    trade_date=trade_date,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=close,
                    volume=int(row["Volume"]),
                    source=YFINANCE_SOURCE,
                    previous_close=previous_close,
                    change=None if previous_close is None else close - previous_close,
                    change_percent=(
                        None
                        if not previous_close
                        else (close - previous_close) / previous_close * 100
                    ),
                )
            )
            previous_close = close
        return bars

    def get_corporate_actions(
        self, source_symbol: str, start: date, end: date
    ) -> list[RawCorporateAction]:
        import yfinance as yf

        try:
            actions = yf.Ticker(source_symbol).actions
        except Exception as exc:
            raise ProviderError(
                f"yfinance corporate actions fetch failed for {source_symbol}: {exc}"
            ) from exc

        if actions is None or actions.empty:
            return []

        results: list[RawCorporateAction] = []
        for action_timestamp, row in actions.iterrows():
            ex_date = _to_canonical_trade_date(action_timestamp)
            if not (start <= ex_date <= end):
                continue

            dividend = float(row.get("Dividends", 0) or 0)
            if dividend > 0:
                results.append(
                    RawCorporateAction(
                        source_symbol=source_symbol,
                        action_type=CorporateActionType.CASH_DIVIDEND,
                        ex_date=ex_date,
                        source=YFINANCE_SOURCE,
                        amount=dividend,
                    )
                )

            split_ratio = float(row.get("Stock Splits", 0) or 0)
            if split_ratio > 0:
                action_type = (
                    CorporateActionType.SPLIT
                    if split_ratio >= 1
                    else CorporateActionType.REVERSE_SPLIT
                )
                results.append(
                    RawCorporateAction(
                        source_symbol=source_symbol,
                        action_type=action_type,
                        ex_date=ex_date,
                        source=YFINANCE_SOURCE,
                        ratio=split_ratio,
                    )
                )
        return results

    def get_calendar(self, start: date, end: date) -> list[RawCalendarDay]:
        # yfinance has no holiday/trading-calendar endpoint. Callers should
        # rely on the calendar rows derived from observed bars during
        # ingestion instead (documented limitation, not a silent gap).
        return []

    def get_latest_quote(self, source_symbol: str) -> RawBar | None:
        today = datetime.now(UTC).date()
        recent_bars = self.get_daily_bars(
            source_symbol, start=date.fromordinal(today.toordinal() - 7), end=today
        )
        if not recent_bars:
            return None
        return max(recent_bars, key=lambda bar: bar.trade_date)
