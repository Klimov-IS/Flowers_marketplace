# ADR-004: Single-supplier orders в MVP

## Статус

Accepted

## Дата

2025-01-13

## Контекст

При создании заказа покупатель может выбрать офферы от разных поставщиков. Варианты:

1. **Multi-supplier order**: один заказ с позициями от разных поставщиков
2. **Single-supplier order**: заказ только от одного поставщика
3. **Auto-split**: автоматическое разбиение на sub-orders

Требования MVP:
- Простота реализации
- Простота для поставщика (один заказ = один поставщик)
- Минимум edge cases
- Возможность расширения в будущем

## Решение

**Single-supplier orders** в MVP:

1. Все офферы в заказе должны быть от одного поставщика
2. Валидация при создании: если разные suppliers → 400 Bad Request
3. Покупатель должен создать отдельные заказы для разных поставщиков

```python
def validate_order(items: List[OrderItem]) -> None:
    suppliers = set(item.offer.supplier_id for item in items)
    if len(suppliers) > 1:
        raise HTTPException(
            status_code=400,
            detail="All items must be from the same supplier"
        )
```

## Последствия

### Плюсы

- **Simplicity**: простая модель данных
- **Clear ownership**: один поставщик отвечает за весь заказ
- **Simple workflow**: confirm/reject на уровне заказа
- **No split logic**: не нужно разбивать заказы
- **Easy support**: легко разбираться в спорах

### Минусы

- **UX friction**: покупатель должен создавать несколько заказов
- **Extra work**: больше заказов = больше работы
- **Cart complexity**: корзина должна группировать по suppliers

### Mitigation

- Frontend: показывать группировку в корзине
- Frontend: кнопка "Оформить все" создаёт несколько заказов
- API: batch create endpoint (future)

## Альтернативы

### Multi-supplier order

- Плюс: удобнее для покупателя
- Минус: сложный workflow (partial confirm, split delivery)

### Auto-split

- Плюс: прозрачно для покупателя
- Минус: сложная реализация, неявное поведение

## Эволюция

После MVP можно добавить:
1. Auto-split при создании (один request → несколько orders)
2. Групповой статус для связанных заказов
3. Multi-supplier order с sub-orders

## Пример использования

```bash
# Покупатель хочет заказать от двух поставщиков

# Заказ 1 (Поставщик A)
curl -X POST /orders -d '{
  "buyer_id": "...",
  "items": [
    {"offer_id": "offer-from-supplier-a", "quantity": 10}
  ]
}'

# Заказ 2 (Поставщик B)
curl -X POST /orders -d '{
  "buyer_id": "...",
  "items": [
    {"offer_id": "offer-from-supplier-b", "quantity": 5}
  ]
}'
```
