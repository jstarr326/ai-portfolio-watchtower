from datetime import datetime, timedelta, timezone

from ai_portfolio_watchtower.holdings import holding_status_for_event, holding_update_from_event
from ai_portfolio_watchtower.models import HoldingStatus, PortfolioAction, PortfolioEvent


def make_event(**overrides) -> PortfolioEvent:
    data = {
        "portfolio": "Claude Portfolio",
        "source_account": "theaiportfolios",
        "post_id": "123",
        "post_url": "https://x.com/theaiportfolios/status/123",
        "created_at": datetime(2026, 6, 3, tzinfo=timezone.utc),
        "tickers": ["AVGO"],
        "action": PortfolioAction.BUY,
        "event_type": "new_position",
        "allocation_pct": 8,
        "thesis_summary": "Opening a new position based on AI infrastructure demand.",
        "evidence_quotes": ["Bought AVGO at 8% allocation"],
        "confidence": 0.8,
        "conviction_score": 80,
    }
    data.update(overrides)
    return PortfolioEvent(**data)


def test_holding_status_for_event() -> None:
    assert holding_status_for_event(make_event(action=PortfolioAction.BUY)) == HoldingStatus.ACTIVE
    assert holding_status_for_event(make_event(action=PortfolioAction.TRIM)) == HoldingStatus.ACTIVE
    assert holding_status_for_event(make_event(action=PortfolioAction.EXIT)) == HoldingStatus.EXITED
    assert (
        holding_status_for_event(make_event(action=PortfolioAction.COMMENTARY))
        == HoldingStatus.UNKNOWN
    )


def test_holding_update_from_new_buy() -> None:
    event = make_event()

    holding = holding_update_from_event(event, "AVGO")

    assert holding is not None
    assert holding.ticker == "AVGO"
    assert holding.status == HoldingStatus.ACTIVE
    assert holding.first_seen_at == event.created_at
    assert holding.last_action == PortfolioAction.BUY
    assert holding.latest_allocation_pct == 8


def test_holding_update_preserves_existing_allocation_when_missing() -> None:
    first = holding_update_from_event(make_event(), "AVGO")
    later = make_event(
        post_id="456",
        action=PortfolioAction.HOLD,
        event_type="performance_update",
        allocation_pct=None,
        created_at=datetime(2026, 6, 10, tzinfo=timezone.utc),
        thesis_summary="AVGO remains an existing holding after earnings.",
        confidence=0.6,
    )

    updated = holding_update_from_event(later, "AVGO", first)

    assert updated is not None
    assert updated.first_seen_at == first.first_seen_at
    assert updated.last_seen_at == later.created_at
    assert updated.latest_allocation_pct == 8
    assert updated.latest_thesis == "AVGO remains an existing holding after earnings."
    assert updated.confidence == 0.8


def test_holding_update_marks_exit() -> None:
    first = holding_update_from_event(make_event(), "AVGO")
    exit_event = make_event(
        post_id="789",
        action=PortfolioAction.EXIT,
        event_type="allocation_change",
        allocation_pct=0,
        created_at=datetime(2026, 6, 3, tzinfo=timezone.utc) + timedelta(days=3),
    )

    updated = holding_update_from_event(exit_event, "AVGO", first)

    assert updated is not None
    assert updated.status == HoldingStatus.EXITED
    assert updated.last_action == PortfolioAction.EXIT


def test_holding_update_ignores_commentary() -> None:
    event = make_event(action=PortfolioAction.COMMENTARY, event_type="commentary")

    assert holding_update_from_event(event, "AVGO") is None
