"""Send password reset codes via Email (Yandex SMTP)."""
import ssl
from email.message import EmailMessage

import aiosmtplib

from apps.api.config import settings
from apps.api.logging_config import get_logger

logger = get_logger(__name__)


async def send_reset_code_email(to_email: str, code: str) -> bool:
    """Send a 6-digit reset code to the user's email.

    Returns True if the message was sent successfully.
    """
    if not settings.smtp_user or not settings.smtp_password:
        logger.error("smtp_not_configured")
        return False

    msg = EmailMessage()
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = f"Код для сброса пароля: {code}"

    msg.set_content(
        f"Ваш код для сброса пароля: {code}\n\n"
        "Код действует 10 минут.\n"
        "Если вы не запрашивали сброс пароля, проигнорируйте это письмо.\n\n"
        "— Вцвет Маркет"
    )

    html_body = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px;">
  <h2 style="color: #2d2d2d; margin: 0 0 24px 0; font-size: 20px;">Сброс пароля</h2>
  <p style="color: #555; font-size: 15px; line-height: 1.5; margin: 0 0 24px 0;">
    Ваш код для сброса пароля:
  </p>
  <div style="background: #f5f5f5; border-radius: 8px; padding: 20px; text-align: center; margin: 0 0 24px 0;">
    <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1a1a1a;">{code}</span>
  </div>
  <p style="color: #888; font-size: 13px; line-height: 1.5; margin: 0;">
    Код действует 10 минут. Если вы не запрашивали сброс пароля, проигнорируйте это письмо.
  </p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
  <p style="color: #aaa; font-size: 12px; margin: 0;">Вцвет Маркет</p>
</div>"""
    msg.add_alternative(html_body, subtype="html")

    try:
        context = ssl.create_default_context()
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=True,
            tls_context=context,
        )
        logger.info("reset_code_email_sent", to=to_email)
        return True
    except Exception as exc:
        logger.error("smtp_send_error", to=to_email, error=str(exc))
        return False
