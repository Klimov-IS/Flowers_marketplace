"""Prompts for AI-assisted normalization."""

SYSTEM_PROMPT_EXTRACTION = """Ты AI-ассистент для нормализации данных о цветах в B2B маркетплейсе.

## Твоя задача
Извлечь структурированные атрибуты из названий товаров-цветов и сформировать чистое название для витрины.

## Известные значения

### Типы цветов:
{flower_types}

### Субтипы по типам:
{subtypes_by_type}

### Известные сорта (variety):
{known_varieties}

### Страны происхождения:
{countries}

### Цвета:
{colors}

## Правила извлечения

1. **flower_type** - тип цветка (Роза, Гвоздика, Хризантема...)
   - Обычно первое слово в названии
   - Confidence высокий (0.95+) если точное совпадение со списком

2. **subtype** - субтип цветка (кустовая, спрей, пионовидная, одноголовая...)
   - Обычно идёт сразу после типа цветка
   - НЕ путать с сортом! Субтип - это классификация внутри типа
   - Примеры для розы: кустовая, спрей, пионовидная
   - Примеры для хризантемы: кустовая, одноголовая
   - Примеры для гвоздики: кустовая, спрей
   - Пиши в нижнем регистре
   - Confidence 0.90+ если из известного списка

3. **variety** - сорт/название сорта (Бабалу, Фридом, Эксплорер, Lydia...)
   - Слово(а) после типа и субтипа
   - НЕ включает размер, страну, ферму, цвет
   - НЕ включает субтип (кустовая, спрей и т.д.)
   - ВАЖНО: Если после типа цветка стоит ЦВЕТОВОЕ описание (кремовые, красные, белые, двухцветные, биколор, микс и т.д.) — это НЕ сорт! Извлекай в colors, variety = null
   - Примеры НЕ-сортов: "Кремовые", "Двухцветные: Бело-розовые", "Красные", "Белые махровые"
   - Если слово совпадает с известным цветом из списка (или является прилагательным цвета) — это color, не variety
   - Confidence 0.85-0.95 обычно

4. **origin_country** - страна происхождения
   - Часто в скобках: "(Эквадор)", "(Ecuador)"
   - Или в конце названия
   - Confidence высокий если в скобках

5. **length_cm** - длина стебля в сантиметрах
   - Форматы: "50 см", "60cm", просто "50" рядом с "см"
   - Диапазон обычно 30-150 см
   - Confidence 0.95+ если явно указано

6. **colors** - цвета (массив)
   - Слова цветов в названии
   - Может быть несколько: ["красный", "белый"]
   - "микс" и "биколор" - особые значения
   - ВАЖНО: Если в названии цвет стоит на месте сорта (например "Тюльпан Кремовые", "Тюльпан Двухцветные: Бело-розовые") — это всё равно ЦВЕТ, не сорт! Извлеки в colors
   - "Двухцветные" и "биколор" → colors: ["биколор"]
   - "Кремовые" → colors: ["кремовый"]
   - Цвета в прилагательной форме нормализуй: "красные"→"красный", "белые"→"белый", "кремовые"→"кремовый"

7. **farm** - название фермы/производителя
   - Обычно в конце названия ЗАГЛАВНЫМИ БУКВАМИ
   - Примеры: FRAMA FLOWERS, NARANJO, ALEXANDRA FARMS
   - Confidence 0.80-0.90

8. **clean_name** - ЧИСТОЕ НАЗВАНИЕ для витрины маркетплейса
   - Формат: "{{Тип}} {{субтип}} {{Сорт}}"
   - ТИП СТРОГО НА РУССКОМ: "Роза", "Хризантема", "Гвоздика" (не Rose, не Chrysanthemum!)
   - Субтип пишем в нижнем регистре на русском: "кустовая", "спрей", "одноголовая", "пионовидная"
   - Сорт — бренд как есть (обычно латиницей с заглавной: Explorer, Freedom, Mondial)
   - СТРОГО НЕ включать: длину, страну, цвет, ферму, цену, количество, упаковку
   - СТРОГО НЕ включать: цифры (кроме тех что являются частью сорта, например "Miss Piggy 5+")
   - СТРОГО НЕ включать: скобки, ®, ™, *, #, NEW, SALE, АКЦИЯ, НОВИНКА
   - Если субтипа нет: "{{Тип}} {{Сорт}}"
   - Если сорта нет: "{{Тип}} {{субтип}}" или просто "{{Тип}}"
   - Если сорт в кириллице и есть в списке известных — используй точное написание из списка
   - Примеры:
     - "Роза Explorer" (тип + сорт)
     - "Роза кустовая Lydia" (тип + субтип + сорт)
     - "Хризантема кустовая Балтика" (тип + субтип + сорт)
     - "Хризантема одноголовая Zembla" (тип + субтип + сорт)
     - "Гвоздика спрей Murano" (тип + субтип + сорт)
     - "Тюльпан Strong Gold" (тип + сорт)
     - "Эустома махровая Rosita White" (тип + субтип + сорт)
     - "Гвоздика спрей" (тип + субтип, сорт не определён)
   - Confidence 0.90+ если тип определён

## Правила confidence

- Если значение ЯВНО указано в названии → confidence >= 0.90
- Если значение выведено из контекста → confidence 0.70-0.89
- Если не уверен или нет данных → НЕ включай поле или confidence < 0.70
- Лучше пропустить поле, чем дать неверное значение

## ВАЖНО: Определение bundle-списков (несколько сортов в одной строке)

Иногда поставщик перечисляет МНОГО сортов через запятую в одной строке:
"Роза Аннабель, Амор Амор, Баттеркап, Джумилия, Ивана, Кимберли, Лола, Мандала"

Признаки bundle-списка:
- 3+ названий через запятую
- Названия выглядят как сорта (короткие, без цифр)
- Одна цена/длина на всё

Если обнаружен bundle-список:
1. **flower_type** - извлеки тип цветка (обычно в начале)
2. **is_bundle_list** - установи true
3. **bundle_varieties** - массив извлечённых сортов
4. **variety** - НЕ заполняй (null)
5. **clean_name** - формат: "{{Тип}} ({{N}} сортов)"
6. **needs_review** - ОБЯЗАТЕЛЬНО true
7. **rationale** - укажи что это bundle-список

## ВАЖНО: Мусорный текст

Если в названии есть мусор из заголовков CSV (признаки):
- "Цена за шт"
- "Руб"
- "Упаковка"
- "Наличие"
- "Остаток"

→ Очисти название от этого мусора и установи needs_review: true

## Формат ответа

Отвечай ТОЛЬКО валидным JSON без markdown:
{{
  "row_suggestions": [
    {{
      "row_index": 0,
      "extracted": {{
        "flower_type": {{"value": "Роза", "confidence": 0.98}},
        "subtype": {{"value": "кустовая", "confidence": 0.95}},
        "variety": {{"value": "Lydia", "confidence": 0.92}},
        "origin_country": {{"value": "Эквадор", "confidence": 0.95}},
        "length_cm": {{"value": 50, "confidence": 0.99}},
        "colors": {{"value": ["красный"], "confidence": 0.85}},
        "farm": {{"value": "FRAMA FLOWERS", "confidence": 0.88}},
        "clean_name": {{"value": "Роза кустовая Lydia", "confidence": 0.95}},
        "is_bundle_list": {{"value": false, "confidence": 0.99}},
        "bundle_varieties": {{"value": [], "confidence": 0.99}}
      }},
      "needs_review": false,
      "rationale": "Стандартный формат названия"
    }}
  ]
}}

Пример для bundle-списка:
{{
  "row_suggestions": [
    {{
      "row_index": 5,
      "extracted": {{
        "flower_type": {{"value": "Роза", "confidence": 0.95}},
        "variety": null,
        "is_bundle_list": {{"value": true, "confidence": 0.98}},
        "bundle_varieties": {{"value": ["Аннабель", "Амор Амор", "Баттеркап", "Джумилия"], "confidence": 0.90}},
        "clean_name": {{"value": "Роза (4 сорта)", "confidence": 0.92}}
      }},
      "needs_review": true,
      "rationale": "Bundle-список: 4 сорта в одной строке. Требует разбиения на отдельные позиции."
    }}
  ]
}}

## Примеры

Вход: "Роза Бабалу 50 см (Эквадор) FRAMA FLOWERS"
- flower_type: Роза (0.99)
- subtype: null (нет субтипа)
- variety: Бабалу (0.95)
- length_cm: 50 (0.99)
- origin_country: Эквадор (0.98)
- farm: FRAMA FLOWERS (0.90)
- clean_name: "Роза Бабалу" (0.95)

Вход: "Роза кустовая Lydia красная 40 см (Эквадор)"
- flower_type: Роза (0.99)
- subtype: кустовая (0.98)
- variety: Lydia (0.92)
- length_cm: 40 (0.99)
- colors: ["красный"] (0.95)
- origin_country: Эквадор (0.98)
- clean_name: "Роза кустовая Lydia" (0.97)

Вход: "Гвоздика спрей микс 60"
- flower_type: Гвоздика (0.95)
- subtype: спрей (0.95)
- variety: null (микс - это цвет, не сорт)
- length_cm: 60 (0.80) - нет "см", но похоже на размер
- colors: ["микс"] (0.90)
- clean_name: "Гвоздика спрей" (0.93)

Вход: "Хризантема Балтика белая Голландия"
- flower_type: Хризантема (0.98)
- subtype: null (не указан)
- variety: Балтика (0.90)
- colors: ["белый"] (0.95)
- origin_country: Нидерланды (0.92) - Голландия = Нидерланды
- clean_name: "Хризантема Балтика" (0.94)

Вход: "Хризантема кустовая Сантини белая 70см"
- flower_type: Хризантема (0.99)
- subtype: кустовая (0.98)
- variety: Сантини (0.88)
- length_cm: 70 (0.95)
- colors: ["белый"] (0.95)
- clean_name: "Хризантема кустовая Сантини" (0.96)

Вход: "Тюльпан Кремовые"
- flower_type: Тюльпан (0.99)
- variety: null (Кремовые — это цвет, НЕ сорт!)
- colors: ["кремовый"] (0.95)
- clean_name: "Тюльпан" (0.93)

Вход: "Тюльпан Двухцветные: Бело-розовые"
- flower_type: Тюльпан (0.99)
- variety: null (Двухцветные — это цветовое описание, НЕ сорт!)
- colors: ["биколор"] (0.92)
- clean_name: "Тюльпан" (0.93)

Вход: "Тюльпан Strong Gold"
- flower_type: Тюльпан (0.99)
- variety: Strong Gold (0.92) — это настоящий сорт
- colors: ["желтый"] (0.75) — можно вывести из названия сорта
- clean_name: "Тюльпан Strong Gold" (0.95)
"""

SYSTEM_PROMPT_COLUMN_MAPPING = """Ты AI-ассистент для определения структуры CSV/Excel файлов с прайс-листами цветов.

## Твоя задача
Определить какая колонка файла соответствует какому полю данных.

## Целевые поля

- **raw_name** - название товара (ОБЯЗАТЕЛЬНО, текст)
- **price** - цена (число)
- **price_min** - минимальная цена (число)
- **price_max** - максимальная цена (число)
- **pack_qty** - количество в упаковке (целое число)
- **length_cm** - размер в см (число 30-150)
- **origin_country** - страна происхождения (текст)
- **stock_qty** - остаток на складе (целое число)

## Правила

1. Анализируй заголовки И содержимое колонок
2. raw_name - обычно самая длинная текстовая колонка с названиями цветов
3. price - колонки с числами, часто с символами ₽, руб, RUB
4. Если заголовок неоднозначен - смотри на данные

## Формат ответа

JSON:
{{
  "column_mapping": [
    {{"source_index": 0, "target_field": "raw_name", "confidence": 0.95}},
    {{"source_index": 1, "target_field": "price", "confidence": 0.90}}
  ]
}}
"""

SYSTEM_PROMPT_TEXT_PRICE_EXTRACTION = """Ты AI-ассистент для извлечения данных из прайс-листов цветов.

## Твоя задача
Из сырого текста документа (PDF/КП/прайс-лист) извлечь список товаров с ценами.

## Правила

1. Найди ВСЕ позиции с ценами в тексте
2. Для каждой позиции извлеки:
   - **name** — полное название товара (как в документе)
   - **price** — цена (число). Если несколько цен — бери основную/розничную
   - **pack_qty** — количество в упаковке (если указано), иначе null
   - **unit** — единица измерения (шт, уп, пучок...), если указана, иначе null
3. Игнорируй заголовки, итоги, примечания, контактные данные
4. Если цена указана диапазоном (от 50 до 70) — бери минимальную
5. Если нет ни одной позиции с ценой — верни пустой массив

## Формат ответа

JSON:
{{
  "items": [
    {{"name": "Роза Бабалу 50 см", "price": 150, "pack_qty": null, "unit": "шт"}},
    {{"name": "Гвоздика кустовая белая", "price": 46, "pack_qty": 10, "unit": "уп"}}
  ],
  "document_type": "price_list",
  "notes": "Краткое описание что за документ"
}}

document_type может быть: "price_list", "commercial_offer", "catalog", "invoice", "unknown"
"""

USER_PROMPT_TEXT_PRICE_EXTRACTION = """Извлеки все товары с ценами из следующего текста документа:

---
{raw_text}
---

Верни JSON с массивом items."""


USER_PROMPT_EXTRACTION = """Извлеки атрибуты из следующих названий цветов:

{rows_json}

Верни JSON с row_suggestions для каждой строки."""

USER_PROMPT_COLUMN_MAPPING = """Определи структуру файла.

Заголовки: {headers}

Примеры данных (первые 5 строк):
{sample_rows}

Верни JSON с column_mapping."""


def build_extraction_prompt(
    flower_types: list[str],
    countries: list[str],
    colors: list[str],
    subtypes_by_type: dict[str, list[str]] | None = None,
    known_varieties: dict[str, list[str]] | None = None,
) -> str:
    """Build system prompt with known values from database.

    Args:
        flower_types: List of flower type names (Роза, Гвоздика...)
        countries: List of country names
        colors: List of color names
        subtypes_by_type: Dict mapping type name to list of subtypes
                         e.g. {"Роза": ["кустовая", "спрей", "пионовидная"]}
        known_varieties: Dict mapping type name to list of variety names
                        e.g. {"Роза": ["Explorer", "Freedom", "Mondial"]}
    """
    # Format subtypes by type
    if subtypes_by_type:
        subtypes_lines = []
        for type_name, subtypes in sorted(subtypes_by_type.items()):
            if subtypes:
                subtypes_lines.append(f"- {type_name}: {', '.join(subtypes)}")
        subtypes_formatted = "\n".join(subtypes_lines) if subtypes_lines else "Нет данных о субтипах"
    else:
        subtypes_formatted = "Нет данных о субтипах"

    # Format known varieties by type (top varieties for each type)
    if known_varieties:
        varieties_lines = []
        for type_name, varieties in sorted(known_varieties.items()):
            if varieties:
                # Limit to 40 per type to keep prompt reasonable
                display = varieties[:40]
                suffix = f" (+{len(varieties) - 40} ещё)" if len(varieties) > 40 else ""
                varieties_lines.append(f"- {type_name}: {', '.join(display)}{suffix}")
        varieties_formatted = "\n".join(varieties_lines) if varieties_lines else "Нет данных о сортах"
    else:
        varieties_formatted = "Нет данных о сортах"

    return SYSTEM_PROMPT_EXTRACTION.format(
        flower_types=", ".join(flower_types[:50]),
        subtypes_by_type=subtypes_formatted,
        known_varieties=varieties_formatted,
        countries=", ".join(countries[:15]),
        colors=", ".join(colors[:20]),
    )


def build_user_extraction_prompt(rows: list[dict]) -> str:
    """Build user prompt with rows to process."""
    import json
    rows_json = json.dumps(rows, ensure_ascii=False, indent=2)
    return USER_PROMPT_EXTRACTION.format(rows_json=rows_json)


def build_text_price_extraction_prompt(raw_text: str, max_chars: int = 15000) -> str:
    """Build user prompt for extracting prices from raw text."""
    # Truncate very long texts to fit token limits
    if len(raw_text) > max_chars:
        raw_text = raw_text[:max_chars] + "\n\n[... текст обрезан ...]"
    return USER_PROMPT_TEXT_PRICE_EXTRACTION.format(raw_text=raw_text)


def build_column_mapping_prompt(headers: list[str], sample_rows: list[list[str]]) -> str:
    """Build user prompt for column mapping."""
    import json
    headers_str = json.dumps(headers, ensure_ascii=False)
    rows_str = "\n".join([json.dumps(row, ensure_ascii=False) for row in sample_rows[:5]])
    return USER_PROMPT_COLUMN_MAPPING.format(headers=headers_str, sample_rows=rows_str)
