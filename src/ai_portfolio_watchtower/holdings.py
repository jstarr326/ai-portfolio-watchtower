from datetime import datetime

from ai_portfolio_watchtower.models import (
    HoldingSnapshot,
    HoldingStatus,
    PortfolioAction,
    PortfolioEvent,
)


TRACKED_HOLDING_ACTIONS = {
    PortfolioAction.BUY,
    PortfolioAction.ADD,
    PortfolioAction.HOLD,
    PortfolioAction.TRIM,
    PortfolioAction.SELL,
    PortfolioAction.EXIT,
    PortfolioAction.PERFORMANCE_UPDATE,
}


def holding_status_for_event(event: PortfolioEvent) -> HoldingStatus:
    if event.action in {PortfolioAction.SELL, PortfolioAction.EXIT}:
        return HoldingStatus.EXITED
    if event.action in {
        PortfolioAction.BUY,
        PortfolioAction.ADD,
        PortfolioAction.HOLD,
        PortfolioAction.TRIM,
        PortfolioAction.PERFORMANCE_UPDATE,
    }:
        return HoldingStatus.ACTIVE
    return HoldingStatus.UNKNOWN


def holding_update_from_event(
    event: PortfolioEvent,
    ticker: str,
    existing: HoldingSnapshot | None = None,
) -> HoldingSnapshot | None:
    if event.action not in TRACKED_HOLDING_ACTIONS:
        return None

    status = holding_status_for_event(event)
    first_seen_at = existing.first_seen_at if existing else event.created_at
    latest_allocation_pct = event.allocation_pct
    if latest_allocation_pct is None and existing:
        latest_allocation_pct = existing.latest_allocation_pct

    latest_thesis = event.thesis_summary or (existing.latest_thesis if existing else "")
    confidence = max(event.confidence, existing.confidence if existing else 0)

    return HoldingSnapshot(
        portfolio=event.portfolio,
        ticker=ticker,
        status=status,
        source_account=event.source_account,
        first_seen_at=first_seen_at,
        last_seen_at=max_datetime(existing.last_seen_at, event.created_at) if existing else event.created_at,
        last_post_id=event.post_id,
        last_post_url=event.post_url,
        last_action=event.action,
        latest_allocation_pct=latest_allocation_pct,
        latest_thesis=latest_thesis,
        confidence=confidence,
    )


def max_datetime(left: datetime, right: datetime) -> datetime:
    return left if left >= right else right
