"""Telegram bot entry point."""
import logging
import traceback

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from apps.bot.api_client import BotAPIClient
from apps.bot.config import bot_settings
from apps.bot.handlers.common import (
    help_cmd,
    status_cmd,
    stub_cmd,
    text_handler,
    unlink_cmd,
    unlink_callback,
)
from apps.bot.handlers.price import handle_document, price_cmd, price_button_handler
from apps.bot.handlers.start import (
    handle_contact,
    handle_company_name,
    role_callback,
    start_cmd,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    if not bot_settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Exiting.")
        return

    # Build application
    app = Application.builder().token(bot_settings.telegram_bot_token).build()

    # Store API client in bot_data for access in handlers
    api_client = BotAPIClient(
        base_url=bot_settings.api_base_url,
        bot_token=bot_settings.telegram_internal_token,
    )
    app.bot_data["api"] = api_client

    # Error handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Exception: %s", context.error, exc_info=context.error)
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка. Попробуйте позже или нажмите /start."
            )

    app.add_error_handler(error_handler)

    # --- Register handlers (order matters!) ---

    # Commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("unlink", unlink_cmd))

    # Stubs for future features
    app.add_handler(CommandHandler("orders", stub_cmd))
    app.add_handler(CommandHandler("cart", stub_cmd))
    app.add_handler(CommandHandler("search", stub_cmd))

    # Callback queries (inline buttons)
    app.add_handler(CallbackQueryHandler(role_callback, pattern=r"^role:"))
    app.add_handler(CallbackQueryHandler(unlink_callback, pattern=r"^unlink:"))
    app.add_handler(CallbackQueryHandler(price_button_handler, pattern=r"^price:"))

    # Contact (phone number)
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    # Document (file upload)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Text messages (reply keyboard buttons + free text)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Start bot
    if bot_settings.bot_mode == "webhook":
        logger.info(
            "Starting bot in WEBHOOK mode on %s:%s",
            bot_settings.bot_host,
            bot_settings.bot_port,
        )
        app.run_webhook(
            listen=bot_settings.bot_host,
            port=bot_settings.bot_port,
            webhook_url=bot_settings.telegram_webhook_url,
            secret_token=bot_settings.telegram_webhook_secret,
        )
    else:
        logger.info("Starting bot in POLLING mode (development)")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
