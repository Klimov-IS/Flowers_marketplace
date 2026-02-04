# ТЗ: Кабинет Продавца — Страница Ассортимента

## Статус: Фаза 1-4 завершены (Backend + Frontend + Модалы)
## Прототип: `prototype/seller_cabinet.html`

---

## 1. Бизнес-требования

### 1.1 Цель
Создать операционную страницу для управления ассортиментом продавца, где он может:
- Видеть все свои товары в едином табличном интерфейсе
- Отслеживать статус каждой позиции (активна, на проверке, ошибка)
- Загружать и обновлять прайс-листы
- Просматривать детали по каждому товару с вариантами (размеры/упаковки)

### 1.2 Пользователи
- **Продавец (Supplier)** — основной пользователь страницы
- Должен быть авторизован с ролью `supplier`

### 1.3 Ключевые сценарии

| Сценарий | Описание |
|----------|----------|
| Просмотр ассортимента | Продавец видит таблицу со всеми своими товарами |
| Поиск товара | Фильтрация по названию, стране, цвету |
| Раскрытие вариантов | Клик на стрелку показывает все варианты (размер/упаковка/цена) |
| Загрузка прайса | Модальное окно для загрузки CSV/XLSX файла |
| Просмотр деталей | Модальное окно с полной информацией о товаре |

---

## 2. Функциональные требования

### 2.1 Навигация (Header)
- Логотип "Flower Market" (ссылка на главную)
- Навигационные ссылки: Витрина, Кабинет покупателя, **Кабинет продавца** (активный)
- Бейдж пользователя: роль + название компании
- Кнопка "Выйти"

### 2.2 Табы
| Таб | Описание | Бейдж |
|-----|----------|-------|
| Ассортимент | Основная таблица товаров | — |
| Проверка | Товары на ручной проверке | Кол-во |
| Ошибки | Ошибки парсинга | Кол-во (красный) |
| История импорта | Список загрузок прайсов | — |

### 2.3 Таблица ассортимента

#### Колонки (в порядке отображения)
| # | Колонка | Ширина | Описание |
|---|---------|--------|----------|
| 1 | Expand | 40px | Кнопка раскрытия вариантов (если >1 варианта) |
| 2 | Название | 18% | `supplier_item.raw_name` |
| 3 | Страна | 10% | `supplier_item.attributes.origin_country` (код: EC, NL, CO...) |
| 4 | Цвет | 12% | Цветные квадратики с тултипом |
| 5 | Размеры | 12% | Диапазон `min–max см` из вариантов |
| 6 | Упаковка | 12% | Тип упаковки (Бак/Упак/—) |
| 7 | Цена ₽ | 12% | Диапазон `min–max` из вариантов |
| 8 | Остаток | 12% | Число + цветной индикатор |
| 9 | Действия | 12% | Иконки: Детали, Редактировать, Скрыть |

#### Раскрываемая строка (Expanded Row)
При клике на стрелку под основной строкой появляется вложенная таблица:
| Размер | Упаковка | Цена ₽ | Остаток | Статус |
|--------|----------|--------|---------|--------|
| 40 см | Бак | 62 | 50 | ok |
| 40 см | Упак | 67 | 80 | ok |
| ... | | | | |

### 2.4 Цветовые индикаторы

#### Цвета товаров
```javascript
const COLORS = {
    'белый': '#ffffff',
    'красный': '#e53935',
    'розовый': '#ec407a',
    'жёлтый': '#fdd835',
    'оранжевый': '#ff9800',
    'фиолетовый': '#9c27b0',
    'синий': '#1e88e5',
    'зелёный': '#43a047',
    'микс': 'linear-gradient(...)'
};
```

#### Индикатор остатков
| Уровень | Условие | Цвет |
|---------|---------|------|
| high | stock >= 50 | Зелёный |
| medium | 20 <= stock < 50 | Жёлтый |
| low | 0 < stock < 20 | Красный |
| none | stock = 0 | Серый |

### 2.5 Поиск
- Поле ввода с иконкой поиска
- Фильтрация по: `raw_name`, `colors`, `origin`
- Фильтрация в реальном времени (debounce 300ms)

### 2.6 Модальное окно загрузки прайса

#### Состояния
1. **Initial** — Drag&drop зона + кнопка выбора файла
2. **Processing** — Спиннер + прогресс-бар
3. **Result** — Статистика: обработано, успешно, на проверку, ошибок

#### Поддерживаемые форматы
- CSV
- XLSX
- XLS
- TXT

### 2.7 Модальное окно деталей товара

#### Секция "Исходные данные"
- Raw Name
- Источник (файл)
- Строка в файле

#### Секция "Нормализованные данные"
- Название
- Цвета (через запятую)
- Страна
- Источник

#### Секция "Варианты"
Таблица со всеми `offer_candidates` для данного `supplier_item`

---

## 3. API Endpoints

### 3.1 Получение ассортимента ✅ РЕАЛИЗОВАНО
```
GET /admin/suppliers/{supplier_id}/items
```

**Query Parameters:**
| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `q` | string | null | Поиск по названию (raw_name, name_norm) |
| `page` | int | 1 | Номер страницы (1-based) |
| `per_page` | int | 50 | Элементов на странице (max 100) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "raw_name": "Роза Аваланш",
      "origin_country": "EC",
      "colors": ["белый"],
      "length_min": 40,
      "length_max": 60,
      "price_min": "62.00",
      "price_max": "95.00",
      "stock_total": 450,
      "status": "active",
      "source_file": "price_dec_2025.csv",
      "variants_count": 3,
      "variants": [
        {
          "id": "uuid",
          "length_cm": 40,
          "pack_type": "bak",
          "pack_qty": 25,
          "price": "62.00",
          "price_max": null,
          "stock": 50,
          "validation": "ok"
        }
      ]
    }
  ],
  "total": 30,
  "page": 1,
  "per_page": 50
}
```

**Реализация:** [apps/api/routers/admin.py](apps/api/routers/admin.py#L172-L329)

### 3.2 Поиск ✅ РЕАЛИЗОВАНО
```
GET /admin/suppliers/{supplier_id}/items?q=роза
```
Поддерживает поиск по `raw_name` и `name_norm` (case-insensitive)

### 3.3 Загрузка прайса
```
POST /api/suppliers/{supplier_id}/imports
Content-Type: multipart/form-data

file: <binary>
```

**Response:**
```json
{
  "batch_id": "uuid",
  "status": "processing"
}
```

### 3.4 Статус импорта
```
GET /api/imports/{batch_id}/status
```

**Response:**
```json
{
  "batch_id": "uuid",
  "status": "completed",
  "rows_total": 127,
  "rows_success": 118,
  "rows_review": 6,
  "rows_error": 3
}
```

### 3.5 Детали товара
```
GET /api/supplier-items/{item_id}
```

---

## 4. Модели данных

### 4.1 SupplierItem (существует)
```python
class SupplierItem:
    id: UUID
    supplier_id: UUID
    stable_key: str
    raw_name: str
    name_norm: str
    attributes: dict  # {"origin_country": "EC", "colors": ["белый"]}
    status: str  # "active", "review", "error", "hidden"
    last_import_batch_id: UUID
```

### 4.2 OfferCandidate (существует)
```python
class OfferCandidate:
    id: UUID
    supplier_item_id: UUID
    length_cm: int
    pack_type: str  # "bak", "pack", None
    price_min: Decimal
    price_max: Decimal
    stock_qty: int
    validation: str  # "ok", "warning", "error"
```

### 4.3 Новое: Цвета в attributes
Добавить поле `colors` в `attributes` supplier_item:
```json
{
  "origin_country": "EC",
  "colors": ["белый", "розовый"]
}
```

---

## 5. Frontend компоненты

### 5.1 Структура файлов
```
frontend/src/features/seller/
├── SellerCabinetPage.tsx       # Основная страница
├── components/
│   ├── AssortmentTable.tsx     # Таблица товаров
│   ├── AssortmentRow.tsx       # Строка таблицы
│   ├── ExpandedRow.tsx         # Раскрытые варианты
│   ├── ColorSquares.tsx        # Цветовые квадратики
│   ├── StockIndicator.tsx      # Индикатор остатков
│   ├── UploadModal.tsx         # Модал загрузки
│   ├── DetailsModal.tsx        # Модал деталей
│   └── TabsNav.tsx             # Навигация по табам
├── hooks/
│   └── useSupplierItems.ts     # Хук для загрузки данных
├── api/
│   └── supplierApi.ts          # RTK Query endpoints
└── types.ts                    # TypeScript типы
```

### 5.2 Основные компоненты

#### SellerCabinetPage
```tsx
export default function SellerCabinetPage() {
  const [activeTab, setActiveTab] = useState('assortment');
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  return (
    <div className="seller-cabinet">
      <TabsNav activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'assortment' && (
        <>
          <SearchBar value={searchQuery} onChange={setSearchQuery} />
          <AssortmentTable searchQuery={searchQuery} />
        </>
      )}

      <UploadModal open={uploadModalOpen} onClose={() => setUploadModalOpen(false)} />
    </div>
  );
}
```

---

## 6. Стили (Tailwind + CSS Variables)

### 6.1 CSS Variables (из прототипа)
```css
:root {
    --bg-primary: #ffffff;
    --bg-secondary: #f7f7f5;
    --bg-hover: #f1f1ef;
    --text-primary: #37352f;
    --text-secondary: #6b6b6b;
    --border-color: #e9e9e7;
    --primary: #2383e2;
    --success: #0f7b6c;
    --warning: #d9730d;
    --error: #e03e3e;
}
```

### 6.2 Ключевые классы
- `.data-table` — основная таблица
- `.color-square` — квадратик цвета (16x16px, border-radius: 3px)
- `.stock-indicator` — индикатор остатков с точкой
- `.expand-btn` — кнопка раскрытия строки

---

## 7. План реализации

### Фаза 1: Backend API ✅ ЗАВЕРШЕНО
- [x] Эндпоинт GET /admin/suppliers/{id}/items с пагинацией и поиском
- [x] Pydantic схемы: `SupplierItemResponse`, `OfferVariantResponse`, `SupplierItemsListResponse`
- [x] Агрегация вариантов (price range, length range, stock total)
- [x] Интеграционные тесты: `tests/integration/test_supplier_items.py`
- [ ] Добавить colors в attributes при парсинге (зависит от формата прайса)

### Фаза 2: Frontend — Базовая страница ✅ ЗАВЕРШЕНО
- [x] Обновить SellerDashboard с табами (Ассортимент, Заказы, Загрузка)
- [x] Реализовать TabsNav компонент
- [x] Реализовать AssortmentTable с раскрываемыми строками
- [x] Добавить RTK Query endpoint `getSupplierItems`

### Фаза 3: Frontend — Расширенный функционал ✅ ЗАВЕРШЕНО
- [x] Раскрываемые строки с вариантами (ExpandedRow)
- [x] Поиск с debounce (SearchBar + useDebounce)
- [x] ColorSquares компонент с цветовыми квадратиками
- [x] StockIndicator компонент с индикаторами остатков
- [x] Пагинация

### Фаза 4: Модальные окна ✅ ЗАВЕРШЕНО
- [x] UploadModal с drag&drop (PriceListUpload — уже существовал)
- [x] DetailsModal с информацией о товаре (ItemDetailsModal)

### Фаза 5: Интеграция и тестирование
- [x] Подключение к API через RTK Query
- [ ] Тестирование всех сценариев
- [ ] Исправление багов

---

## 8. Критерии приёмки

1. **Таблица отображает данные** — все колонки заполнены корректно
2. **Поиск работает** — фильтрация происходит в реальном времени
3. **Раскрытие работает** — клик показывает/скрывает варианты
4. **Загрузка прайса** — файл загружается и обрабатывается
5. **Цвета корректны** — квадратики показывают правильные цвета
6. **Остатки корректны** — индикаторы отображают правильный уровень
7. **Мобильная версия** — страница читаема на планшете (опционально)

---

## 9. Реализованные файлы

### Фаза 1: Backend API
| Файл | Описание |
|------|----------|
| `apps/api/routers/admin.py` | Эндпоинт GET /admin/suppliers/{id}/items (строки 172-329) |
| `tests/integration/test_supplier_items.py` | Интеграционные тесты для эндпоинта |

### Фаза 2-3: Frontend
| Файл | Описание |
|------|----------|
| `frontend/src/types/supplierItem.ts` | TypeScript типы для SupplierItem, OfferVariant |
| `frontend/src/features/seller/supplierApi.ts` | RTK Query endpoint getSupplierItems |
| `frontend/src/features/seller/SellerDashboard.tsx` | Обновлённый дашборд с табами |
| `frontend/src/features/seller/components/TabsNav.tsx` | Компонент навигации по табам |
| `frontend/src/features/seller/components/AssortmentTab.tsx` | Таб ассортимента с поиском и пагинацией |
| `frontend/src/features/seller/components/AssortmentTable.tsx` | Таблица товаров с раскрываемыми строками |
| `frontend/src/features/seller/components/ColorSquares.tsx` | Цветные квадратики |
| `frontend/src/features/seller/components/StockIndicator.tsx` | Индикатор остатков |
| `frontend/src/features/seller/components/SearchBar.tsx` | Поле поиска |

### Фаза 4: Модальные окна
| Файл | Описание |
|------|----------|
| `frontend/src/features/seller/components/ItemDetailsModal.tsx` | Модал с деталями товара |

---

## 10. Ссылки

- **Прототип:** `prototype/seller_cabinet.html`
- **Стили прототипа:** `prototype/styles.css`
- **JS прототипа:** `prototype/app.js`
- **Модель данных:** `docs/architecture/CORE_DATA_MODEL.md`
- **API архитектура:** `docs/architecture/ADMIN_API.md`
