import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

MAX_QUESTION_LENGTH = 4000


class AnalyzeRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    symbol: str | None = None


class AnalysisSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instrument_id: uuid.UUID | None
    provider: str
    model: str
    prompt_version: str
    question: str
    tool_calls: list[dict[str, object]]
    structured_data_snapshot: list[dict[str, object]]
    response: str
    guardrail_flags: list[str]
    created_at: datetime
