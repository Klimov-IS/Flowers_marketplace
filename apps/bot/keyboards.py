"""Telegram bot keyboards."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

# --- Callback data constants ---
CB_ROLE_SUPPLIER = "role:supplier"
CB_ROLE_BUYER = "role:buyer"
CB_UNLINK_CONFIRM = "unlink:yes"
CB_UNLINK_CANCEL = "unlink:no"

# --- Inline keyboards ---

def role_selection_keyboard() -> InlineKeyboardMarkup:
    """Role selection: Supplier or Buyer."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Поставщик", callback_data=CB_ROLE_SUPPLIER),
            InlineKeyboardButton("Покупатель", callback_data=CB_ROLE_BUYER),
        ],
    ])


def unlink_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm account unlinking."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Да, отвязать", callback_data=CB_UNLINK_CONFIRM),
            InlineKeyboardButton("Отмена", callback_data=CB_UNLINK_CANCEL),
        ],
    ])


# --- Reply keyboards ---

def phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard with phone number request button."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def supplier_main_keyboard() -> ReplyKeyboardMarkup:
    """Main supplier menu keyboard."""
    return ReplyKeyboardMarkup(
        [
            ["Загрузить прайс", "Последний прайс"],
            ["Помощь"],
        ],
        resize_keyboard=True,
    )


REMOVE_KEYBOARD = ReplyKeyboardRemove()
