"""Normalized SKU service."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.logging_config import get_logger
from apps.api.models import NormalizedSKU

logger = get_logger(__name__)


class SKUService:
    """Service for normalized SKU management."""

    def __init__(self, db: AsyncSession):
        """Initialize SKU service."""
        self.db = db

    async def create_sku(
        self,
        product_type: str,
        title: str,
        variety: Optional[str] = None,
        color: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> NormalizedSKU:
        """
        Create a new normalized SKU.

        Args:
            product_type: Product type (rose, carnation, etc)
            title: Human-readable title
            variety: Variety/cultivar name
            color: Color
            meta: Additional metadata

        Returns:
            Created normalized SKU
        """
        sku = NormalizedSKU(
            product_type=product_type,
            title=title,
            variety=variety,
            color=color,
            meta=meta or {},
        )

        self.db.add(sku)
        await self.db.commit()
        await self.db.refresh(sku)

        logger.info(
            "normalized_sku_created",
            sku_id=str(sku.id),
            product_type=product_type,
            title=title,
        )

        return sku

    async def list_skus(
        self,
        q: Optional[str] = None,
        product_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[NormalizedSKU]:
        """
        List normalized SKUs with optional search and filters.

        Args:
            q: Search query (matches title, variety, product_type)
            product_type: Filter by product type
            limit: Max results
            offset: Pagination offset

        Returns:
            List of normalized SKUs
        """
        query = select(NormalizedSKU)

        # Apply filters
        if product_type:
            query = query.where(NormalizedSKU.product_type == product_type)

        # Apply search
        if q:
            search_term = f"%{q.lower()}%"
            query = query.where(
                or_(
                    NormalizedSKU.title.ilike(search_term),
                    NormalizedSKU.variety.ilike(search_term),
                    NormalizedSKU.product_type.ilike(search_term),
                )
            )

        # Order and paginate
        query = query.order_by(NormalizedSKU.product_type, NormalizedSKU.title)
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_sku(self, sku_id: UUID) -> Optional[NormalizedSKU]:
        """
        Get SKU by ID.

        Args:
            sku_id: SKU UUID

        Returns:
            Normalized SKU or None
        """
        result = await self.db.execute(
            select(NormalizedSKU).where(NormalizedSKU.id == sku_id)
        )
        return result.scalar_one_or_none()

    async def find_by_product_type_and_variety(
        self,
        product_type: str,
        variety: Optional[str] = None,
    ) -> Optional[NormalizedSKU]:
        """
        Find SKU by exact product_type and variety match.

        Args:
            product_type: Product type
            variety: Variety name

        Returns:
            Normalized SKU or None
        """
        query = select(NormalizedSKU).where(
            NormalizedSKU.product_type == product_type
        )

        if variety:
            query = query.where(NormalizedSKU.variety == variety)
        else:
            query = query.where(NormalizedSKU.variety.is_(None))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
