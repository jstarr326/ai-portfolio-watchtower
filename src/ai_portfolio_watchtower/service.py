from datetime import datetime, timedelta, timezone

from ai_portfolio_watchtower.extraction import Extractor
from ai_portfolio_watchtower.models import HoldingStatus, PortfolioEvent
from ai_portfolio_watchtower.notifier import SlackNotifier
from ai_portfolio_watchtower.scoring import ScoringContext, score_event, should_alert
from ai_portfolio_watchtower.storage import Storage
from ai_portfolio_watchtower.weekly_analysis import WeeklyAnalyst
from ai_portfolio_watchtower.x_client import XClient, default_accounts


class WatchtowerService:
    def __init__(
        self,
        x_client: XClient,
        storage: Storage,
        extractor: Extractor,
        analyst: WeeklyAnalyst | None = None,
        notifier: SlackNotifier | None = None,
    ) -> None:
        self.x_client = x_client
        self.storage = storage
        self.extractor = extractor
        self.analyst = analyst
        self.notifier = notifier

    def poll(self, max_results: int) -> int:
        processed = 0
        context = ScoringContext(recent_buys_by_ticker=self.storage.recent_buys_by_ticker())
        recently_alerted = self.storage.recently_alerted_tickers()

        for account in default_accounts():
            for post in self.x_client.fetch_posts(account, max_results=max_results):
                inserted = self.storage.insert_raw_post(post)
                if not inserted:
                    continue

                extracted_events = self.extractor.extract(post)
                for extracted in extracted_events:
                    event = PortfolioEvent(
                        portfolio=post.portfolio,
                        source_account=post.source_account,
                        post_id=post.post_id,
                        post_url=post.post_url,
                        created_at=post.created_at,
                        tickers=extracted.tickers,
                        action=extracted.action,
                        event_type=extracted.event_type,
                        allocation_pct=extracted.allocation_pct,
                        thesis_summary=extracted.thesis_summary,
                        evidence_quotes=extracted.evidence_quotes,
                        confidence=extracted.confidence,
                    )
                    scored = score_event(event, context)
                    self.storage.insert_event(scored)
                    if self.notifier and should_alert(scored, recently_alerted):
                        self.notifier.send_alert(scored)
                        self.storage.mark_alerted(scored.post_id)
                        recently_alerted.update(scored.tickers)
                processed += 1

        return processed

    def send_daily_digest(self) -> int:
        since = datetime.now(timezone.utc) - timedelta(days=1)
        events = self.storage.events_since(since)
        if self.notifier:
            self.notifier.send_digest(events, datetime.now(timezone.utc))
        return len(events)

    def rebuild_holdings(self) -> int:
        return self.storage.rebuild_holdings()

    def send_weekly_brief(self, days: int = 7, send: bool = True) -> str:
        if not self.analyst:
            raise RuntimeError("Weekly analyst is not configured.")

        until = datetime.now(timezone.utc)
        since = until - timedelta(days=days)
        events = self.storage.events_between(since, until)
        holdings = self.storage.list_holdings(HoldingStatus.ACTIVE)
        markdown = self.analyst.build_brief(events, holdings, since, until)
        self.storage.store_weekly_brief(since, until, markdown)
        if send and self.notifier:
            self.notifier.send_weekly_brief(markdown)
        return markdown
