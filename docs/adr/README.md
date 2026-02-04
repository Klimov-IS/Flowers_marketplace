# Architecture Decision Records (ADR)

## Что такое ADR?

ADR — Architecture Decision Record — документ, фиксирующий значимое архитектурное решение:
- **Контекст**: почему возникла необходимость
- **Решение**: что решили
- **Последствия**: к чему это приводит

## Формат

Каждый ADR следует шаблону:

```markdown
# ADR-XXX: Название решения

## Статус
Accepted / Superseded / Deprecated

## Контекст
Описание проблемы или потребности

## Решение
Что решили сделать

## Последствия
Плюсы и минусы решения

## Альтернативы
Какие варианты рассматривались
```

## Индекс ADR

| ADR | Название | Статус | Дата |
|-----|----------|--------|------|
| [001](001-dictionary-driven-normalization.md) | Dictionary-driven нормализация | Accepted | 2025-01-12 |
| [002](002-immutable-raw-layer.md) | Immutable RAW layer | Accepted | 2025-01-12 |
| [003](003-manual-confirmation-for-publishing.md) | Manual confirmation для публикации | Accepted | 2025-01-12 |
| [004](004-single-supplier-orders.md) | Single-supplier orders в MVP | Accepted | 2025-01-13 |
| [005](005-jwt-authentication.md) | JWT аутентификация | Accepted | 2026-02-03 |

## Когда создавать ADR?

- Выбор технологии/фреймворка
- Изменение архитектуры
- Компромиссное решение
- Решение, которое сложно отменить
- Решение, влияющее на несколько компонентов
