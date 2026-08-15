import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.db.enums import AlertType


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_type: AlertType
    instrument_id: uuid.UUID
    trigger_date: date
    message: str
    details: dict[str, object]
    created_at: datetime
