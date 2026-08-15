from enum import StrEnum


class ListingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELISTED = "DELISTED"


class DataQualityStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    STALE = "STALE"
    SUSPECT = "SUSPECT"


class CorporateActionType(StrEnum):
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    CASH_DIVIDEND = "CASH_DIVIDEND"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    BONUS_ISSUE = "BONUS_ISSUE"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    OTHER = "OTHER"


class IngestionStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class SetupType(StrEnum):
    BREAKOUT = "BREAKOUT"
    PULLBACK_CONTINUATION = "PULLBACK_CONTINUATION"
    MOMENTUM_CONTINUATION = "MOMENTUM_CONTINUATION"
    MA_RECLAIM = "MA_RECLAIM"
    VOLATILITY_SQUEEZE = "VOLATILITY_SQUEEZE"


class ScanStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class BacktestStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ExecutionModel(StrEnum):
    NEXT_OPEN = "NEXT_OPEN"


class ExitReason(StrEnum):
    STOP = "STOP"
    TARGET = "TARGET"
    TIME = "TIME"
    END_OF_BACKTEST = "END_OF_BACKTEST"


class TradePlanStatus(StrEnum):
    VALID = "VALID"
    REJECTED = "REJECTED"
