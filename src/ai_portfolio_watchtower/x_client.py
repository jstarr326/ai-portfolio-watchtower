from datetime import datetime

import httpx

from ai_portfolio_watchtower.models import MONITORED_ACCOUNTS, PortfolioAccount, RawPost


class XApiPaymentRequiredError(RuntimeError):
    """Raised when X rejects an API request because credits or billing access are missing."""


class XClient:
    base_url = "https://api.x.com/2"

    def __init__(self, bearer_token: str) -> None:
        self.headers = {"Authorization": f"Bearer {bearer_token}"}

    def fetch_posts(self, account: PortfolioAccount, max_results: int = 10) -> list[RawPost]:
        user_id = account.user_id or self._lookup_user_id(account.handle)
        params = {
            "max_results": max(5, min(max_results, 100)),
            "tweet.fields": "created_at",
            "exclude": "retweets,replies",
        }
        url = f"{self.base_url}/users/{user_id}/tweets"
        response = httpx.get(url, headers=self.headers, params=params, timeout=30)
        _raise_for_x_status(response)
        payload = response.json()
        posts = []
        for item in payload.get("data", []):
            posts.append(
                RawPost(
                    post_id=item["id"],
                    source_account=account.handle,
                    portfolio=account.portfolio,
                    post_url=f"https://x.com/{account.handle}/status/{item['id']}",
                    text=item["text"],
                    created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                )
            )
        return posts

    def _lookup_user_id(self, handle: str) -> str:
        response = httpx.get(
            f"{self.base_url}/users/by/username/{handle}",
            headers=self.headers,
            timeout=30,
        )
        _raise_for_x_status(response)
        return response.json()["data"]["id"]


def default_accounts() -> list[PortfolioAccount]:
    return list(MONITORED_ACCOUNTS)


def _raise_for_x_status(response: httpx.Response) -> None:
    if response.status_code == 402:
        raise XApiPaymentRequiredError(
            "X API returned 402 Payment Required. In the X Developer Console, confirm that "
            "your app/project has purchased API credits, a positive credit balance, and access "
            "to read User and Post resources. Adding a payment card alone may not add credits."
        )
    response.raise_for_status()
