from datetime import datetime, timezone

from ai_portfolio_watchtower.models import EventType, PortfolioAction, PortfolioEvent
from ai_portfolio_watchtower.scoring import ScoringContext, score_event, should_alert


def make_event(**overrides) -> PortfolioEvent:
    data = {
        "portfolio": "Claude Portfolio",
        "source_account": "theaiportfolios",
        "post_id": "123",
        "post_url": "https://x.com/theaiportfolios/status/123",
        "created_at": datetime.now(timezone.utc),
        "tickers": ["NVDA"],
        "action": PortfolioAction.BUY,
        "event_type": EventType.NEW_POSITION,
        "allocation_pct": 10,
        "thesis_summary": (
            "New position because data center demand, accelerator supply, and inference growth "
            "support durable revenue acceleration."
        ),
        "evidence_quotes": ["NVDA is now a top holding at 10% allocation"],
        "confidence": 0.9,
    }
    data.update(overrides)
    return PortfolioEvent(**data)


def test_score_event_applies_conviction_rules() -> None:
    event = make_event()
    scored = score_event(
        event,
        ScoringContext(recent_buys_by_ticker={"NVDA": {"Grok Portfolio"}}),
    )

    assert scored.conviction_score == 115
    assert "new position +30" in scored.scoring_reasons
    assert "allocation >=10% +30" in scored.scoring_reasons
    assert "largest/top holding +20" in scored.scoring_reasons
    assert "detailed thesis +10" in scored.scoring_reasons
    assert "NVDA bought by multiple portfolios within 14 days +25" in scored.scoring_reasons


def test_commentary_only_penalty() -> None:
    event = make_event(
        action=PortfolioAction.COMMENTARY,
        event_type=EventType.COMMENTARY,
        allocation_pct=None,
        thesis_summary="Interesting valuation commentary, but no portfolio decision.",
    )

    assert score_event(event).conviction_score == -30


def test_should_alert_requires_buy_add_score_and_no_recent_duplicate() -> None:
    assert should_alert(make_event(conviction_score=75), set())
    assert not should_alert(make_event(conviction_score=74), set())
    assert not should_alert(make_event(conviction_score=90), {"NVDA"})
    assert not should_alert(
        make_event(action=PortfolioAction.SELL, conviction_score=100),
        set(),
    )
