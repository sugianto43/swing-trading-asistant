from datetime import date

from app.db.models import PriceBar


def dedupe_price_bars_by_trade_date(bars: list[PriceBar]) -> list[PriceBar]:
    """Two PriceBar rows can legitimately coexist for the same
    instrument+date if ingested from different sources (Phase 2's unique
    constraint is instrument_id+trade_date+source, not just trade_date —
    e.g. a symbol re-ingested from a different provider). Any downstream
    per-date calculation (indicators, scanner) cannot tolerate a repeated
    data point, so pick one bar per date deterministically: the most
    recently ingested one wins."""
    by_date: dict[date, PriceBar] = {}
    for bar in bars:
        existing = by_date.get(bar.trade_date)
        if existing is None or bar.ingested_at >= existing.ingested_at:
            by_date[bar.trade_date] = bar
    return list(by_date.values())
