from collections import Counter
from datetime import datetime

import httpx

from ai_portfolio_watchtower.models import PortfolioAction, PortfolioEvent


class SlackNotifier:
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send_alert(self, event: PortfolioEvent) -> None:
        tickers = ", ".join(f"${ticker}" for ticker in event.tickers) or "No ticker parsed"
        text = (
            f"*AI Portfolio Alert* {tickers}\n"
            f"{event.portfolio} posted a `{event.action.value}` event "
            f"(score {event.conviction_score}).\n"
            f"{event.thesis_summary}\n"
            f"<{event.post_url}|Open post>"
        )
        self._post({"text": text})

    def send_digest(self, events: list[PortfolioEvent], generated_at: datetime) -> None:
        text = build_digest_text(events, generated_at)
        self._post({"text": text})

    def send_weekly_brief(self, markdown: str) -> None:
        self._post({"text": markdown})

    def _post(self, payload: dict) -> None:
        response = httpx.post(self.webhook_url, json=payload, timeout=30)
        response.raise_for_status()


def build_digest_text(events: list[PortfolioEvent], generated_at: datetime) -> str:
    if not events:
        return f"*AI Portfolio Daily Digest* ({generated_at.date()})\nNo new portfolio events found."

    buys_adds_sells = [
        event
        for event in events
        if event.action in {PortfolioAction.BUY, PortfolioAction.ADD, PortfolioAction.SELL, PortfolioAction.EXIT}
    ]
    high_conviction = sorted(events, key=lambda event: event.conviction_score, reverse=True)[:5]
    recurring = Counter(ticker for event in events for ticker in event.tickers).most_common(5)
    commentary = [
        event
        for event in events
        if event.action == PortfolioAction.COMMENTARY and event.conviction_score > -30
    ][:5]

    lines = [f"*AI Portfolio Daily Digest* ({generated_at.date()})"]
    lines.append("*Buys/adds/sells*")
    lines.extend(_event_line(event) for event in buys_adds_sells[:10])
    if not buys_adds_sells:
        lines.append("None.")

    lines.append("*Highest-conviction tickers*")
    lines.extend(_event_line(event) for event in high_conviction)

    lines.append("*Top recurring holdings*")
    lines.extend(f"${ticker}: {count} mentions" for ticker, count in recurring)
    if not recurring:
        lines.append("None.")

    lines.append("*Common themes*")
    lines.append(_summarize_themes(events))

    lines.append("*Important-looking commentary*")
    lines.extend(_event_line(event) for event in commentary)
    if not commentary:
        lines.append("None.")

    return "\n".join(lines)


def _event_line(event: PortfolioEvent) -> str:
    tickers = ", ".join(f"${ticker}" for ticker in event.tickers) or "No ticker"
    return f"- {tickers}: {event.action.value} by {event.portfolio}, score {event.conviction_score}"


def _summarize_themes(events: list[PortfolioEvent]) -> str:
    words = Counter()
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "because", "portfolio"}
    for event in events:
        for word in event.thesis_summary.lower().replace("/", " ").split():
            cleaned = word.strip(".,:;()[]{}!?$#").lower()
            if len(cleaned) > 4 and cleaned not in stop:
                words[cleaned] += 1
    common = [word for word, _ in words.most_common(8)]
    return ", ".join(common) if common else "No strong repeated themes parsed."
