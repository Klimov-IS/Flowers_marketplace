# ADR-003: Manual confirmation для публикации

## Статус

Accepted

## Дата

2025-01-12

## Контекст

После нормализации supplier_item → normalized_sku нужно решить, когда публиковать оффер:

1. **Auto-publish**: публиковать сразу после propose (любой confidence)
2. **Threshold auto-publish**: авто-публикация при high confidence
3. **Manual confirmation**: всегда требовать подтверждения

Требования:
- Качество данных для покупателей
- Минимизация ручной работы
- Возможность быстрого запуска нового поставщика
- Избежание публикации мусора

## Решение

**Manual confirmation обязателен** для публикации офферов:

1. `sku_mappings.status = "proposed"` → оффер НЕ публикуется
2. `sku_mappings.status = "confirmed"` → оффер публикуется

Опционально:
- Auto-confirm при confidence ≥ 0.90 (флаг на уровне supplier)
- Batch confirm для оператора
- "Trust supplier" режим для проверенных поставщиков

## Последствия

### Плюсы

- **Data quality**: только проверенные данные публикуются
- **Trust**: покупатели видят качественный каталог
- **Control**: оператор контролирует, что публикуется
- **Reversibility**: легко отменить ошибочный mapping

### Минусы

- **Bottleneck**: оператор может стать узким местом
- **Delay**: задержка между импортом и публикацией
- **Cost**: требуется оператор для review

### Mitigation

- High confidence auto-confirm (опционально)
- Priority queue для важных задач
- Batch операции для массового подтверждения
- Dashboard с метриками очереди

## Альтернативы

### Auto-publish all

- Плюс: скорость, без ручной работы
- Минус: мусор в каталоге, низкое доверие покупателей

### Threshold auto-publish

- Плюс: баланс скорости и качества
- Минус: сложнее настроить threshold, edge cases

## Реализация

```python
# Publish service
def can_publish(offer_candidate) -> bool:
    mapping = get_confirmed_mapping(offer_candidate.supplier_item_id)
    return mapping is not None and mapping.status == "confirmed"

# При публикации
for candidate in offer_candidates:
    if can_publish(candidate):
        create_offer(candidate)
    else:
        stats["skipped_unmapped"] += 1
```

## Эволюция

В будущем возможен переход к threshold auto-publish:
1. Накопить статистику confirmation decisions
2. Калибровать threshold на реальных данных
3. A/B тест качества
4. Постепенно включать auto-confirm для trusted suppliers
