"""Seed data for known flower farms / growers.

Contains ~40 entries covering major Ecuadorian, Colombian, Kenyan,
Dutch, Chinese and Israeli farms that appear in Russian wholesale
flower price lists.

Each entry follows the schema:
    canonical_name  - English uppercase canonical name
    slug            - lowercase, URL-safe identifier
    country         - Country of origin (None if unknown)
    synonyms        - List of known spellings (Latin lowercase + Cyrillic)

Usage:
    from apps.api.data.farms import KNOWN_FARMS, build_farm_lookup

    lookup = build_farm_lookup()          # synonym -> canonical_name
    lookup.get("фрама")                   # -> "FRAMA FLOWERS"
    lookup.get("тесса")                   # -> "TESSA"
"""
from typing import Dict, List


KNOWN_FARMS: List[dict] = [
    # ========================================================================
    # ECUADOR — Major farms
    # ========================================================================
    {
        "canonical_name": "ROSAPRIMA",
        "slug": "rosaprima",
        "country": "Ecuador",
        "synonyms": [
            "rosaprima", "rosa prima", "розаприма", "роза прима",
        ],
    },
    {
        "canonical_name": "NARANJO",
        "slug": "naranjo",
        "country": "Ecuador",
        "synonyms": ["naranjo", "наранхо"],
    },
    {
        "canonical_name": "BROWN BREEDING",
        "slug": "brown-breeding",
        "country": "Ecuador",
        "synonyms": ["brown breeding", "brown breed", "браун бридинг"],
    },
    {
        "canonical_name": "ALEXANDRA FARMS",
        "slug": "alexandra-farms",
        "country": "Ecuador",
        "synonyms": [
            "alexandra farms", "alexandra farm", "александра фармс",
        ],
    },
    {
        "canonical_name": "ESMERALDA",
        "slug": "esmeralda",
        "country": "Ecuador",
        "synonyms": ["esmeralda", "эсмеральда"],
    },
    {
        "canonical_name": "AGROCOEX",
        "slug": "agrocoex",
        "country": "Ecuador",
        "synonyms": ["agrocoex", "агрокоэкс"],
    },
    {
        "canonical_name": "FRAMA FLOWERS",
        "slug": "frama-flowers",
        "country": "Ecuador",
        "synonyms": [
            "frama flowers", "frama flower", "frama",
            "фрама флауэрс", "фрама",
        ],
    },
    {
        "canonical_name": "FLOWERS DESIGN",
        "slug": "flowers-design",
        "country": "Ecuador",
        "synonyms": [
            "flowers design", "flower design", "флауэрс дизайн",
        ],
    },
    {
        "canonical_name": "GALAXY",
        "slug": "galaxy",
        "country": "Ecuador",
        "synonyms": ["galaxy", "гэлэкси", "галакси"],
    },
    {
        "canonical_name": "TESSA",
        "slug": "tessa",
        "country": "Ecuador",
        "synonyms": ["tessa", "тесса"],
    },
    {
        "canonical_name": "LUAN",
        "slug": "luan",
        "country": "Ecuador",
        "synonyms": ["luan", "луан"],
    },
    {
        "canonical_name": "PIANGOFLOR",
        "slug": "piangoflor",
        "country": "Ecuador",
        "synonyms": ["piangoflor", "пиангофлор"],
    },
    {
        "canonical_name": "ISABELLA",
        "slug": "isabella",
        "country": "Ecuador",
        "synonyms": ["isabella", "изабелла"],
    },
    {
        "canonical_name": "LA UNION",
        "slug": "la-union",
        "country": "Ecuador",
        "synonyms": ["la union", "ла юнион"],
    },
    {
        "canonical_name": "PROTEAS",
        "slug": "proteas",
        "country": "Ecuador",
        "synonyms": ["proteas", "протеас"],
    },
    {
        "canonical_name": "HOJA VERDE",
        "slug": "hoja-verde",
        "country": "Ecuador",
        "synonyms": ["hoja verde", "ходжа верде", "хойя верде"],
    },
    {
        "canonical_name": "ROYAL FLOWERS",
        "slug": "royal-flowers",
        "country": "Ecuador",
        "synonyms": ["royal flowers", "royal flower", "роял флауэрс"],
    },
    {
        "canonical_name": "AGRIGAN",
        "slug": "agrigan",
        "country": "Ecuador",
        "synonyms": ["agrigan", "агриган"],
    },
    {
        "canonical_name": "PONTE TRESA",
        "slug": "ponte-tresa",
        "country": "Ecuador",
        "synonyms": ["ponte tresa", "понте треса"],
    },
    # ========================================================================
    # ECUADOR — Farm codes (used in composite farm strings like СТАР+КОРАЗОН)
    # ========================================================================
    {
        "canonical_name": "STAR ROSES",
        "slug": "star-roses",
        "country": "Ecuador",
        "synonyms": ["star roses", "star", "стар"],
    },
    {
        "canonical_name": "CORAZON",
        "slug": "corazon",
        "country": "Ecuador",
        "synonyms": ["corazon", "коразон"],
    },
    {
        "canonical_name": "MATIZ",
        "slug": "matiz",
        "country": "Ecuador",
        "synonyms": ["matiz", "матиз"],
    },
    {
        "canonical_name": "ECO ROZ",
        "slug": "eco-roz",
        "country": "Ecuador",
        "synonyms": ["eco roz", "эко роз"],
    },
    {
        "canonical_name": "SOPHIE",
        "slug": "sophie",
        "country": "Ecuador",
        "synonyms": ["sophie", "софи"],
    },
    {
        "canonical_name": "BELLA ROSA",
        "slug": "bella-rosa",
        "country": "Ecuador",
        "synonyms": ["bella rosa", "белла роз", "белла роза"],
    },
    {
        "canonical_name": "CHARMING",
        "slug": "charming",
        "country": "Ecuador",
        "synonyms": ["charming", "чарминг"],
    },
    {
        "canonical_name": "ANNI ROSA",
        "slug": "anni-rosa",
        "country": "Ecuador",
        "synonyms": ["anni rosa", "анни роза"],
    },
    {
        "canonical_name": "ATLAS",
        "slug": "atlas",
        "country": "Ecuador",
        "synonyms": ["atlas", "атлас", "алтас"],
    },
    # ========================================================================
    # COLOMBIA
    # ========================================================================
    {
        "canonical_name": "ELITE FLOWER",
        "slug": "elite-flower",
        "country": "Colombia",
        "synonyms": ["elite flower", "elite flowers", "элит флауэр"],
    },
    {
        "canonical_name": "QFC",
        "slug": "qfc",
        "country": "Colombia",
        "synonyms": ["qfc"],
    },
    {
        "canonical_name": "SUNSHINE BOUQUET",
        "slug": "sunshine-bouquet",
        "country": "Colombia",
        "synonyms": ["sunshine bouquet", "саншайн букет"],
    },
    # ========================================================================
    # KENYA
    # ========================================================================
    {
        "canonical_name": "SIAN",
        "slug": "sian",
        "country": "Kenya",
        "synonyms": ["sian", "сиан"],
    },
    {
        "canonical_name": "AAA ROSES",
        "slug": "aaa-roses",
        "country": "Kenya",
        "synonyms": ["aaa roses", "aaa", "ааа розес"],
    },
    {
        "canonical_name": "TAMBUZI",
        "slug": "tambuzi",
        "country": "Kenya",
        "synonyms": ["tambuzi", "тамбузи"],
    },
    {
        "canonical_name": "RED LANDS ROSES",
        "slug": "red-lands-roses",
        "country": "Kenya",
        "synonyms": ["red lands roses", "red lands", "ред лэндс"],
    },
    # ========================================================================
    # NETHERLANDS
    # ========================================================================
    {
        "canonical_name": "DUMMEN ORANGE",
        "slug": "dummen-orange",
        "country": "Netherlands",
        "synonyms": ["dummen orange", "дюммен оранж"],
    },
    {
        "canonical_name": "DE RUITER",
        "slug": "de-ruiter",
        "country": "Netherlands",
        "synonyms": ["de ruiter", "де рюйтер"],
    },
    {
        "canonical_name": "VAN DEN BERG",
        "slug": "van-den-berg",
        "country": "Netherlands",
        "synonyms": ["van den berg", "ван ден берг"],
    },
    # ========================================================================
    # CHINA
    # ========================================================================
    {
        "canonical_name": "LI HUA",
        "slug": "li-hua",
        "country": "China",
        "synonyms": ["li hua", "ли хуа"],
    },
]


def build_farm_lookup() -> Dict[str, str]:
    """Build a flat synonym -> canonical_name lookup dictionary.

    Returns:
        Dict mapping lowercase synonym to uppercase canonical_name.
    """
    lookup: Dict[str, str] = {}
    for farm in KNOWN_FARMS:
        canonical = farm["canonical_name"]
        for syn in farm["synonyms"]:
            lookup[syn.lower()] = canonical
    return lookup
