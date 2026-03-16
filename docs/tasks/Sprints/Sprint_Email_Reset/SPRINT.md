# Спринт: Перевод сброса пароля с Telegram на Email

**Дата создания:** 2026-03-16
**Статус:** Завершён

---

## Контекст

Бэкенд переведён на email-first сброс пароля (код отправляется на email, в Telegram — бонусом если привязан). Фронтенд и документация обновлены.

---

## Выполненные задачи

### Бэкенд (сделано ранее в этой сессии)

| Компонент | Статус | Детали |
|-----------|--------|--------|
| `apps/api/routers/auth.py` — эндпоинт `/forgot-password` | ✅ | Email — основной канал, Telegram — бонус |
| `apps/api/auth/email_notify.py` — отправка email | ✅ | HTML-шаблон, Яндекс SMTP |
| `apps/api/auth/telegram_notify.py` — отправка в Telegram | ✅ | Опциональный канал |
| `apps/api/models/password_reset.py` — модель | ✅ | `telegram_chat_id` nullable |
| Миграция `20260316_email_password_reset` | ✅ | Применена на проде |
| SMTP конфигурация на сервере | ✅ | vcvet.info@yandex.ru |

### Фронтенд и документация (этот спринт)

- [x] **Задача 1:** Обновить текст на фронтенде (ResetPasswordPage.tsx) — убраны все упоминания Telegram, заменены на email
- [x] **Задача 2:** Обновить комментарии в коде (schemas.py, password_reset.py)
- [x] **Задача 3:** Обновить документацию (ADR, ADMIN_API, CORE_DATA_MODEL)
- [x] **Задача 4:** Пометить EMAIL_PASSWORD_RESET.md как выполненную
- [x] **Задача 5:** Деплой
- [x] **Задача 6:** Проверить flow на проде
