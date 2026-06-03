from datetime import datetime, timezone

from supabase import Client, create_client

from ai_portfolio_watchtower.holdings import holding_update_from_event
from ai_portfolio_watchtower.models import (
    HoldingSnapshot,
    HoldingStatus,
    PortfolioAction,
    PortfolioEvent,
    RawPost,
)
from ai_portfolio_watchtower.scoring import alert_window_start, multi_portfolio_window_start


class Storage:
    def __init__(self, supabase_url: str, supabase_service_key: str) -> None:
        self.client: Client = create_client(supabase_url, supabase_service_key)

    def insert_raw_post(self, post: RawPost) -> bool:
        payload = {
            "post_id": post.post_id,
            "source_account": post.source_account,
            "portfolio": post.portfolio,
            "post_url": str(post.post_url),
            "text": post.text,
            "created_at": post.created_at.isoformat(),
        }
        result = (
            self.client.table("raw_posts")
            .upsert(payload, on_conflict="post_id", ignore_duplicates=True)
            .execute()
        )
        return bool(result.data)

    def insert_event(self, event: PortfolioEvent) -> None:
        payload = _event_to_row(event)
        self.client.table("portfolio_events").insert(payload).execute()
        self.upsert_holdings_from_event(event)

    def recent_buys_by_ticker(self, now: datetime | None = None) -> dict[str, set[str]]:
        since = multi_portfolio_window_start(now).isoformat()
        result = (
            self.client.table("portfolio_events")
            .select("portfolio,tickers")
            .in_("action", [PortfolioAction.BUY.value, PortfolioAction.ADD.value])
            .gte("created_at", since)
            .execute()
        )
        grouped: dict[str, set[str]] = {}
        for row in result.data or []:
            for ticker in row.get("tickers") or []:
                grouped.setdefault(ticker, set()).add(row["portfolio"])
        return grouped

    def recently_alerted_tickers(self, now: datetime | None = None) -> set[str]:
        since = alert_window_start(now).isoformat()
        result = (
            self.client.table("portfolio_events")
            .select("tickers")
            .not_.is_("alerted_at", "null")
            .gte("alerted_at", since)
            .execute()
        )
        tickers: set[str] = set()
        for row in result.data or []:
            tickers.update(row.get("tickers") or [])
        return tickers

    def mark_alerted(self, post_id: str) -> None:
        self.client.table("portfolio_events").update(
            {"alerted_at": datetime.now(timezone.utc).isoformat()}
        ).eq("post_id", post_id).execute()

    def events_since(self, since: datetime) -> list[PortfolioEvent]:
        result = (
            self.client.table("portfolio_events")
            .select("*")
            .gte("created_at", since.isoformat())
            .order("created_at", desc=True)
            .execute()
        )
        return [_row_to_event(row) for row in result.data or []]

    def events_between(self, since: datetime, until: datetime) -> list[PortfolioEvent]:
        result = (
            self.client.table("portfolio_events")
            .select("*")
            .gte("created_at", since.isoformat())
            .lt("created_at", until.isoformat())
            .order("created_at", desc=False)
            .execute()
        )
        return [_row_to_event(row) for row in result.data or []]

    def get_holding(self, portfolio: str, ticker: str) -> HoldingSnapshot | None:
        result = (
            self.client.table("portfolio_holdings")
            .select("*")
            .eq("portfolio", portfolio)
            .eq("ticker", ticker)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return _row_to_holding(result.data[0])

    def list_holdings(self, status: HoldingStatus | None = None) -> list[HoldingSnapshot]:
        query = self.client.table("portfolio_holdings").select("*").order("last_seen_at", desc=True)
        if status:
            query = query.eq("status", status.value)
        result = query.execute()
        return [_row_to_holding(row) for row in result.data or []]

    def upsert_holdings_from_event(self, event: PortfolioEvent) -> int:
        updated = 0
        for ticker in event.tickers:
            existing = self.get_holding(event.portfolio, ticker)
            holding = holding_update_from_event(event, ticker, existing)
            if not holding:
                continue
            self.client.table("portfolio_holdings").upsert(
                _holding_to_row(holding),
                on_conflict="portfolio,ticker",
            ).execute()
            updated += 1
        return updated

    def rebuild_holdings(self) -> int:
        result = (
            self.client.table("portfolio_events")
            .select("*")
            .order("created_at", desc=False)
            .execute()
        )
        updated = 0
        for row in result.data or []:
            updated += self.upsert_holdings_from_event(_row_to_event(row))
        return updated

    def store_weekly_brief(self, since: datetime, until: datetime, markdown: str) -> None:
        payload = {
            "period_start": since.isoformat(),
            "period_end": until.isoformat(),
            "markdown": markdown,
        }
        self.client.table("weekly_briefs").insert(payload).execute()


def _event_to_row(event: PortfolioEvent) -> dict:
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
        "evidence_quotes": event.evidence_quotes,
        "confidence": event.confidence,
        "conviction_score": event.conviction_score,
        "scoring_reasons": event.scoring_reasons,
    }


def _row_to_event(row: dict) -> PortfolioEvent:
    return PortfolioEvent(
        portfolio=row["portfolio"],
        source_account=row["source_account"],
        post_id=row["post_id"],
        post_url=row["post_url"],
        created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
        tickers=row.get("tickers") or [],
        action=row["action"],
        event_type=row["event_type"],
        allocation_pct=float(row["allocation_pct"]) if row.get("allocation_pct") is not None else None,
        thesis_summary=row.get("thesis_summary") or "",
        evidence_quotes=row.get("evidence_quotes") or [],
        confidence=float(row["confidence"]),
        conviction_score=int(row.get("conviction_score") or 0),
        scoring_reasons=row.get("scoring_reasons") or [],
    )


def _holding_to_row(holding: HoldingSnapshot) -> dict:
    return {
        "portfolio": holding.portfolio,
        "ticker": holding.ticker,
        "status": holding.status.value,
        "source_account": holding.source_account,
        "first_seen_at": holding.first_seen_at.isoformat(),
        "last_seen_at": holding.last_seen_at.isoformat(),
        "last_post_id": holding.last_post_id,
        "last_post_url": str(holding.last_post_url),
        "last_action": holding.last_action.value,
        "latest_allocation_pct": holding.latest_allocation_pct,
        "latest_thesis": holding.latest_thesis,
        "confidence": holding.confidence,
    }


def _row_to_holding(row: dict) -> HoldingSnapshot:
    return HoldingSnapshot(
        portfolio=row["portfolio"],
        ticker=row["ticker"],
        status=row["status"],
        source_account=row["source_account"],
        first_seen_at=datetime.fromisoformat(row["first_seen_at"].replace("Z", "+00:00")),
        last_seen_at=datetime.fromisoformat(row["last_seen_at"].replace("Z", "+00:00")),
        last_post_id=row["last_post_id"],
        last_post_url=row["last_post_url"],
        last_action=row["last_action"],
        latest_allocation_pct=(
            float(row["latest_allocation_pct"])
            if row.get("latest_allocation_pct") is not None
            else None
        ),
        latest_thesis=row.get("latest_thesis") or "",
        confidence=float(row["confidence"]),
    )
