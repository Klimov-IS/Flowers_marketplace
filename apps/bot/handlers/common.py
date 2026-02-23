"""Common handlers: /help, /status, /unlink, stubs, text router."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.api_client import BotAPIClient
from apps.bot.keyboards import (
    CB_UNLINK_CANCEL,
    CB_UNLINK_CONFIRM,
    REMOVE_KEYBOARD,
    supplier_main_keyboard,
    unlink_confirm_keyboard,
)

logger = logging.getLogger(__name__)


def _get_api(context: ContextTypes.DEFAULT_TYPE) -> BotAPIClient:
    return context.bot_data["api"]


HELP_TEXT = (
    "Flower Market — площадка для оптовой торговли цветами.\n\n"
    "Через этот бот вы можете загружать свой прайс-лист, "
    "чтобы покупатели видели ваши товары и цены.\n\n"
    "Как загрузить прайс:\n"
    "Просто отправьте файл (Excel, CSV или PDF) в этот чат.\n\n"
    "Команды:\n"
    "/start — Главное меню\n"
    "/price — Информация о последнем прайсе\n"
    "/status — Ваш аккаунт\n"
    "/help — Справка"
)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — show help text."""
    await update.message.reply_text(HELP_TEXT)


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status — show account info."""
    api = _get_api(context)
    link = await api.get_link(update.effective_user.id)

    if not link:
        await update.message.reply_text(
            "Ваш Telegram-аккаунт не привязан к системе.\n"
            "Нажмите /start для регистрации."
        )
        return

    role_label = "Поставщик" if link["role"] == "supplier" else "Покупатель"
    name = link.get("entity_name", "—")

    await update.message.reply_text(
        f"Ваш аккаунт:\n\n"
        f"Компания: {name}\n"
        f"Роль: {role_label}",
    )


async def unlink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/unlink — confirm and unlink account."""
    api = _get_api(context)
    link = await api.get_link(update.effective_user.id)

    if not link:
        await update.message.reply_text(
            "Ваш аккаунт не привязан. Нечего отвязывать."
        )
        return

    name = link.get("entity_name", "")
    await update.message.reply_text(
        f"Вы уверены, что хотите отвязать аккаунт?\n"
        f"Компания: {name}\n\n"
        f"После отвязки вы не сможете загружать прайсы "
        f"и получать уведомления через этот бот.",
        reply_markup=unlink_confirm_keyboard(),
    )


async def unlink_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unlink confirmation callback."""
    query = update.callback_query
    await query.answer()

    if query.data == CB_UNLINK_CANCEL:
        await query.edit_message_text("Отвязка отменена.")
        return

    if query.data == CB_UNLINK_CONFIRM:
        api = _get_api(context)
        success = await api.delete_link(update.effective_user.id)

        if success:
            await query.edit_message_text(
                "Аккаунт отвязан.\n\n"
                "Нажмите /start для повторной привязки.",
            )
            logger.info("Account unlinked: tg=%d", update.effective_user.id)
        else:
            await query.edit_message_text("Не удалось отвязать аккаунт. Попробуйте /start.")


STUB_TEXT = "Этот раздел находится в разработке. Следите за обновлениями!"


async def stub_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stub for unimplemented commands."""
    await update.message.reply_text(STUB_TEXT)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free text messages and reply keyboard buttons."""
    text = update.message.text.strip()

    # Handle reply keyboard buttons
    if text == "Загрузить прайс":
        await update.message.reply_text(
            "Для загрузки прайса отправьте файл (CSV, XLSX или PDF) в этот чат."
        )
        return

    if text == "Последний прайс":
        from apps.bot.handlers.price import price_cmd
        await price_cmd(update, context)
        return

    if text == "Помощь":
        await help_cmd(update, context)
        return

    # Check if user is in registration flow
    onboarding = context.user_data.get("onboarding")
    if onboarding == "supplier_register":
        from apps.bot.handlers.start import handle_company_name
        await handle_company_name(update, context)
        return

    # Default response
    api = _get_api(context)
    link = await api.get_link(update.effective_user.id)

    if link and link["role"] == "supplier":
        await update.message.reply_text(
            "Для загрузки прайса отправьте файл (CSV, XLSX или PDF).\n"
            "Для справки — /help",
            reply_markup=supplier_main_keyboard(),
        )
    else:
        await update.message.reply_text(
            "Я не понимаю это сообщение.\n"
            "Нажмите /start для начала или /help для справки."
        )
