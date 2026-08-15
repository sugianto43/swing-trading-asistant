from datetime import date

from app.db.enums import DataQualityStatus
from app.marketdata.provider import RawBar, RawCalendarDay, RawCorporateAction

DEFAULT_MAX_STALENESS_DAYS = 5
ABNORMAL_VOLUME_MULTIPLIER = 20


def validate_bar(bar: RawBar, as_of: date, previous_bar: RawBar | None = None) -> list[str]:
    """Per-bar OHLC/volume/timestamp sanity checks.

    Returns a list of issue codes; an empty list means the bar is VALID.
    Invalid data is always marked, never silently dropped or accepted
    (MASTER-PRD FR-003).
    """
    issues: list[str] = []

    if bar.trade_date > as_of:
        # A bar dated after "now" cannot exist yet — this is the ingestion-time
        # guard against future-data leakage (MASTER-PRD §8, QUANT-TRADING-RULES).
        issues.append("FUTURE_DATED_BAR")

    if bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0:
        issues.append("NON_POSITIVE_PRICE")

    if bar.volume < 0:
        issues.append("NEGATIVE_VOLUME")

    if bar.high < max(bar.open, bar.close, bar.low):
        issues.append("HIGH_BELOW_OTHER_PRICES")

    if bar.low > min(bar.open, bar.close, bar.high):
        issues.append("LOW_ABOVE_OTHER_PRICES")

    if (
        previous_bar is not None
        and previous_bar.volume > 0
        and bar.volume > previous_bar.volume * ABNORMAL_VOLUME_MULTIPLIER
    ):
        issues.append("ABNORMAL_VOLUME")

    return issues


def classify_quality(issues: list[str]) -> DataQualityStatus:
    hard_failures = {
        "FUTURE_DATED_BAR",
        "NON_POSITIVE_PRICE",
        "NEGATIVE_VOLUME",
        "HIGH_BELOW_OTHER_PRICES",
        "LOW_ABOVE_OTHER_PRICES",
    }
    if any(issue in hard_failures for issue in issues):
        return DataQualityStatus.INVALID
    if issues:
        return DataQualityStatus.SUSPECT
    return DataQualityStatus.VALID


def find_duplicate_trade_dates(bars: list[RawBar]) -> dict[date, int]:
    """Detect a provider handing back more than one row for the same
    trade_date. Returns {date: occurrence_count} for dates seen more than
    once. Ingestion keeps the first occurrence deterministically and flags
    the run as PARTIAL when duplicates are found."""
    counts: dict[date, int] = {}
    for bar in bars:
        counts[bar.trade_date] = counts.get(bar.trade_date, 0) + 1
    return {trade_date: count for trade_date, count in counts.items() if count > 1}


def find_missing_sessions(bars: list[RawBar], calendar_days: list[RawCalendarDay]) -> list[date]:
    """Compare ingested trade dates against known trading days. Only flags
    gaps for calendar days explicitly marked as trading days — if the
    calendar has no data for a range, this is a no-op (documented
    limitation: the calendar itself is only as complete as what has been
    observed so far)."""
    ingested_dates = {bar.trade_date for bar in bars}
    return sorted(
        day.date for day in calendar_days if day.is_trading_day and day.date not in ingested_dates
    )


def validate_corporate_action(action: RawCorporateAction, as_of: date) -> list[str]:
    """Sanity/leakage checks for corporate actions, mirroring validate_bar.

    CorporateAction has no quality_status column, so callers skip (rather
    than persist-and-flag) records that fail these checks — see
    IngestionService.ingest_corporate_actions, which records skips in the
    run's notes instead of silently accepting them.
    """
    issues: list[str] = []

    if action.ex_date > as_of:
        issues.append("FUTURE_DATED_EX_DATE")

    if action.effective_date is not None and action.effective_date > as_of:
        issues.append("FUTURE_DATED_EFFECTIVE_DATE")

    if action.announced_at is not None and action.announced_at.date() > as_of:
        issues.append("FUTURE_ANNOUNCED_AT")

    if action.ratio is not None and action.ratio <= 0:
        issues.append("NON_POSITIVE_RATIO")

    if action.amount is not None and action.amount <= 0:
        issues.append("NON_POSITIVE_AMOUNT")

    return issues


def is_stale(
    latest_trade_date: date | None,
    as_of: date,
    max_staleness_days: int = DEFAULT_MAX_STALENESS_DAYS,
) -> bool:
    """Freshness check per MASTER-PRD §20: when data is stale, callers must
    not generate a fresh trading signal. This function only reports
    staleness; enforcement belongs to the scanner/signal phases."""
    if latest_trade_date is None:
        return True
    return (as_of - latest_trade_date).days > max_staleness_days
