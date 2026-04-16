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
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    supplier=Depends(get_current_supplier),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    """List products for the authenticated supplier."""
    query = (
        select(Product)
        .where(
            Product.supplier_id == supplier.id,
            Product.status != "deleted",
        )
    )

    if status:
        query = query.where(Product.status == status)

    if q:
        q_lower = q.lower()
        query = query.where(
            func.lower(Product.title).contains(q_lower)
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Product.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    products = result.scalars().all()

    return ProductListResponse(
        products=[
            ProductRow(
                id=p.id,
                title=p.title,
                flower_type=p.flower_type,
                variety=p.variety,
                length_cm=p.length_cm,
                color=p.color,
                origin_country=p.origin_country,
                pack_type=p.pack_type,
                pack_qty=p.pack_qty,
                photo_url=p.photo_url,
                price=p.price,
                currency=p.currency,
                stock_qty=p.stock_qty,
                status=p.status,
                is_active=p.is_active,
                raw_name=p.raw_name,
            )
            for p in products
        ],
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
