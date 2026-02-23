"""Price list upload and status handlers."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.api_client import BotAPIClient
from apps.bot.keyboards import supplier_main_keyboard

logger = logging.getLogger(__name__)

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

ALLOWED_EXTENSIONS = (".csv", ".xlsx", ".xls", ".pdf")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _get_api(context: ContextTypes.DEFAULT_TYPE) -> BotAPIClient:
    return context.bot_data["api"]


async def _get_supplier_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    """Get supplier link or send error message."""
    api = _get_api(context)
    link = await api.get_link(update.effective_user.id)

    if not link:
        await update.message.reply_text(
            "Ваш аккаунт не привязан. Нажмите /start для регистрации."
        )
        return None

    if link["role"] != "supplier":
        await update.message.reply_text(
            "Загрузка файлов доступна только поставщикам."
        )
        return None

    return link


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle uploaded document — process as price list."""
    document = update.message.document

    # Check link
    link = await _get_supplier_link(update, context)
    if not link:
        return

    # Validate file
    filename = document.file_name or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if f".{ext}" not in ALLOWED_EXTENSIONS:
        await update.message.reply_text(
            f"Формат .{ext} не поддерживается.\n"
            f"Отправьте прайс-лист в формате: CSV, XLSX или PDF"
        )
        return

    if document.file_size and document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"Файл слишком большой ({document.file_size // 1024 // 1024} МБ).\n"
            f"Максимальный размер — 10 МБ."
        )
        return

    # Send processing message
    processing_msg = await update.message.reply_text(
        f"Файл получен: {filename}\nОбрабатываю..."
    )

    # Download file
    api = _get_api(context)
    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
    except Exception as e:
        logger.error("Failed to download file: %s", e)
        await processing_msg.edit_text("Не удалось скачать файл. Попробуйте ещё раз.")
        return

    # Upload to API
    supplier_id = link["entity_id"]
    try:
        result = await api.upload_price(
            supplier_id=supplier_id,
            filename=filename,
            content=bytes(file_bytes),
        )
    except Exception as e:
        error_detail = str(e)
        logger.error("Import failed for supplier %s: %s", supplier_id, error_detail)

        # Try to extract detail from httpx error
        if hasattr(e, "response") and e.response is not None:
            try:
                detail = e.response.json().get("detail", error_detail)
            except Exception:
                detail = error_detail
        else:
            detail = error_detail

        # Translate known error messages to Russian
        user_message = _translate_import_error(detail)

        await processing_msg.edit_text(
            f"Не удалось обработать файл.\n\n"
            f"{user_message}\n\n"
            f"Если проблема повторяется — попробуйте сохранить "
            f"прайс в формате XLSX или CSV и отправить заново."
        )
        return

    # Format result
    items = result.get("supplier_items_count", 0)
    type_pct = result.get("type_detected_pct", 0)
    variety_pct = result.get("variety_detected_pct", 0)
    errors = result.get("parse_errors_count", 0)

    text = f"Прайс обработан!\n\n"
    text += f"Загружено товаров: {items}\n"

    if type_pct == 100:
        text += f"Все товары распознаны корректно.\n"
    elif type_pct >= 80:
        text += f"Распознано корректно: {type_pct}% товаров.\n"
    else:
        text += f"Распознано: {type_pct}% товаров. Остальные требуют проверки.\n"

    if errors > 0:
        error_details = result.get("parse_errors", [])
        if error_details:
            text += f"\nПропущено строк: {errors}\n"
            for err in error_details[:5]:
                label = _error_label(err.get("code", ""))
                text += f"  — {label}\n"
            if errors > 5:
                text += f"  ...и ещё {errors - 5}\n"
        else:
            text += f"\nПропущено строк: {errors}.\n"

    text += (
        f"\nВаш прайс-лист сохранён и доступен покупателям на площадке. "
        f"Чтобы обновить прайс — отправьте новый файл."
    )

    await processing_msg.edit_text(text)
    logger.info(
        "Price uploaded via TG: supplier=%s, items=%d, type=%d%%, variety=%d%%",
        supplier_id, items, type_pct, variety_pct,
    )


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/price — show last import info."""
    link = await _get_supplier_link(update, context)
    if not link:
        return

    api = _get_api(context)
    last_import = await api.get_last_import(link["entity_id"])

    if not last_import:
        await update.message.reply_text(
            "У вас пока нет загруженных прайсов.\n\n"
            "Для загрузки отправьте файл (CSV, XLSX или PDF) в этот чат.",
            reply_markup=supplier_main_keyboard(),
        )
        return

    filename = _clean_filename(last_import.get("filename", "—"))
    status = last_import.get("status", "—")
    items = last_import.get("supplier_items_count", 0)
    imported_at = _format_date(last_import.get("imported_at", "—"))

    status_label = {
        "parsed": "Обработан",
        "published": "Опубликован",
        "failed": "Ошибка обработки",
        "received": "Обрабатывается",
    }.get(status, status)

    await update.message.reply_text(
        f"Последний прайс:\n\n"
        f"Файл: {filename}\n"
        f"Дата загрузки: {imported_at}\n"
        f"Статус: {status_label}\n"
        f"Товаров: {items}\n\n"
        f"Чтобы обновить прайс — отправьте новый файл.",
        reply_markup=supplier_main_keyboard(),
    )


_IMPORT_ERROR_TRANSLATIONS = {
    "PDF contains no extractable table data":
        "В PDF-файле не найдено таблиц с данными.\n"
        "Убедитесь, что прайс-лист оформлен в виде таблицы, "
        "а не как текстовый документ или картинка.",
    "Import failed: PDF contains no extractable table data":
        "В PDF-файле не найдено таблиц с данными.\n"
        "Убедитесь, что прайс-лист оформлен в виде таблицы, "
        "а не как текстовый документ или картинка.",
    "Unsupported file format":
        "Формат файла не поддерживается.\n"
        "Отправьте прайс в формате CSV, XLSX или PDF.",
    "No data rows found":
        "В файле не найдено строк с данными.\n"
        "Убедитесь, что файл содержит таблицу с товарами.",
}


def _translate_import_error(detail: str) -> str:
    """Translate API error detail to user-friendly Russian message."""
    # Exact match
    if detail in _IMPORT_ERROR_TRANSLATIONS:
        return _IMPORT_ERROR_TRANSLATIONS[detail]

    # Partial match (error may be wrapped in "Import failed: ...")
    for key, translation in _IMPORT_ERROR_TRANSLATIONS.items():
        if key in detail:
            return translation

    # Unknown error — show generic message
    return (
        "Произошла ошибка при обработке файла.\n"
        "Убедитесь, что в файле есть столбцы с наименованием и ценой."
    )


_ERROR_LABELS = {
    "MISSING_NAME": "нет наименования товара",
    "EMPTY_NAME": "пустое наименование товара",
    "MISSING_PRICE": "нет цены",
    "INVALID_PRICE": "некорректная цена",
    "ROW_PROCESSING_FAILED": "не удалось обработать строку",
}


def _error_label(code: str) -> str:
    """Translate error code to human-readable Russian label."""
    return _ERROR_LABELS.get(code, code)


def _clean_filename(filename: str) -> str:
    """Remove internal CSV sheet suffix from filename.

    'Мой прайс.xlsx - Прайс на декабрь 2025.csv' -> 'Мой прайс.xlsx'
    """
    if " - " in filename and filename.endswith(".csv"):
        # Check if original was xlsx/xls that got split into sheets
        base = filename.split(" - ")[0]
        if base.endswith((".xlsx", ".xls")):
            return base
    return filename


def _format_date(date_str: str) -> str:
    """Format ISO date to Russian: '2026-02-23T...' -> '23 февраля 2026'."""
    try:
        date_part = date_str.split("T")[0] if "T" in date_str else date_str
        parts = date_part.split("-")
        if len(parts) == 3:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            month_name = MONTHS_RU.get(month, str(month))
            return f"{day} {month_name} {year}"
    except (ValueError, IndexError):
        pass
    return date_str


async def price_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle price-related callback queries (future use)."""
    query = update.callback_query
    await query.answer("В разработке")
