"""Bot configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    """Telegram bot settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""
    telegram_internal_token: str = ""

    # API connection
    api_base_url: str = "http://127.0.0.1:8000"

    # Bot server
    bot_host: str = "0.0.0.0"
    bot_port: int = 8081

    # Mode: "webhook" or "polling" (polling for local dev)
    bot_mode: str = "polling"


bot_settings = BotSettings()
