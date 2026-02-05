"""Flower catalog management endpoints.

Provides CRUD operations for:
- Flower categories (optional grouping)
- Flower types (Роза, Хризантема, etc.)
- Flower subtypes (Кустовая, Спрей, etc.)
- Flower varieties (Explorer, Freedom, etc.)
- Synonyms for all of the above
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models.catalog import (
    FlowerCategory,
    FlowerSubtype,
    FlowerType,
    FlowerVariety,
    SubtypeSynonym,
    TypeSynonym,
    VarietySynonym,
)

router = APIRouter()
logger = get_logger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================

# --- Category Schemas ---
class CategoryResponse(BaseModel):
    """Flower category response."""
    id: UUID
    name: str
    slug: str
    sort_order: int

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    """Create category request."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    sort_order: int = 0


# --- Synonym Schemas ---
class SynonymResponse(BaseModel):
    """Synonym response (for any entity)."""
    id: UUID
    synonym: str
    priority: int

    class Config:
        from_attributes = True


class SynonymCreate(BaseModel):
    """Create synonym request."""
    synonym: str = Field(..., min_length=1, max_length=100)
    priority: int = 100


# --- Type Schemas ---
class TypeResponse(BaseModel):
    """Flower type response."""
    id: UUID
    category_id: UUID | None
    canonical_name: str
    slug: str
    meta: dict
    is_active: bool
    synonyms: List[SynonymResponse] = []
    subtypes_count: int = 0

    class Config:
        from_attributes = True


class TypeWithSubtypesResponse(TypeResponse):
    """Flower type response with subtypes included."""
    subtypes: List["SubtypeResponse"] = []


class TypeCreate(BaseModel):
    """Create flower type request."""
    canonical_name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    category_id: UUID | None = None
    meta: dict = {}
    is_active: bool = True
    synonyms: List[str] = []


class TypeUpdate(BaseModel):
    """Update flower type request."""
    canonical_name: str | None = None
    category_id: UUID | None = None
    meta: dict | None = None
    is_active: bool | None = None


# --- Subtype Schemas ---
class SubtypeResponse(BaseModel):
    """Flower subtype response."""
    id: UUID
    type_id: UUID
    name: str
    slug: str
    meta: dict
    is_active: bool
    synonyms: List[SynonymResponse] = []

    class Config:
        from_attributes = True


class SubtypeCreate(BaseModel):
    """Create subtype request."""
    type_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    meta: dict = {}
    is_active: bool = True
    synonyms: List[str] = []


class SubtypeUpdate(BaseModel):
    """Update subtype request."""
    name: str | None = None
    meta: dict | None = None
    is_active: bool | None = None


# --- Variety Schemas ---
class VarietyResponse(BaseModel):
    """Flower variety response."""
    id: UUID
    type_id: UUID
    subtype_id: UUID | None
    name: str
    slug: str
    official_colors: List[str] | None
    typical_length_min: int | None
    typical_length_max: int | None
    meta: dict
    is_verified: bool
    is_active: bool
    synonyms: List[SynonymResponse] = []

    class Config:
        from_attributes = True


class VarietyCreate(BaseModel):
    """Create variety request."""
    type_id: UUID
    subtype_id: UUID | None = None
    name: str = Field(..., min_length=1, max_length=150)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    official_colors: List[str] | None = None
    typical_length_min: int | None = Field(None, gt=0, le=200)
    typical_length_max: int | None = Field(None, gt=0, le=200)
    meta: dict = {}
    is_verified: bool = False
    is_active: bool = True
    synonyms: List[str] = []


class VarietyUpdate(BaseModel):
    """Update variety request."""
    subtype_id: UUID | None = None
    name: str | None = None
    official_colors: List[str] | None = None
    typical_length_min: int | None = None
    typical_length_max: int | None = None
    meta: dict | None = None
    is_verified: bool | None = None
    is_active: bool | None = None


class VarietyBulkCreate(BaseModel):
    """Bulk create varieties request."""
    items: List[VarietyCreate]


# --- Lookup Response ---
class TypeLookupResponse(BaseModel):
    """Lookup response: synonym -> canonical_name mapping."""
    types: dict[str, str]  # synonym -> canonical_name
    subtypes: dict[str, dict]  # synonym -> {name, type_slug}


# =============================================================================
# Category Endpoints
# =============================================================================

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> List[FlowerCategory]:
    """List all flower categories ordered by sort_order."""
    result = await db.execute(
        select(FlowerCategory).order_by(FlowerCategory.sort_order)
    )
    return list(result.scalars().all())


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
) -> FlowerCategory:
    """Create a new flower category."""
    # Check for duplicate slug
    existing = await db.execute(
        select(FlowerCategory).where(FlowerCategory.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Category with slug '{data.slug}' already exists")

    category = FlowerCategory(
        name=data.name,
        slug=data.slug,
        sort_order=data.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


# =============================================================================
# Type Endpoints
# =============================================================================

@router.get("/types", response_model=List[TypeWithSubtypesResponse])
async def list_types(
    category_id: UUID | None = None,
    active_only: bool = True,
    include_subtypes: bool = True,
    db: AsyncSession = Depends(get_db),
) -> List[FlowerType]:
    """
    List flower types with their synonyms.

    Args:
        category_id: Filter by category (optional)
        active_only: Return only active types (default: True)
        include_subtypes: Include subtypes in response (default: True)
    """
    query = select(FlowerType).options(
        selectinload(FlowerType.synonyms),
        selectinload(FlowerType.subtypes).selectinload(FlowerSubtype.synonyms) if include_subtypes else selectinload(FlowerType.subtypes),
    )

    if category_id:
        query = query.where(FlowerType.category_id == category_id)
    if active_only:
        query = query.where(FlowerType.is_active == True)

    query = query.order_by(FlowerType.canonical_name)

    result = await db.execute(query)
    types = list(result.scalars().unique().all())

    # Add subtypes_count
    for t in types:
        t.subtypes_count = len(t.subtypes)

    return types


@router.get("/types/{type_id}", response_model=TypeWithSubtypesResponse)
async def get_type(
    type_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FlowerType:
    """Get a single flower type by ID."""
    result = await db.execute(
        select(FlowerType)
        .options(
            selectinload(FlowerType.synonyms),
            selectinload(FlowerType.subtypes).selectinload(FlowerSubtype.synonyms),
        )
        .where(FlowerType.id == type_id)
    )
    flower_type = result.scalar_one_or_none()
    if not flower_type:
        raise HTTPException(status_code=404, detail="Flower type not found")

    flower_type.subtypes_count = len(flower_type.subtypes)
    return flower_type


@router.post("/types", response_model=TypeResponse, status_code=201)
async def create_type(
    data: TypeCreate,
    db: AsyncSession = Depends(get_db),
) -> FlowerType:
    """Create a new flower type with optional synonyms."""
    # Check for duplicate
    existing = await db.execute(
        select(FlowerType).where(
            (FlowerType.slug == data.slug) | (FlowerType.canonical_name == data.canonical_name)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Flower type with this slug or name already exists")

    flower_type = FlowerType(
        canonical_name=data.canonical_name,
        slug=data.slug,
        category_id=data.category_id,
        meta=data.meta,
        is_active=data.is_active,
    )
    db.add(flower_type)
    await db.flush()

    # Add synonyms
    for syn in data.synonyms:
        syn_lower = syn.lower()
        # Check if synonym exists globally
        existing_syn = await db.execute(
            select(TypeSynonym).where(TypeSynonym.synonym == syn_lower)
        )
        if existing_syn.scalar_one_or_none():
            logger.warning("type_synonym_exists", synonym=syn_lower)
            continue

        synonym = TypeSynonym(
            type_id=flower_type.id,
            synonym=syn_lower,
            priority=100,
        )
        db.add(synonym)

    await db.commit()
    await db.refresh(flower_type)

    # Load synonyms for response
    result = await db.execute(
        select(FlowerType)
        .options(selectinload(FlowerType.synonyms))
        .where(FlowerType.id == flower_type.id)
    )
    return result.scalar_one()


@router.patch("/types/{type_id}", response_model=TypeResponse)
async def update_type(
    type_id: UUID,
    data: TypeUpdate,
    db: AsyncSession = Depends(get_db),
) -> FlowerType:
    """Update a flower type."""
    result = await db.execute(
        select(FlowerType)
        .options(selectinload(FlowerType.synonyms))
        .where(FlowerType.id == type_id)
    )
    flower_type = result.scalar_one_or_none()
    if not flower_type:
        raise HTTPException(status_code=404, detail="Flower type not found")

    if data.canonical_name is not None:
        flower_type.canonical_name = data.canonical_name
    if data.category_id is not None:
        flower_type.category_id = data.category_id
    if data.meta is not None:
        flower_type.meta = data.meta
    if data.is_active is not None:
        flower_type.is_active = data.is_active

    await db.commit()
    await db.refresh(flower_type)
    return flower_type


@router.post("/types/{type_id}/synonyms", response_model=SynonymResponse, status_code=201)
async def add_type_synonym(
    type_id: UUID,
    data: SynonymCreate,
    db: AsyncSession = Depends(get_db),
) -> TypeSynonym:
    """Add a synonym to a flower type."""
    # Check type exists
    result = await db.execute(
        select(FlowerType).where(FlowerType.id == type_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Flower type not found")

    syn_lower = data.synonym.lower()

    # Check if synonym exists
    existing = await db.execute(
        select(TypeSynonym).where(TypeSynonym.synonym == syn_lower)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Synonym '{syn_lower}' already exists")

    synonym = TypeSynonym(
        type_id=type_id,
        synonym=syn_lower,
        priority=data.priority,
    )
    db.add(synonym)
    await db.commit()
    await db.refresh(synonym)
    return synonym


@router.delete("/types/{type_id}/synonyms/{synonym_id}", status_code=204)
async def delete_type_synonym(
    type_id: UUID,
    synonym_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a synonym from a flower type."""
    result = await db.execute(
        select(TypeSynonym).where(
            TypeSynonym.id == synonym_id,
            TypeSynonym.type_id == type_id,
        )
    )
    synonym = result.scalar_one_or_none()
    if not synonym:
        raise HTTPException(status_code=404, detail="Synonym not found")

    await db.delete(synonym)
    await db.commit()


# =============================================================================
# Subtype Endpoints
# =============================================================================

@router.get("/subtypes", response_model=List[SubtypeResponse])
async def list_subtypes(
    type_id: UUID | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
) -> List[FlowerSubtype]:
    """List flower subtypes."""
    query = select(FlowerSubtype).options(selectinload(FlowerSubtype.synonyms))

    if type_id:
        query = query.where(FlowerSubtype.type_id == type_id)
    if active_only:
        query = query.where(FlowerSubtype.is_active == True)

    query = query.order_by(FlowerSubtype.name)

    result = await db.execute(query)
    return list(result.scalars().unique().all())


@router.post("/subtypes", response_model=SubtypeResponse, status_code=201)
async def create_subtype(
    data: SubtypeCreate,
    db: AsyncSession = Depends(get_db),
) -> FlowerSubtype:
    """Create a new flower subtype."""
    # Check type exists
    result = await db.execute(
        select(FlowerType).where(FlowerType.id == data.type_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Flower type not found")

    # Check for duplicate
    existing = await db.execute(
        select(FlowerSubtype).where(
            FlowerSubtype.type_id == data.type_id,
            FlowerSubtype.slug == data.slug,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Subtype with this slug already exists for this type")

    subtype = FlowerSubtype(
        type_id=data.type_id,
        name=data.name,
        slug=data.slug,
        meta=data.meta,
        is_active=data.is_active,
    )
    db.add(subtype)
    await db.flush()

    # Add synonyms
    for syn in data.synonyms:
        syn_lower = syn.lower()
        synonym = SubtypeSynonym(
            subtype_id=subtype.id,
            synonym=syn_lower,
            priority=100,
        )
        db.add(synonym)

    await db.commit()
    await db.refresh(subtype)

    # Load synonyms for response
    result = await db.execute(
        select(FlowerSubtype)
        .options(selectinload(FlowerSubtype.synonyms))
        .where(FlowerSubtype.id == subtype.id)
    )
    return result.scalar_one()


@router.patch("/subtypes/{subtype_id}", response_model=SubtypeResponse)
async def update_subtype(
    subtype_id: UUID,
    data: SubtypeUpdate,
    db: AsyncSession = Depends(get_db),
) -> FlowerSubtype:
    """Update a flower subtype."""
    result = await db.execute(
        select(FlowerSubtype)
        .options(selectinload(FlowerSubtype.synonyms))
        .where(FlowerSubtype.id == subtype_id)
    )
    subtype = result.scalar_one_or_none()
    if not subtype:
        raise HTTPException(status_code=404, detail="Subtype not found")

    if data.name is not None:
        subtype.name = data.name
    if data.meta is not None:
        subtype.meta = data.meta
    if data.is_active is not None:
        subtype.is_active = data.is_active

    await db.commit()
    await db.refresh(subtype)
    return subtype


@router.post("/subtypes/{subtype_id}/synonyms", response_model=SynonymResponse, status_code=201)
async def add_subtype_synonym(
    subtype_id: UUID,
    data: SynonymCreate,
    db: AsyncSession = Depends(get_db),
) -> SubtypeSynonym:
    """Add a synonym to a flower subtype."""
    result = await db.execute(
        select(FlowerSubtype).where(FlowerSubtype.id == subtype_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subtype not found")

    syn_lower = data.synonym.lower()

    # Check if synonym exists for this subtype
    existing = await db.execute(
        select(SubtypeSynonym).where(
            SubtypeSynonym.subtype_id == subtype_id,
            SubtypeSynonym.synonym == syn_lower,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Synonym '{syn_lower}' already exists for this subtype")

    synonym = SubtypeSynonym(
        subtype_id=subtype_id,
        synonym=syn_lower,
        priority=data.priority,
    )
    db.add(synonym)
    await db.commit()
    await db.refresh(synonym)
    return synonym


# =============================================================================
# Variety Endpoints
# =============================================================================

@router.get("/varieties", response_model=List[VarietyResponse])
async def list_varieties(
    type_id: UUID | None = None,
    subtype_id: UUID | None = None,
    search: str | None = Query(None, min_length=2),
    verified_only: bool = False,
    active_only: bool = True,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> List[FlowerVariety]:
    """
    List flower varieties with filters and search.

    Args:
        type_id: Filter by flower type
        subtype_id: Filter by subtype
        search: Search by name (fuzzy, min 2 chars)
        verified_only: Return only verified varieties
        active_only: Return only active varieties
        limit: Max results (default 100, max 500)
        offset: Pagination offset
    """
    query = select(FlowerVariety).options(selectinload(FlowerVariety.synonyms))

    if type_id:
        query = query.where(FlowerVariety.type_id == type_id)
    if subtype_id:
        query = query.where(FlowerVariety.subtype_id == subtype_id)
    if verified_only:
        query = query.where(FlowerVariety.is_verified == True)
    if active_only:
        query = query.where(FlowerVariety.is_active == True)
    if search:
        # Use trigram similarity for fuzzy search
        query = query.where(
            FlowerVariety.name.ilike(f"%{search}%")
        ).order_by(
            func.similarity(FlowerVariety.name, search).desc()
        )
    else:
        query = query.order_by(FlowerVariety.name)

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().unique().all())


@router.get("/varieties/{variety_id}", response_model=VarietyResponse)
async def get_variety(
    variety_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FlowerVariety:
    """Get a single variety by ID."""
    result = await db.execute(
        select(FlowerVariety)
        .options(selectinload(FlowerVariety.synonyms))
        .where(FlowerVariety.id == variety_id)
    )
    variety = result.scalar_one_or_none()
    if not variety:
        raise HTTPException(status_code=404, detail="Variety not found")
    return variety


@router.post("/varieties", response_model=VarietyResponse, status_code=201)
async def create_variety(
    data: VarietyCreate,
    db: AsyncSession = Depends(get_db),
) -> FlowerVariety:
    """Create a new flower variety."""
    # Validate type exists
    result = await db.execute(
        select(FlowerType).where(FlowerType.id == data.type_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Flower type not found")

    # Validate subtype if provided
    if data.subtype_id:
        result = await db.execute(
            select(FlowerSubtype).where(
                FlowerSubtype.id == data.subtype_id,
                FlowerSubtype.type_id == data.type_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Subtype not found or doesn't belong to this type")

    # Check for duplicate
    existing = await db.execute(
        select(FlowerVariety).where(
            FlowerVariety.type_id == data.type_id,
            FlowerVariety.slug == data.slug,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Variety with this slug already exists for this type")

    # Validate length range
    if data.typical_length_min and data.typical_length_max:
        if data.typical_length_min > data.typical_length_max:
            raise HTTPException(status_code=400, detail="typical_length_min must be <= typical_length_max")

    variety = FlowerVariety(
        type_id=data.type_id,
        subtype_id=data.subtype_id,
        name=data.name,
        slug=data.slug,
        official_colors=data.official_colors,
        typical_length_min=data.typical_length_min,
        typical_length_max=data.typical_length_max,
        meta=data.meta,
        is_verified=data.is_verified,
        is_active=data.is_active,
    )
    db.add(variety)
    await db.flush()

    # Add synonyms
    for syn in data.synonyms:
        syn_lower = syn.lower()
        synonym = VarietySynonym(
            variety_id=variety.id,
            synonym=syn_lower,
            priority=100,
        )
        db.add(synonym)

    await db.commit()
    await db.refresh(variety)

    # Load synonyms for response
    result = await db.execute(
        select(FlowerVariety)
        .options(selectinload(FlowerVariety.synonyms))
        .where(FlowerVariety.id == variety.id)
    )
    return result.scalar_one()


@router.post("/varieties/bulk", response_model=dict, status_code=201)
async def bulk_create_varieties(
    data: VarietyBulkCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Bulk create varieties.

    Returns:
        dict with created/skipped counts
    """
    created = 0
    skipped = 0

    for item in data.items:
        try:
            # Check if exists
            existing = await db.execute(
                select(FlowerVariety).where(
                    FlowerVariety.type_id == item.type_id,
                    FlowerVariety.slug == item.slug,
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            variety = FlowerVariety(
                type_id=item.type_id,
                subtype_id=item.subtype_id,
                name=item.name,
                slug=item.slug,
                official_colors=item.official_colors,
                typical_length_min=item.typical_length_min,
                typical_length_max=item.typical_length_max,
                meta=item.meta,
                is_verified=item.is_verified,
                is_active=item.is_active,
            )
            db.add(variety)
            await db.flush()

            # Add synonyms
            for syn in item.synonyms:
                synonym = VarietySynonym(
                    variety_id=variety.id,
                    synonym=syn.lower(),
                    priority=100,
                )
                db.add(synonym)

            created += 1
        except Exception as e:
            logger.warning("variety_bulk_create_item_failed", error=str(e), item=item.slug)
            skipped += 1

    await db.commit()
    return {"created": created, "skipped": skipped, "total": len(data.items)}


@router.patch("/varieties/{variety_id}", response_model=VarietyResponse)
async def update_variety(
    variety_id: UUID,
    data: VarietyUpdate,
    db: AsyncSession = Depends(get_db),
) -> FlowerVariety:
    """Update a flower variety."""
    result = await db.execute(
        select(FlowerVariety)
        .options(selectinload(FlowerVariety.synonyms))
        .where(FlowerVariety.id == variety_id)
    )
    variety = result.scalar_one_or_none()
    if not variety:
        raise HTTPException(status_code=404, detail="Variety not found")

    if data.subtype_id is not None:
        variety.subtype_id = data.subtype_id
    if data.name is not None:
        variety.name = data.name
    if data.official_colors is not None:
        variety.official_colors = data.official_colors
    if data.typical_length_min is not None:
        variety.typical_length_min = data.typical_length_min
    if data.typical_length_max is not None:
        variety.typical_length_max = data.typical_length_max
    if data.meta is not None:
        variety.meta = data.meta
    if data.is_verified is not None:
        variety.is_verified = data.is_verified
    if data.is_active is not None:
        variety.is_active = data.is_active

    await db.commit()
    await db.refresh(variety)
    return variety


@router.put("/varieties/{variety_id}/verify", response_model=VarietyResponse)
async def verify_variety(
    variety_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FlowerVariety:
    """Mark a variety as verified."""
    result = await db.execute(
        select(FlowerVariety)
        .options(selectinload(FlowerVariety.synonyms))
        .where(FlowerVariety.id == variety_id)
    )
    variety = result.scalar_one_or_none()
    if not variety:
        raise HTTPException(status_code=404, detail="Variety not found")

    variety.is_verified = True
    await db.commit()
    await db.refresh(variety)
    return variety


@router.post("/varieties/{variety_id}/synonyms", response_model=SynonymResponse, status_code=201)
async def add_variety_synonym(
    variety_id: UUID,
    data: SynonymCreate,
    db: AsyncSession = Depends(get_db),
) -> VarietySynonym:
    """Add a synonym to a variety."""
    result = await db.execute(
        select(FlowerVariety).where(FlowerVariety.id == variety_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Variety not found")

    syn_lower = data.synonym.lower()

    # Check if synonym exists for this variety
    existing = await db.execute(
        select(VarietySynonym).where(
            VarietySynonym.variety_id == variety_id,
            VarietySynonym.synonym == syn_lower,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Synonym '{syn_lower}' already exists for this variety")

    synonym = VarietySynonym(
        variety_id=variety_id,
        synonym=syn_lower,
        priority=data.priority,
    )
    db.add(synonym)
    await db.commit()
    await db.refresh(synonym)
    return synonym


# =============================================================================
# Lookup Endpoint (for parser)
# =============================================================================

@router.get("/lookup", response_model=TypeLookupResponse)
async def get_type_lookup(
    db: AsyncSession = Depends(get_db),
) -> TypeLookupResponse:
    """
    Get lookup tables for the parser.

    Returns:
        - types: dict[synonym -> canonical_name]
        - subtypes: dict[synonym -> {name, type_slug}]
    """
    # Get type synonyms
    type_result = await db.execute(
        select(TypeSynonym.synonym, FlowerType.canonical_name)
        .join(FlowerType)
        .where(FlowerType.is_active == True)
    )
    types = {row.synonym: row.canonical_name for row in type_result}

    # Get subtype synonyms
    subtype_result = await db.execute(
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
        for row in subtype_result
    }

    return TypeLookupResponse(types=types, subtypes=subtypes)


# =============================================================================
# Seed Endpoint
# =============================================================================

@router.post("/seed", response_model=dict)
async def seed_catalog(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Seed the flower catalog with initial data.

    This endpoint runs the seed script programmatically.
    Can be called multiple times safely (idempotent).
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

    from scripts.seed_flower_catalog import seed_catalog as do_seed

    try:
        stats = await do_seed(db)
        logger.info("catalog_seed_success", stats=stats)
        return {"status": "success", **stats}
    except Exception as e:
        logger.error("catalog_seed_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Seed failed: {str(e)}")


# Needed for forward reference resolution
TypeWithSubtypesResponse.model_rebuild()
