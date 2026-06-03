# ai-portfolio-watchtower

Monitor a fixed set of AI-managed portfolio accounts on X, extract structured portfolio events with an LLM, score conviction deterministically, store everything in Supabase, and send Slack alerts.

This is monitoring and research-support software. It does not execute trades and its output is not financial advice.

## Slack first

Slack incoming webhooks are the simplest v1 delivery mechanism. Slack's current Free plan includes up to 10 apps/integrations, and Slack's developer docs describe incoming webhooks as app-based URLs that post into a selected channel. That should be enough for a personal workspace unless you exceed Slack's free-plan app/history limits.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Create the Supabase tables:

```bash
psql "$DATABASE_URL" -f supabase/schema.sql
```

Set these environment variables:

```bash
X_API_BEARER_TOKEN=...
OPENAI_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
SLACK_WEBHOOK_URL=...
```

## Commands

Poll X, store posts, extract events, score, and alert:

```bash
watchtower poll
```

Generate and send a daily Slack digest:

```bash
watchtower digest
```

Rebuild inferred holdings from stored events:

```bash
watchtower rebuild-holdings
```

Generate a weekly portfolio intelligence brief without sending to Slack:

```bash
watchtower weekly-brief --no-send
```

Generate and send the weekly brief to Slack:

```bash
watchtower weekly-brief
```

Run tests:

```bash
pytest
```

## Monitored Accounts

- `@theaiportfolios`: Claude Portfolio
- `@grkportfolio`: Grok Portfolio
- `@aifinancelabs`: AI Finance Labs / DeepSeek commentary
