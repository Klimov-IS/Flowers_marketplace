"""Send password reset codes via Telegram Bot API."""
import httpx

from apps.api.config import settings
from apps.api.logging_config import get_logger

logger = get_logger(__name__)

TELEGRAM_API = "https://api.telegram.org"


async def send_reset_code(chat_id: int, code: str) -> bool:
    """Send a 6-digit reset code to a Telegram chat.

    Returns True if the message was sent successfully.
    """
    token = settings.telegram_bot_token
    if not token:
        logger.error("telegram_bot_token_not_configured")
        return False

    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": (
            f"🔐 Код для сброса пароля: *{code}*\n\n"
            "Действует 10 минут. Никому не сообщайте этот код."
        ),
        "parse_mode": "Markdown",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("reset_code_sent", chat_id=chat_id)
                return True
            logger.error("telegram_send_failed", status=resp.status_code, body=resp.text)
            return False
    except httpx.HTTPError as exc:
        logger.error("telegram_send_error", error=str(exc))
        return False
