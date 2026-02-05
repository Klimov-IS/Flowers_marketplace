# 🧠 NORMALIZATION_RULES — MVP (Dictionary-driven + Manual Review)

## 0) Цель

Стабильно сопоставлять позиции поставщиков (`supplier_items`) с каноническими SKU (`normalized_skus`), чтобы:
- публиковать офферы (`offers`) только после confirmed mapping,
- быстро чинить качество данных через словарь (без правок raw),
- иметь управляемый ручной разбор (очередь задач).

---

## 1) Принципиальные решения MVP

1) **SKU ≠ Offer**
- SKU — “что это за товар” (тип + сорт/линейка + опционально цвет/подтип).
- Offer — “как продаётся” (длина, упаковка, кратность, цена, тиры).

2) **Длина по умолчанию хранится в Offer**, а не в SKU.  
Исключение: если рынок у заказчика требует SKU “Роза 60см Explorer” как отдельную карточку — тогда включаем length в SKU (но это усложняет каталог).

3) Нормализация управляется **словарём (dictionary_entries)** + ручным подтверждением.

---

## 2) Каноническая модель SKU (что именно нормализуем)

### 2.1 Поля normalized_sku (MVP)
- `product_type` (обяз.) — rose / carnation / alstroemeria / chrysanthemum / greens / packaging / etc.
- `variety` (желательно) — сорт/линейка (Explorer, Mondial, Pink Floyd…)
- `color` (опц.) — если реально стабильно встречается в данных
- `title` — человекочитаемый заголовок
- `meta` (json) — доп. атрибуты:
  - `subtype`: spray / bush / standard / premium / etc
  - `origin_default`: Ecuador / Colombia / Netherlands / Kenya / Israel (если для SKU важно)
  - `brand_farm`: PIANGOFLOR / FRAMA FLOWERS (если влияет на сущность)

> В MVP: страна/ферма чаще идут как атрибут Offer/Source, а не SKU.  
Но допускаем хранение в meta, если заказчик требует “разные поставщики” не смешивать.

---

## 3) Dictionary и иерархический каталог цветов

### 3.0 Иерархический каталог цветов (NEW)

Помимо `dictionary_entries`, система использует **иерархический каталог цветов** для более точной нормализации:

```
flower_categories (опционально)
    └── flower_types (Роза, Хризантема, Эвкалипт)
          ├── flower_subtypes (Кустовая, Спрей, Пионовидная)
          │     └── subtype_synonyms
          ├── type_synonyms (роза, розы, rose → Роза)
          └── flower_varieties (Explorer, Freedom, Red Naomi)
                └── variety_synonyms (эксплорер → Explorer)
```

**Преимущества иерархического каталога:**
- Субтипы привязаны к типам (кустовая роза vs кустовая хризантема)
- Сорта связаны с типом/субтипом
- Синонимы хранятся в отдельных таблицах с индексами
- Триграммный индекс для fuzzy search сортов
- Редактирование через админку без изменения кода

**API каталога:** `GET /admin/catalog/lookup` — возвращает словари для парсера.

### 3.1 dictionary_entries (legacy)

`dictionary_entries` хранит "управляемые знания" для нормализации (цвета, страны, pack_type).

**Общая структура записи:**
- `dict_type`: строка (тип словаря)
- `key`: ключ
- `value`: каноническое значение
- `synonyms`: массив синонимов
- `rules`: json с правилами (regex/replace/extract)
- `status`: active/deprecated

> **Note:** Типы цветов (product_type) теперь управляются через `flower_types` + `type_synonyms`.
> `dictionary_entries` остаётся для: country, pack_type, stopwords, regex_rule, variety_alias.

### 3.2 Набор dict_type для MVP

> **UPDATE:** `product_type` теперь управляется через `flower_types` + `type_synonyms`.
> Используйте API `/admin/catalog/types` для добавления новых типов цветов.

1) ~~`product_type`~~ → **Перенесено в `flower_types`**
- Используйте `/admin/catalog/types` для управления
- Пример: "Роза" с синонимами ["роза", "розы", "rose", "roses"]

2) `country`
- key: "эквадор"
- value: "Ecuador"
- synonyms: ["ecuador", "(эквадор)", "экв."]

3) `pack_type`
- key: "бак"
- value: "bak"
- synonyms: ["бак.", "bucket", "ведро"]
- key: "упак"
- value: "pack"
- synonyms: ["упак.", "упаковка", "bunch", "box"]

4) `stopwords`
- key/value: одно значение (удаляемые токены)
- примеры: ["импорт", "сортовые", "поставка", "цена", "руб", "р", "см", "cm"]

5) `regex_rule`
- правила извлечения атрибутов (см. блок 4)

6) `variety_alias`
- для популярных сортов: key=любой вариант написания → value=канон
- пример: key="mondial" value="Mondial" synonyms=["мондиаль","mondial®"]

> На старте `variety_alias` можно наполнять по мере ручного разбора топ-100 сортов.

---

## 4) Извлечение атрибутов (parsing rules)

**Важно:** часть атрибутов (length, pack_type) может прийти уже в `offer_candidates` из матриц/тиров.  
Тогда из `raw_name` их не извлекаем повторно, а используем как “source of truth”.

### 4.1 Нормализация текста (preprocess)
Перед любыми правилами:
- lower()
- trim
- заменить "–" и "—" на "-"
- заменить множественные пробелы на один
- убрать служебные символы (таб/переводы строк)
- унифицировать "см" / "cm"
- удалить валюту: "руб", "р", "₽" (если попало в name)

### 4.2 Regex: длина (length_cm)
Используем только если length_cm ещё не заполнен в offer_candidate:

- `(?<!\d)(\d{2,3})\s*(см|cm)\b`
- `\b(\d{2,3})\s*см\b`
- `\b(\d{2,3})\b(?=\s*см)` (упрощённо)

Пост-валидация:
- допустимые длины: 30–120 (иначе warn)

### 4.3 Regex: страна (origin_country)
- `\((эквадор|колумбия|голландия|нидерланды|кения|израиль)\)`
- `\b(эквадор|колумбия|голландия|нидерланды|кения|израиль)\b`
Маппим через dict_type=country.

### 4.4 Regex: упаковка (pack_qty / pack_type)
- pack_qty:
  - `\((\d{1,3})\)\s*$`  (в конце)
  - `\((\d{1,3})\s*шт\)`  
  - `\b(\d{1,3})\s*шт\b` (осторожно: может быть “100 шт” как tier — не путать)
- pack_type:
  - `\b(бак|упак)\b` или из заголовков матрицы

Пост-логика:
- если `pack_qty` в пределах 5–50 → трактуем как “кратность/упаковка”
- если большие числа (>=80) рядом с “шт” → вероятно tier, не pack_qty (warn)

### 4.5 Regex: подтип/качество/форма (subtype/grade)
Ключевые маркеры:
- `спрей|spray` → subtype=spray
- `кустовая` → subtype=bush
- `стандарт|standard` → grade=standard
- `премиум|premium` → grade=premium
- `микс|mix` → subtype=mix (требует осторожности, часто это не SKU)

---

## 5) Алгоритм propose (автопредложение маппинга)

Вход: `supplier_item` (raw_name, raw_group, name_norm, attributes)  
Выход: записи `sku_mappings` со status=proposed и confidence.

### 5.1 Шаги propose
1) **Context merge**
- берём `raw_group` (категория/страна/раздел) как контекст токенов
- объединяем с `raw_name`

2) **Extract attributes**
- применяем regex_rule: длина/страна/упаковка/подтип/grade/бренд
- сохраняем в `supplier_items.attributes`

3) **Detect product_type** (из иерархического каталога)
Приоритет:
- из raw_group (если он "Розы/Гвоздика/Зелень/…")
- иначе по `flower_types` + `type_synonyms` (из БД с кэшем TTL=5мин)
- fallback на hardcoded FLOWER_TYPES_FALLBACK

4) **Detect subtype** (NEW)
- После определения type_id ищем субтип в `flower_subtypes` + `subtype_synonyms`
- Примеры: "кустовая" → "Кустовая", "спрей" → "Спрей"

5) **Detect variety**
- если встречаются латинские токены (Explorer, Mondial, Pink Floyd…), используем их как первичную variety
- затем прогоняем через `flower_varieties` + `variety_synonyms` (если есть в каталоге)
- fallback на `variety_alias` из dictionary_entries
- если variety не уверена → оставляем NULL и отправляем на manual-review (если product_type тоже не уверен)

6) **Candidate search в normalized_skus**
Методы (по приоритету):
- Exact match: (product_type + variety) совпали по нормализованному виду
- High similarity (trgm): сравнение с title/variety
- Token overlap: пересечение токенов (без стоп-слов)

7) **Create/Update sku_mappings**
- создаём 1..N предложений (N<=5) для ручного выбора
- лучший кандидат идёт с максимальным confidence

---

## 6) Confidence scoring (простая модель MVP)

Цель: ранжировать предложения и решать, что уходит в ручной разбор.

### 6.1 Базовый скор
`score = 0.10`

### 6.2 Прибавки
- product_type совпал (по словарю) → `+0.30`
- variety exact (после alias) → `+0.45`
- variety high similarity (trgm >= 0.70) → `+0.30`
- subtype совпал (spray/bush/standard/premium) → `+0.05`
- country совпал (если учитываем) → `+0.05`
- исторически уже был confirmed mapping для похожего stable_key (если есть) → `+0.15`

### 6.3 Штрафы
- variety содержит “микс/mix” → `-0.25`
- name слишком короткое / мало токенов → `-0.10`
- конфликт: продукт-тип роза, но токены гвоздика → `-0.20`

### 6.4 Пороги
- `score >= 0.90` → можно **auto-confirm (опционально флагом)**  
  (по умолчанию всё равно proposed, но ставим high_priority_review=false)
- `0.70 <= score < 0.90` → proposed → обычный review
- `score < 0.70` → создаём `normalization_task` (manual обязательно)

---

## 7) Manual-review (очередь задач)

### 7.1 Когда создаём normalization_task
- product_type не определён
- variety не определена
- score < 0.70
- несколько кандидатов с близкими score (например, разница < 0.05)
- supplier_item помечен ambiguous

### 7.2 Приоритет (priority)
MVP-приоритет считаем так:
- base = 100
- + (кол-во offer_candidates по supplier_item) * 2
- + 50 если supplier важный (ручная метка в suppliers.meta: `tier=key`)
- + 20 если item встречается в нескольких прайсах (stable_key повторяется)
- - 30 если это “служебное/мусор” (stopwords/комментарии)

### 7.3 Экран админки “Разбор”
Для каждой задачи показываем:
- raw_name, raw_group
- примеры raw_rows (row_ref + raw_text)
- extracted attributes
- top-5 предложенных normalized_sku (title + score)
- кнопки:
  - Confirm выбранный
  - Create new SKU
  - Edit dictionary (в модальном)
  - Reject item (если мусор)

### 7.4 Действия при подтверждении
- sku_mappings.status → confirmed
- sku_mappings.decided_at/by фиксируем
- запускаем republish для соответствующего supplier (см. pipeline publish)

---

## 8) Стратегия создания новых SKU (Create SKU)

Правило MVP:  
Если variety уникальна и повторяется, лучше создать SKU.

### 8.1 Когда создавать SKU
- Есть product_type + variety (или subtype), но в каталоге отсутствует
- Это не “микс”
- Это не “разовое служебное”

### 8.2 Как формировать title
- `Rose Explorer`
- `Carnation Standard`
- `Alstroemeria Garda`
- `Greens Eucalyptus` (если есть)

meta можно наполнить:
- subtype/grade
- origin_default (если строго по рынку)

---

## 9) Примеры (из типовых прайсов)

### Пример 1
`"Роза Explorer 60см (Эквадор)"`
- product_type=rose
- variety=Explorer
- origin=Ecuador (в attributes)
- length_cm=60 (в offer)
→ mapping: Rose Explorer

### Пример 2 (матрица)
строка: `"Роза спрей: Bombastic, ..."`
колонки: `50 см бак`, `50 см упак`, `60 см бак`...
- supplier_item = “Роза спрей Bombastic …” (SAFE MODE: пока bundle)
- offer_candidates = N строк по (length_cm, pack_type)
→ manual-review: либо разнести на сорта, либо создать bundle SKU “Spray Roses Mix” (если реально так продаётся)

### Пример 3 (тиры)
`"Роза ..."` + цены по “от 100 до 200”
- offer_candidates: несколько строк с tier_min_qty/max_qty
- SKU маппится 1 раз, офферы публикуются пачкой

---

## 10) Перепубликация и “эффект словаря”

Когда:
- обновили dictionary_entries
- подтвердили sku_mappings
- поправили supplier_item.attributes

Должно быть возможно:
- пересчитать propose для open tasks
- пересобрать offers (publish stage) без повторного raw import

---

## 11) Минимальный набор словарей для старта (bootstrap checklist)

1) product_type: роза, гвоздика, альстромерия, хризантема, зелень, упаковка
2) country: Эквадор, Колумбия, Голландия/Нидерланды, Кения, Израиль
3) pack_type: бак, упак
4) stopwords: импорт, сортовые, руб/р/₽, см/cm, цена, прайс, лист
5) regex_rule: длина, страна, pack_qty, subtype/grade

---

## 12) Детальный алгоритм нормализации (Implementation Reference)

### 12.1 Модули

Реализация находится в `packages/core/normalization/`:

| Модуль | Назначение |
|--------|------------|
| `tokens.py` | Токенизация и нормализация текста |
| `detection.py` | Определение product_type, variety, subtype |
| `confidence.py` | Расчёт confidence score |

### 12.2 Токенизация (tokens.py)

#### normalize_tokens(text: str) → str

```python
def normalize_tokens(text: str) -> str:
    """
    Нормализация текста для matching.

    Шаги:
    1. Lowercase
    2. Trim
    3. Удалить валютные символы (₽$€)
    4. Заменить em/en dash на hyphen
    5. Удалить спецсимволы (оставить буквы, цифры, пробелы)
    6. Нормализовать пробелы
    """
    normalized = text.lower().strip()
    normalized = re.sub(r"[₽$€]", "", normalized)
    normalized = normalized.replace("–", "-").replace("—", "-")
    normalized = re.sub(r"[^\w\s\-()]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
```

**Пример:**
```
Input:  "Роза Explorer 60см  (Эквадор) — 120₽"
Output: "роза explorer 60см (эквадор) - 120"
```

#### extract_latin_tokens(text: str) → List[str]

```python
def extract_latin_tokens(text: str) -> List[str]:
    """
    Извлечение латинских токенов (потенциальные названия сортов).

    Pattern: Capitalized Latin words
    """
    pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
    return re.findall(pattern, text)
```

**Пример:**
```
Input:  "Роза Explorer Pink Floyd 60см"
Output: ["Explorer", "Pink Floyd"]
```

### 12.3 Detection (detection.py)

#### detect_product_type(text, product_type_dict) → Optional[str]

```python
def detect_product_type(text: str, product_type_dict: dict) -> Optional[str]:
    """
    Определение типа продукта по словарю.

    Алгоритм:
    1. Для каждого product_type в словаре
    2. Проверить value и все synonyms
    3. Вернуть первое совпадение
    """
    text_lower = text.lower()

    for key, entry in product_type_dict.items():
        value = entry.get("value", key)
        synonyms = entry.get("synonyms", [])

        if value.lower() in text_lower:
            return value

        for synonym in synonyms:
            if synonym.lower() in text_lower:
                return value

    return None
```

**Пример словаря:**
```python
product_type_dict = {
    "роза": {
        "value": "rose",
        "synonyms": ["rose", "розы", "roses", "роза спрей", "кустовая роза"]
    },
    "гвоздика": {
        "value": "carnation",
        "synonyms": ["carnation", "гвоздики", "dianthus"]
    }
}
```

#### detect_variety(raw_name, variety_alias_dict) → Optional[str]

```python
def detect_variety(raw_name: str, variety_alias_dict: dict = None) -> Optional[str]:
    """
    Определение сорта.

    Алгоритм:
    1. Извлечь латинские токены
    2. Если есть variety_alias_dict - поиск по алиасам
    3. Иначе вернуть первый латинский токен
    """
    latin_tokens = extract_latin_tokens(raw_name)

    if not latin_tokens:
        return None

    # Поиск по алиасам
    if variety_alias_dict:
        for token in latin_tokens:
            for key, entry in variety_alias_dict.items():
                if token.lower() == key.lower():
                    return entry.get("value", key)
                for synonym in entry.get("synonyms", []):
                    if token.lower() == synonym.lower():
                        return entry.get("value", key)

    return latin_tokens[0]
```

#### detect_subtype(text, regex_rules) → Optional[str]

```python
def detect_subtype(text: str, regex_rules: list) -> Optional[str]:
    """
    Определение подтипа по regex правилам.

    Правила задаются в словаре dict_type=regex_rule.
    """
    for rule in regex_rules:
        pattern = rule.get("pattern")
        result = rule.get("result")

        if re.search(pattern, text, re.IGNORECASE):
            return result

    return None
```

**Пример правил:**
```python
regex_rules = [
    {"pattern": r"\bспрей\b|\bspray\b", "result": "spray"},
    {"pattern": r"\bкустовая\b|\bbush\b", "result": "bush"},
    {"pattern": r"\bстандарт\b|\bstandard\b", "result": "standard"},
    {"pattern": r"\bпремиум\b|\bpremium\b", "result": "premium"},
]
```

### 12.4 Confidence Scoring (confidence.py)

#### Формула расчёта confidence

```
confidence = BASE + Σ(positive_signals) - Σ(penalties)
confidence = clamp(confidence, 0.0, 1.0)
```

#### Таблица весов

| Сигнал | Вес | Условие |
|--------|-----|---------|
| **Base** | +0.10 | Всегда |
| **product_type_match** | +0.30 | Тип продукта найден в словаре |
| **variety_exact** | +0.45 | Точное совпадение сорта |
| **variety_high** | +0.30 | Высокое сходство (≥70% overlap или inclusion) |
| **variety_low** | +0.10 | Низкое сходство (40-70% overlap) |
| **subtype_match** | +0.05 | Подтип совпал (spray/bush/etc) |
| **country_match** | +0.05 | Страна совпала |
| **has_mix_keyword** | -0.25 | Текст содержит "микс/mix" |
| **name_too_short** | -0.10 | Меньше 3 токенов |
| **conflicting_type** | -0.20 | Противоречивые сигналы типа |

#### calculate_confidence() — полная реализация

```python
def calculate_confidence(
    product_type_match: bool = False,
    variety_match: str = None,   # "exact" | "high" | "low" | None
    subtype_match: bool = False,
    country_match: bool = False,
    has_mix_keyword: bool = False,
    name_too_short: bool = False,
    conflicting_product_type: bool = False,
) -> Decimal:
    """
    Расчёт confidence score для SKU mapping.
    """
    score = Decimal("0.10")  # Base

    # Positive signals
    if product_type_match:
        score += Decimal("0.30")

    if variety_match == "exact":
        score += Decimal("0.45")
    elif variety_match == "high":
        score += Decimal("0.30")
    elif variety_match == "low":
        score += Decimal("0.10")

    if subtype_match:
        score += Decimal("0.05")

    if country_match:
        score += Decimal("0.05")

    # Penalties
    if has_mix_keyword:
        score -= Decimal("0.25")

    if name_too_short:
        score -= Decimal("0.10")

    if conflicting_product_type:
        score -= Decimal("0.20")

    # Clamp [0.0, 1.0]
    return max(Decimal("0"), min(Decimal("1"), score))
```

#### variety_similarity(v1, v2) → str

```python
def variety_similarity(variety1: str, variety2: str) -> str:
    """
    Категория сходства сортов.

    Returns: "exact" | "high" | "low" | "none"
    """
    v1, v2 = variety1.lower(), variety2.lower()

    # Exact match
    if v1 == v2:
        return "exact"

    # One contains the other
    if v1 in v2 or v2 in v1:
        return "high"

    # Token overlap
    tokens1, tokens2 = set(v1.split()), set(v2.split())
    overlap = len(tokens1 & tokens2)
    total = len(tokens1 | tokens2)
    similarity = overlap / total if total > 0 else 0.0

    if similarity >= 0.7:
        return "high"
    elif similarity >= 0.4:
        return "low"
    else:
        return "none"
```

### 12.5 Примеры расчёта confidence

#### Пример 1: Высокий confidence

```
raw_name: "Роза Explorer 60см (Эквадор)"

Сигналы:
- product_type_match = True (роза → rose)     +0.30
- variety_match = "exact" (Explorer)          +0.45
- country_match = True (Эквадор)              +0.05
- Base                                        +0.10
─────────────────────────────────────────────
Total: 0.90 (HIGH - auto-confirm candidate)
```

#### Пример 2: Средний confidence

```
raw_name: "Роза красная 50см"

Сигналы:
- product_type_match = True                   +0.30
- variety_match = None                         0.00
- Base                                        +0.10
─────────────────────────────────────────────
Total: 0.40 (LOW - manual review required)
```

#### Пример 3: Низкий confidence с penalty

```
raw_name: "Микс роз"

Сигналы:
- product_type_match = True                   +0.30
- has_mix_keyword = True                      -0.25
- name_too_short = True                       -0.10
- Base                                        +0.10
─────────────────────────────────────────────
Total: 0.05 (VERY LOW - likely bundle/mix)
```

### 12.6 Полный flow нормализации

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    NormalizationService.propose()                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUT: SupplierItem (raw_name, raw_group, attributes)                 │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. TOKENIZE                                                      │   │
│  │    name_norm = normalize_tokens(raw_name + " " + raw_group)     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 2. DETECT ATTRIBUTES                                             │   │
│  │    product_type = detect_product_type(name_norm, dict)          │   │
│  │    variety = detect_variety(raw_name, aliases)                  │   │
│  │    subtype = detect_subtype(name_norm, regex_rules)             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 3. SEARCH CANDIDATE SKUs                                         │   │
│  │    - Exact match by (product_type, variety)                     │   │
│  │    - High similarity by title/variety                           │   │
│  │    - Token overlap scoring                                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 4. CALCULATE CONFIDENCE                                          │   │
│  │    FOR EACH candidate:                                           │   │
│  │      score = calculate_confidence(                               │   │
│  │        product_type_match,                                       │   │
│  │        variety_similarity(item.variety, sku.variety),           │   │
│  │        subtype_match,                                            │   │
│  │        ...                                                       │   │
│  │      )                                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 5. CREATE SKU MAPPINGS                                           │   │
│  │    - Top 5 candidates с confidence > 0.10                       │   │
│  │    - status = "proposed"                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 6. CREATE TASK IF NEEDED                                         │   │
│  │    IF best_confidence < 0.70:                                    │   │
│  │      CREATE NormalizationTask(status=open, reason="low conf")   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  OUTPUT: List[SKUMapping], Optional[NormalizationTask]                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 13) AI Обогащение (AI Enrichment)

### 13.1 Обзор

После детерминированного парсинга система может использовать AI (DeepSeek API) для:
- Извлечения атрибутов, которые парсер не смог определить
- Генерации `clean_name` — чистого названия для витрины
- Валидации извлечённых данных

### 13.2 Извлекаемые поля

AI извлекает следующие атрибуты из `raw_name`:

| Поле | Описание | Пример |
|------|----------|--------|
| `flower_type` | Тип цветка | Роза, Хризантема |
| `subtype` | Субтип (кустовая, спрей) | кустовая, спрей |
| `variety` | Сорт | Explorer, Lydia |
| `origin_country` | Страна происхождения | Эквадор |
| `length_cm` | Длина стебля | 50 |
| `colors` | Цвета (массив) | ["красный"] |
| `farm` | Ферма/производитель | FRAMA FLOWERS |
| `clean_name` | **Чистое название для витрины** | Роза кустовая Lydia |

### 13.3 Формат clean_name

**Формат:** `{Тип} {субтип} {Сорт}`

**Правила:**
- Субтип пишется в нижнем регистре
- Сорт сохраняет оригинальный регистр
- Не включаются: длина, страна, цена, ферма, цвет

**Примеры:**
| raw_name | clean_name |
|----------|------------|
| Роза Explorer 50см (Эквадор) FRAMA | Роза Explorer |
| Роза кустовая Lydia красная 40см | Роза кустовая Lydia |
| Хризантема Балтика белая Голландия | Хризантема Балтика |
| Гвоздика спрей микс 60 | Гвоздика спрей |

### 13.4 Confidence и применение

AI возвращает confidence для каждого поля:

| Confidence | Статус | Действие |
|------------|--------|----------|
| >= 0.90 | AUTO_APPLIED | Применяется автоматически |
| 0.70-0.89 | APPLIED_WITH_MARK | Применяется, помечается как AI |
| < 0.70 | NEEDS_REVIEW | В очередь на проверку |

### 13.5 Источники данных для промпта

AI промпт получает актуальные данные из БД:
- `flower_types` — список активных типов цветов
- `flower_subtypes` — субтипы сгруппированные по типам
- Fallback на hardcoded справочники если БД недоступна

**Кэширование:** TTL = 5 минут

### 13.6 Хранение результатов

AI-извлечённые атрибуты сохраняются в `supplier_items.attributes`:

```json
{
  "flower_type": "Роза",
  "subtype": "кустовая",
  "variety": "Lydia",
  "clean_name": "Роза кустовая Lydia",
  "_sources": {
    "flower_type": "ai",
    "subtype": "ai",
    "variety": "ai",
    "clean_name": "ai"
  },
  "_confidences": {
    "flower_type": 0.98,
    "subtype": 0.95,
    "variety": 0.92,
    "clean_name": 0.96
  }
}
```

### 13.7 Публикация с clean_name

При публикации офферов (`publish_service`):
1. Загружается `clean_name` из `supplier_item.attributes`
2. Если отсутствует — генерируется из `flower_type + subtype + variety`
3. Сохраняется в `offers.display_title`

**API ответ:**
```json
{
  "offers": [{
    "display_title": "Роза кустовая Lydia",
    "length_cm": 50,
    "price_min": 120,
    "sku": {"product_type": "Роза", "variety": "Lydia"}
  }]
}
```

---

## 14) Связанные документы

- [ARCHITECTURE.md](ARCHITECTURE.md) — общая архитектура
- [WORKFLOWS.md](WORKFLOWS.md) — бизнес-процессы
- [DATA_LIFECYCLE.md](DATA_LIFECYCLE.md) — жизненный цикл данных
- [ADMIN_API.md](ADMIN_API.md) — API документация
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md) — пайплайн импорта
- [DDL_SCHEMA.md](DDL_SCHEMA.md) — схема БД