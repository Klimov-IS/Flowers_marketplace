"""Dictionary service for managing normalization dictionaries."""
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.data.dictionary_seed import DICTIONARY_SEED
from apps.api.logging_config import get_logger
from apps.api.models import DictionaryEntry

logger = get_logger(__name__)


class DictionaryService:
    """Service for dictionary management."""

    def __init__(self, db: AsyncSession):
        """Initialize dictionary service."""
        self.db = db

    async def bootstrap(self) -> Dict[str, int]:
        """
        Bootstrap dictionary with seed data (idempotent).

        Uses INSERT ... ON CONFLICT DO UPDATE to ensure idempotency.

        Returns:
            Dict with counts: inserted, updated, total
        """
        logger.info("dictionary_bootstrap_started")

        inserted_count = 0
        updated_count = 0

        for entry_data in DICTIONARY_SEED:
            # Use INSERT ... ON CONFLICT DO UPDATE for idempotency
            stmt = insert(DictionaryEntry).values(
                dict_type=entry_data["dict_type"],
                key=entry_data["key"],
                value=entry_data["value"],
                synonyms=entry_data["synonyms"],
                rules=entry_data["rules"],
                status=entry_data["status"],
            )

            # On conflict (dict_type, key), update the values
            stmt = stmt.on_conflict_do_update(
                constraint="uq_dictionary_entries_type_key",
                set_={
                    "value": stmt.excluded.value,
                    "synonyms": stmt.excluded.synonyms,
                    "rules": stmt.excluded.rules,
                    "status": stmt.excluded.status,
                    "updated_at": "now()",
                },
            )

            result = await self.db.execute(stmt)

            # PostgreSQL doesn't easily tell us if it was insert vs update
            # For now we'll count all as inserts/updates
            # A more precise implementation would check xmax
            inserted_count += 1

        await self.db.commit()

        total = len(DICTIONARY_SEED)
        logger.info(
            "dictionary_bootstrap_completed",
            total=total,
            inserted=inserted_count,
        )

        return {
            "total": total,
            "inserted": inserted_count,
            "updated": 0,  # We can't easily distinguish in this approach
        }

    async def list_entries(
        self,
        dict_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[DictionaryEntry]:
        """
        List dictionary entries with optional filters.

        Args:
            dict_type: Filter by dictionary type
            status: Filter by status

        Returns:
            List of dictionary entries
        """
        query = select(DictionaryEntry)

        if dict_type:
            query = query.where(DictionaryEntry.dict_type == dict_type)

        if status:
            query = query.where(DictionaryEntry.status == status)

        query = query.order_by(DictionaryEntry.dict_type, DictionaryEntry.key)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_entry(
        self,
        dict_type: str,
        key: str,
        value: str,
        synonyms: Optional[List[str]] = None,
        rules: Optional[Dict] = None,
        status: str = "active",
    ) -> DictionaryEntry:
        """
        Create a new dictionary entry.

        Args:
            dict_type: Dictionary type
            key: Entry key
            value: Entry value
            synonyms: List of synonyms
            rules: Rules JSON
            status: Entry status

        Returns:
            Created dictionary entry

        Raises:
            ValueError: If entry with same dict_type+key already exists
        """
        # Check if exists
        result = await self.db.execute(
            select(DictionaryEntry).where(
                DictionaryEntry.dict_type == dict_type,
                DictionaryEntry.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise ValueError(f"Dictionary entry {dict_type}/{key} already exists")

        entry = DictionaryEntry(
            dict_type=dict_type,
            key=key,
            value=value,
            synonyms=synonyms or [],
            rules=rules or {},
            status=status,
        )

        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        logger.info(
            "dictionary_entry_created",
            entry_id=str(entry.id),
            dict_type=dict_type,
            key=key,
        )

        return entry

    async def update_entry(
        self,
        entry_id: UUID,
        key: Optional[str] = None,
        value: Optional[str] = None,
        synonyms: Optional[List[str]] = None,
        rules: Optional[Dict] = None,
        status: Optional[str] = None,
    ) -> DictionaryEntry:
        """
        Update an existing dictionary entry.

        Args:
            entry_id: Entry UUID
            key: New key (optional)
            value: New value (optional)
            synonyms: New synonyms (optional)
            rules: New rules (optional)
            status: New status (optional)

        Returns:
            Updated dictionary entry

        Raises:
            ValueError: If entry not found
        """
        result = await self.db.execute(
            select(DictionaryEntry).where(DictionaryEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            raise ValueError(f"Dictionary entry {entry_id} not found")

        if key is not None:
            entry.key = key
        if value is not None:
            entry.value = value
        if synonyms is not None:
            entry.synonyms = synonyms
        if rules is not None:
            entry.rules = rules
        if status is not None:
            entry.status = status

        await self.db.commit()
        await self.db.refresh(entry)

        logger.info(
            "dictionary_entry_updated",
            entry_id=str(entry.id),
            dict_type=entry.dict_type,
            key=entry.key,
        )

        return entry

    async def get_by_type(self, dict_type: str) -> List[DictionaryEntry]:
        """
        Get all active entries for a dictionary type.

        Args:
            dict_type: Dictionary type

        Returns:
            List of dictionary entries
        """
        result = await self.db.execute(
            select(DictionaryEntry).where(
                DictionaryEntry.dict_type == dict_type,
                DictionaryEntry.status == "active",
            )
        )
        return list(result.scalars().all())
