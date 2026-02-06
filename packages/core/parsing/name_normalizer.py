"""Name normalization for flower products.

Parses raw names like:
  "Роза Бабалу 50 см (Эквадор) FRAMA FLOWERS"
  "Роза спрей Explorer 60 см"

Into structured components:
  - flower_type: "Роза"
  - flower_subtype: "Спрей" (NEW)
  - variety: "Бабалу"
  - length_cm: 50
  - origin_country: "Эквадор"
  - farm: "FRAMA FLOWERS"

Supports loading flower types and subtypes from database (with fallback to hardcoded).
"""
import re
import time
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict

# =============================================================================
# Fallback dictionaries (used when DB not available or not initialized)
# =============================================================================

# Known flower types (Russian names, lowercase for matching)
FLOWER_TYPES_FALLBACK: Dict[str, str] = {
    "роза": "Роза",
    "розы": "Роза",
    "гвоздика": "Гвоздика",
    "гвоздики": "Гвоздика",
    "хризантема": "Хризантема",
    "хризантемы": "Хризантема",
    "сантини": "Сантини",
    "эустома": "Эустома",
    "лизиантус": "Эустома",  # alias
    "альстромерия": "Альстромерия",
    "альстромерии": "Альстромерия",
    "гипсофила": "Гипсофила",
    "гипсофилы": "Гипсофила",
    "илекс": "Илекс",
    "калла": "Калла",
    "каллы": "Калла",
    "герберы": "Гербера",
    "гербера": "Гербера",
    "гортензия": "Гортензия",
    "гортензии": "Гортензия",
    "пион": "Пион",
    "пионы": "Пион",
    "тюльпан": "Тюльпан",
    "тюльпаны": "Тюльпан",
    "лилия": "Лилия",
    "лилии": "Лилия",
    "орхидея": "Орхидея",
    "орхидеи": "Орхидея",
    "статица": "Статица",
    "статицы": "Статица",
    "эвкалипт": "Эвкалипт",
    "эвкалипта": "Эвкалипт",
    "рускус": "Рускус",
    "аспидистра": "Аспидистра",
    "писташ": "Писташ",
    "фисташка": "Писташ",
    "салал": "Салал",
    "гиперикум": "Гиперикум",
    "ранункулюс": "Ранункулюс",
    "ранункулюсы": "Ранункулюс",
    "анемон": "Анемон",
    "анемоны": "Анемон",
    "фрезия": "Фрезия",
    "фрезии": "Фрезия",
    "ирис": "Ирис",
    "ирисы": "Ирис",
    "нарцисс": "Нарцисс",
    "нарциссы": "Нарцисс",
    "мимоза": "Мимоза",
    "мимозы": "Мимоза",
    "антуриум": "Антуриум",
    "антуриумы": "Антуриум",
    "протея": "Протея",
    "протеи": "Протея",
    "леукоспермум": "Леукоспермум",
    "краспедия": "Краспедия",
    "астра": "Астра",
    "астры": "Астра",
    "матрикария": "Матрикария",
    "ромашка": "Ромашка",
    "ромашки": "Ромашка",
    "лимониум": "Лимониум",
    "озотамнус": "Озотамнус",
    "вероника": "Вероника",
    "дельфиниум": "Дельфиниум",
    "дельфиниумы": "Дельфиниум",
    # Декоративная зелень (added 06.02.2026)
    "аспарагус": "Аспарагус",
    "брассика": "Брассика",
    "кипарис": "Кипарис",
    "корилус": "Корилус",
    "леукадендрон": "Леукадендрон",
    "лигустер": "Лигустер",
    "лигуструм": "Лигустер",  # alias
    "магнолия": "Магнолия",
    "магнум": "Магнум",  # likely a variety, but parser sees it as type
    "нобилис": "Нобилис",
    "пинус": "Пинус",
    "мережка": "Мережка",
    # Дополнительные цветы
    "амариллис": "Амариллис",
    "бруния": "Бруния",
    "ваксфлауэр": "Ваксфлауэр",
    "клематис": "Клематис",
    "матиола": "Матиола",
    "маттиола": "Матиола",  # alias
    "оксипеталум": "Оксипеталум",
}

# Fallback subtypes (synonym -> {name, type_slug})
SUBTYPES_FALLBACK: Dict[str, Dict[str, str]] = {
    "кустовая": {"name": "Кустовая", "type_slug": "rosa"},
    "кустовой": {"name": "Кустовая", "type_slug": "rosa"},
    "куст": {"name": "Кустовая", "type_slug": "rosa"},
    "спрей": {"name": "Спрей", "type_slug": "rosa"},
    "пионовидная": {"name": "Пионовидная", "type_slug": "rosa"},
    "пионовидной": {"name": "Пионовидная", "type_slug": "rosa"},
    "одноголовая": {"name": "Одноголовая", "type_slug": "chrysanthemum"},
    "одноголовой": {"name": "Одноголовая", "type_slug": "chrysanthemum"},
    "махровая": {"name": "Махровая", "type_slug": "eustoma"},
    "махровой": {"name": "Махровая", "type_slug": "eustoma"},
    "немахровая": {"name": "Немахровая", "type_slug": "eustoma"},
}

# Known countries (lowercase for matching)
COUNTRIES: Dict[str, str] = {
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
COLORS: Dict[str, str] = {
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


# =============================================================================
# Database Lookup with Caching
# =============================================================================

class FlowerTypeLookup:
    """
    Lazy-loaded lookup for flower types and subtypes from database.

    Provides caching with configurable TTL. Falls back to hardcoded
    dictionaries when database is not available.

    Usage:
        # Async (with database session):
        types = await FlowerTypeLookup.get_types_async(db)

        # Sync (uses cache or fallback):
        types = FlowerTypeLookup.get_types_sync()
    """

    _type_cache: Dict[str, str] | None = None
    _subtype_cache: Dict[str, Dict[str, str]] | None = None
    _cache_time: float = 0
    CACHE_TTL: int = 300  # 5 minutes

    @classmethod
    async def load_from_db(cls, db) -> Tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
        """
        Load type and subtype mappings from database.

        Args:
            db: AsyncSession instance

        Returns:
            Tuple of (type_synonyms, subtype_synonyms)
        """
        from sqlalchemy import select

        # Import here to avoid circular imports
        from apps.api.models.catalog import FlowerType, FlowerSubtype, TypeSynonym, SubtypeSynonym

        # Load type synonyms
        result = await db.execute(
            select(TypeSynonym.synonym, FlowerType.canonical_name)
            .join(FlowerType)
            .where(FlowerType.is_active == True)
        )
        types = {row.synonym: row.canonical_name for row in result}

        # Load subtype synonyms
        result = await db.execute(
            select(
                SubtypeSynonym.synonym,
                FlowerSubtype.name,
                FlowerType.slug.label("type_slug"),
            )
            .join(FlowerSubtype)
            .join(FlowerType)
            .where(FlowerSubtype.is_active == True)
        )
        subtypes = {
            row.synonym: {"name": row.name, "type_slug": row.type_slug}
            for row in result
        }

        return types, subtypes

    @classmethod
    async def get_types_async(cls, db) -> Dict[str, str]:
        """
        Get type lookup (synonym -> canonical_name) with async DB loading.

        Caches result for CACHE_TTL seconds.
        """
        now = time.time()
        if cls._type_cache and now - cls._cache_time < cls.CACHE_TTL:
            return cls._type_cache

        try:
            types, subtypes = await cls.load_from_db(db)
            cls._type_cache = types
            cls._subtype_cache = subtypes
            cls._cache_time = now
            return cls._type_cache
        except Exception:
            # Fallback to hardcoded on error
            return FLOWER_TYPES_FALLBACK

    @classmethod
    async def get_subtypes_async(cls, db) -> Dict[str, Dict[str, str]]:
        """
        Get subtype lookup (synonym -> {name, type_slug}) with async DB loading.
        """
        now = time.time()
        if cls._subtype_cache and now - cls._cache_time < cls.CACHE_TTL:
            return cls._subtype_cache

        try:
            types, subtypes = await cls.load_from_db(db)
            cls._type_cache = types
            cls._subtype_cache = subtypes
            cls._cache_time = now
            return cls._subtype_cache
        except Exception:
            return SUBTYPES_FALLBACK

    @classmethod
    def get_types_sync(cls) -> Dict[str, str]:
        """
        Get type lookup synchronously.

        Uses cached data if available, otherwise falls back to hardcoded.
        """
        if cls._type_cache and time.time() - cls._cache_time < cls.CACHE_TTL:
            return cls._type_cache
        return FLOWER_TYPES_FALLBACK

    @classmethod
    def get_subtypes_sync(cls) -> Dict[str, Dict[str, str]]:
        """
        Get subtype lookup synchronously.

        Uses cached data if available, otherwise falls back to hardcoded.
        """
        if cls._subtype_cache and time.time() - cls._cache_time < cls.CACHE_TTL:
            return cls._subtype_cache
        return SUBTYPES_FALLBACK

    @classmethod
    def invalidate_cache(cls):
        """Force cache invalidation."""
        cls._type_cache = None
        cls._subtype_cache = None
        cls._cache_time = 0

    @classmethod
    def warm_cache(cls, types: Dict[str, str], subtypes: Dict[str, Dict[str, str]]):
        """Manually warm the cache (useful for testing or startup)."""
        cls._type_cache = types
        cls._subtype_cache = subtypes
        cls._cache_time = time.time()


# Backwards compatibility alias
FLOWER_TYPES = FLOWER_TYPES_FALLBACK


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NormalizedName:
    """Result of name normalization."""

    original: str
    flower_type: Optional[str] = None
    flower_subtype: Optional[str] = None  # NEW: Кустовая, Спрей, etc.
    variety: Optional[str] = None
    length_cm: Optional[int] = None
    origin_country: Optional[str] = None
    farm: Optional[str] = None
    colors: List[str] = field(default_factory=list)
    clean_name: Optional[str] = None  # Type + Variety only

    def __post_init__(self):
        if self.colors is None:
            self.colors = []


# =============================================================================
# Extraction Functions
# =============================================================================

def _extract_length(text: str) -> Tuple[Optional[int], str]:
    """Extract length and return remaining text."""
    # Pattern matches "120см", "60 см", "120см(1)" where parenthesis follows
    pattern = r"(?<!\d)(\d{2,3})\s*(?:см|cm)(?:\b|\(|$)"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        length = int(match.group(1))
        if 30 <= length <= 150:
            # Remove the length part from text (keep any trailing parenthesis)
            # Find where "см" or "cm" ends
            end_pos = match.end()
            # Don't consume trailing parenthesis
            if end_pos > 0 and text[end_pos - 1:end_pos] == "(":
                end_pos -= 1
            clean_text = text[: match.start()] + text[end_pos:]
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


def _extract_flower_type(
    text: str,
    type_lookup: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[str], str]:
    """
    Extract flower type and return remaining text.

    Args:
        text: Text to search
        type_lookup: Optional custom lookup dict (uses FLOWER_TYPES_FALLBACK if None)
    """
    lookup = type_lookup or FlowerTypeLookup.get_types_sync()
    words = text.split()

    for i, word in enumerate(words):
        word_lower = word.lower().rstrip(",.;:")
        if word_lower in lookup:
            flower_type = lookup[word_lower]
            # Remove this word from the text
            remaining = " ".join(words[:i] + words[i + 1 :])
            return flower_type, remaining.strip()

    return None, text


def _extract_subtype(
    text: str,
    subtype_lookup: Optional[Dict[str, Dict[str, str]]] = None,
) -> Tuple[Optional[str], str]:
    """
    Extract flower subtype (кустовая, спрей, etc.) and return remaining text.

    Args:
        text: Text to search
        subtype_lookup: Optional custom lookup dict

    Returns:
        Tuple of (subtype_name or None, remaining_text)
    """
    lookup = subtype_lookup or FlowerTypeLookup.get_subtypes_sync()
    words = text.split()

    for i, word in enumerate(words):
        word_lower = word.lower().rstrip(",.;:")
        if word_lower in lookup:
            subtype_name = lookup[word_lower]["name"]
            # Remove this word from the text
            remaining = " ".join(words[:i] + words[i + 1 :])
            return subtype_name, remaining.strip()

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


# =============================================================================
# Main Normalization Functions
# =============================================================================

def normalize_name(
    raw_name: str,
    type_lookup: Optional[Dict[str, str]] = None,
    subtype_lookup: Optional[Dict[str, Dict[str, str]]] = None,
) -> NormalizedName:
    """
    Normalize a flower product name into structured components.

    Args:
        raw_name: Raw product name like "Роза кустовая Бабалу 50 см (Эквадор)"
        type_lookup: Optional custom type lookup dict
        subtype_lookup: Optional custom subtype lookup dict

    Returns:
        NormalizedName with extracted components
    """
    if not raw_name:
        return NormalizedName(original=raw_name or "")

    result = NormalizedName(original=raw_name)
    text = raw_name.strip()

    # Extract in order: farm, country, length, colors, type, subtype
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
    result.flower_type, text = _extract_flower_type(text, type_lookup)

    # 6. Extract subtype (NEW: кустовая, спрей, etc.)
    result.flower_subtype, text = _extract_subtype(text, subtype_lookup)

    # 6.5 Remove pack_qty patterns before variety extraction
    # These are already extracted separately but pollute variety name
    text = re.sub(r"\s*\(\d{1,3}\)\s*$", "", text)  # "(20)" at end
    text = re.sub(r"\s*\(\d{1,3}\s*шт\)", "", text, flags=re.IGNORECASE)  # "(20 шт)"
    text = re.sub(r"\s*х\d{1,2}\s*$", "", text, flags=re.IGNORECASE)  # "х12" at end
    text = text.strip()

    # 7. Remaining text is the variety
    result.variety = _clean_variety(text) if text else None

    # 8. Build clean name (type + subtype + variety)
    parts = []
    if result.flower_type:
        parts.append(result.flower_type)
    if result.flower_subtype:
        parts.append(result.flower_subtype.lower())
    if result.variety:
        parts.append(result.variety)

    result.clean_name = " ".join(parts) if parts else raw_name

    return result


async def normalize_name_async(
    raw_name: str,
    db,
) -> NormalizedName:
    """
    Normalize a flower product name using database lookups.

    This is the preferred method when you have an async database session.

    Args:
        raw_name: Raw product name
        db: AsyncSession instance

    Returns:
        NormalizedName with extracted components
    """
    type_lookup = await FlowerTypeLookup.get_types_async(db)
    subtype_lookup = await FlowerTypeLookup.get_subtypes_async(db)
    return normalize_name(raw_name, type_lookup, subtype_lookup)


def normalize_names_batch(
    names: List[str],
    type_lookup: Optional[Dict[str, str]] = None,
    subtype_lookup: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[NormalizedName]:
    """
    Normalize multiple names in batch.

    Args:
        names: List of raw product names
        type_lookup: Optional custom type lookup dict
        subtype_lookup: Optional custom subtype lookup dict

    Returns:
        List of NormalizedName objects
    """
    return [normalize_name(name, type_lookup, subtype_lookup) for name in names]


async def normalize_names_batch_async(
    names: List[str],
    db,
) -> List[NormalizedName]:
    """
    Normalize multiple names using database lookups.

    Args:
        names: List of raw product names
        db: AsyncSession instance

    Returns:
        List of NormalizedName objects
    """
    type_lookup = await FlowerTypeLookup.get_types_async(db)
    subtype_lookup = await FlowerTypeLookup.get_subtypes_async(db)
    return [normalize_name(name, type_lookup, subtype_lookup) for name in names]


def generate_stable_key(normalized: NormalizedName) -> str:
    """
    Generate a stable key for grouping variants.

    Names with the same flower type, subtype, and variety (but different sizes)
    should have the same stable key.

    Args:
        normalized: Normalized name result

    Returns:
        Stable key string for grouping
    """
    parts = []

    if normalized.flower_type:
        parts.append(normalized.flower_type.lower())

    if normalized.flower_subtype:
        parts.append(normalized.flower_subtype.lower())

    if normalized.variety:
        # Normalize variety for matching
        variety = normalized.variety.lower()
        variety = re.sub(r"\s+", "_", variety)
        variety = re.sub(r"[^a-zа-яё0-9_]", "", variety)
        parts.append(variety)

    if normalized.origin_country:
        parts.append(normalized.origin_country.lower()[:3])

    return "|".join(parts) if parts else normalized.original.lower()[:50]
