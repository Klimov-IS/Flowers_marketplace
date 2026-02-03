"""Publish endpoints (admin)."""
import structlog
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.services.publish_service import PublishService

logger = structlog.get_logger()
router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class PublishResponse(BaseModel):
    """Response from publish endpoint."""

    supplier_id: UUID
    import_batch_id: UUID
    offers_deactivated: int
    offers_created: int
    skipped_unmapped: int


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/suppliers/{supplier_id}", response_model=PublishResponse)
async def publish_supplier_offers(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PublishResponse:
    """
    Publish offers for supplier from latest import.

    Algorithm:
    1. Find latest parsed import_batch
    2. Deactivate all old offers for this supplier
    3. Create new offers for candidates with confirmed mappings
    4. Skip candidates without confirmed mappings

    Returns summary with counts.
    """
    log = logger.bind(supplier_id=str(supplier_id))
    log.info("publish.endpoint.start")

    try:
        publish_service = PublishService(db)
        summary = await publish_service.publish_supplier_offers(supplier_id)
        await db.commit()

        log.info("publish.endpoint.success", summary=summary)
        return PublishResponse(
            supplier_id=supplier_id,
            **summary,
        )

    except ValueError as e:
        await db.rollback()
        log.warning("publish.endpoint.validation_error", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        await db.rollback()
        log.error("publish.endpoint.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Publish failed: {str(e)}")
