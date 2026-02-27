"""Order service - handle order creation and validation."""
import structlog
import sqlalchemy
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from uuid import UUID

from sqlalchemy import select, func, case, cast, Integer, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models import (
    Buyer,
    City,
    Offer,
    Order,
    OrderItem,
    Supplier,
)

logger = structlog.get_logger()


class OrderService:
    """Service for order creation and management."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def create_order(
        self,
        buyer_id: UUID,
        items: List[Dict],
        delivery_address: str | None = None,
        delivery_date: str | None = None,
        notes: str | None = None,
    ) -> Order:
        """
        Create order from buyer.

        Validation:
        1. Buyer exists and is active
        2. All offers exist and are active
        3. All offers from same supplier (MVP constraint)
        4. Items have positive quantity

        Args:
            buyer_id: Buyer UUID
            items: List of dicts with:
                - offer_id: UUID
                - quantity: int (positive)
            delivery_address: Optional delivery address
            delivery_date: Optional delivery date
            notes: Optional notes

        Returns:
            Created Order instance (with items relationship loaded)

        Raises:
            ValueError: If validation fails
        """
        log = logger.bind(buyer_id=str(buyer_id))
        log.info("order.create.start", items_count=len(items))

        # Step 1: Validate buyer
        result = await self.db.execute(
            select(Buyer).where(Buyer.id == buyer_id)
        )
        buyer = result.scalar_one_or_none()

        if not buyer:
            log.warning("order.buyer_not_found")
            raise ValueError(f"Buyer not found: {buyer_id}")

        if buyer.status != "active":
            log.warning("order.buyer_not_active", status=buyer.status)
            raise ValueError(f"Buyer is not active: {buyer.status}")

        log.debug("order.buyer_validated", buyer_name=buyer.name)

        # Step 2: Validate items non-empty
        if not items:
            log.warning("order.items_empty")
            raise ValueError("Order must have at least one item")

        # Extract offer_ids
        offer_ids = [item["offer_id"] for item in items]

        # Step 3: Fetch offers
        result = await self.db.execute(
            select(Offer).where(Offer.id.in_(offer_ids))
        )
        offers = result.scalars().all()

        if len(offers) != len(offer_ids):
            found_ids = {o.id for o in offers}
            missing = set(offer_ids) - found_ids
            log.warning("order.offers_not_found", missing=str(missing))
            raise ValueError(f"Offers not found: {missing}")

        # Validate all offers active
        inactive = [o.id for o in offers if not o.is_active]
        if inactive:
            log.warning("order.offers_not_active", inactive=str(inactive))
            raise ValueError(f"Offers not active: {inactive}")

        log.debug("order.offers_validated", count=len(offers))

        # Step 4: Validate single supplier (MVP constraint)
        supplier_ids = {o.supplier_id for o in offers}
        if len(supplier_ids) != 1:
            log.warning("order.multiple_suppliers", suppliers=str(supplier_ids))
            raise ValueError(
                f"All items must be from the same supplier (MVP constraint). Found: {len(supplier_ids)} suppliers"
            )

        supplier_id = supplier_ids.pop()
        log = log.bind(supplier_id=str(supplier_id))
        log.debug("order.supplier_validated")

        # Validate supplier exists and active
        result = await self.db.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        supplier = result.scalar_one_or_none()

        if not supplier:
            log.warning("order.supplier_not_found")
            raise ValueError(f"Supplier not found: {supplier_id}")

        if supplier.status != "active":
            log.warning("order.supplier_not_active", status=supplier.status)
            raise ValueError(f"Supplier is not active: {supplier.status}")

        # Build offer lookup
        offer_map = {o.id: o for o in offers}

        # Step 5: Validate item quantities and calculate total
        total_amount = Decimal("0")
        order_items_data = []

        for item in items:
            offer_id = item["offer_id"]
            quantity = item["quantity"]

            if quantity <= 0:
                log.warning("order.invalid_quantity", offer_id=str(offer_id), quantity=quantity)
                raise ValueError(f"Quantity must be positive for offer {offer_id}: {quantity}")

            offer = offer_map[offer_id]

            # Use price_min for MVP (or average if range)
            if offer.price_type == "range" and offer.price_max:
                unit_price = (offer.price_min + offer.price_max) / 2
            else:
                unit_price = offer.price_min

            total_price = unit_price * quantity
            total_amount += total_price

            order_items_data.append({
                "offer_id": offer_id,
                "offer": offer,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
            })

        log.debug("order.total_calculated", total_amount=str(total_amount))

        # Step 6: Create order
        order = Order(
            buyer_id=buyer_id,
            supplier_id=supplier_id,
            status="pending",
            total_amount=total_amount,
            currency=offers[0].currency,  # All from same supplier, use first
            delivery_address=delivery_address,
            delivery_date=delivery_date,
            notes=notes,
        )
        self.db.add(order)
        await self.db.flush()  # Get order.id

        log = log.bind(order_id=str(order.id))
        log.info("order.created", status="pending")

        # Step 7: Create order items
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                offer_id=item_data["offer_id"],
                normalized_sku_id=item_data["offer"].normalized_sku_id,
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                total_price=item_data["total_price"],
                notes=item.get("notes"),
            )
            self.db.add(order_item)

        await self.db.flush()
        log.info("order.items_created", count=len(order_items_data))

        # Refresh to load relationships
        await self.db.refresh(order, ["items", "buyer", "supplier"])

        log.info("order.create.complete")
        return order

    async def confirm_order(
        self,
        order_id: UUID,
        supplier_id: UUID,
    ) -> Order:
        """
        Confirm order (supplier action).

        Validation:
        1. Order exists and belongs to supplier
        2. Order status is 'pending'

        Args:
            order_id: Order UUID
            supplier_id: Supplier UUID (for authorization check)

        Returns:
            Updated Order instance

        Raises:
            ValueError: If validation fails
        """
        log = logger.bind(order_id=str(order_id), supplier_id=str(supplier_id))
        log.info("order.confirm.start")

        # Fetch order
        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            log.warning("order.not_found")
            raise ValueError(f"Order not found: {order_id}")

        # Check belongs to supplier
        if order.supplier_id != supplier_id:
            log.warning("order.wrong_supplier", actual=str(order.supplier_id))
            raise ValueError(f"Order does not belong to supplier {supplier_id}")

        # Check status
        if order.status != "pending":
            log.warning("order.not_pending", status=order.status)
            raise ValueError(f"Order cannot be confirmed, current status: {order.status}")

        # Update status
        order.status = "confirmed"
        order.confirmed_at = datetime.utcnow()

        await self.db.flush()
        log.info("order.confirm.complete", confirmed_at=order.confirmed_at)

        return order

    async def reject_order(
        self,
        order_id: UUID,
        supplier_id: UUID,
        reason: str,
    ) -> Order:
        """
        Reject order (supplier action).

        Validation:
        1. Order exists and belongs to supplier
        2. Order status is 'pending'

        Args:
            order_id: Order UUID
            supplier_id: Supplier UUID (for authorization check)
            reason: Rejection reason text

        Returns:
            Updated Order instance

        Raises:
            ValueError: If validation fails
        """
        log = logger.bind(order_id=str(order_id), supplier_id=str(supplier_id))
        log.info("order.reject.start")

        # Fetch order
        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            log.warning("order.not_found")
            raise ValueError(f"Order not found: {order_id}")

        # Check belongs to supplier
        if order.supplier_id != supplier_id:
            log.warning("order.wrong_supplier", actual=str(order.supplier_id))
            raise ValueError(f"Order does not belong to supplier {supplier_id}")

        # Check status
        if order.status != "pending":
            log.warning("order.not_pending", status=order.status)
            raise ValueError(f"Order cannot be rejected, current status: {order.status}")

        # Update status
        order.status = "rejected"
        order.rejected_at = datetime.utcnow()
        order.rejection_reason = reason

        await self.db.flush()
        log.info("order.reject.complete", rejected_at=order.rejected_at, reason=reason)

        return order

    async def assemble_order(
        self,
        order_id: UUID,
        supplier_id: UUID,
    ) -> Order:
        """
        Mark order as assembled/picked (supplier action).

        Validation:
        1. Order exists and belongs to supplier
        2. Order status is 'confirmed'
        """
        log = logger.bind(order_id=str(order_id), supplier_id=str(supplier_id))
        log.info("order.assemble.start")

        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            log.warning("order.not_found")
            raise ValueError(f"Order not found: {order_id}")

        if order.supplier_id != supplier_id:
            log.warning("order.wrong_supplier", actual=str(order.supplier_id))
            raise ValueError(f"Order does not belong to supplier {supplier_id}")

        if order.status != "confirmed":
            log.warning("order.not_confirmed", status=order.status)
            raise ValueError(f"Order cannot be assembled, current status: {order.status}")

        order.status = "assembled"
        order.assembled_at = datetime.utcnow()

        await self.db.flush()
        log.info("order.assemble.complete", assembled_at=order.assembled_at)

        return order

    async def get_order_metrics(self, supplier_id: UUID | None = None) -> Dict:
        """
        Get order statistics.

        Args:
            supplier_id: Optional supplier filter

        Returns:
            Dict with order counts by status and revenue totals.
        """
        log = logger.bind(supplier_id=str(supplier_id) if supplier_id else "all")
        log.info("order.metrics.start")

        # Build base query
        # Use literal_column for ENUM comparison in PostgreSQL
        query = select(
            func.count(Order.id).label("total"),
            func.sum(
                cast(Order.status == literal_column("'pending'"), Integer)
            ).label("pending"),
            func.sum(
                cast(Order.status == literal_column("'confirmed'"), Integer)
            ).label("confirmed"),
            func.sum(
                cast(Order.status == literal_column("'assembled'"), Integer)
            ).label("assembled"),
            func.sum(
                cast(Order.status == literal_column("'rejected'"), Integer)
            ).label("rejected"),
            func.sum(
                cast(Order.status == literal_column("'cancelled'"), Integer)
            ).label("cancelled"),
            func.sum(
                case(
                    (Order.status.in_(["confirmed", "assembled"]), Order.total_amount),
                    else_=0
                )
            ).label("revenue"),
        )

        if supplier_id:
            query = query.where(Order.supplier_id == supplier_id)

        result = await self.db.execute(query)
        row = result.one()

        metrics = {
            "total_orders": row.total or 0,
            "pending": row.pending or 0,
            "confirmed": row.confirmed or 0,
            "assembled": row.assembled or 0,
            "rejected": row.rejected or 0,
            "cancelled": row.cancelled or 0,
            "total_revenue": row.revenue or Decimal("0"),
        }

        log.info("order.metrics.complete", metrics=metrics)
        return metrics
