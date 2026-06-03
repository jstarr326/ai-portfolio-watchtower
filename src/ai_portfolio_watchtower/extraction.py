import json
import re
from html import unescape
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from ai_portfolio_watchtower.models import ExtractedEvent, RawPost


class Extractor(Protocol):
    def extract(self, post: RawPost) -> list[ExtractedEvent]:
        ...


class ExtractionResult(BaseModel):
    events: list[ExtractedEvent] = Field(default_factory=list)


class OpenAIExtractor:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract(self, post: RawPost) -> list[ExtractedEvent]:
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract portfolio events from social posts. Return JSON only with an "
                        "`events` array. Use action values: buy, add, hold, trim, sell, exit, "
                        "commentary, performance_update, unknown. Use event_type values: "
                        "new_position, allocation_change, thesis_update, performance_update, "
                        "commentary. Evidence quotes must be short direct snippets from the post. "
                        "Every event must include confidence as a number from 0 to 1. "
                        "If the post is market commentary without a portfolio decision, return one "
                        "commentary event when it still seems important, otherwise return an empty "
                        "events array."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Portfolio: {post.portfolio}\n"
                        f"Source account: @{post.source_account}\n"
                        f"Post ID: {post.post_id}\n"
                        f"Created at: {post.created_at.isoformat()}\n"
                        f"Post text:\n{post.text}"
                    ),
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        result = parse_extraction_json(content)
        return [apply_post_fallbacks(event, post) for event in result.events]


def parse_extraction_json(content: str) -> ExtractionResult:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM extraction did not return valid JSON") from exc

    try:
        return ExtractionResult.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"LLM extraction returned invalid event data: {exc}") from exc


def apply_post_fallbacks(event: ExtractedEvent, post: RawPost) -> ExtractedEvent:
    text = _clean_post_text(post.text)
    updates = {}
    if not event.tickers:
        updates["tickers"] = _candidate_tickers(text)
    if not event.thesis_summary:
        updates["thesis_summary"] = _fallback_summary(text)
    if not event.evidence_quotes and text:
        updates["evidence_quotes"] = [text[:220]]
    return event.model_copy(update=updates)


def _clean_post_text(text: str) -> str:
    cleaned = unescape(text)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _candidate_tickers(text: str) -> list[str]:
    stop_words = {
        "AI",
        "API",
        "CEO",
        "CFO",
        "CPI",
        "EPS",
        "ETF",
        "FOMC",
        "GDP",
        "IPO",
        "LLM",
        "PM",
        "DR",
        "SEC",
        "TL",
        "USA",
        "USD",
    }
    company_tickers = {
        "broadcom": "AVGO",
        "innodata": "INOD",
        "micron": "MU",
        "microsoft": "MSFT",
        "nvidia": "NVDA",
        "qualcomm": "QCOM",
    }
    tickers: list[str] = []

    lower_text = text.lower()
    for company, ticker in company_tickers.items():
        if company in lower_text and ticker not in tickers:
            tickers.append(ticker)

    for match in re.finditer(r"\$([A-Za-z]{1,5})\b", text):
        ticker = match.group(1).upper()
        if ticker not in tickers and ticker not in stop_words:
            tickers.append(ticker)

    for match in re.finditer(r"\b[A-Z]{2,5}\b", text):
        ticker = match.group(0)
        if ticker not in tickers and ticker not in stop_words:
            tickers.append(ticker)

    return tickers[:5]


def _fallback_summary(text: str) -> str:
    if not text:
        return ""
    sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    if len(sentence) <= 240:
        return sentence
    return sentence[:237].rstrip() + "..."
