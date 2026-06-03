import json
from datetime import datetime

from openai import OpenAI

from ai_portfolio_watchtower.models import HoldingSnapshot, PortfolioEvent


class WeeklyAnalyst:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def build_brief(
        self,
        events: list[PortfolioEvent],
        holdings: list[HoldingSnapshot],
        since: datetime,
        until: datetime,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write concise portfolio-monitoring research briefs. This is not "
                        "financial advice. Do not tell the user what to buy now. Summarize what "
                        "the monitored AI portfolios appear to have done, what changed, what is "
                        "watchlist-worthy, what remains unconfirmed, and what risks or missing "
                        "context matter. Be direct when there were no fresh buy/add signals. "
                        "Separate decisions first reported during the period from older decisions "
                        "that were merely mentioned again in performance commentary. Avoid phrases "
                        "like 'warranted' or 'should buy'; use neutral research language."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "period_start": since.isoformat(),
                            "period_end": until.isoformat(),
                            "portfolio_events": [_event_payload(event) for event in events],
                            "inferred_holdings": [
                                _holding_payload(holding) for holding in holdings
                            ],
                            "required_sections": [
                                "Executive readout",
                                "Fresh portfolio decisions this period",
                                "Historical decisions mentioned this period",
                                "Watchlist candidates, not buy recommendations",
                                "Current inferred holdings",
                                "Recurring themes",
                                "Risks and missing context",
                                "No-action notes",
                            ],
                        },
                        default=str,
                    ),
                },
            ],
        )
        return response.choices[0].message.content or "No weekly brief generated."


def _event_payload(event: PortfolioEvent) -> dict:
    return {
        "portfolio": event.portfolio,
        "source_account": event.source_account,
        "post_id": event.post_id,
        "post_url": str(event.post_url),
        "created_at": event.created_at.isoformat(),
        "tickers": event.tickers,
        "action": event.action.value,
        "event_type": event.event_type.value,
        "allocation_pct": event.allocation_pct,
        "thesis_summary": event.thesis_summary,
        "confidence": event.confidence,
        "conviction_score": event.conviction_score,
        "scoring_reasons": event.scoring_reasons,
    }


def _holding_payload(holding: HoldingSnapshot) -> dict:
    return {
        "portfolio": holding.portfolio,
        "ticker": holding.ticker,
        "status": holding.status.value,
        "source_account": holding.source_account,
        "first_seen_at": holding.first_seen_at.isoformat(),
        "last_seen_at": holding.last_seen_at.isoformat(),
        "last_action": holding.last_action.value,
        "latest_allocation_pct": holding.latest_allocation_pct,
        "latest_thesis": holding.latest_thesis,
        "confidence": holding.confidence,
    }
