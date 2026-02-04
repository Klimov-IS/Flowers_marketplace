# OPERATIONS.md — Операционное руководство

## Обзор

Руководство по локальной разработке, тестированию, деплою и обслуживанию B2B Flower Market Platform.

---

## 1. Локальная разработка

### 1.1 Требования

| Компонент | Версия | Назначение |
|-----------|--------|------------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| PostgreSQL | 16+ | Database |
| Docker | 24+ | Контейнеризация |
| Docker Compose | 2.0+ | Оркестрация |

### 1.2 Первоначальная настройка

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd Маркетплейс

# 2. Создать виртуальное окружение
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить переменные окружения
cp .env.example .env
# Отредактировать .env под свои настройки
```

### 1.3 Запуск базы данных

```bash
# Способ 1: Docker Compose (рекомендуется)
cd infra
docker compose up -d
cd ..

# Способ 2: Локальный PostgreSQL
# Создать базу данных
createdb flower_market
```

### 1.4 Применение миграций

```bash
# Применить все миграции
alembic upgrade head

# Проверить текущую версию
alembic current

# Показать историю миграций
alembic history
```

### 1.5 Bootstrap данных

```bash
# Загрузить начальные данные (словарь, города)
curl -X POST http://localhost:8000/admin/dictionary/bootstrap

# Или через Python
python -m apps.api.scripts.bootstrap_data
```

### 1.6 Запуск API

```bash
# Development mode (с auto-reload)
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 1.7 Запуск Frontend

```bash
cd frontend
npm install
npm run dev

# Production build
npm run build
```

### 1.8 Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health

# Ожидаемый ответ
{"status": "ok", "database": "connected"}

# API docs
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

---

## 2. Структура конфигурации

### 2.1 Environment Variables (.env)

```bash
# === Database ===
DB_HOST=localhost
DB_PORT=5432
DB_NAME=flower_market
DB_USER=flower_user
DB_PASSWORD=flower_password

# === Application ===
APP_ENV=development          # development | staging | production
LOG_LEVEL=INFO               # DEBUG | INFO | WARNING | ERROR
DEBUG=true                   # Enable debug mode

# === API ===
API_HOST=0.0.0.0
API_PORT=8000

# === Security ===
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# === CORS ===
CORS_ORIGINS=*               # Comma-separated list or *
# CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# === Rate Limiting ===
RATE_LIMIT_ENABLED=false     # Enable rate limiting
RATE_LIMIT_REQUESTS=100      # Requests per window
RATE_LIMIT_WINDOW=60         # Window in seconds

# === File Upload ===
MAX_UPLOAD_SIZE_MB=10
ALLOWED_EXTENSIONS=csv,xlsx
```

### 2.2 Конфигурация по окружениям

| Параметр | Development | Staging | Production |
|----------|-------------|---------|------------|
| DEBUG | true | false | false |
| LOG_LEVEL | DEBUG | INFO | WARNING |
| CORS_ORIGINS | * | specific | specific |
| RATE_LIMIT | false | true | true |
| SECRET_KEY | dev-key | random | random |

---

## 3. База данных

### 3.1 Создание миграций

```bash
# Автогенерация миграции из изменений в models
alembic revision --autogenerate -m "add_new_field"

# Ручное создание миграции
alembic revision -m "custom_migration"
```

### 3.2 Управление миграциями

```bash
# Применить все миграции
alembic upgrade head

# Применить следующую миграцию
alembic upgrade +1

# Откатить последнюю миграцию
alembic downgrade -1

# Откатить до конкретной версии
alembic downgrade <revision_id>

# Показать SQL без применения
alembic upgrade head --sql
```

### 3.3 Структура миграций

```
alembic/
├── env.py              # Конфигурация Alembic
├── script.py.mako      # Шаблон миграции
└── versions/
    ├── 20250112_001_initial_schema.py
    ├── 20250112_002_normalized_layer.py
    ├── 20250113_003_orders.py
    └── 20260203_004_auth_fields.py
```

### 3.4 Backup и Restore

```bash
# Создать backup
pg_dump -h localhost -U flower_user -d flower_market > backup_$(date +%Y%m%d).sql

# Restore
psql -h localhost -U flower_user -d flower_market < backup_20250112.sql

# Backup только схемы
pg_dump -h localhost -U flower_user -d flower_market --schema-only > schema.sql

# Backup только данных
pg_dump -h localhost -U flower_user -d flower_market --data-only > data.sql
```

### 3.5 Полезные SQL запросы

```sql
-- Статистика по импортам
SELECT
    supplier_id,
    status,
    COUNT(*) as count,
    MAX(created_at) as last_import
FROM import_batches
GROUP BY supplier_id, status;

-- Pending normalization tasks
SELECT
    COUNT(*) as pending_tasks,
    AVG(priority) as avg_priority
FROM normalization_tasks
WHERE status = 'open';

-- Active offers by supplier
SELECT
    s.name,
    COUNT(o.id) as offer_count
FROM offers o
JOIN suppliers s ON o.supplier_id = s.id
WHERE o.is_active = true
GROUP BY s.name
ORDER BY offer_count DESC;

-- Order statistics
SELECT
    status,
    COUNT(*) as count,
    SUM(total_amount) as total_revenue
FROM orders
GROUP BY status;
```

---

## 4. Тестирование

### 4.1 Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=apps --cov=packages

# Конкретный файл
pytest tests/test_parsing.py

# Конкретный тест
pytest tests/test_parsing.py::test_parse_price

# Verbose output
pytest -v

# Остановиться на первой ошибке
pytest -x

# Показать print statements
pytest -s
```

### 4.2 Структура тестов

```
tests/
├── conftest.py           # Fixtures
├── unit/
│   ├── test_parsing.py   # packages/core/parsing
│   ├── test_normalization.py
│   └── test_tokens.py
├── integration/
│   ├── test_import_flow.py
│   ├── test_normalization_flow.py
│   └── test_order_flow.py
└── fixtures/
    ├── sample_prices.csv
    └── test_data.json
```

### 4.3 Тестирование парсера с реальными прайсами

```bash
# Запустить тест реальных прайсов
python -m apps.api.scripts.test_real_prices

# Ожидаемый вывод:
# Found 2 CSV files in docs/samples/prices
# Testing: Росцветторг.csv
# Total rows parsed: 150
# Valid prices: 145/150
# Success rate: 96.7%
# ...
```

### 4.4 Fixtures

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session

@pytest.fixture
def sample_csv_content():
    """Return sample CSV content for testing."""
    return b"Наименование;Цена\nРоза Explorer 60см;150\n"
```

---

## 5. Деплой

### 5.1 Docker Build

```bash
# Build API image
docker build -t flower-market-api:latest .

# Build with specific tag
docker build -t flower-market-api:v1.0.0 .
```

### 5.2 Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: flower-market-api:latest
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=flower_market
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - SECRET_KEY=${SECRET_KEY}
      - APP_ENV=production
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=flower_market
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
```

### 5.3 Deployment Checklist

```markdown
Pre-deployment:
□ All tests pass
□ Migrations tested on staging
□ Environment variables configured
□ Secrets rotated (if needed)
□ Backup created
□ Monitoring configured

Deployment:
□ Pull latest code
□ Build new image
□ Apply migrations
□ Start new containers
□ Verify health check
□ Smoke test critical endpoints

Post-deployment:
□ Monitor error rates
□ Check response times
□ Verify logs
□ Notify team
```

### 5.4 Rollback

```bash
# If deployment fails

# 1. Stop new containers
docker compose down

# 2. Restore previous image
docker compose up -d --force-recreate

# 3. Rollback migration (if needed)
alembic downgrade -1

# 4. Restore database (if data corrupted)
psql -d flower_market < backup.sql
```

---

## 6. Мониторинг

### 6.1 Health Endpoints

| Endpoint | Назначение |
|----------|------------|
| `GET /health` | Basic health + DB check |
| `GET /health/ready` | Ready for traffic |
| `GET /health/live` | Container alive |

### 6.2 Logging

```python
# Structured logging with structlog
import structlog

logger = structlog.get_logger()

# Log with context
logger.info(
    "import_completed",
    batch_id=str(batch.id),
    rows_total=150,
    duration_ms=1234
)
```

### 6.3 Log Format

```json
{
  "timestamp": "2025-01-12T10:00:00Z",
  "level": "info",
  "event": "import_completed",
  "batch_id": "uuid",
  "rows_total": 150,
  "duration_ms": 1234,
  "logger": "apps.api.services.import_service"
}
```

### 6.4 Метрики (опционально)

```python
# Prometheus metrics (если настроено)
from prometheus_client import Counter, Histogram

import_counter = Counter(
    'imports_total',
    'Total number of imports',
    ['supplier_id', 'status']
)

import_duration = Histogram(
    'import_duration_seconds',
    'Import duration in seconds'
)
```

---

## 7. Обслуживание

### 7.1 Очистка старых данных

```sql
-- Архивирование старых импортов (>90 дней)
UPDATE import_batches
SET status = 'archived'
WHERE created_at < NOW() - INTERVAL '90 days'
  AND status = 'published';

-- Удаление неактивных офферов (>30 дней)
DELETE FROM offers
WHERE is_active = false
  AND created_at < NOW() - INTERVAL '30 days';

-- Очистка resolved tasks (>60 дней)
DELETE FROM normalization_tasks
WHERE status = 'done'
  AND updated_at < NOW() - INTERVAL '60 days';
```

### 7.2 Регулярные задачи

| Задача | Частота | Команда |
|--------|---------|---------|
| Backup DB | Daily | `pg_dump > backup.sql` |
| Clean old imports | Weekly | SQL script |
| Vacuum DB | Weekly | `VACUUM ANALYZE;` |
| Rotate logs | Daily | logrotate |
| Update dependencies | Monthly | `pip list --outdated` |

### 7.3 Troubleshooting

```bash
# Проверить логи API
docker logs flower-api --tail 100 -f

# Проверить подключение к БД
psql -h localhost -U flower_user -d flower_market -c "SELECT 1"

# Проверить порты
netstat -tlnp | grep 8000

# Проверить память/CPU
docker stats

# Проверить миграции
alembic current
alembic history
```

---

## 8. Полезные скрипты

### 8.1 Быстрый тест всего flow

```bash
#!/bin/bash
# test_flow.sh

# 1. Health check
curl -s http://localhost:8000/health | jq .

# 2. Bootstrap dictionary
curl -s -X POST http://localhost:8000/admin/dictionary/bootstrap | jq .

# 3. Create supplier
SUPPLIER=$(curl -s -X POST http://localhost:8000/admin/suppliers \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Supplier", "status": "active"}')
SUPPLIER_ID=$(echo $SUPPLIER | jq -r '.id')

# 4. Import CSV
curl -s -X POST "http://localhost:8000/admin/suppliers/${SUPPLIER_ID}/imports/csv" \
  -F "file=@docs/samples/prices/test.csv" | jq .

# 5. Propose mappings
curl -s -X POST http://localhost:8000/admin/normalization/propose \
  -H "Content-Type: application/json" \
  -d "{\"supplier_id\": \"${SUPPLIER_ID}\"}" | jq .

# 6. Check tasks
curl -s "http://localhost:8000/admin/normalization/tasks?status=open" | jq .

echo "Flow test completed!"
```

### 8.2 Reset локальной БД

```bash
#!/bin/bash
# reset_db.sh

echo "Dropping database..."
dropdb flower_market

echo "Creating database..."
createdb flower_market

echo "Running migrations..."
alembic upgrade head

echo "Bootstrapping data..."
curl -s -X POST http://localhost:8000/admin/dictionary/bootstrap

echo "Database reset completed!"
```

---

## 9. Связанные документы

- [ARCHITECTURE.md](ARCHITECTURE.md) — архитектура системы
- [WORKFLOWS.md](WORKFLOWS.md) — бизнес-процессы
- [FAILURE_MODES.md](FAILURE_MODES.md) — обработка ошибок
- [ADMIN_API.md](ADMIN_API.md) — API документация
