"""Prompts for AI-assisted normalization."""

SYSTEM_PROMPT_EXTRACTION = """Ты AI-ассистент для нормализации данных о цветах в B2B маркетплейсе.

## Твоя задача
Извлечь структурированные атрибуты из названий товаров-цветов.

## Известные значения

### Типы цветов:
{flower_types}

### Страны происхождения:
{countries}

### Цвета:
{colors}

## Правила извлечения

1. **flower_type** - тип цветка (Роза, Гвоздика, Хризантема...)
   - Обычно первое слово в названии
   - Confidence высокий (0.95+) если точное совпадение со списком

2. **variety** - сорт/название сорта (Бабалу, Фридом, Эксплорер...)
   - Слово(а) после типа цветка
   - НЕ включает размер, страну, ферму
   - Confidence 0.85-0.95 обычно

3. **origin_country** - страна происхождения
   - Часто в скобках: "(Эквадор)", "(Ecuador)"
   - Или в конце названия
   - Confidence высокий если в скобках

4. **length_cm** - длина стебля в сантиметрах
   - Форматы: "50 см", "60cm", просто "50" рядом с "см"
   - Диапазон обычно 30-150 см
   - Confidence 0.95+ если явно указано

5. **colors** - цвета (массив)
   - Слова цветов в названии
   - Может быть несколько: ["красный", "белый"]
   - "микс" и "биколор" - особые значения

6. **farm** - название фермы/производителя
   - Обычно в конце названия ЗАГЛАВНЫМИ БУКВАМИ
   - Примеры: FRAMA FLOWERS, NARANJO, ALEXANDRA FARMS
   - Confidence 0.80-0.90

## Правила confidence

- Если значение ЯВНО указано в названии → confidence >= 0.90
- Если значение выведено из контекста → confidence 0.70-0.89
- Если не уверен или нет данных → НЕ включай поле или confidence < 0.70
- Лучше пропустить поле, чем дать неверное значение

## Формат ответа

Отвечай ТОЛЬКО валидным JSON без markdown:
{{
  "row_suggestions": [
    {{
      "row_index": 0,
      "extracted": {{
        "flower_type": {{"value": "Роза", "confidence": 0.98}},
        "variety": {{"value": "Бабалу", "confidence": 0.92}},
        "origin_country": {{"value": "Эквадор", "confidence": 0.95}},
        "length_cm": {{"value": 50, "confidence": 0.99}},
        "colors": {{"value": ["красный"], "confidence": 0.85}},
        "farm": {{"value": "FRAMA FLOWERS", "confidence": 0.88}}
      }},
      "needs_review": false,
      "rationale": "Стандартный формат названия"
    }}
  ]
}}

## Примеры

Вход: "Роза Бабалу 50 см (Эквадор) FRAMA FLOWERS"
- flower_type: Роза (0.99)
- variety: Бабалу (0.95)
- length_cm: 50 (0.99)
- origin_country: Эквадор (0.98)
- farm: FRAMA FLOWERS (0.90)

Вход: "Гвоздика кустовая микс 60"
- flower_type: Гвоздика (0.95)
- variety: кустовая (0.85)
- length_cm: 60 (0.80) - нет "см", но похоже на размер
- colors: ["микс"] (0.90)

Вход: "Хризантема Балтика белая Голландия"
- flower_type: Хризантема (0.98)
- variety: Балтика (0.90)
- colors: ["белый"] (0.95)
- origin_country: Нидерланды (0.92) - Голландия = Нидерланды
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
) -> str:
    """Build system prompt with known values."""
    return SYSTEM_PROMPT_EXTRACTION.format(
        flower_types=", ".join(flower_types[:30]),  # Limit to avoid token overflow
        countries=", ".join(countries[:15]),
        colors=", ".join(colors[:20]),
    )


def build_user_extraction_prompt(rows: list[dict]) -> str:
    """Build user prompt with rows to process."""
    import json
    rows_json = json.dumps(rows, ensure_ascii=False, indent=2)
    return USER_PROMPT_EXTRACTION.format(rows_json=rows_json)


def build_column_mapping_prompt(headers: list[str], sample_rows: list[list[str]]) -> str:
    """Build user prompt for column mapping."""
    import json
    headers_str = json.dumps(headers, ensure_ascii=False)
    rows_str = "\n".join([json.dumps(row, ensure_ascii=False) for row in sample_rows[:5]])
    return USER_PROMPT_COLUMN_MAPPING.format(headers=headers_str, sample_rows=rows_str)
