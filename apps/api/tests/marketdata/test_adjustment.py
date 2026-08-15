import uuid
from datetime import date

from app.db.enums import CorporateActionType
from app.db.models import CorporateAction, PriceBar
from app.marketdata.adjustment import compute_split_adjusted_bars


def _bar(trade_date: date, close: float) -> PriceBar:
    return PriceBar(
        instrument_id=uuid.uuid4(),
        trade_date=trade_date,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000,
        source="fixture",
        source_symbol="BBCA.JK",
    )


def _split(ex_date: date, ratio: float) -> CorporateAction:
    return CorporateAction(
        instrument_id=uuid.uuid4(),
        action_type=CorporateActionType.SPLIT,
        ex_date=ex_date,
        source="fixture",
        source_symbol="BBCA.JK",
        ratio=ratio,
    )


def test_no_corporate_actions_leaves_prices_unchanged() -> None:
    bars = [_bar(date(2024, 1, 2), 1000.0)]
    adjusted = compute_split_adjusted_bars(bars, [])
    assert adjusted[0].close == 1000.0


def test_split_adjusts_prices_before_ex_date() -> None:
    bars = [
        _bar(date(2024, 1, 2), 2000.0),  # before split
        _bar(date(2024, 2, 2), 1000.0),  # after split (post-split price)
    ]
    actions = [_split(date(2024, 2, 1), ratio=2.0)]

    adjusted = compute_split_adjusted_bars(bars, actions)

    assert adjusted[0].close == 1000.0  # 2000 / 2.0
    assert adjusted[1].close == 1000.0  # unaffected, already after ex_date


def test_split_volume_adjusted_inversely() -> None:
    bars = [_bar(date(2024, 1, 2), 2000.0)]
    bars[0].volume = 1000
    actions = [_split(date(2024, 2, 1), ratio=2.0)]

    adjusted = compute_split_adjusted_bars(bars, actions)

    assert adjusted[0].volume == 2000


def test_dividends_do_not_affect_split_adjustment() -> None:
    bars = [_bar(date(2024, 1, 2), 1000.0)]
    dividend = CorporateAction(
        instrument_id=uuid.uuid4(),
        action_type=CorporateActionType.CASH_DIVIDEND,
        ex_date=date(2024, 1, 5),
        source="fixture",
        source_symbol="BBCA.JK",
        amount=50.0,
    )

    adjusted = compute_split_adjusted_bars(bars, [dividend])

    assert adjusted[0].close == 1000.0
