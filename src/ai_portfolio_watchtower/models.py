from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class PortfolioAccount(BaseModel):
    handle: str
    portfolio: str
    user_id: str | None = None


MONITORED_ACCOUNTS = [
    PortfolioAccount(handle="theaiportfolios", portfolio="Claude Portfolio"),
    PortfolioAccount(handle="grkportfolio", portfolio="Grok Portfolio"),
    PortfolioAccount(handle="aifinancelabs", portfolio="AI Finance Labs / DeepSeek commentary"),
]


class PortfolioAction(StrEnum):
    BUY = "buy"
    ADD = "add"
    HOLD = "hold"
    TRIM = "trim"
    SELL = "sell"
    EXIT = "exit"
    COMMENTARY = "commentary"
    PERFORMANCE_UPDATE = "performance_update"
    UNKNOWN = "unknown"


class EventType(StrEnum):
    NEW_POSITION = "new_position"
    ALLOCATION_CHANGE = "allocation_change"
    THESIS_UPDATE = "thesis_update"
    PERFORMANCE_UPDATE = "performance_update"
    COMMENTARY = "commentary"


class HoldingStatus(StrEnum):
    ACTIVE = "active"
    EXITED = "exited"
    UNKNOWN = "unknown"


class RawPost(BaseModel):
    post_id: str
    source_account: str
    portfolio: str
    post_url: HttpUrl
    text: str
    created_at: datetime


class PortfolioEvent(BaseModel):
    portfolio: str
    source_account: str
    post_id: str
    post_url: HttpUrl
    created_at: datetime
    tickers: list[str] = Field(default_factory=list)
    action: PortfolioAction
    event_type: EventType
    allocation_pct: float | None = None
    thesis_summary: str = ""
    evidence_quotes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    conviction_score: int = 0
    scoring_reasons: list[str] = Field(default_factory=list)

    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, tickers: list[str]) -> list[str]:
        cleaned = []
        for ticker in tickers:
            normalized = ticker.strip().upper().lstrip("$")
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned


class ExtractedEvent(BaseModel):
    tickers: list[str] = Field(default_factory=list)
    action: PortfolioAction
    event_type: EventType
    allocation_pct: float | None = None
    thesis_summary: str = ""
    evidence_quotes: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)

    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, tickers: list[str]) -> list[str]:
        cleaned = []
        for ticker in tickers:
            normalized = ticker.strip().upper().lstrip("$")
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned


class HoldingSnapshot(BaseModel):
    portfolio: str
    ticker: str
    status: HoldingStatus
    source_account: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_post_id: str
    last_post_url: HttpUrl
    last_action: PortfolioAction
    latest_allocation_pct: float | None = None
    latest_thesis: str = ""
    confidence: float = Field(ge=0, le=1)
