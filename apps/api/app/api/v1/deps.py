from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Instrument


def get_instrument_or_404(db: Session, symbol: str) -> Instrument:
    instrument = db.scalar(select(Instrument).where(Instrument.symbol == symbol.upper()))
    if instrument is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="instrument not found")
    return instrument
