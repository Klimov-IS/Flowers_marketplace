"""Name normalization for flower products.

Parses raw names like:
  "Роза Бабалу 50 см (Эквадор) FRAMA FLOWERS"

Into structured components:
  - flower_type: "Роза"
  - variety: "Бабалу"
  - length_cm: 50
  - origin_country: "Эквадор"
  - farm: "FRAMA FLOWERS"
"""
import re
from dataclasses import dataclass
from typing import Optional, List, Tuple

# Known flower types (Russian names, lowercase for matching)
FLOWER_TYPES = {
    "роза": "Роза",
    "гвоздика": "Гвоздика",
    "хризантема": "Хризантема",
    "сантини": "Сантини",
    "эустома": "Эустома",
    "лизиантус": "Эустома",  # alias
    "альстромерия": "Альстромерия",
    "гипсофила": "Гипсофила",
    "илекс": "Илекс",
    "калла": "Калла",
    "каллы": "Калла",  # plural
    "герберы": "Гербера",
    "гербера": "Гербера",
    "гортензия": "Гортензия",
    "пион": "Пион",
    "пионы": "Пион",  # plural
    "тюльпан": "Тюльпан",
    "тюльпаны": "Тюльпан",  # plural
    "лилия": "Лилия",
    "орхидея": "Орхидея",
    "статица": "Статица",
    "эвкалипт": "Эвкалипт",
    "рускус": "Рускус",
    "аспидистра": "Аспидистра",
    "писташ": "Писташ",
    "салал": "Салал",
    "гиперикум": "Гиперикум",
    "ранункулюс": "Ранункулюс",
    "анемон": "Анемон",
    "фрезия": "Фрезия",
    "ирис": "Ирис",
    "нарцисс": "Нарцисс",
    "мимоза": "Мимоза",
    "антуриум": "Антуриум",
    "протея": "Протея",
    "леукоспермум": "Леукоспермум",
    "краспедия": "Краспедия",
    "астра": "Астра",
    "матрикария": "Матрикария",
    "ромашка": "Ромашка",
    "лимониум": "Лимониум",
    "озотамнус": "Озотамнус",
    "вероника": "Вероника",
    "дельфиниум": "Дельфиниум",
}

# Known countries (lowercase for matching)
COUNTRIES = {
    "эквадор": "Эквадор",
    "ecuador": "Эквадор",
    "колумбия": "Колумбия",
    "colombia": "Колумбия",
    "голландия": "Нидерланды",
    "нидерланды": "Нидерланды",
    "netherlands": "Нидерланды",
    "holland": "Нидерланды",
    "кения": "Кения",
    "kenya": "Кения",
    "израиль": "Израиль",
    "israel": "Израиль",
    "россия": "Россия",
    "russia": "Россия",
    "эфиопия": "Эфиопия",
    "ethiopia": "Эфиопия",
    "италия": "Италия",
    "italy": "Италия",
}

# Known farm codes (uppercase patterns at end of name)
FARM_PATTERNS = [
    r"\b(FRAMA\s*FLOWERS?)\b",
    r"\b(NARANJO)\b",
    r"\b(BROWN\s*BREEDING)\b",
    r"\b(ALEXANDRA\s*FARMS?)\b",
    r"\b(ROSAPRIMA)\b",
    r"\b(ESMERALDA)\b",
    r"\b(AGROCOEX)\b",
    r"\b([A-Z]{2,}(?:\s+[A-Z]{2,})*)\b",  # Fallback: all-caps words at end
]

# Color words (for extraction)
COLORS = {
    "белый": "белый",
    "белая": "белый",
    "белые": "белый",
    "красный": "красный",
    "красная": "красный",
    "красные": "красный",
    "розовый": "розовый",
    "розовая": "розовый",
    "розовые": "розовый",
    "желтый": "желтый",
    "желтая": "желтый",
    "желтые": "желтый",
    "оранжевый": "оранжевый",
    "оранжевая": "оранжевый",
    "оранжевые": "оранжевый",
    "синий": "синий",
    "синяя": "синий",
    "синие": "синий",
    "фиолетовый": "фиолетовый",
    "фиолетовая": "фиолетовый",
    "фиолетовые": "фиолетовый",
    "лиловый": "лиловый",
    "сиреневый": "сиреневый",
    "бордовый": "бордовый",
    "бордовая": "бордовый",
    "зеленый": "зеленый",
    "зеленая": "зеленый",
    "кремовый": "кремовый",
    "кремовая": "кремовый",
    "персиковый": "персиковый",
    "персиковая": "персиковый",
    "коралловый": "коралловый",
    "лавандовый": "лавандовый",
    "пудровый": "пудровый",
    "биколор": "биколор",
    "микс": "микс",
}


@dataclass
class NormalizedName:
    """Result of name normalization."""

    original: str
    flower_type: Optional[str] = None
    variety: Optional[str] = None
    length_cm: Optional[int] = None
    origin_country: Optional[str] = None
    farm: Optional[str] = None
    colors: List[str] = None
    clean_name: Optional[str] = None  # Type + Variety only

    def __post_init__(self):
        if self.colors is None:
            self.colors = []


def _extract_length(text: str) -> Tuple[Optional[int], str]:
    """Extract length and return remaining text."""
    pattern = r"(\d{2,3})\s*(?:см|cm)\b"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        length = int(match.group(1))
        if 30 <= length <= 150:
            # Remove the match from text
            clean_text = text[: match.start()] + text[match.end() :]
            return length, clean_text.strip()

    return None, text


def _extract_country(text: str) -> Tuple[Optional[str], str]:
    """Extract country from parentheses and return remaining text."""
    # First try parentheses
    paren_pattern = r"\(([^)]+)\)"
    matches = re.finditer(paren_pattern, text)

    for match in matches:
        content = match.group(1).strip().lower()
        if content in COUNTRIES:
            clean_text = text[: match.start()] + text[match.end() :]
            return COUNTRIES[content], clean_text.strip()

    # Then try plain text
    text_lower = text.lower()
    for key, value in COUNTRIES.items():
        if key in text_lower:
            # Remove country word
            pattern = re.compile(re.escape(key), re.IGNORECASE)
            clean_text = pattern.sub("", text)
            return value, clean_text.strip()

    return None, text


def _extract_farm(text: str) -> Tuple[Optional[str], str]:
    """Extract farm name and return remaining text."""
    for pattern in FARM_PATTERNS[:-1]:  # Skip fallback pattern first
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            farm = match.group(1).strip()
            clean_text = text[: match.start()] + text[match.end() :]
            return farm, clean_text.strip()

    # Fallback: look for all-caps words at end of string
    fallback_match = re.search(r"\b([A-Z]{3,}(?:\s+[A-Z]{3,})*)\s*$", text)
    if fallback_match:
        farm = fallback_match.group(1).strip()
        # Make sure it's not just the flower type or variety
        if len(farm) > 4:  # Minimum farm name length
            clean_text = text[: fallback_match.start()].strip()
            return farm, clean_text

    return None, text


def _extract_flower_type(text: str) -> Tuple[Optional[str], str]:
    """Extract flower type and return remaining text."""
    text_lower = text.lower()
    words = text.split()

    for i, word in enumerate(words):
        word_lower = word.lower().rstrip(",.;:")
        if word_lower in FLOWER_TYPES:
            flower_type = FLOWER_TYPES[word_lower]
            # Remove this word from the text
            remaining = " ".join(words[:i] + words[i + 1 :])
            return flower_type, remaining.strip()

    return None, text


def _extract_colors(text: str) -> Tuple[List[str], str]:
    """Extract colors and return remaining text."""
    found_colors = []
    clean_text = text
    text_lower = text.lower()

    for color_key, color_norm in COLORS.items():
        if color_key in text_lower and color_norm not in found_colors:
            found_colors.append(color_norm)
            # Remove color word
            pattern = re.compile(re.escape(color_key), re.IGNORECASE)
            clean_text = pattern.sub("", clean_text)

    # Clean up multiple spaces
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    return found_colors, clean_text


def _clean_variety(text: str) -> str:
    """Clean up variety name after extraction."""
    # Remove common suffixes/noise
    text = re.sub(r"\s*[-–—]\s*", " ", text)  # Replace dashes with spaces
    text = re.sub(r"\s+", " ", text)  # Multiple spaces to one
    text = text.strip(" ,;.()[]")

    # Capitalize words properly
    words = text.split()
    if words:
        words = [w.capitalize() if w.islower() else w for w in words]
        return " ".join(words)

    return text


def normalize_name(raw_name: str) -> NormalizedName:
    """
    Normalize a flower product name into structured components.

    Args:
        raw_name: Raw product name like "Роза Бабалу 50 см (Эквадор) FRAMA FLOWERS"

    Returns:
        NormalizedName with extracted components
    """
    if not raw_name:
        return NormalizedName(original=raw_name or "")

    result = NormalizedName(original=raw_name)
    text = raw_name.strip()

    # Extract in order: farm, country, length, colors, type
    # Each step cleans the text for the next

    # 1. Extract farm (usually at end)
    result.farm, text = _extract_farm(text)

    # 2. Extract country (usually in parentheses)
    result.origin_country, text = _extract_country(text)

    # 3. Extract length
    result.length_cm, text = _extract_length(text)

    # 4. Extract colors
    result.colors, text = _extract_colors(text)

    # 5. Extract flower type
    result.flower_type, text = _extract_flower_type(text)

    # 6. Remaining text is the variety
    result.variety = _clean_variety(text) if text else None

    # 7. Build clean name (type + variety)
    if result.flower_type and result.variety:
        result.clean_name = f"{result.flower_type} {result.variety}"
    elif result.flower_type:
        result.clean_name = result.flower_type
    elif result.variety:
        result.clean_name = result.variety
    else:
        result.clean_name = raw_name

    return result


def normalize_names_batch(names: List[str]) -> List[NormalizedName]:
    """
    Normalize multiple names in batch.

    Args:
        names: List of raw product names

    Returns:
        List of NormalizedName objects
    """
    return [normalize_name(name) for name in names]


def generate_stable_key(normalized: NormalizedName) -> str:
    """
    Generate a stable key for grouping variants.

    Names with the same flower type and variety (but different sizes)
    should have the same stable key.

    Args:
        normalized: Normalized name result

    Returns:
        Stable key string for grouping
    """
    parts = []

    if normalized.flower_type:
        parts.append(normalized.flower_type.lower())

    if normalized.variety:
        # Normalize variety for matching
        variety = normalized.variety.lower()
        variety = re.sub(r"\s+", "_", variety)
        variety = re.sub(r"[^a-zа-яё0-9_]", "", variety)
        parts.append(variety)

    if normalized.origin_country:
        parts.append(normalized.origin_country.lower()[:3])

    return "|".join(parts) if parts else normalized.original.lower()[:50]
