"""Admin products endpoints — supplier cabinet CRUD."""
import io
import os
import uuid as uuid_module

import structlog
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.dependencies import get_current_supplier
from apps.api.database import get_db
from apps.api.models.product import Product

logger = structlog.get_logger()
router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class ProductCreate(BaseModel):
    title: str
    flower_type: str | None = None
    variety: str | None = None
    length_cm: int | None = None
    color: str | None = None
    origin_country: str | None = None
    pack_type: str | None = None
    pack_qty: int | None = None
    price: Decimal
    currency: str = "RUB"
    stock_qty: int | None = None


class ProductUpdate(BaseModel):
    title: str | None = None
    flower_type: str | None = None
    variety: str | None = None
    length_cm: int | None = None
    color: str | None = None
    origin_country: str | None = None
    pack_type: str | None = None
    pack_qty: int | None = None
    price: Decimal | None = None
    stock_qty: int | None = None
    is_active: bool | None = None


class ProductRow(BaseModel):
    id: UUID
    title: str
    flower_type: str | None = None
    variety: str | None = None
    length_cm: int | None = None
    color: str | None = None
    origin_country: str | None = None
    pack_type: str | None = None
    pack_qty: int | None = None
    photo_url: str | None = None
    price: Decimal
    currency: str
    stock_qty: int | None = None
    status: str
    is_active: bool
    raw_name: str | None = None

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    products: list[ProductRow]
    total: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/products")
async def list_supplier_products(
    q: str | None = Query(None),
    status: list[str] | None = Query(None),
    origin_country: list[str] | None = Query(None),
    colors: list[str] | None = Query(None),
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
    length_min: int | None = Query(None),
    length_max: int | None = Query(None),
    stock_min: int | None = Query(None),
    stock_max: int | None = Query(None),
    sort_by: str | None = Query(None),
    sort_dir: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    """List products for the authenticated supplier with filtering and sorting."""
    query = (
        select(Product)
        .where(
            Product.supplier_id == supplier.id,
            Product.status != "deleted",
        )
    )

    # Multi-status filter
    if status:
        query = query.where(Product.status.in_(status))

    # Text search
    if q:
        q_lower = q.lower()
        query = query.where(
            func.lower(Product.title).contains(q_lower)
        )

    # Origin country filter (supports __null__ sentinel)
    if origin_country:
        conditions = []
        has_null = "__null__" in origin_country
        real_countries = [c for c in origin_country if c != "__null__"]
        if real_countries:
            conditions.append(Product.origin_country.in_(real_countries))
        if has_null:
            conditions.append(Product.origin_country.is_(None))
        if conditions:
            from sqlalchemy import or_
            query = query.where(or_(*conditions))

    # Color filter (supports __null__ sentinel)
    if colors:
        conditions = []
        has_null = "__null__" in colors
        real_colors = [c for c in colors if c != "__null__"]
        if real_colors:
            conditions.append(Product.color.in_(real_colors))
        if has_null:
            conditions.append(Product.color.is_(None))
        if conditions:
            from sqlalchemy import or_
            query = query.where(or_(*conditions))

    # Range filters
    if price_min is not None:
        query = query.where(Product.price >= price_min)
    if price_max is not None:
        query = query.where(Product.price <= price_max)
    if length_min is not None:
        query = query.where(Product.length_cm >= length_min)
    if length_max is not None:
        query = query.where(Product.length_cm <= length_max)
    if stock_min is not None:
        query = query.where(Product.stock_qty >= stock_min)
    if stock_max is not None:
        query = query.where(Product.stock_qty <= stock_max)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sorting
    sort_columns = {
        "raw_name": Product.title,
        "title": Product.title,
        "price": Product.price,
        "length_cm": Product.length_cm,
        "stock_qty": Product.stock_qty,
        "created_at": Product.created_at,
    }
    sort_col = sort_columns.get(sort_by or "", Product.created_at)
    if sort_dir == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Pagination (page/per_page)
    offset = (page - 1) * per_page
    query = query.limit(per_page).offset(offset)

    result = await db.execute(query)
    products = result.scalars().all()

    return ProductListResponse(
        products=[ProductRow.model_validate(p) for p in products],
        total=total,
    )


@router.get("/products/{product_id}")
async def get_product(
    product_id: UUID,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
) -> ProductRow:
    """Get a single product by ID."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.supplier_id == supplier.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductRow.model_validate(product)


@router.post("/products", status_code=201)
async def create_product(
    body: ProductCreate,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Create a new product. Immediately visible in the catalog."""
    product = Product(
        supplier_id=supplier.id,
        title=body.title,
        flower_type=body.flower_type,
        variety=body.variety,
        length_cm=body.length_cm,
        color=body.color,
        origin_country=body.origin_country,
        pack_type=body.pack_type,
        pack_qty=body.pack_qty,
        price=body.price,
        currency=body.currency,
        stock_qty=body.stock_qty,
        status="active",
        is_active=True,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    logger.info("product.created", product_id=str(product.id), title=body.title)
    return {"product_id": product.id}


@router.patch("/products/{product_id}")
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Update product fields. Only non-null fields in the request body are updated."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.supplier_id == supplier.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    logger.info("product.updated", product_id=str(product_id), fields=list(update_data.keys()))
    return {"ok": True}


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: UUID,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a product (set status=deleted, is_active=false)."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.supplier_id == supplier.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.status = "deleted"
    product.is_active = False
    await db.commit()

    logger.info("product.deleted", product_id=str(product_id))
    return {"ok": True}


@router.post("/products/{product_id}/photo")
async def upload_product_photo(
    product_id: UUID,
    file: UploadFile = File(...),
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Upload a photo for a product. Accepts JPEG/PNG/WebP images."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.supplier_id == supplier.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: JPEG, PNG, WebP"
        )

    # Validate file size (max 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size: 5MB")

    from PIL import Image

    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "uploads", "photos",
    )
    os.makedirs(upload_dir, exist_ok=True)

    # Optimize image: resize to max 800px and convert to WebP
    img = Image.open(io.BytesIO(contents))
    img = img.convert("RGB")
    img.thumbnail((800, 800), Image.LANCZOS)

    filename = f"{uuid_module.uuid4().hex}.webp"
    filepath = os.path.join(upload_dir, filename)
    img.save(filepath, "WEBP", quality=85)

    photo_url = f"/uploads/photos/{filename}"
    product.photo_url = photo_url
    await db.commit()

    logger.info("product.photo_uploaded", product_id=str(product_id), photo_url=photo_url)
    return {"photo_url": photo_url}


@router.post("/products/{product_id}/hide")
async def hide_product(
    product_id: UUID,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Hide a product (set status=hidden, is_active=false)."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.supplier_id == supplier.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.status = "hidden"
    product.is_active = False
    await db.commit()

    logger.info("product.hidden", product_id=str(product_id))
    return {"id": str(product_id), "status": "hidden", "message": "Product hidden"}


@router.post("/products/{product_id}/restore")
async def restore_product(
    product_id: UUID,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Restore a hidden product (set status=active, is_active=true)."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.supplier_id == supplier.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.status = "active"
    product.is_active = True
    await db.commit()

    logger.info("product.restored", product_id=str(product_id))
    return {"id": str(product_id), "status": "active", "message": "Product restored"}


@router.post("/products/{product_id}/duplicate")
async def duplicate_product(
    product_id: UUID,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate a product — create a copy with '(копия)' suffix."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.supplier_id == supplier.id,
        )
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Product not found")

    copy = Product(
        supplier_id=supplier.id,
        title=f"{original.title} (копия)",
        flower_type=original.flower_type,
        variety=original.variety,
        length_cm=original.length_cm,
        color=original.color,
        origin_country=original.origin_country,
        pack_type=original.pack_type,
        pack_qty=original.pack_qty,
        photo_url=original.photo_url,
        price=original.price,
        currency=original.currency,
        stock_qty=original.stock_qty,
        status="active",
        is_active=True,
        raw_name=original.raw_name,
    )
    db.add(copy)
    await db.commit()
    await db.refresh(copy)

    logger.info("product.duplicated", original_id=str(product_id), new_id=str(copy.id))
    return {"original_id": str(product_id), "new_product_id": str(copy.id), "message": "Product duplicated"}


class BulkActionRequest(BaseModel):
    product_ids: list[UUID]


@router.post("/products/bulk-delete")
async def bulk_delete_products(
    body: BulkActionRequest,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete multiple products."""
    result = await db.execute(
        select(Product).where(
            Product.id.in_(body.product_ids),
            Product.supplier_id == supplier.id,
            Product.status != "deleted",
        )
    )
    products = result.scalars().all()
    for p in products:
        p.status = "deleted"
        p.is_active = False
    await db.commit()
    return {"affected_count": len(products), "status": "deleted", "message": f"Deleted {len(products)} products"}


@router.post("/products/bulk-hide")
async def bulk_hide_products(
    body: BulkActionRequest,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Hide multiple products."""
    result = await db.execute(
        select(Product).where(
            Product.id.in_(body.product_ids),
            Product.supplier_id == supplier.id,
            Product.status != "deleted",
        )
    )
    products = result.scalars().all()
    for p in products:
        p.status = "hidden"
        p.is_active = False
    await db.commit()
    return {"affected_count": len(products), "status": "hidden", "message": f"Hidden {len(products)} products"}


@router.post("/products/bulk-restore")
async def bulk_restore_products(
    body: BulkActionRequest,
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Restore multiple products."""
    result = await db.execute(
        select(Product).where(
            Product.id.in_(body.product_ids),
            Product.supplier_id == supplier.id,
        )
    )
    products = result.scalars().all()
    for p in products:
        p.status = "active"
        p.is_active = True
    await db.commit()
    return {"affected_count": len(products), "status": "active", "message": f"Restored {len(products)} products"}
