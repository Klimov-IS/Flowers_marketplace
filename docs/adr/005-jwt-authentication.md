# ADR-005: JWT аутентификация

## Статус

Accepted

## Дата

2026-02-03

## Контекст

Платформе нужна система аутентификации для:
- Покупателей (buyers)
- Поставщиков (suppliers)
- Администраторов (future)

Варианты:
1. **Session-based**: сессии в Redis/DB
2. **JWT stateless**: токены без серверного состояния
3. **OAuth2 / OIDC**: внешний identity provider

Требования:
- Простота реализации
- Масштабируемость (stateless)
- Поддержка разных ролей
- Mobile-friendly

## Решение

**JWT (JSON Web Tokens)** с двумя типами токенов:

1. **Access Token** (15 минут)
   - Короткоживущий
   - Для авторизации API запросов
   - Содержит: user_id, role, exp

2. **Refresh Token** (7 дней)
   - Долгоживущий
   - Для обновления access token
   - Хранится клиентом безопасно

### Token Structure

```json
{
  "sub": "user-uuid",
  "role": "buyer",
  "type": "access",
  "exp": 1704067200,
  "iat": 1704066300
}
```

### Flow

```
1. Login: email + password → access_token + refresh_token
2. API call: Authorization: Bearer <access_token>
3. Token expired: POST /auth/refresh → new tokens
4. Refresh expired: re-login required
```

## Последствия

### Плюсы

- **Stateless**: не нужно хранить сессии
- **Scalable**: любой сервер может валидировать
- **Mobile-friendly**: легко хранить на клиенте
- **Self-contained**: токен содержит всю информацию
- **Standard**: широко поддерживается

### Минусы

- **No revocation**: нельзя отозвать токен до истечения
- **Token size**: больше чем session ID
- **Clock skew**: требуется синхронизация времени

### Mitigation

- Короткий TTL для access token (15 мин)
- Blacklist в Redis (для production)
- Refresh token rotation

## Альтернативы

### Session-based

- Плюс: легко отозвать, меньше payload
- Минус: требует shared storage, не stateless

### OAuth2 / OIDC

- Плюс: делегированная авторизация, SSO
- Минус: сложнее setup, overkill для MVP

## Реализация

```python
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

def create_access_token(user_id: UUID, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=15)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: UUID, role: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "refresh",
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

## Безопасность

1. **HTTPS only**: токены передаются только по HTTPS
2. **HttpOnly cookies**: опционально для web (XSS protection)
3. **Short TTL**: минимизирует окно атаки
4. **Refresh rotation**: новый refresh при каждом использовании
5. **Blacklist** (production): Redis для отозванных токенов

## Эволюция

1. MVP: stateless JWT
2. Production: добавить blacklist в Redis
3. Future: OAuth2 для third-party интеграций
