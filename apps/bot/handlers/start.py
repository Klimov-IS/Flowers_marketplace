"""Onboarding handlers: /start, role selection, phone linking, registration."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.api_client import BotAPIClient
from apps.bot.keyboards import (
    CB_ROLE_BUYER,
    CB_ROLE_SUPPLIER,
    REMOVE_KEYBOARD,
    phone_request_keyboard,
    role_selection_keyboard,
    supplier_main_keyboard,
)

logger = logging.getLogger(__name__)


def _get_api(context: ContextTypes.DEFAULT_TYPE) -> BotAPIClient:
    return context.bot_data["api"]


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — check link and show appropriate menu."""
    user = update.effective_user
    api = _get_api(context)

    link = await api.get_link(user.id)

    if link:
        name = link.get("entity_name", "")
        await update.message.reply_text(
            f"Здравствуйте, {user.first_name}!\n"
            f"Компания: {name}\n\n"
            f"Чтобы обновить прайс — отправьте файл (Excel, CSV или PDF).",
            reply_markup=supplier_main_keyboard() if link["role"] == "supplier" else REMOVE_KEYBOARD,
        )
    else:
        await update.message.reply_text(
            f"Добро пожаловать в Flower Market, {user.first_name}!\n\n"
            "Выберите вашу роль:",
            reply_markup=role_selection_keyboard(),
        )


async def role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle role selection callback."""
    query = update.callback_query
    await query.answer()

    if query.data == CB_ROLE_BUYER:
        await query.edit_message_text(
            "Раздел покупателя находится в разработке.\n"
            "Следите за обновлениями!\n\n"
            "Нажмите /start чтобы начать заново."
        )
        return

    if query.data == CB_ROLE_SUPPLIER:
        await query.edit_message_text(
            "Отлично! Давайте привяжем ваш аккаунт.\n\n"
            "Нажмите кнопку ниже, чтобы отправить номер телефона "
            "и мы найдем вашу компанию в системе."
        )
        await query.message.reply_text(
            "Отправьте номер телефона:",
            reply_markup=phone_request_keyboard(),
        )
        # Mark that user is in supplier onboarding flow
        context.user_data["onboarding"] = "supplier_phone"


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle shared contact (phone number)."""
    contact = update.message.contact
    phone = contact.phone_number
    user = update.effective_user
    api = _get_api(context)

    # Check if already linked
    link = await api.get_link(user.id)
    if link:
        await update.message.reply_text(
            "Ваш аккаунт уже привязан. Используйте /unlink для отвязки.",
            reply_markup=supplier_main_keyboard(),
        )
        return

    # Search supplier by phone
    result = await api.find_supplier_by_phone(phone)

    if result:
        # Found — link account
        entity_id = result["entity_id"]
        supplier_name = result["name"]
        supplier_status = result["status"]

        await api.create_link(
            telegram_user_id=user.id,
            telegram_chat_id=update.effective_chat.id,
            role="supplier",
            entity_id=entity_id,
            username=user.username,
            first_name=user.first_name,
        )

        status_text = ""
        if supplier_status == "pending":
            status_text = "\n\nВаш аккаунт ожидает активации администратором."
        elif supplier_status == "blocked":
            status_text = "\n\nВаш аккаунт заблокирован. Обратитесь к администратору."

        await update.message.reply_text(
            f"Аккаунт привязан!\n"
            f"Компания: {supplier_name}{status_text}\n\n"
            f"Для загрузки прайса — отправьте файл (CSV, XLSX или PDF).",
            reply_markup=supplier_main_keyboard(),
        )
        logger.info("Supplier linked: tg=%d -> %s (%s)", user.id, entity_id, supplier_name)
    else:
        # Not found — offer registration
        context.user_data["onboarding"] = "supplier_register"
        context.user_data["register_phone"] = phone
        await update.message.reply_text(
            "Номер не найден в системе.\n\n"
            "Давайте зарегистрируем вашу компанию.\n"
            "Введите название компании:",
            reply_markup=REMOVE_KEYBOARD,
        )


async def handle_company_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle company name input during registration."""
    user = update.effective_user
    api = _get_api(context)
    company_name = update.message.text.strip()

    if len(company_name) < 2:
        await update.message.reply_text("Название слишком короткое. Попробуйте ещё раз:")
        return

    phone = context.user_data.get("register_phone", "")

    try:
        result = await api.register_supplier(
            name=company_name,
            phone=phone,
        )
    except Exception as e:
        error_msg = str(e)
        if "409" in error_msg:
            await update.message.reply_text(
                "Компания с таким названием уже зарегистрирована.\n"
                "Попробуйте другое название или обратитесь к администратору."
            )
            return
        logger.error("Registration failed: %s", e)
        await update.message.reply_text(
            "Произошла ошибка при регистрации. Попробуйте позже."
        )
        return

    supplier_id = result["supplier_id"]

    # Auto-link
    await api.create_link(
        telegram_user_id=user.id,
        telegram_chat_id=update.effective_chat.id,
        role="supplier",
        entity_id=supplier_id,
        username=user.username,
        first_name=user.first_name,
    )

    # Clear onboarding state
    context.user_data.pop("onboarding", None)
    context.user_data.pop("register_phone", None)

    await update.message.reply_text(
        f"Регистрация завершена!\n"
        f"Компания: {company_name}\n\n"
        f"Вы можете сразу загрузить свой прайс-лист — "
        f"просто отправьте файл (CSV, XLSX или PDF) в этот чат.",
        reply_markup=supplier_main_keyboard(),
    )
    logger.info("Supplier registered via TG: tg=%d, name=%s, id=%s", user.id, company_name, supplier_id)
