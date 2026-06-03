import typer
from dotenv import load_dotenv
from openai import RateLimitError

from ai_portfolio_watchtower.config import get_settings
from ai_portfolio_watchtower.extraction import OpenAIExtractor
from ai_portfolio_watchtower.notifier import SlackNotifier
from ai_portfolio_watchtower.service import WatchtowerService
from ai_portfolio_watchtower.storage import Storage
from ai_portfolio_watchtower.weekly_analysis import WeeklyAnalyst
from ai_portfolio_watchtower.x_client import XApiPaymentRequiredError, XClient

app = typer.Typer(help="Monitor AI portfolio accounts and send alerts.")


@app.command()
def poll() -> None:
    """Poll X, extract events, store them, and send Slack alerts."""
    service = _build_service()
    try:
        count = service.poll(max_results=get_settings().poll_max_results)
    except XApiPaymentRequiredError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except RateLimitError as exc:
        raise typer.BadParameter(
            "OpenAI returned insufficient quota or a rate limit error. Check that your OpenAI "
            "project has billing credits, your monthly spend limit has room, and the selected "
            "model is available to this API key."
        ) from exc
    typer.echo(f"Processed {count} new posts.")


@app.command()
def digest() -> None:
    """Send a daily Slack digest for events from the last 24 hours."""
    service = _build_service()
    count = service.send_daily_digest()
    typer.echo(f"Included {count} events in the digest.")


@app.command("rebuild-holdings")
def rebuild_holdings() -> None:
    """Rebuild inferred holdings from stored portfolio events."""
    service = _build_service()
    count = service.rebuild_holdings()
    typer.echo(f"Applied {count} holding updates.")


@app.command("weekly-brief")
def weekly_brief(
    days: int = typer.Option(7, min=1, max=31, help="Number of trailing days to analyze."),
    send: bool = typer.Option(True, help="Send the generated brief to Slack."),
) -> None:
    """Generate a weekly portfolio intelligence brief."""
    service = _build_service()
    try:
        markdown = service.send_weekly_brief(days=days, send=send)
    except RateLimitError as exc:
        raise typer.BadParameter(
            "OpenAI returned insufficient quota or a rate limit error while generating the "
            "weekly brief. Check billing, limits, and model access."
        ) from exc
    typer.echo(markdown)


def _build_service() -> WatchtowerService:
    load_dotenv()
    settings = get_settings()
    _require_settings(settings)
    notifier = SlackNotifier(settings.slack_webhook_url) if settings.slack_webhook_url else None
    return WatchtowerService(
        x_client=XClient(settings.x_api_bearer_token),
        storage=Storage(settings.supabase_url, settings.supabase_service_key),
        extractor=OpenAIExtractor(settings.openai_api_key, settings.openai_model),
        analyst=WeeklyAnalyst(settings.openai_api_key, settings.openai_model),
        notifier=notifier,
    )


def _require_settings(settings) -> None:
    missing = [
        name
        for name, value in {
            "X_API_BEARER_TOKEN": settings.x_api_bearer_token,
            "OPENAI_API_KEY": settings.openai_api_key,
            "SUPABASE_URL": settings.supabase_url,
            "SUPABASE_SERVICE_KEY": settings.supabase_service_key,
        }.items()
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise typer.BadParameter(f"Missing required environment values in .env: {joined}")


if __name__ == "__main__":
    app()
