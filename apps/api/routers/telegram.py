"""Internal Telegram bot API endpoints.

These endpoints are used by the Telegram bot service to interact with
the platform. Protected by X-Bot-Token header.
"""
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import ImportBatch, Supplier
from apps.api.models.items import OfferCandidate, SupplierItem
from apps.api.models.telegram import TelegramLink
from apps.api.services.import_service import ImportService

router = APIRouter(prefix="/internal/telegram", tags=["telegram-internal"])
logger = get_logger(__name__)


# --- Auth dependency ---

async def verify_bot_token(x_bot_token: str = Header(...)) -> None:
    """Verify internal bot token."""
    if not settings.telegram_internal_token:
        raise HTTPException(status_code=503, detail="Telegram integration not configured")
    if x_bot_token != settings.telegram_internal_token:
        raise HTTPException(status_code=403, detail="Invalid bot token")


# --- Schemas ---

class FindByPhoneRequest(BaseModel):
    phone: str


class FindByPhoneResponse(BaseModel):
    found: bool
    entity_id: UUID | None = None
    entity_type: str | None = None
    name: str | None = None
    status: str | None = None


class LinkRequest(BaseModel):
    telegram_user_id: int
    telegram_chat_id: int
    role: str
    entity_id: UUID
    username: str | None = None
    first_name: str | None = None


class LinkResponse(BaseModel):
    id: UUID
    telegram_user_id: int
    role: str
    entity_id: UUID
    entity_name: str | None = None

    class Config:
        from_attributes = True


class RegisterSupplierRequest(BaseModel):
    name: str
    phone: str
    city_name: str | None = None


class RegisterSupplierResponse(BaseModel):
    supplier_id: UUID
    name: str
    status: str


class ParseErrorDetail(BaseModel):
    code: str
    message: str


class UploadPriceResponse(BaseModel):
    batch_id: UUID
    status: str
    filename: str | None
    raw_rows_count: int
    supplier_items_count: int
    offer_candidates_count: int
    parse_errors_count: int
    parse_errors: list[ParseErrorDetail] = []
    type_detected_pct: int
    variety_detected_pct: int


class LastImportResponse(BaseModel):
    batch_id: UUID
    filename: str | None
    status: str
    imported_at: datetime
    raw_rows_count: int
    supplier_items_count: int
    offer_candidates_count: int


# --- Endpoints ---

@router.post("/find-by-phone", response_model=FindByPhoneResponse, dependencies=[Depends(verify_bot_token)])
async def find_by_phone(
    data: FindByPhoneRequest,
    db: AsyncSession = Depends(get_db),
) -> FindByPhoneResponse:
    """Find supplier by phone number in contacts JSONB."""
    phone = _normalize_phone(data.phone)

    # Search in suppliers.contacts->'phone' (text extraction, no JSONB cast)
    result = await db.execute(
        select(Supplier).where(
            Supplier.contacts["phone"].astext.is_not(None),
        )
    )
    suppliers = result.scalars().all()

    for supplier in suppliers:
        stored_phone = supplier.contacts.get("phone", "")
        if _normalize_phone(stored_phone) == phone:
            return FindByPhoneResponse(
                found=True,
                entity_id=supplier.id,
                entity_type="supplier",
                name=supplier.name,
                status=supplier.status,
            )

    return FindByPhoneResponse(found=False)


@router.post("/link", response_model=LinkResponse, dependencies=[Depends(verify_bot_token)])
async def create_link(
    data: LinkRequest,
    db: AsyncSession = Depends(get_db),
) -> LinkResponse:
    """Create Telegram link for a user."""
    # Check if already linked
    existing = await db.execute(
        select(TelegramLink).where(TelegramLink.telegram_user_id == data.telegram_user_id)
    )
    link = existing.scalar_one_or_none()
    if link:
        raise HTTPException(status_code=409, detail="Telegram user already linked")

    # Get entity name
    entity_name = None
    if data.role == "supplier":
        result = await db.execute(select(Supplier).where(Supplier.id == data.entity_id))
        supplier = result.scalar_one_or_none()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        entity_name = supplier.name

    link = TelegramLink(
        telegram_user_id=data.telegram_user_id,
        telegram_chat_id=data.telegram_chat_id,
        role=data.role,
        entity_id=data.entity_id,
        username=data.username,
        first_name=data.first_name,
    )
    db.add(link)
    await db.flush()

    logger.info(
        "telegram_linked",
        telegram_user_id=data.telegram_user_id,
        role=data.role,
        entity_id=str(data.entity_id),
    )

    return LinkResponse(
        id=link.id,
        telegram_user_id=link.telegram_user_id,
        role=link.role,
        entity_id=link.entity_id,
        entity_name=entity_name,
    )


@router.get("/link/{telegram_user_id}", response_model=LinkResponse | None, dependencies=[Depends(verify_bot_token)])
async def get_link(
    telegram_user_id: int,
    db: AsyncSession = Depends(get_db),
) -> LinkResponse | None:
    """Get Telegram link for a user."""
    result = await db.execute(
        select(TelegramLink).where(
            TelegramLink.telegram_user_id == telegram_user_id,
            TelegramLink.is_active.is_(True),
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Get entity name
    entity_name = None
    if link.role == "supplier":
        r = await db.execute(select(Supplier).where(Supplier.id == link.entity_id))
        supplier = r.scalar_one_or_none()
        entity_name = supplier.name if supplier else None

    return LinkResponse(
        id=link.id,
        telegram_user_id=link.telegram_user_id,
        role=link.role,
        entity_id=link.entity_id,
        entity_name=entity_name,
    )


@router.delete("/link/{telegram_user_id}", dependencies=[Depends(verify_bot_token)])
async def delete_link(
    telegram_user_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Unlink Telegram account."""
    result = await db.execute(
        select(TelegramLink).where(TelegramLink.telegram_user_id == telegram_user_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    await db.delete(link)

    logger.info("telegram_unlinked", telegram_user_id=telegram_user_id)
    return {"ok": True, "message": "Account unlinked"}


@router.post("/register-supplier", response_model=RegisterSupplierResponse, dependencies=[Depends(verify_bot_token)])
async def register_supplier(
    data: RegisterSupplierRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterSupplierResponse:
    """Register a new supplier from Telegram bot."""
    # Check duplicate name
    existing = await db.execute(
        select(Supplier).where(Supplier.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Supplier with this name already exists")

    supplier = Supplier(
        name=data.name,
        contacts={"phone": data.phone},
        status="pending",
    )
    db.add(supplier)
    await db.flush()

    logger.info(
        "supplier_registered_via_telegram",
        supplier_id=str(supplier.id),
        name=data.name,
    )

    return RegisterSupplierResponse(
        supplier_id=supplier.id,
        name=supplier.name,
        status=supplier.status,
    )


@router.post("/upload-price/{supplier_id}", response_model=UploadPriceResponse, dependencies=[Depends(verify_bot_token)])
async def upload_price(
    supplier_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> UploadPriceResponse:
    """Upload a price list file for a supplier."""
    # Verify supplier exists
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Read content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Import via existing service
    import_service = ImportService(db)
    try:
        batch = await import_service.import_file(
            supplier_id=supplier_id,
            filename=file.filename,
            content=content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("telegram_import_failed", supplier_id=str(supplier_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    # Gather stats
    items_count = (await db.execute(
        select(func.count()).select_from(SupplierItem).where(
            SupplierItem.last_import_batch_id == batch.id
        )
    )).scalar() or 0

    candidates_count = (await db.execute(
        select(func.count()).select_from(OfferCandidate).where(
            OfferCandidate.import_batch_id == batch.id
        )
    )).scalar() or 0

    from apps.api.models.imports import ParseEvent
    errors_count = (await db.execute(
        select(func.count()).select_from(ParseEvent).where(
            ParseEvent.parse_run_id.in_(
                select(ParseEvent.parse_run_id).where(
                    ParseEvent.severity == "error"
                )
            ),
        ).where(
            ParseEvent.parse_run_id.in_(
                select(func.distinct(ParseEvent.parse_run_id))
            )
        )
    )).scalar() or 0

    # Simpler error count: count parse events with severity=error for this batch
    from apps.api.models.imports import ParseRun
    error_count_result = await db.execute(
        select(func.count()).select_from(ParseEvent).join(
            ParseRun, ParseEvent.parse_run_id == ParseRun.id
        ).where(
            ParseRun.import_batch_id == batch.id,
            ParseEvent.severity == "error",
        )
    )
    errors_count = error_count_result.scalar() or 0

    # Fetch first 10 error details for user feedback
    error_details_result = await db.execute(
        select(ParseEvent.code, ParseEvent.message).join(
            ParseRun, ParseEvent.parse_run_id == ParseRun.id
        ).where(
            ParseRun.import_batch_id == batch.id,
            ParseEvent.severity == "error",
        ).limit(10)
    )
    error_details = [
        ParseErrorDetail(code=row.code, message=row.message)
        for row in error_details_result.all()
    ]

    # Calculate type/variety detection percentages
    type_detected = 0
    variety_detected = 0
    if items_count > 0:
        type_result = await db.execute(
            select(func.count()).select_from(SupplierItem).where(
                SupplierItem.last_import_batch_id == batch.id,
                SupplierItem.attributes["flower_type"].astext != "",
                SupplierItem.attributes["flower_type"].isnot(None),
            )
        )
        type_detected = int((type_result.scalar() or 0) / items_count * 100)

        variety_result = await db.execute(
            select(func.count()).select_from(SupplierItem).where(
                SupplierItem.last_import_batch_id == batch.id,
                SupplierItem.attributes["variety"].astext != "",
                SupplierItem.attributes["variety"].isnot(None),
            )
        )
        variety_detected = int((variety_result.scalar() or 0) / items_count * 100)

    from apps.api.models.imports import RawRow
    raw_count = (await db.execute(
        select(func.count()).select_from(RawRow).where(
            RawRow.import_batch_id == batch.id
        )
    )).scalar() or 0

    logger.info(
        "telegram_price_uploaded",
        supplier_id=str(supplier_id),
        batch_id=str(batch.id),
        items=items_count,
    )

    return UploadPriceResponse(
        batch_id=batch.id,
        status=batch.status,
        filename=batch.source_filename,
        raw_rows_count=raw_count,
        supplier_items_count=items_count,
        offer_candidates_count=candidates_count,
        parse_errors_count=errors_count,
        parse_errors=error_details,
        type_detected_pct=type_detected,
        variety_detected_pct=variety_detected,
    )


@router.get("/last-import/{supplier_id}", response_model=LastImportResponse, dependencies=[Depends(verify_bot_token)])
async def get_last_import(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> LastImportResponse:
    """Get the last import batch for a supplier."""
    result = await db.execute(
        select(ImportBatch)
        .where(ImportBatch.supplier_id == supplier_id)
        .order_by(ImportBatch.created_at.desc())
        .limit(1)
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="No imports found")

    # Count items
    from apps.api.models.imports import RawRow
    raw_count = (await db.execute(
        select(func.count()).select_from(RawRow).where(RawRow.import_batch_id == batch.id)
    )).scalar() or 0

    items_count = (await db.execute(
        select(func.count()).select_from(SupplierItem).where(
            SupplierItem.last_import_batch_id == batch.id
        )
    )).scalar() or 0

    candidates_count = (await db.execute(
        select(func.count()).select_from(OfferCandidate).where(
            OfferCandidate.import_batch_id == batch.id
        )
    )).scalar() or 0

    return LastImportResponse(
        batch_id=batch.id,
        filename=batch.source_filename,
        status=batch.status,
        imported_at=batch.created_at,
        raw_rows_count=raw_count,
        supplier_items_count=items_count,
        offer_candidates_count=candidates_count,
    )


def _normalize_phone(phone: str) -> str:
    """Normalize phone number for comparison (keep only digits)."""
    digits = "".join(c for c in phone if c.isdigit())
    # Handle Russian +7/8 prefix
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return digits
    return digits
