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
    "хамелациум": "Ваксфлауэр",
    "клематис": "Клематис",
    "матиола": "Матиола",
    "маттиола": "Матиола",  # alias
    "оксипеталум": "Оксипеталум",
    # Хвойные и декоративные
    "туя": "Туя",
    "туи": "Туя",
    "сосна": "Сосна",
    "ель": "Ель",
    "можжевельник": "Можжевельник",
    "самшит": "Самшит",
    # Экзотика
    "стрелиция": "Стрелиция",
    "протея": "Протея",
    "банксия": "Банксия",
    "скабиоза": "Скабиоза",
    "целозия": "Целозия",
    "цинерария": "Цинерария",
    # Зелень
    "аралия": "Аралия",
    "берграс": "Берграс",
    "папоротник": "Папоротник",
    "питтоспорум": "Питтоспорум",
    "робеллини": "Робеллини",
    "тласпи": "Тласпи",
    "флокс": "Флокс",
    # Дополнительные типы (06.02.2026 - batch 2)
    "вакс": "Ваксфлауэр",  # alias
    "кохия": "Кохия",
    "подсолнух": "Подсолнух",
    "подсолнечник": "Подсолнух",  # alias
    "солидаго": "Солидаго",
    "танацетум": "Танацетум",
    "эрингиум": "Эрингиум",
    "скиммия": "Скиммия",
    "цимбидиум": "Цимбидиум",
    "ранункулус": "Ранункулюс",  # alias (already have ранункулюс)
    "питоспорум": "Питтоспорум",  # alias
    "розенботтел": "Розенботтел",
    # Сухоцветы и стабилизированные
    "амарант": "Амарант",
    "хлопок": "Хлопок",
    "лаванда": "Лаванда",
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

# Slug-to-canonical mapping for building variety→type fallback
_TYPE_SLUG_TO_CANONICAL: Dict[str, str] = {
    "rosa": "Роза",
    "chrysanthemum": "Хризантема",
    "carnation": "Гвоздика",
    "tulip": "Тюльпан",
    "eustoma": "Эустома",
    "alstroemeria": "Альстромерия",
    "gerbera": "Гербера",
    "hydrangea": "Гортензия",
    "peony": "Пион",
    "calla": "Калла",
    "ranunculus": "Ранункулюс",
    "freesia": "Фрезия",
    "iris": "Ирис",
    "eucalyptus": "Эвкалипт",
    "ruscus": "Рускус",
    "aspidistra": "Аспидистра",
    "pistacia": "Писташ",
    "salal": "Салал",
    "santini": "Сантини",
    "gypsophila": "Гипсофила",
    "lily": "Лилия",
    "orchid": "Орхидея",
    "statice": "Статица",
    "narcissus": "Нарцисс",
    "anemone": "Анемон",
    "hypericum": "Гиперикум",
}


# Supplemental Cyrillic variety names commonly seen in Russian price lists.
# Covers gaps where seed data has Latin names but suppliers write in Russian.
_CYRILLIC_VARIETY_SUPPLEMENT: Dict[str, str] = {
    # Розы — стандартные
    "аваланш": "Роза", "аваланж": "Роза", "аква": "Роза",
    "анастасия": "Роза", "аннабель": "Роза", "бабалу": "Роза",
    "бариста": "Роза", "би свит": "Роза", "блэк мэджик": "Роза",
    "булевард": "Роза", "ви пинк": "Роза", "гран при": "Роза",
    "готча": "Роза", "джумилия": "Роза",
    "кантри блюз": "Роза", "карнелиан": "Роза",
    "кахала": "Роза", "кенди экспрешен": "Роза", "кендилайт": "Роза",
    "кэндлайт": "Роза", "коттон экспрешн": "Роза",
    "лучано": "Роза", "мандарин экспрешн": "Роза",
    "моментум": "Роза", "мондиал": "Роза",
    "мультиколор": "Роза", "нина": "Роза",
    "оранж краш": "Роза", "пинк мондиал": "Роза",
    "плэй бланка": "Роза", "фридом": "Роза",
    "фрутетто": "Роза", "хот спот": "Роза",
    "шокин блу": "Роза", "шоколад": "Роза",
    "эксплорер": "Роза", "эсперанс": "Роза",
    "ред наоми": "Роза", "софи лорен": "Роза",
    "мирослава": "Роза", "рокси": "Роза",
    "амор амор": "Роза", "баттеркап": "Роза",
    "кимберли": "Роза", "мандала": "Роза", "шиммер": "Роза",
    "ивана": "Роза", "лола": "Роза",
    "александра": "Роза", "баракуда": "Роза", "кларенс": "Роза",
    "пич аваланш": "Роза", "пенни лейн": "Роза",
    "ред монстер": "Роза", "пинк монстер": "Роза",
    "ред пинк монстер": "Роза",
    # Розы — кустовые/спрей (Голландия)
    "грин глоу": "Роза", "джесси": "Роза", "джульетта": "Роза",
    "доминиция": "Роза", "капучино": "Роза",
    "роял порцелина": "Роза", "саммер денс": "Роза",
    "файерворкс": "Роза", "фатал аттра": "Роза",
    # Розы — спрей (бабблс и др.)
    "голден трандсеттер": "Роза", "жозефина": "Роза",
    "лавли лидия": "Роза", "лидия": "Роза",
    "супер сенсейшн": "Роза", "сплэш сенсейшн": "Роза",
    "трейси": "Роза", "хейли": "Роза",
    "черри хеопс": "Роза", "яна": "Роза",
    "айвори дидикейншен": "Роза", "броиз бабблс": "Роза",
    "джелато": "Роза", "кинг бабблс": "Роза",
    "крем деменши": "Роза", "марвел бабблс": "Роза",
    "пинк дименшн": "Роза", "пленти": "Роза",
    "скарлет дименшн": "Роза", "спешиал дименшн": "Роза",
    "твайлайт бабблс": "Роза", "фемке": "Роза",
    "черри бабблс": "Роза", "леди бомбастик": "Роза",
    "мадам бомбастик": "Роза", "мисс бомбастик": "Роза",
    "мисти бабблс": "Роза", "парфюм бабблс": "Роза",
    "софи": "Роза",
    # Хризантемы
    "балтика": "Хризантема", "зембла": "Хризантема",
    "бейб": "Хризантема", "калимба": "Хризантема",
    "кеннеди": "Хризантема", "командер пинк": "Хризантема",
    "ньютон": "Хризантема", "пастел пинк": "Хризантема",
    "туту": "Хризантема", "чик": "Хризантема",
    "магнум": "Хризантема", "бакарди": "Хризантема",
    # Сантини
    "алтай": "Сантини", "дориа черри": "Сантини",
    "пурпетта": "Сантини", "росси": "Сантини",
    "сан-ап": "Сантини", "эллисон салмон": "Сантини",
    # Тюльпаны
    "колумбус": "Тюльпан", "супер пэррот": "Тюльпан",
    "флэш поинт": "Тюльпан", "стронг голд": "Тюльпан",
    # Эустомы
    "алисса": "Эустома", "корелли": "Эустома", "розита": "Эустома",
    # Лилии
    "амистад": "Лилия", "анжела": "Лилия",
    "сантандер": "Лилия", "таблденс": "Лилия",
    # Каллы
    "кантор": "Калла", "коломбэ": "Калла",
    "пикассо": "Калла", "россо": "Калла", "суматра": "Калла",
    # Гортензии
    "май виенна": "Гортензия",
    # Ранункулюс
    "ханой": "Ранункулюс",
}


def _build_variety_to_type_map() -> Dict[str, str]:
    """Build a fallback map: variety synonym (lowercase) → flower type canonical name.

    Uses seed data from varieties_roses.py and varieties_other.py,
    plus a supplemental Cyrillic dictionary.
    Loaded lazily on first call.
    """
    mapping: Dict[str, str] = {}

    # 1. Load from seed files
    try:
        from apps.api.data.varieties_roses import ROSE_VARIETIES
    except ImportError:
        ROSE_VARIETIES = []
    try:
        from apps.api.data.varieties_other import OTHER_VARIETIES
    except ImportError:
        OTHER_VARIETIES = []

    for entry in ROSE_VARIETIES + OTHER_VARIETIES:
        type_slug = entry.get("type_slug", "")
        canonical_type = _TYPE_SLUG_TO_CANONICAL.get(type_slug)
        if not canonical_type:
            continue
        # Map variety name itself
        name_lower = entry.get("name", "").lower().strip()
        if name_lower and name_lower not in mapping:
            mapping[name_lower] = canonical_type
        # Map all synonyms
        for syn in entry.get("synonyms", []):
            syn_lower = syn.lower().strip()
            if syn_lower and syn_lower not in mapping:
                mapping[syn_lower] = canonical_type

    # 2. Merge supplemental Cyrillic names (don't overwrite seed data)
    for name, flower_type in _CYRILLIC_VARIETY_SUPPLEMENT.items():
        if name not in mapping:
            mapping[name] = flower_type

    return mapping


# Lazy-loaded variety→type fallback
_VARIETY_TO_TYPE_CACHE: Optional[Dict[str, str]] = None


def _get_variety_to_type_map() -> Dict[str, str]:
    """Get or build the variety→type fallback map."""
    global _VARIETY_TO_TYPE_CACHE
    if _VARIETY_TO_TYPE_CACHE is None:
        _VARIETY_TO_TYPE_CACHE = _build_variety_to_type_map()
    return _VARIETY_TO_TYPE_CACHE


# Lazy-loaded farm synonym→canonical lookup
_FARM_LOOKUP_CACHE: Optional[Dict[str, str]] = None


def _get_farm_lookup() -> Dict[str, str]:
    """Get or build the farm synonym→canonical_name lookup."""
    global _FARM_LOOKUP_CACHE
    if _FARM_LOOKUP_CACHE is None:
        try:
            from apps.api.data.farms import build_farm_lookup
            _FARM_LOOKUP_CACHE = build_farm_lookup()
        except ImportError:
            _FARM_LOOKUP_CACHE = {}
    return _FARM_LOOKUP_CACHE


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
    "китай": "Китай",
    "china": "Китай",
    "турция": "Турция",
    "turkey": "Турция",
    "индия": "Индия",
    "india": "Индия",
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
    r"\b(PIANGOFLOR)\b",
    r"\b(ISABELLA)\b",
    r"\b([A-Z]{2,}(?:\s+[A-Z]{2,})*)\b",  # Fallback: all-caps words at end
]

# Known farms that appear in parentheses (case-insensitive)
FARM_NAMES_IN_PARENS = {
    "тесса": "TESSA",
    "tessa": "TESSA",
    "розаприма": "ROSAPRIMA",
    "rosaprima": "ROSAPRIMA",
    "анни роза": "ANNI ROSA",
    "anni rosa": "ANNI ROSA",
}

# Color words (for extraction)
# Compound colors MUST come before base colors so "светло-розовая" matches
# before "розовая". The _extract_colors() function iterates by key length desc.
COLORS: Dict[str, str] = {
    # --- Compound colors (prefix + base) ---
    "светло-розовый": "розовый",
    "светло-розовая": "розовый",
    "нежно-розовый": "розовый",
    "нежно-розовая": "розовый",
    "ярко-розовый": "розовый",
    "ярко-розовая": "розовый",
    "тёмно-розовый": "розовый",
    "тёмно-розовая": "розовый",
    "темно-розовый": "розовый",
    "темно-розовая": "розовый",
    "светло-желтый": "жёлтый",
    "светло-желтая": "жёлтый",
    "ярко-желтый": "жёлтый",
    "ярко-желтая": "жёлтый",
    "тёмно-красный": "красный",
    "тёмно-красная": "красный",
    "темно-красный": "красный",
    "темно-красная": "красный",
    "ярко-красный": "красный",
    "ярко-красная": "красный",
    "светло-сиреневый": "сиреневый",
    "светло-сиреневая": "сиреневый",
    "нежно-сиреневый": "сиреневый",
    "нежно-сиреневая": "сиреневый",
    "светло-зеленый": "зелёный",
    "светло-зеленая": "зелёный",
    "тёмно-бордовый": "бордовый",
    "тёмно-бордовая": "бордовый",
    "темно-бордовый": "бордовый",
    "темно-бордовая": "бордовый",
    "ярко-оранжевый": "оранжевый",
    "ярко-оранжевая": "оранжевый",
    "нежно-кремовый": "кремовый",
    "нежно-кремовая": "кремовый",
    "нежно-персиковый": "персиковый",
    "нежно-персиковая": "персиковый",
    # --- Base colors ---
    "белый": "белый",
    "белая": "белый",
    "белые": "белый",
    "красный": "красный",
    "красная": "красный",
    "красные": "красный",
    "розовый": "розовый",
    "розовая": "розовый",
    "розовые": "розовый",
    "желтый": "жёлтый",
    "желтая": "жёлтый",
    "желтые": "жёлтый",
    "жёлтый": "жёлтый",
    "жёлтая": "жёлтый",
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
    "сиреневая": "сиреневый",
    "бордовый": "бордовый",
    "бордовая": "бордовый",
    "зеленый": "зелёный",
    "зеленая": "зелёный",
    "зелёный": "зелёный",
    "зелёная": "зелёный",
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

    # Bundle detection (NEW)
    is_bundle_list: bool = False  # Multiple varieties in one row
    bundle_varieties: List[str] = field(default_factory=list)  # Extracted variety names
    warnings: List[str] = field(default_factory=list)  # Parsing warnings

    def __post_init__(self):
        if self.colors is None:
            self.colors = []
        if self.bundle_varieties is None:
            self.bundle_varieties = []
        if self.warnings is None:
            self.warnings = []


# =============================================================================
# Extraction Functions
# =============================================================================

def _extract_length(text: str) -> Tuple[Optional[int], str]:
    """Extract length and return remaining text."""
    # Pattern 1: explicit "120см", "60 см", "120см(1)"
    pattern = r"(?<!\d)(\d{2,3})\s*(?:см|cm)(?:\b|\(|$)"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        length = int(match.group(1))
        if 30 <= length <= 200:
            # Remove the length part from text (keep any trailing parenthesis)
            end_pos = match.end()
            # Don't consume trailing parenthesis
            if end_pos > 0 and text[end_pos - 1:end_pos] == "(":
                end_pos -= 1
            clean_text = text[: match.start()] + text[end_pos:]
            return length, clean_text.strip()

    # Pattern 2: number without "см" followed by pack qty in parens: "130(1)", "120 (5)"
    # Common in supplier prices: "Корилус 130(1)", "Магнолия 120см(1)"
    pattern2 = r"\b(\d{2,3})\s*\(\d+\)"
    match2 = re.search(pattern2, text)
    if match2:
        length = int(match2.group(1))
        if 30 <= length <= 200:
            # Remove just the number, keep the parenthesized part for pack_qty extraction
            clean_text = text[:match2.start()] + text[match2.start() + len(match2.group(1)):]
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

    # Then try country abbreviations (Экв, Гол, Кол, Кен, Изр)
    abbrev_pattern = r"\b(Экв|Гол|Кол|Кен|Изр|Кит)\b"
    abbrev_match = re.search(abbrev_pattern, text, re.IGNORECASE)
    if abbrev_match:
        abbrev = abbrev_match.group(1).lower()
        country_map = {
            "экв": "Эквадор",
            "гол": "Нидерланды",
            "кол": "Колумбия",
            "кен": "Кения",
            "изр": "Израиль",
            "кит": "Китай",
        }
        if abbrev in country_map:
            clean_text = text[:abbrev_match.start()] + text[abbrev_match.end():]
            return country_map[abbrev], clean_text.strip()

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

    # Pattern 1: Farm codes with + signs in parentheses (СТАР+КОРАЗОН+МАТИЗ+...)
    # These are lists of farm codes separated by +
    plus_pattern = r"\s*\(([А-ЯA-Z][А-ЯA-Zа-яa-z\s]*(?:\+[А-ЯA-Zа-яa-z\s]+){2,})\)\s*"
    plus_match = re.search(plus_pattern, text)
    if plus_match:
        farm = plus_match.group(1).strip()
        # Join with space to avoid concatenation issues like "50смЭкв"
        clean_text = text[:plus_match.start()].rstrip() + " " + text[plus_match.end():].lstrip()
        return farm, clean_text.strip()

    # Pattern 2: Known farm names in parentheses (hardcoded + dictionary)
    farm_lookup = _get_farm_lookup()

    # 2a: Hardcoded list (legacy, fast check)
    for farm_key, farm_name in FARM_NAMES_IN_PARENS.items():
        pattern = rf"\s*\({re.escape(farm_key)}\)\s*"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            clean_text = text[:match.start()].rstrip() + " " + text[match.end():].lstrip()
            return farm_name, clean_text.strip()

    # 2b: Dictionary-based lookup in parentheses
    for paren_match in re.finditer(r"\(([^)]+)\)", text):
        content = paren_match.group(1).strip().lower()
        canonical = farm_lookup.get(content)
        if canonical:
            clean_text = text[:paren_match.start()].rstrip() + " " + text[paren_match.end():].lstrip()
            return canonical, clean_text.strip()

    # Pattern 3: Standard farm patterns (FRAMA FLOWERS, NARANJO, etc.)
    for pattern in FARM_PATTERNS[:-1]:  # Skip fallback pattern first
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            farm = match.group(1).strip()
            # Normalize via dictionary if possible
            farm_canonical = farm_lookup.get(farm.lower())
            clean_text = text[: match.start()] + text[match.end() :]
            return farm_canonical or farm, clean_text.strip()

    # Fallback: look for all-caps words at end of string
    # Try long words first (3+ chars each), then shorter (2+ chars)
    for min_len in (3, 2):
        pat = rf"\b([A-Z]{{{min_len},}}(?:\s+[A-Z]{{{min_len},}})*)\s*$"
        fallback_match = re.search(pat, text)
        if fallback_match:
            farm = fallback_match.group(1).strip()
            # Check if preceded by a short ALL-CAPS word (e.g. "LA" before "UNION")
            prefix_text = text[: fallback_match.start()].rstrip()
            prefix_match = re.search(r"\b([A-Z]{2,3})\s*$", prefix_text)
            if prefix_match:
                extended_farm = prefix_match.group(1) + " " + farm
                extended_canonical = farm_lookup.get(extended_farm.lower())
                if extended_canonical:
                    clean_text = text[: prefix_match.start()].strip()
                    return extended_canonical, clean_text
            farm_canonical = farm_lookup.get(farm.lower())
            # Accept if known in dictionary (any length) or long enough
            if farm_canonical or len(farm) > 4:
                clean_text = text[: fallback_match.start()].strip()
                return farm_canonical or farm, clean_text

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
    """Extract colors and return remaining text.

    Iterates COLORS keys by length descending so compound colors
    like "светло-розовая" match before base "розовая".
    """
    found_colors = []
    clean_text = text

    # Sort by key length desc — compound colors first
    for color_key in sorted(COLORS, key=len, reverse=True):
        color_norm = COLORS[color_key]
        if color_key in clean_text.lower() and color_norm not in found_colors:
            found_colors.append(color_norm)
            # Remove color word
            pattern = re.compile(re.escape(color_key), re.IGNORECASE)
            clean_text = pattern.sub("", clean_text)

    # Clean up multiple spaces
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    return found_colors, clean_text


def _sanitize_text(text: str, flower_type: Optional[str] = None) -> str:
    """
    Multi-stage sanitization pipeline for raw product names.

    Applied early in the normalization flow to remove garbage before extraction.
    """
    if not text:
        return ""

    # Stage 1: Remove Unicode garbage (®, ™, ©, smart quotes, zero-width chars)
    text = re.sub(r"[®™©«»„""\u200b\u00a0\ufeff]", "", text)

    # Stage 2: Remove supplier markers at start (* # ! NEW НОВИНКА ХИТ SALE АКЦИЯ)
    text = re.sub(r"^[\s*#!•·▪►]+", "", text)
    text = re.sub(
        r"\b(?:NEW|НОВИНК[АИ]|ХИТ|SALE|АКЦИЯ|РАСПРОДАЖА|СКИДКА|HOT|BEST)[!.\s]*\b",
        "", text, flags=re.IGNORECASE,
    )

    # Stage 3: Remove leading numbering ("1. Explorer", "1) Explorer", "01 - Explorer")
    text = re.sub(r"^\s*\d{1,3}\s*[.):\-]\s*", "", text)

    # Stage 4: Remove parentheses with non-variety content
    # Keep country names, remove everything else that looks like noise
    noise_in_parens = (
        r"руб|шт|упак|цена|наличи|акци|new|нов|sale|скидк|хит|"
        r"остаток|количество|кол-во|заказ|предзаказ|под\s*заказ|"
        r"\d{3,}"  # 3+ digits (likely price)
    )
    text = re.sub(
        rf"\([^)]*(?:{noise_in_parens})[^)]*\)",
        "", text, flags=re.IGNORECASE,
    )

    # Stage 4.5: Remove parentheses with single-word synonyms/alt names
    # "ФИСТАШКА (пистация)" → "ФИСТАШКА", "Розенботтел (rosehip)" → "Розенботтел"
    # Keep: country names, farm names, pack qty like (25), variety-relevant content
    def _is_synonym_parens(content: str) -> bool:
        content = content.strip()
        # Skip numbers (pack qty)
        if re.match(r"^\d+", content):
            return False
        # Skip country names
        if content.lower() in COUNTRIES:
            return False
        # Single word, 3-20 letters, mostly Cyrillic or Latin = likely synonym
        if re.match(r"^[а-яёА-ЯЁa-zA-Z\-]{3,20}$", content):
            return True
        return False

    text = re.sub(
        r"\(([^)]{3,20})\)",
        lambda m: "" if _is_synonym_parens(m.group(1)) else m.group(0),
        text,
    )

    # Stage 5: Remove duplicate flower type from text
    # e.g., if flower_type="Роза" and text starts with "Роза " — remove the duplicate
    if flower_type:
        ft_lower = flower_type.lower()
        pattern = re.compile(r"\b" + re.escape(ft_lower) + r"\b", re.IGNORECASE)
        matches = list(pattern.finditer(text))
        if len(matches) > 1:
            # Remove all but the first occurrence
            for m in reversed(matches[1:]):
                text = text[:m.start()] + text[m.end():]
        elif len(matches) == 1:
            # If the flower_type is already extracted, we may still have it in text
            # This is handled elsewhere, so just clean trailing duplicate
            pass

    # Stage 6: Remove excessive punctuation
    text = re.sub(r"\.{2,}", "", text)      # "..."
    text = re.sub(r"!{2,}", "", text)       # "!!!"
    text = re.sub(r"-{3,}", "-", text)      # "---" -> "-"
    text = re.sub(r"_{2,}", " ", text)      # "__" -> " "

    # Stage 7: Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _clean_variety(text: str, flower_type: Optional[str] = None) -> str:
    """Clean up variety name after extraction."""
    if not text:
        return ""

    # Run sanitizer first (catches residual garbage)
    text = _sanitize_text(text, flower_type)

    # Remove leading digits that aren't part of variety name
    # "1 Explorer" -> "Explorer", "25 шт Freedom" -> "Freedom"
    text = re.sub(r"^\d{1,3}\s+(?=[A-ZА-ЯЁ])", "", text)

    # Remove common suffixes/noise
    text = re.sub(r"\s*[-–—]\s*", " ", text)  # Replace dashes with spaces

    # Fix unbalanced parentheses
    if "(" in text and ")" not in text:
        text = re.sub(r"\s*\([^)]*$", "", text)
    if ")" in text and "(" not in text:
        text = re.sub(r"^[^(]*\)\s*", "", text)

    # Remove trailing numbers that might be leftover pack qty (including decimals)
    text = re.sub(r"\s+\d{1,3}(?:\.\d+)?\s*$", "", text)

    # Remove country abbreviations like "Экв", "Гол", "Кол" at end
    text = re.sub(r"\s+(Экв|Гол|Кол|Кен|Изр)\s*$", "", text, flags=re.IGNORECASE)

    # Remove common noise words at end
    text = re.sub(r"\s+(дв|од)\s*$", "", text, flags=re.IGNORECASE)

    # Remove "N пуч" (number of bunches) anywhere
    text = re.sub(r"\s+\d{1,2}\s*пуч\b", "", text, flags=re.IGNORECASE)

    # Remove duplicate flower type from variety
    if flower_type:
        ft_lower = flower_type.lower()
        text_lower = text.lower()
        if text_lower.startswith(ft_lower + " "):
            text = text[len(ft_lower):].strip()
        elif text_lower.startswith(ft_lower):
            text = text[len(ft_lower):].strip()

    # Remove slashes that might remain
    text = re.sub(r"[/\\]+", " ", text)

    # Clean up multiple spaces
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" ,;.()[]")

    # Capitalize words properly
    words = text.split()
    if words:
        words = [w.capitalize() if w.islower() else w for w in words]
        return " ".join(words)

    return text


# =============================================================================
# Bundle Detection (multiple varieties in one row)
# =============================================================================

# Garbage patterns that should not be in product names
GARBAGE_PATTERNS = [
    r"цена\s*за\s*шт",  # "Цена За Шт"
    r"руб\.?(?:\s|$|/)",  # "Руб" or "Руб."
    r"цена\s*за\s*упак",  # "Цена за упак"
    r"штук[аи]?\b",  # "штука", "штуки"
    r"упаков[ка]",  # "упаковка"
    r"за\s*(?:шт|упак)",  # "за шт", "за упак"
    r"прайс",  # "прайс"
    r"наличи[ей]",  # "наличие"
    r"остаток",  # "остаток"
    r"количество",  # "количество"
    r"\b\d+[.,]?\d*\s*(?:кг|г)\b",  # "0,5 кг", "1 кг", "500 г"
]

# Minimum items to consider as bundle list
BUNDLE_MIN_ITEMS = 3


def _detect_bundle_list(text: str) -> Tuple[bool, List[str], List[str]]:
    """
    Detect if text contains a bundle list (multiple varieties comma-separated).

    Args:
        text: Text to analyze

    Returns:
        Tuple of (is_bundle, extracted_varieties, warnings)
    """
    warnings = []
    varieties = []

    # Check for garbage patterns first
    text_lower = text.lower()
    for pattern in GARBAGE_PATTERNS:
        if re.search(pattern, text_lower):
            warnings.append(f"garbage_text_detected: {pattern}")

    # Clean garbage from text BEFORE splitting by comma
    cleaned_text = _clean_garbage_from_text(text)
    # Also remove trailing dots and punctuation left after cleanup
    cleaned_text = re.sub(r"[.;:!]+\s*$", "", cleaned_text).strip()

    # Split by comma and analyze
    parts = [p.strip() for p in cleaned_text.split(",") if p.strip()]

    # Check if this looks like a variety list
    if len(parts) >= BUNDLE_MIN_ITEMS:
        # Additional heuristics:
        # 1. Most parts should be short (variety names are typically 1-3 words)
        # 2. Parts shouldn't contain numbers (prices, lengths)
        # 3. Parts shouldn't be too long (>30 chars suggests it's not a variety)

        valid_variety_count = 0
        for part in parts:
            part_clean = part.strip()
            # Strip trailing/leading dots/punctuation/slashes from each variety
            part_clean = re.sub(r"^[.;:!/\\]+|[.;:!/\\]+$", "", part_clean).strip()
            # Skip if only punctuation/whitespace left
            if not part_clean or not re.search(r"[а-яёА-ЯЁa-zA-Z]", part_clean):
                continue
            # Skip if has numbers (likely price/length)
            if re.search(r"\d", part_clean):
                continue
            # Skip if too long
            if len(part_clean) > 40:
                continue
            # Skip if too short (likely garbage)
            if len(part_clean) < 2:
                continue
            # Skip if it matches a garbage pattern
            part_lower = part_clean.lower()
            is_garbage = False
            for gp in GARBAGE_PATTERNS:
                if re.search(gp, part_lower):
                    is_garbage = True
                    break
            if is_garbage:
                continue
            # Remove type prefix from first variety (e.g., "Роза спрей: Голден" → "Голден")
            if not varieties:  # First variety
                colon_match = re.match(r"^.+?:\s*(.+)$", part_clean)
                if colon_match:
                    part_clean = colon_match.group(1).strip()
            # Looks like a variety name
            valid_variety_count += 1
            varieties.append(part_clean)

        # If we have 3+ valid varieties, it's a bundle list
        if valid_variety_count >= BUNDLE_MIN_ITEMS:
            return True, varieties, warnings + ["bundle_list_detected"]

    return False, [], warnings


def _extract_pack_qty(text: str) -> Tuple[Optional[int], str]:
    """
    Extract pack quantity from text BEFORE garbage cleanup.

    Handles patterns like:
    - "(25)" - just number in parens
    - "(50/10)" - bundle format (e.g., 50 stems in packs of 10)
    - "(25 шт)" - with explicit "шт"
    - "(б)", "(с)", "(м)" - size abbreviations (большой/средний/маленький)

    Returns:
        Tuple of (pack_qty or None, cleaned text)
    """
    pack_qty = None

    # Pattern 1: (number/number) at end - bundle format like "(50/10)"
    pattern1 = r"\s*\((\d{1,3})[/\\](\d{1,3})\)\s*$"
    match1 = re.search(pattern1, text)
    if match1:
        # First number is usually total, second is pack size
        qty = int(match1.group(2))  # Use pack size
        if 1 <= qty <= 100:
            pack_qty = qty
        text = text[:match1.start()].strip()
        return pack_qty, text

    # Pattern 2: (number) at end
    pattern2 = r"\s*\((\d{1,3})\)\s*$"
    match2 = re.search(pattern2, text)
    if match2:
        qty = int(match2.group(1))
        if 1 <= qty <= 100:
            pack_qty = qty
        text = text[:match2.start()].strip()
        return pack_qty, text

    # Pattern 3: (number шт) anywhere
    pattern3 = r"\s*\((\d{1,3})\s*шт\.?\)\s*"
    match3 = re.search(pattern3, text, re.IGNORECASE)
    if match3:
        qty = int(match3.group(1))
        if 1 <= qty <= 100:
            pack_qty = qty
        text = text[:match3.start()] + text[match3.end():]
        text = text.strip()
        return pack_qty, text

    # Pattern 4: Size abbreviations (б), (с), (м) for большой/средний/маленький
    pattern4 = r"\s*\([бсмБСМbsm]\)\s*$"
    match4 = re.search(pattern4, text)
    if match4:
        # Just remove, no qty extracted (it's a size indicator)
        text = text[:match4.start()].strip()
        return None, text

    # Pattern 5: "х10", "х12" at end (multiply indicator)
    pattern5 = r"\s*[хxХX](\d{1,2})\s*$"
    match5 = re.search(pattern5, text)
    if match5:
        qty = int(match5.group(1))
        if 1 <= qty <= 50:
            pack_qty = qty
        text = text[:match5.start()].strip()
        return pack_qty, text

    # Pattern 6: "(1 б.)", "(1 банч)", "(1 пуч)" - count with abbreviation
    pattern6 = r"\s*\((\d{1,2})\s*(?:б\.|банч|пуч)\)\s*$"
    match6 = re.search(pattern6, text, re.IGNORECASE)
    if match6:
        qty = int(match6.group(1))
        if 1 <= qty <= 50:
            pack_qty = qty
        text = text[:match6.start()].strip()
        return pack_qty, text

    # Pattern 7: "(N пуч)" - number of bunches anywhere
    pattern7 = r"\s*\((\d{1,2})\s*пуч\)\s*"
    match7 = re.search(pattern7, text, re.IGNORECASE)
    if match7:
        qty = int(match7.group(1))
        if 1 <= qty <= 50:
            pack_qty = qty
        text = text[:match7.start()] + text[match7.end():]
        text = text.strip()
        return pack_qty, text

    return pack_qty, text


def _clean_garbage_from_text(text: str) -> str:
    """Remove garbage patterns from text (header text that leaked in)."""
    for pattern in GARBAGE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Clean up extra punctuation (but NOT slashes - those are handled in _extract_pack_qty)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _apply_section_context(
    result: "NormalizedName",
    section_context: str,
    type_lookup: Optional[Dict[str, str]] = None,
) -> None:
    """Apply section header context as fallback for missing fields.

    Section context is a header like "Роза Эквадор" or "Хризантема" that
    applies to all rows in that section.  We parse it once and use the
    extracted type/country as fallback if the row itself didn't provide them.
    """
    if not section_context:
        return

    lookup = type_lookup or FlowerTypeLookup.get_types_sync()

    # Try to extract flower type from section context
    if result.flower_type is None:
        for word in section_context.split():
            word_lower = word.lower().rstrip(",.;:")
            if word_lower in lookup:
                result.flower_type = lookup[word_lower]
                break

    # Try to extract country from section context
    if result.origin_country is None:
        ctx_lower = section_context.lower()
        for country_key, country_name in COUNTRIES.items():
            if country_key in ctx_lower:
                result.origin_country = country_name
                break


# =============================================================================
# Main Normalization Functions
# =============================================================================

def normalize_name(
    raw_name: str,
    type_lookup: Optional[Dict[str, str]] = None,
    subtype_lookup: Optional[Dict[str, Dict[str, str]]] = None,
    section_context: Optional[str] = None,
) -> NormalizedName:
    """
    Normalize a flower product name into structured components.

    Args:
        raw_name: Raw product name like "Роза кустовая Бабалу 50 см (Эквадор)"
        type_lookup: Optional custom type lookup dict
        subtype_lookup: Optional custom subtype lookup dict
        section_context: Optional section header text (e.g. "Роза Эквадор")
            used as fallback for flower_type and origin_country when
            the row itself doesn't contain them.

    Returns:
        NormalizedName with extracted components
    """
    if not raw_name:
        return NormalizedName(original=raw_name or "")

    result = NormalizedName(original=raw_name)
    text = raw_name.strip()

    # 0. Detect bundle list FIRST (before other extractions)
    is_bundle, bundle_varieties, bundle_warnings = _detect_bundle_list(text)
    result.is_bundle_list = is_bundle
    result.bundle_varieties = bundle_varieties
    result.warnings = bundle_warnings

    # 0.1 Early sanitization (removes unicode garbage, markers, numbering)
    text = _sanitize_text(text)

    # 0.3 Extract pack_qty BEFORE garbage cleanup (to preserve slashes in patterns like 50/10)
    _, text = _extract_pack_qty(text)

    # 0.5 Clean garbage from text (header text that leaked in)
    text = _clean_garbage_from_text(text)

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

    # 6.5 Additional cleanup for any remaining pack patterns (second pass)
    _, text = _extract_pack_qty(text)  # Second pass with cleaned text
    text = text.strip()

    # 7. Remaining text is the variety (pass flower_type for dedup)
    result.variety = _clean_variety(text, result.flower_type) if text else None

    # 7.1 Fix: if variety is a pure number and no length detected, it's likely length
    if (result.variety and result.length_cm is None
            and re.match(r"^\d{1,3}$", result.variety)):
        num = int(result.variety)
        if 30 <= num <= 200:
            # Direct cm: "Корилус 130" → 130 cm
            result.length_cm = num
            result.variety = None
        elif 3 <= num <= 20 and result.flower_type:
            # Decimeter notation: "Роза 7" → 70 cm
            result.length_cm = num * 10
            result.variety = None

    # 7.5 Fallback: if type not detected but variety is known, infer type from library
    if result.flower_type is None and result.variety and not result.is_bundle_list:
        variety_map = _get_variety_to_type_map()
        variety_lower = result.variety.lower().strip()
        inferred_type = variety_map.get(variety_lower)
        if inferred_type:
            result.flower_type = inferred_type

    # 7.6 Fallback: use section_context to fill missing type/country
    if section_context:
        _apply_section_context(result, section_context, type_lookup)

    # 8. Build clean name (type + subtype + variety)
    parts = []
    if result.flower_type:
        parts.append(result.flower_type)
    if result.flower_subtype:
        parts.append(result.flower_subtype.lower())

    # For bundles, don't include the full variety list in clean_name
    if result.is_bundle_list:
        count = len(result.bundle_varieties)
        parts.append(f"({count} сортов)")
        result.variety = None  # Clear variety for bundles
    elif result.variety:
        parts.append(result.variety)

    result.clean_name = " ".join(parts) if parts else raw_name

    return result


async def normalize_name_async(
    raw_name: str,
    db,
    section_context: Optional[str] = None,
) -> NormalizedName:
    """
    Normalize a flower product name using database lookups.

    This is the preferred method when you have an async database session.

    Args:
        raw_name: Raw product name
        db: AsyncSession instance
        section_context: Optional section header for fallback

    Returns:
        NormalizedName with extracted components
    """
    type_lookup = await FlowerTypeLookup.get_types_async(db)
    subtype_lookup = await FlowerTypeLookup.get_subtypes_async(db)
    return normalize_name(raw_name, type_lookup, subtype_lookup, section_context)


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
