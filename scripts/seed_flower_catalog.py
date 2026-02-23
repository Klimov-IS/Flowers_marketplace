"""Seed script for flower catalog data.

Seeds flower types, subtypes, and their synonyms from the existing
hardcoded dictionaries in name_normalizer.py.

Usage:
    python scripts/seed_flower_catalog.py

Or from API endpoint (will be added later).
"""
import asyncio
import os
import sys
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.api.models.catalog import (
    FlowerCategory,
    FlowerSubtype,
    FlowerType,
    FlowerVariety,
    SubtypeSynonym,
    TypeSynonym,
    VarietySynonym,
)

# Database URL from environment or default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://flower_user:flower_pass@localhost:5433/flower_market"
)

# Categories (optional grouping)
CATEGORIES = [
    {"name": "Срезанные цветы", "slug": "cut-flowers", "sort_order": 1},
    {"name": "Зелень и листья", "slug": "greenery", "sort_order": 2},
    {"name": "Сухоцветы", "slug": "dried", "sort_order": 3},
]

# Flower types with their synonyms and category
# Format: (canonical_name, slug, category_slug, [synonyms])
FLOWER_TYPES = [
    # Cut flowers
    ("Роза", "rosa", "cut-flowers", ["роза", "розы", "розу", "розой", "rose", "roses"]),
    ("Гвоздика", "carnation", "cut-flowers", ["гвоздика", "гвоздики", "гвоздику", "carnation"]),
    ("Хризантема", "chrysanthemum", "cut-flowers", ["хризантема", "хризантемы", "chrysanthemum"]),
    ("Сантини", "santini", "cut-flowers", ["сантини", "santini"]),
    ("Эустома", "eustoma", "cut-flowers", ["эустома", "лизиантус", "eustoma", "lisianthus"]),
    ("Альстромерия", "alstroemeria", "cut-flowers", ["альстромерия", "альстромерии", "alstroemeria"]),
    ("Гипсофила", "gypsophila", "cut-flowers", ["гипсофила", "гипсофилы", "gypsophila"]),
    ("Калла", "calla", "cut-flowers", ["калла", "каллы", "каллу", "calla"]),
    ("Гербера", "gerbera", "cut-flowers", ["гербера", "герберы", "герберу", "gerbera"]),
    ("Гортензия", "hydrangea", "cut-flowers", ["гортензия", "гортензии", "hydrangea"]),
    ("Пион", "peony", "cut-flowers", ["пион", "пионы", "пиона", "peony", "peonies"]),
    ("Тюльпан", "tulip", "cut-flowers", ["тюльпан", "тюльпаны", "тюльпана", "tulip", "tulips"]),
    ("Лилия", "lily", "cut-flowers", ["лилия", "лилии", "лилию", "lily", "lilies"]),
    ("Орхидея", "orchid", "cut-flowers", ["орхидея", "орхидеи", "orchid"]),
    ("Статица", "statice", "cut-flowers", ["статица", "статицы", "statice", "limonium"]),
    ("Ранункулюс", "ranunculus", "cut-flowers", ["ранункулюс", "ранункулюсы", "ranunculus"]),
    ("Анемон", "anemone", "cut-flowers", ["анемон", "анемоны", "анемона", "anemone"]),
    ("Фрезия", "freesia", "cut-flowers", ["фрезия", "фрезии", "freesia"]),
    ("Ирис", "iris", "cut-flowers", ["ирис", "ирисы", "ириса", "iris"]),
    ("Нарцисс", "narcissus", "cut-flowers", ["нарцисс", "нарциссы", "нарцисса", "narcissus", "daffodil"]),
    ("Мимоза", "mimosa", "cut-flowers", ["мимоза", "мимозы", "mimosa"]),
    ("Антуриум", "anthurium", "cut-flowers", ["антуриум", "антуриумы", "anthurium"]),
    ("Протея", "protea", "cut-flowers", ["протея", "протеи", "protea"]),
    ("Леукоспермум", "leucospermum", "cut-flowers", ["леукоспермум", "leucospermum"]),
    ("Краспедия", "craspedia", "cut-flowers", ["краспедия", "craspedia"]),
    ("Астра", "aster", "cut-flowers", ["астра", "астры", "aster"]),
    ("Матрикария", "matricaria", "cut-flowers", ["матрикария", "matricaria"]),
    ("Ромашка", "chamomile", "cut-flowers", ["ромашка", "ромашки", "chamomile"]),
    ("Лимониум", "limonium", "cut-flowers", ["лимониум", "limonium"]),
    ("Озотамнус", "ozothamnus", "cut-flowers", ["озотамнус", "ozothamnus"]),
    ("Вероника", "veronica", "cut-flowers", ["вероника", "veronica"]),
    ("Дельфиниум", "delphinium", "cut-flowers", ["дельфиниум", "дельфиниумы", "delphinium"]),
    ("Гиперикум", "hypericum", "cut-flowers", ["гиперикум", "hypericum"]),
    ("Илекс", "ilex", "cut-flowers", ["илекс", "ilex"]),

    # Greenery
    ("Эвкалипт", "eucalyptus", "greenery", ["эвкалипт", "эвкалипта", "eucalyptus"]),
    ("Рускус", "ruscus", "greenery", ["рускус", "ruscus"]),
    ("Аспидистра", "aspidistra", "greenery", ["аспидистра", "aspidistra"]),
    ("Писташ", "pistacia", "greenery", ["писташ", "фисташка", "pistacia", "pistachio"]),
    ("Салал", "salal", "greenery", ["салал", "salal"]),
]

# Subtypes with their synonyms
# Format: (type_slug, name, slug, [synonyms])
SUBTYPES = [
    # Rose subtypes
    ("rosa", "Кустовая", "shrub", ["кустовая", "кустовой", "куст", "shrub", "spray"]),
    ("rosa", "Спрей", "spray-rose", ["спрей", "spray"]),
    ("rosa", "Пионовидная", "peony-style", ["пионовидная", "пионовидной", "peony"]),
    ("rosa", "Эквадорская", "ecuadorian", ["эквадорская", "эквадорской", "ecuador", "ecuadorian"]),

    # Chrysanthemum subtypes
    ("chrysanthemum", "Кустовая", "shrub", ["кустовая", "кустовой", "куст"]),
    ("chrysanthemum", "Одноголовая", "single-head", ["одноголовая", "одноголовой", "одна голова"]),

    # Carnation subtypes
    ("carnation", "Кустовая", "shrub", ["кустовая", "кустовой", "куст"]),
    ("carnation", "Одноголовая", "single-head", ["одноголовая", "одноголовой"]),

    # Eustoma subtypes
    ("eustoma", "Махровая", "double", ["махровая", "махровой", "double"]),
    ("eustoma", "Немахровая", "single", ["немахровая", "немахровой", "single"]),

    # Gerbera subtypes
    ("gerbera", "Мини", "mini", ["мини", "mini", "минигербера"]),
]


async def seed_catalog(db: AsyncSession) -> dict:
    """Seed flower catalog data.

    Returns:
        dict with counts of created entities
    """
    stats = {
        "categories": 0,
        "types": 0,
        "type_synonyms": 0,
        "subtypes": 0,
        "subtype_synonyms": 0,
    }

    # 1. Create categories
    category_map = {}  # slug -> id
    for cat_data in CATEGORIES:
        # Check if exists
        result = await db.execute(
            select(FlowerCategory).where(FlowerCategory.slug == cat_data["slug"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            category_map[cat_data["slug"]] = existing.id
            print(f"  Category '{cat_data['name']}' already exists")
            continue

        category = FlowerCategory(
            id=uuid4(),
            name=cat_data["name"],
            slug=cat_data["slug"],
            sort_order=cat_data["sort_order"],
        )
        db.add(category)
        category_map[cat_data["slug"]] = category.id
        stats["categories"] += 1
        print(f"  Created category: {cat_data['name']}")

    await db.flush()

    # 2. Create flower types with synonyms
    type_map = {}  # slug -> id
    for canonical_name, slug, category_slug, synonyms in FLOWER_TYPES:
        # Check if type exists
        result = await db.execute(
            select(FlowerType).where(FlowerType.slug == slug)
        )
        existing = result.scalar_one_or_none()
        if existing:
            type_map[slug] = existing.id
            print(f"  Type '{canonical_name}' already exists")
            continue

        flower_type = FlowerType(
            id=uuid4(),
            category_id=category_map.get(category_slug),
            canonical_name=canonical_name,
            slug=slug,
            is_active=True,
        )
        db.add(flower_type)
        type_map[slug] = flower_type.id
        stats["types"] += 1
        print(f"  Created type: {canonical_name}")

        # Create synonyms for this type
        for syn in synonyms:
            syn_lower = syn.lower()
            # Check if synonym already exists
            result = await db.execute(
                select(TypeSynonym).where(TypeSynonym.synonym == syn_lower)
            )
            if result.scalar_one_or_none():
                continue

            synonym = TypeSynonym(
                id=uuid4(),
                type_id=flower_type.id,
                synonym=syn_lower,
                priority=100,
            )
            db.add(synonym)
            stats["type_synonyms"] += 1

    await db.flush()

    # 3. Create subtypes with synonyms
    for type_slug, name, subtype_slug, synonyms in SUBTYPES:
        type_id = type_map.get(type_slug)
        if not type_id:
            print(f"  WARNING: Type '{type_slug}' not found for subtype '{name}'")
            continue

        # Check if subtype exists
        result = await db.execute(
            select(FlowerSubtype).where(
                FlowerSubtype.type_id == type_id,
                FlowerSubtype.slug == subtype_slug,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  Subtype '{name}' for '{type_slug}' already exists")
            continue

        subtype = FlowerSubtype(
            id=uuid4(),
            type_id=type_id,
            name=name,
            slug=subtype_slug,
            is_active=True,
        )
        db.add(subtype)
        stats["subtypes"] += 1
        print(f"  Created subtype: {type_slug}/{name}")

        # Create synonyms for this subtype
        for syn in synonyms:
            syn_lower = syn.lower()
            synonym = SubtypeSynonym(
                id=uuid4(),
                subtype_id=subtype.id,
                synonym=syn_lower,
                priority=100,
            )
            db.add(synonym)
            stats["subtype_synonyms"] += 1

    await db.commit()
    return stats


async def seed_varieties(db: AsyncSession) -> dict:
    """Seed flower varieties from data files.

    Returns:
        dict with counts of created entities
    """
    stats = {
        "varieties": 0,
        "variety_synonyms": 0,
        "skipped": 0,
    }

    # Import variety data files
    try:
        from apps.api.data.varieties_roses import ROSE_VARIETIES
    except ImportError:
        print("  WARNING: varieties_roses.py not found, skipping rose varieties")
        ROSE_VARIETIES = []

    try:
        from apps.api.data.varieties_other import OTHER_VARIETIES
    except ImportError:
        print("  WARNING: varieties_other.py not found, skipping other varieties")
        OTHER_VARIETIES = []

    all_varieties = ROSE_VARIETIES + OTHER_VARIETIES
    if not all_varieties:
        print("  No variety data found")
        return stats

    print(f"  Loading {len(all_varieties)} varieties...")

    # Build type_slug -> type_id mapping
    result = await db.execute(select(FlowerType))
    type_map = {t.slug: t.id for t in result.scalars()}

    # Build (type_slug, subtype_slug) -> subtype_id mapping
    result = await db.execute(
        select(FlowerSubtype, FlowerType.slug.label("type_slug"))
        .join(FlowerType)
    )
    subtype_map = {}
    for row in result:
        subtype = row[0]
        type_slug = row[1]
        subtype_map[(type_slug, subtype.slug)] = subtype.id

    for entry in all_varieties:
        type_slug = entry["type_slug"]
        type_id = type_map.get(type_slug)
        if not type_id:
            stats["skipped"] += 1
            continue

        variety_slug = entry["slug"]

        # Check if variety already exists (by type + slug)
        result = await db.execute(
            select(FlowerVariety).where(
                FlowerVariety.type_id == type_id,
                FlowerVariety.slug == variety_slug,
            )
        )
        if result.scalar_one_or_none():
            stats["skipped"] += 1
            continue

        # Resolve subtype_id if provided
        subtype_id = None
        if entry.get("subtype_slug"):
            subtype_id = subtype_map.get((type_slug, entry["subtype_slug"]))

        variety = FlowerVariety(
            id=uuid4(),
            type_id=type_id,
            subtype_id=subtype_id,
            name=entry["name"],
            slug=variety_slug,
            official_colors=entry.get("official_colors"),
            is_verified=False,  # Mass seed = not manually verified
            is_active=True,
        )
        db.add(variety)
        stats["varieties"] += 1

        # Create synonyms
        seen_synonyms = set()
        for syn in entry.get("synonyms", []):
            syn_lower = syn.lower().strip()
            if not syn_lower or syn_lower in seen_synonyms:
                continue
            seen_synonyms.add(syn_lower)

            # Check if synonym already exists for this variety
            existing = await db.execute(
                select(VarietySynonym).where(
                    VarietySynonym.variety_id == variety.id,
                    VarietySynonym.synonym == syn_lower,
                )
            )
            if existing.scalar_one_or_none():
                continue

            synonym = VarietySynonym(
                id=uuid4(),
                variety_id=variety.id,
                synonym=syn_lower,
                priority=100,
            )
            db.add(synonym)
            stats["variety_synonyms"] += 1

        # Flush periodically to avoid huge transactions
        if stats["varieties"] % 100 == 0:
            await db.flush()
            print(f"    ... {stats['varieties']} varieties created so far")

    await db.commit()
    return stats


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Flower Catalog Seed Script")
    print("=" * 60)

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Phase 1-3: Types, subtypes, categories
        print("\nPhase 1-3: Seeding flower types and subtypes...")
        try:
            stats = await seed_catalog(db)
            print(f"  Categories created: {stats['categories']}")
            print(f"  Types created: {stats['types']}")
            print(f"  Type synonyms created: {stats['type_synonyms']}")
            print(f"  Subtypes created: {stats['subtypes']}")
            print(f"  Subtype synonyms created: {stats['subtype_synonyms']}")
        except Exception as e:
            print(f"\nError during type/subtype seeding: {e}")
            raise

        # Phase 4: Varieties
        print("\nPhase 4: Seeding flower varieties...")
        try:
            v_stats = await seed_varieties(db)
            print(f"  Varieties created: {v_stats['varieties']}")
            print(f"  Variety synonyms created: {v_stats['variety_synonyms']}")
            print(f"  Skipped (already exist): {v_stats['skipped']}")
        except Exception as e:
            print(f"\nError during variety seeding: {e}")
            raise

    print("\n" + "=" * 60)
    print("Seed completed successfully!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
