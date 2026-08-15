from dataclasses import dataclass
from datetime import date

from app.db.enums import CorporateActionType
from app.db.models import CorporateAction, PriceBar

_SPLIT_TYPES = {CorporateActionType.SPLIT, CorporateActionType.REVERSE_SPLIT}


@dataclass(frozen=True, slots=True)
class AdjustedBar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


def compute_split_adjusted_bars(
    bars: list[PriceBar], corporate_actions: list[CorporateAction]
) -> list[AdjustedBar]:
    """Backward split-adjustment only.

    This does NOT produce a total-return (dividend-adjusted) series — that
    would require an adjustment methodology this phase has not defined.
    Raw bars remain the single source of truth; this is a deterministic
    read-time transform, not a persisted second table.
    """
    split_ratios = sorted(
        (
            (action.ex_date, float(action.ratio))
            for action in corporate_actions
            if action.action_type in _SPLIT_TYPES and action.ratio
        ),
        key=lambda item: item[0],
    )

    adjusted: list[AdjustedBar] = []
    for bar in sorted(bars, key=lambda b: b.trade_date):
        cumulative_factor = 1.0
        for ex_date, ratio in split_ratios:
            if bar.trade_date < ex_date:
                cumulative_factor *= ratio
        adjusted.append(
            AdjustedBar(
                trade_date=bar.trade_date,
                open=float(bar.open) / cumulative_factor,
                high=float(bar.high) / cumulative_factor,
                low=float(bar.low) / cumulative_factor,
                close=float(bar.close) / cumulative_factor,
                volume=int(bar.volume * cumulative_factor),
            )
        )
    return adjusted
