import pytest

from datetime import datetime, timezone

from ai_portfolio_watchtower.extraction import apply_post_fallbacks, parse_extraction_json
from ai_portfolio_watchtower.models import EventType, PortfolioAction
from ai_portfolio_watchtower.models import ExtractedEvent, RawPost


def test_parse_extraction_json_normalizes_tickers() -> None:
    result = parse_extraction_json(
        """
        {
          "events": [
            {
              "tickers": ["$nvda", "NVDA", "msft"],
              "action": "buy",
              "event_type": "new_position",
              "allocation_pct": 8,
              "thesis_summary": "Opening a new AI infrastructure basket position.",
              "evidence_quotes": ["Bought $NVDA at 8% allocation"],
              "confidence": 0.92
            }
          ]
        }
        """
    )

    event = result.events[0]
    assert event.tickers == ["NVDA", "MSFT"]
    assert event.action == PortfolioAction.BUY
    assert event.event_type == EventType.NEW_POSITION


def test_parse_extraction_json_rejects_invalid_json() -> None:
    with pytest.raises(ValueError):
        parse_extraction_json("not json")


def test_parse_extraction_json_defaults_missing_confidence() -> None:
    result = parse_extraction_json(
        """
        {
          "events": [
            {
              "tickers": ["TSLA"],
              "action": "commentary",
              "event_type": "commentary",
              "thesis_summary": "Important AI market commentary without a portfolio action.",
              "evidence_quotes": ["AI capex could become a systemic risk."]
            }
          ]
        }
        """
    )

    assert result.events[0].confidence == 0.5


def test_apply_post_fallbacks_adds_ticker_summary_and_evidence() -> None:
    event = ExtractedEvent(
        action="hold",
        event_type="performance_update",
        confidence=0.6,
    )
    post = RawPost(
        post_id="2062220942072586571",
        source_account="theaiportfolios",
        portfolio="Claude Portfolio",
        post_url="https://x.com/theaiportfolios/status/2062220942072586571",
        created_at=datetime.now(timezone.utc),
        text=(
            "AVGO is one of Claude's holdings, up about 48% since entry. "
            "It reports earnings today after the close. https://t.co/example"
        ),
    )

    updated = apply_post_fallbacks(event, post)

    assert updated.tickers == ["AVGO"]
    assert updated.thesis_summary == "AVGO is one of Claude's holdings, up about 48% since entry."
    assert updated.evidence_quotes == [
        "AVGO is one of Claude's holdings, up about 48% since entry. "
        "It reports earnings today after the close."
    ]


def test_apply_post_fallbacks_maps_company_names_and_ignores_tldr() -> None:
    event = ExtractedEvent(
        action="performance_update",
        event_type="performance_update",
        confidence=0.6,
    )
    post = RawPost(
        post_id="206",
        source_account="grkportfolio",
        portfolio="Grok Portfolio",
        post_url="https://x.com/grkportfolio/status/206",
        created_at=datetime.now(timezone.utc),
        text="TL;DR: Grok bought Broadcom on April 7 and it is up about 39% since.",
    )

    updated = apply_post_fallbacks(event, post)

    assert updated.tickers == ["AVGO"]
