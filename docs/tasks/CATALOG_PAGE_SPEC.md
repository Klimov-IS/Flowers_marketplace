# ТЗ: Страница Каталога — Витрина для Покупателя

## Статус: Фаза 4 завершена (Sidebar Filters)
## Прототип: `prototype/catalog_page.html` ✅
## Production: http://158.160.229.16/flower/

---

## 1. Бизнес-требования

### 1.1 Цель
Создать информативную витрину для покупателя (флориста), где он может:
- Быстро находить нужные цветы по типу, стране, цвету, размеру, цене
- Видеть полную информацию о товаре: изображение, атрибуты, цена
- Сравнивать предложения от разных поставщиков
- Понимать ценовые тиры (оптовые скидки)
- Добавлять товары в корзину

### 1.2 Пользователи
- **Покупатель (Buyer)** — основной пользователь страницы
- Преимущественно флористы, закупающие цветы для салонов

### 1.3 Ключевые сценарии

| Сценарий | Описание |
|----------|----------|
| Поиск товара | Быстрый текстовый поиск по названию, сорту |
| Фильтрация | Отбор по типу цветка, стране, цвету, размеру, цене |
| Просмотр карточки | Полная информация о товаре в карточке |
| Сравнение цен | Группировка по товару, сортировка по цене |
| Добавление в корзину | Выбор количества и добавление в корзину |

---

## 2. Функциональные требования

### 2.1 Текущее состояние (реализовано)

| Элемент | Статус | Описание |
|---------|--------|----------|
| Hero Section | ✅ | Баннер с заголовком |
| Поиск | ✅ | Текстовый поиск с debounce |
| Sidebar Layout | ✅ | 260px sidebar + content grid |
| Фильтр по типу | ✅ | Checkboxes в sidebar (rosa, carnation, etc.) |
| Фильтр по стране | ✅ | Checkboxes с флагами (EC, NL, CO, KE, RU) |
| Фильтр по цвету | ✅ | Color swatches grid |
| Фильтр по длине | ✅ | Range inputs (min/max) |
| Фильтр по цене | ✅ | Range inputs (min/max) |
| Только в наличии | ✅ | Toggle switch |
| Грид карточек | ✅ | 3 колонки на desktop (с sidebar) |
| Изображения | ✅ | По типу цветка (flowerImages.ts) |
| Страна | ✅ | Флаг + название (origin_country) |
| Цвета | ✅ | Через запятую (colors[]) |
| Упаковка | ✅ | pack_type + pack_qty |
| Цена | ✅ | price_min с ₽, compact layout |
| Остаток | ✅ | stock_qty справа от цены |
| Тир | ✅ | tier_min_qty/tier_max_qty под остатком |
| Поставщик | ✅ | supplier.name |
| Корзина | ✅ | Базовая функциональность |

### 2.2 Что нужно добавить

#### 2.2.1 Карточка товара — новые поля

| Поле | Источник | Описание |
|------|----------|----------|
| Страна | `attributes.origin_country` | Флаг + код (🇪🇨 EC, 🇳🇱 NL, 🇨🇴 CO) |
| Цвета | `attributes.colors[]` | Через запятую, минималистично |
| Упаковка | `pack_type` + `pack_qty` | "Бак 25 шт" / "Упак 10 шт" |
| Тир цены | `tier_min_qty` - `tier_max_qty` | "от 10 шт" / "10-50 шт" |

#### 2.2.2 Фильтры — расширение

| Фильтр | Тип | Источник данных |
|--------|-----|-----------------|
| Тип цветка | Checkbox | `normalized_skus.product_type` |
| Страна | Checkbox | `supplier_items.attributes.origin_country` |
| Цвет | Color picker/chips | `supplier_items.attributes.colors` |
| Длина | Range slider | `offers.length_cm` |
| Цена | Range slider | `offers.price_min` |
| Остаток | Toggle | `offers.stock_qty > 0` |

### 2.3 Группировка по товару (V2)

**Концепция:** Группировка offers по `normalized_sku_id` с отображением:
- Одна карточка на уникальный `тип + сорт`
- Показ диапазона цен от разных поставщиков
- Раскрытие для просмотра всех предложений

> **MVP:** Плоский список offers (текущая реализация)
> **V2:** Группировка по SKU

---

## 3. Дизайн карточки товара

### 3.1 Макет карточки (MVP)

```
┌─────────────────────────────────┐
│  ┌───────────────────────────┐  │
│  │                           │  │
│  │      [Изображение]        │  │
│  │       (по типу)           │  │
│  │                           │  │
│  └───────────────────────────┘  │
│                                 │
│  🇪🇨 Эквадор                    │  ← Страна с флагом
│                                 │
│  Роза Аваланш                   │  ← Название (display_title)
│  белый, кремовый                │  ← Цвета через запятую
│                                 │
│  60 см · Бак 25 шт              │  ← Длина · Упаковка
│  ───────────────────────────────│
│  85 ₽               Ост: 450   │  ← Цена слева, метрики справа
│                     от 50 шт   │  ← Тир под остатком (компактно)
│                                 │
│  ФлораОпт                       │  ← Поставщик (мелким)
│                                 │
│  [ - ] [ 10 ] [ + ]             │  ← Счётчик количества
│  [    В корзину    ]            │  ← Кнопка
└─────────────────────────────────┘
```

**Ключевые принципы:**
- Цена всегда слева, метрики (остаток, тир) справа — выровнены
- Тир отображается под остатком, минималистично
- Все карточки одинаковой высоты независимо от наличия тира

### 3.2 Цветовые индикаторы стран

```javascript
const COUNTRY_FLAGS = {
  'EC': { flag: '🇪🇨', name: 'Эквадор' },
  'NL': { flag: '🇳🇱', name: 'Нидерланды' },
  'CO': { flag: '🇨🇴', name: 'Колумбия' },
  'KE': { flag: '🇰🇪', name: 'Кения' },
  'RU': { flag: '🇷🇺', name: 'Россия' },
  'BY': { flag: '🇧🇾', name: 'Беларусь' },
};
```

### 3.3 Форматирование упаковки

```typescript
function formatPackInfo(packType: string | null, packQty: number | null): string {
  if (!packType && !packQty) return '';

  const typeMap: Record<string, string> = {
    'bak': 'Бак',
    'pack': 'Упак',
    'bunch': 'Пучок',
  };

  const type = typeMap[packType || ''] || packType || '';
  const qty = packQty ? `${packQty} шт` : '';

  return [type, qty].filter(Boolean).join(' ');
}
```

### 3.4 Форматирование тиров

```typescript
function formatTier(tierMin: number | null, tierMax: number | null): string {
  if (!tierMin && !tierMax) return '';
  if (tierMin && !tierMax) return `от ${tierMin} шт`;
  if (!tierMin && tierMax) return `до ${tierMax} шт`;
  return `${tierMin}–${tierMax} шт`;
}
```

---

## 4. API Изменения

### 4.1 Текущий OfferDetail

```python
class OfferDetail(BaseModel):
    id: UUID
    supplier: SupplierInfo
    sku: SKUInfo
    display_title: str | None
    length_cm: int | None
    pack_type: str | None
    pack_qty: int | None
    price_type: str
    price_min: Decimal
    price_max: Decimal | None
    currency: str
    tier_min_qty: int | None
    tier_max_qty: int | None
    availability: str
    stock_qty: int | None
    published_at: datetime
```

### 4.2 Новые поля (добавить)

```python
class OfferDetail(BaseModel):
    # ... existing fields ...

    # NEW: Атрибуты из supplier_item
    origin_country: str | None = None      # EC, NL, CO
    colors: list[str] = []                  # ["белый", "кремовый"]
```

### 4.3 Новые фильтры в GET /offers ✅ РЕАЛИЗОВАНО

| Параметр | Тип | Описание | Статус |
|----------|-----|----------|--------|
| `origin_country` | `list[str]` | Фильтр по странам (EC, NL, CO) | ✅ |
| `colors` | `list[str]` | Фильтр по цветам | ✅ |
| `in_stock` | `bool` | Только с остатком > 0 | ✅ |

**Реализация:**
- `origin_country` — фильтрует через JSONB `supplier_items.attributes['origin_country']`
- `colors` — фильтрует через JSONB array `supplier_items.attributes['colors']` (ANY match)
- `in_stock` — фильтрует `offers.stock_qty > 0`

### 4.4 Агрегация для фильтров (новый endpoint)

```
GET /offers/facets
```

**Response:**
```json
{
  "product_types": [
    { "value": "rose", "label": "Роза", "count": 44 },
    { "value": "carnation", "label": "Гвоздика", "count": 12 }
  ],
  "origin_countries": [
    { "value": "EC", "label": "Эквадор", "count": 38 },
    { "value": "NL", "label": "Нидерланды", "count": 15 }
  ],
  "colors": [
    { "value": "белый", "count": 22 },
    { "value": "красный", "count": 18 }
  ],
  "length_range": { "min": 40, "max": 90 },
  "price_range": { "min": 35, "max": 250 }
}
```

---

## 5. Frontend Компоненты

### 5.1 Структура файлов (реализовано)

```
frontend/src/features/catalog/
├── CatalogPage.tsx           # ✅ Sidebar layout + product grid
├── catalogApi.ts             # ✅ Filters: origin_country, colors, in_stock
├── filtersSlice.ts           # ✅ Extended state + actions
└── components/
    └── FilterSidebar.tsx     # ✅ Sidebar с фильтрами

frontend/src/utils/
└── catalogFormatters.ts      # ✅ getCountryFlag, formatPackInfo, formatTier, formatColors

frontend/src/types/
└── product.ts                # ✅ Extended ProductFilters interface
```

### 5.2 ProductCard Component

```tsx
interface ProductCardProps {
  offer: OfferDetail;
  onAddToCart: (offerId: string, quantity: number) => void;
}

export function ProductCard({ offer, onAddToCart }: ProductCardProps) {
  const [quantity, setQuantity] = useState(1);

  return (
    <Card className="flex flex-col h-full">
      {/* Image */}
      <div className="aspect-square bg-gray-100 rounded-lg mb-4 overflow-hidden flex items-end justify-center">
        <img
          src={getFlowerImage(offer.sku.product_type)}
          alt={offer.display_title || offer.sku.title}
          className="max-w-full max-h-full object-contain"
          loading="lazy"
        />
      </div>

      {/* Country */}
      {offer.origin_country && (
        <CountryFlag code={offer.origin_country} />
      )}

      {/* Title */}
      <h3 className="font-semibold text-gray-900 line-clamp-2">
        {offer.display_title || offer.sku.title}
      </h3>

      {/* Colors */}
      {offer.colors.length > 0 && (
        <p className="text-sm text-gray-600">
          {offer.colors.join(', ')}
        </p>
      )}

      {/* Length & Pack */}
      <p className="text-xs text-gray-500">
        {offer.length_cm && `${offer.length_cm} см`}
        {offer.length_cm && offer.pack_type && ' · '}
        {formatPackInfo(offer.pack_type, offer.pack_qty)}
      </p>

      {/* Price Block */}
      <div className="mt-auto pt-4">
        <div className="flex justify-between items-baseline">
          <span className="text-2xl font-bold text-primary-600">
            {offer.price_min} ₽
          </span>
          <span className="text-xs text-gray-500">
            {offer.stock_qty ? `Ост: ${offer.stock_qty}` : '—'}
          </span>
        </div>

        {/* Tier */}
        {(offer.tier_min_qty || offer.tier_max_qty) && (
          <TierBadge min={offer.tier_min_qty} max={offer.tier_max_qty} />
        )}

        {/* Supplier */}
        <p className="text-xs text-gray-400 mt-1">
          {offer.supplier.name}
        </p>

        {/* Quantity & Add */}
        <QuantitySelector value={quantity} onChange={setQuantity} />
        <Button onClick={() => onAddToCart(offer.id, quantity)}>
          В корзину
        </Button>
      </div>
    </Card>
  );
}
```

### 5.3 FilterPanel Component

```tsx
interface FilterPanelProps {
  facets: FacetsResponse;
  filters: CatalogFilters;
  onFilterChange: (filters: Partial<CatalogFilters>) => void;
}

export function FilterPanel({ facets, filters, onFilterChange }: FilterPanelProps) {
  return (
    <div className="space-y-6">
      {/* Product Type Pills */}
      <FilterSection title="Тип цветка">
        <div className="flex flex-wrap gap-2">
          {facets.product_types.map(type => (
            <FilterPill
              key={type.value}
              label={type.label}
              count={type.count}
              active={filters.product_type === type.value}
              onClick={() => onFilterChange({ product_type: type.value })}
            />
          ))}
        </div>
      </FilterSection>

      {/* Country Checkboxes */}
      <FilterSection title="Страна">
        {facets.origin_countries.map(country => (
          <FilterCheckbox
            key={country.value}
            label={`${getCountryFlag(country.value)} ${country.label}`}
            count={country.count}
            checked={filters.origin_countries?.includes(country.value)}
            onChange={(checked) => toggleCountry(country.value, checked)}
          />
        ))}
      </FilterSection>

      {/* Color Chips */}
      <FilterSection title="Цвет">
        <div className="flex flex-wrap gap-2">
          {facets.colors.map(color => (
            <FilterChip
              key={color.value}
              label={color.value}
              count={color.count}
              active={filters.colors?.includes(color.value)}
              onClick={() => toggleColor(color.value)}
            />
          ))}
        </div>
      </FilterSection>

      {/* Length Range */}
      <FilterSection title="Длина, см">
        <RangeSlider
          min={facets.length_range.min}
          max={facets.length_range.max}
          value={[filters.length_min, filters.length_max]}
          onChange={([min, max]) => onFilterChange({ length_min: min, length_max: max })}
        />
      </FilterSection>

      {/* Price Range */}
      <FilterSection title="Цена, ₽">
        <RangeSlider
          min={facets.price_range.min}
          max={facets.price_range.max}
          value={[filters.price_min, filters.price_max]}
          onChange={([min, max]) => onFilterChange({ price_min: min, price_max: max })}
        />
      </FilterSection>

      {/* In Stock Toggle */}
      <FilterToggle
        label="Только в наличии"
        checked={filters.in_stock}
        onChange={(checked) => onFilterChange({ in_stock: checked })}
      />
    </div>
  );
}
```

---

## 6. Данные из БД

### 6.1 Источники атрибутов

| Атрибут | Таблица | Поле | Пример |
|---------|---------|------|--------|
| Тип цветка | `normalized_skus` | `product_type` | "rose" |
| Сорт | `normalized_skus` | `variety` | "Avalanche" |
| Страна | `supplier_items` | `attributes->>'origin_country'` | "EC" |
| Цвета | `supplier_items` | `attributes->'colors'` | ["белый"] |
| Длина | `offers` | `length_cm` | 60 |
| Упаковка | `offers` | `pack_type`, `pack_qty` | "bak", 25 |
| Цена | `offers` | `price_min`, `price_max` | 85.00, null |
| Тир | `offers` | `tier_min_qty`, `tier_max_qty` | 50, null |
| Остаток | `offers` | `stock_qty` | 450 |

### 6.2 SQL для обогащения offers

```sql
-- Связь offer → supplier_item для получения атрибутов
SELECT
    o.*,
    si.attributes->>'origin_country' as origin_country,
    si.attributes->'colors' as colors
FROM offers o
JOIN sku_mappings sm ON sm.normalized_sku_id = o.normalized_sku_id
JOIN supplier_items si ON si.id = sm.supplier_item_id
WHERE o.supplier_id = si.supplier_id
  AND sm.status = 'confirmed';
```

### 6.3 Текущие данные (из анализа)

| Тип цветка | Кол-во | Страны | Цвета |
|-----------|--------|--------|-------|
| Роза | 44 | EC, NL, CO | белый, красный, розовый, жёлтый |
| Гвоздика | 2 | CO, NL | красный, микс |
| Гипсофила | 2 | EC | белый |
| Рускус | 2 | EC | зелёный |
| Альстромерия | 1 | CO | микс |
| Писташ | 1 | IL | зелёный |
| Протея | 1 | ZA | розовый |
| Эвкалипт | 1 | EC | зелёный |

---

## 7. План реализации

### Фаза 1: HTML Прототип ✅ ЗАВЕРШЕНО
- [x] Создать `prototype/catalog_page.html`
- [x] Дизайн карточки с новыми полями (страна, цвета, упаковка, тир)
- [x] Дизайн панели фильтров (checkboxes для типа и страны)
- [x] Компактный блок цены (цена слева, остаток+тир справа)
- [x] Мобильная адаптация

### Фаза 2: Backend API ✅ ЗАВЕРШЕНО
- [x] Добавить `origin_country`, `colors` в OfferDetail
- [x] Связать offers с supplier_items через sku_mappings
- [x] Добавить фильтры в GET /offers (origin_country, colors, in_stock)
- [ ] Создать endpoint GET /offers/facets (опционально для V2)

### Фаза 3: Frontend — Карточка ✅ ЗАВЕРШЕНО
- [x] Обновить CatalogPage с новым дизайном карточки
- [x] Добавить утилиты: catalogFormatters.ts (getCountryFlag, formatPackInfo, formatTier, formatColors)
- [x] Компактный price-block с выровненными метриками

### Фаза 4: Frontend — Фильтры ✅ ЗАВЕРШЕНО
- [x] Создать FilterSidebar компонент (sidebar 260px)
- [x] Расширить filtersSlice (origin_country[], colors[], in_stock, length_min, length_max)
- [x] Интегрировать в CatalogPage (flex layout: sidebar + content)
- [x] Добавить catalogApi с новыми filter parameters

### Фаза 5: Тестирование
- [ ] Unit тесты для форматирования
- [ ] Integration тесты для API
- [ ] E2E тест фильтрации

---

## 8. Критерии приёмки

1. **Карточка информативна** — все поля отображаются корректно
2. **Страна видна** — флаг + название для всех товаров с origin_country
3. **Цвета читаемы** — минималистичный список через запятую
4. **Упаковка понятна** — "Бак 25 шт" вместо raw данных
5. **Тиры объяснены** — "от 50 шт" рядом с ценой
6. **Фильтры работают** — комбинация фильтров сужает результат
7. **Сброс работает** — кнопка "Сбросить" очищает все фильтры
8. **Мобильная версия** — карточки и фильтры адаптивны

---

## 9. Ссылки

- **Текущая реализация:** `frontend/src/features/catalog/CatalogPage.tsx`
- **API offers:** `apps/api/routers/offers.py`
- **Модели:** `apps/api/models/normalized.py`, `apps/api/models/items.py`
- **Изображения:** `frontend/src/utils/flowerImages.ts`
- **Seller Cabinet (референс):** `docs/tasks/SELLER_CABINET_SPEC.md`
