# Документация B2B Flower Market Platform

## Структура

```
docs/
├── DEPLOYMENT.md    # Руководство по деплою (сервер, SSH, команды)
├── architecture/    # Архитектурная документация (постоянная)
├── adr/             # Architecture Decision Records
├── tasks/           # Задачи и ТЗ
│   └── completed/   # Выполненные задачи
├── samples/         # Тестовые данные
│   └── prices/      # Прайсы для тестирования
└── reference/       # Референсы и макеты
```

---

## Архитектура (architecture/)

### Основные документы

| Документ | Описание |
|----------|----------|
| [ARCHITECTURE.md](architecture/ARCHITECTURE.md) | **Общая архитектура системы** — слои, компоненты, data flow |
| [VISION.md](architecture/VISION.md) | Видение продукта и цели |
| [MVP_SCOPE.md](architecture/MVP_SCOPE.md) | Scope MVP |
| [CORE_DATA_MODEL.md](architecture/CORE_DATA_MODEL.md) | Модель данных |

### Процессы и алгоритмы

| Документ | Описание |
|----------|----------|
| [WORKFLOWS.md](architecture/WORKFLOWS.md) | **Бизнес-процессы** — все end-to-end flow |
| [DATA_LIFECYCLE.md](architecture/DATA_LIFECYCLE.md) | **Жизненный цикл данных** — state machines, retention |
| [IMPORT_PIPELINE.md](architecture/IMPORT_PIPELINE.md) | Пайплайн импорта CSV |
| [NORMALIZATION_RULES.md](architecture/NORMALIZATION_RULES.md) | **Правила и алгоритм нормализации** |

### Операции и API

| Документ | Описание |
|----------|----------|
| [ADMIN_API.md](architecture/ADMIN_API.md) | **Backend API документация** — все endpoints |
| [OPERATIONS.md](architecture/OPERATIONS.md) | **Операционное руководство** — setup, deploy, monitoring |
| [FAILURE_MODES.md](architecture/FAILURE_MODES.md) | **Обработка ошибок** — failures, recovery |

### Справочные материалы

| Документ | Описание |
|----------|----------|
| [DDL_SCHEMA.md](architecture/DDL_SCHEMA.md) | Схема БД (черновик) |
| [QUICK_TEST.md](architecture/QUICK_TEST.md) | Инструкция быстрого теста |

---

## ADR (Architecture Decision Records)

Записи архитектурных решений в [adr/](adr/README.md):

| ADR | Название | Статус |
|-----|----------|--------|
| [001](adr/001-dictionary-driven-normalization.md) | Dictionary-driven нормализация | Accepted |
| [002](adr/002-immutable-raw-layer.md) | Immutable RAW layer | Accepted |
| [003](adr/003-manual-confirmation-for-publishing.md) | Manual confirmation для публикации | Accepted |
| [004](adr/004-single-supplier-orders.md) | Single-supplier orders в MVP | Accepted |
| [005](adr/005-jwt-authentication.md) | JWT аутентификация | Accepted |

---

## Задачи (tasks/)

### Активные

| Документ | Описание |
|----------|----------|
| [TASK documentation.md](tasks/TASK%20documentation.md) | ТЗ на документирование |
| [SPRINT_4_PLAN.md](tasks/SPRINT_4_PLAN.md) | План Sprint 4 |

### Выполненные

См. папку [tasks/completed/](tasks/completed/)

---

## Deployment

| Документ | Описание |
|----------|----------|
| [DEPLOYMENT.md](DEPLOYMENT.md) | **Руководство по деплою** — сервер, SSH, команды, troubleshooting |

**Текущий деплой:**
- **Frontend**: http://158.160.217.236/flower/
- **API**: http://158.160.217.236/flower/api/
- **API Docs**: http://158.160.217.236/flower/api/docs

---

## Быстрый старт

### Для разработчика

1. Прочитать [ARCHITECTURE.md](architecture/ARCHITECTURE.md)
2. Настроить окружение по [OPERATIONS.md](architecture/OPERATIONS.md)
3. Изучить API в [ADMIN_API.md](architecture/ADMIN_API.md)
4. **Деплой** — см. [DEPLOYMENT.md](DEPLOYMENT.md)

### Для оператора

1. Прочитать [WORKFLOWS.md](architecture/WORKFLOWS.md)
2. Изучить [NORMALIZATION_RULES.md](architecture/NORMALIZATION_RULES.md)
3. Посмотреть [FAILURE_MODES.md](architecture/FAILURE_MODES.md) для troubleshooting

### Для архитектора

1. Начать с [VISION.md](architecture/VISION.md) и [MVP_SCOPE.md](architecture/MVP_SCOPE.md)
2. Изучить [CORE_DATA_MODEL.md](architecture/CORE_DATA_MODEL.md)
3. Посмотреть ADR в [adr/](adr/)

---

## Тестовые данные (samples/)

- `prices/` — реальные прайсы поставщиков для тестирования парсера

---

## Референсы (reference/)

Скриншоты UI, макеты и визуальные материалы.
