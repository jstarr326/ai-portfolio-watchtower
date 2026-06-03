from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ai_portfolio_watchtower.models import EventType, PortfolioAction, PortfolioEvent


@dataclass
class ScoringContext:
    recent_buys_by_ticker: dict[str, set[str]] = field(default_factory=dict)


def score_event(event: PortfolioEvent, context: ScoringContext | None = None) -> PortfolioEvent:
    score = 0
    reasons: list[str] = []
    is_commentary = (
        event.action == PortfolioAction.COMMENTARY or event.event_type == EventType.COMMENTARY
    )

    if event.event_type == EventType.NEW_POSITION:
        score += 30
        reasons.append("new position +30")

    if event.action == PortfolioAction.ADD:
        score += 20
        reasons.append("add +20")

    if event.allocation_pct is not None:
        if event.allocation_pct >= 10:
            score += 30
            reasons.append("allocation >=10% +30")
        elif event.allocation_pct >= 5:
            score += 20
            reasons.append("allocation >=5% +20")

    thesis_text = event.thesis_summary.lower()
    quote_text = " ".join(event.evidence_quotes).lower()
    combined = f"{thesis_text} {quote_text}"
    if not is_commentary and (
        "largest" in combined or "top holding" in combined or "top position" in combined
    ):
        score += 20
        reasons.append("largest/top holding +20")

    if not is_commentary and _has_detailed_thesis(event):
        score += 10
        reasons.append("detailed thesis +10")

    if context:
        for ticker in event.tickers:
            portfolios = context.recent_buys_by_ticker.get(ticker, set())
            other_portfolios = portfolios - {event.portfolio}
            if other_portfolios and event.action in {PortfolioAction.BUY, PortfolioAction.ADD}:
                score += 25
                reasons.append(f"{ticker} bought by multiple portfolios within 14 days +25")
                break

    if is_commentary:
        score -= 30
        reasons.append("commentary only -30")

    return event.model_copy(update={"conviction_score": score, "scoring_reasons": reasons})


def should_alert(event: PortfolioEvent, recently_alerted_tickers: set[str]) -> bool:
    if event.action not in {PortfolioAction.BUY, PortfolioAction.ADD}:
        return False
    if event.conviction_score < 75:
        return False
    return not any(ticker in recently_alerted_tickers for ticker in event.tickers)


def alert_window_start(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    return current - timedelta(days=7)


def multi_portfolio_window_start(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    return current - timedelta(days=14)


def _has_detailed_thesis(event: PortfolioEvent) -> bool:
    if len(event.thesis_summary.split()) >= 15:
        return True
    return len(event.evidence_quotes) >= 2 and sum(len(q.split()) for q in event.evidence_quotes) >= 18
