"""Dictionary management endpoints."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.logging_config import get_logger
from apps.api.models import DictionaryEntry
from apps.api.services.dictionary_service import DictionaryService

router = APIRouter()
logger = get_logger(__name__)


# Pydantic schemas
class DictionaryEntryResponse(BaseModel):
    """Dictionary entry response schema."""

    id: UUID
    dict_type: str
    key: str
    value: str
    synonyms: List[str] | None
    rules: dict
    status: str

    class Config:
        from_attributes = True


class DictionaryEntryCreate(BaseModel):
    """Dictionary entry creation schema."""

    dict_type: str
    key: str
    value: str
    synonyms: List[str] | None = None
    rules: dict = {}
    status: str = "active"


class DictionaryEntryUpdate(BaseModel):
    """Dictionary entry update schema."""

    key: Optional[str] = None
    value: Optional[str] = None
    synonyms: Optional[List[str]] = None
    rules: Optional[dict] = None
    status: Optional[str] = None


class BootstrapResponse(BaseModel):
    """Bootstrap response schema."""

    total: int
    inserted: int
    updated: int


# Endpoints
@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap_dictionary(db: AsyncSession = Depends(get_db)) -> BootstrapResponse:
    """
    Bootstrap dictionary with seed data (idempotent).

    This endpoint can be called multiple times safely - it will
    insert new entries and update existing ones.

    Returns:
        Counts of total/inserted/updated entries
    """
    service = DictionaryService(db)
    try:
        result = await service.bootstrap()
        logger.info("dictionary_bootstrap_success", result=result)
        return BootstrapResponse(**result)
    except Exception as e:
        logger.error("dictionary_bootstrap_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Bootstrap failed: {str(e)}")


@router.get("", response_model=List[DictionaryEntryResponse])
async def list_dictionary_entries(
    dict_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[DictionaryEntry]:
    """
    List dictionary entries with optional filters.

    Args:
        dict_type: Filter by dictionary type (product_type, country, etc)
        status: Filter by status (active, deprecated)

    Returns:
        List of dictionary entries
    """
    service = DictionaryService(db)
    entries = await service.list_entries(dict_type=dict_type, status=status)
    return entries


@router.post("", response_model=DictionaryEntryResponse, status_code=201)
async def create_dictionary_entry(
    entry_data: DictionaryEntryCreate,
    db: AsyncSession = Depends(get_db),
) -> DictionaryEntry:
    """
    Create a new dictionary entry.

    Args:
        entry_data: Dictionary entry data

    Returns:
        Created dictionary entry
    """
    service = DictionaryService(db)
    try:
        entry = await service.create_entry(
            dict_type=entry_data.dict_type,
            key=entry_data.key,
            value=entry_data.value,
            synonyms=entry_data.synonyms,
            rules=entry_data.rules,
            status=entry_data.status,
        )
        return entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("dictionary_entry_create_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Creation failed: {str(e)}")


@router.patch("/{entry_id}", response_model=DictionaryEntryResponse)
async def update_dictionary_entry(
    entry_id: UUID,
    entry_data: DictionaryEntryUpdate,
    db: AsyncSession = Depends(get_db),
) -> DictionaryEntry:
    """
    Update an existing dictionary entry.

    Args:
        entry_id: Entry UUID
        entry_data: Fields to update

    Returns:
        Updated dictionary entry
    """
    service = DictionaryService(db)
    try:
        entry = await service.update_entry(
            entry_id=entry_id,
            key=entry_data.key,
            value=entry_data.value,
            synonyms=entry_data.synonyms,
            rules=entry_data.rules,
            status=entry_data.status,
        )
        return entry
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("dictionary_entry_update_failed", error=str(e), entry_id=str(entry_id))
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
