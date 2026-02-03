# Документация B2B Flower Market Platform

## Структура

```
docs/
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

| Документ | Описание |
|----------|----------|
| [VISION.md](architecture/VISION.md) | Видение продукта и цели |
| [MVP_SCOPE.md](architecture/MVP_SCOPE.md) | Scope MVP |
| [CORE_DATA_MODEL.md](architecture/CORE_DATA_MODEL.md) | Модель данных |
| [IMPORT_PIPELINE.md](architecture/IMPORT_PIPELINE.md) | Пайплайн импорта |
| [NORMALIZATION_RULES.md](architecture/NORMALIZATION_RULES.md) | Правила нормализации |
| [ADMIN_API.md](architecture/ADMIN_API.md) | API документация |
| [DDL_SCHEMA.md](architecture/DDL_SCHEMA.md) | Схема БД (черновик) |
| [QUICK_TEST.md](architecture/QUICK_TEST.md) | Инструкция быстрого теста |

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

## ADR (Architecture Decision Records)

Папка `adr/` содержит записи архитектурных решений.

Формат каждой записи:
- **Контекст**: почему возникла необходимость
- **Решение**: что решили
- **Последствия**: к чему это приводит

---

## Тестовые данные (samples/)

- `prices/` — реальные прайсы поставщиков для тестирования парсера

---

## Референсы (reference/)

Скриншоты UI, макеты и визуальные материалы.
