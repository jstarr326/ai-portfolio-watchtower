from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    x_api_bearer_token: str = Field(default="", alias="X_API_BEARER_TOKEN")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_key: str = Field(default="", alias="SUPABASE_SERVICE_KEY")
    slack_webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    poll_max_results: int = Field(default=10, alias="POLL_MAX_RESULTS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

