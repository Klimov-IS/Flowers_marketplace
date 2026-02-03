"""Unit tests for order validation logic."""
import pytest
from decimal import Decimal
from uuid import uuid4

from apps.api.services.order_service import OrderService


@pytest.mark.asyncio
class TestOrderValidation:
    """Test order creation validation rules."""

    async def test_order_requires_active_buyer(self, db_session, sample_supplier, sample_city):
        """Test that order creation fails for inactive buyer."""
        from apps.api.models import Buyer

        # Create blocked buyer
        buyer = Buyer(
            name="Blocked Buyer",
            phone="+79001112233",
            city_id=sample_city.id,
            status="blocked",
        )
        db_session.add(buyer)
        await db_session.commit()

        order_service = OrderService(db_session)

        with pytest.raises(ValueError, match="Buyer is not active"):
            await order_service.create_order(
                buyer_id=buyer.id,
                items=[{"offer_id": uuid4(), "quantity": 10}],
            )

    async def test_order_requires_existing_buyer(self, db_session):
        """Test that order creation fails for non-existent buyer."""
        order_service = OrderService(db_session)
        fake_buyer_id = uuid4()

        with pytest.raises(ValueError, match="Buyer not found"):
            await order_service.create_order(
                buyer_id=fake_buyer_id,
                items=[{"offer_id": uuid4(), "quantity": 10}],
            )

    async def test_order_requires_at_least_one_item(
        self, db_session, sample_buyer
    ):
        """Test that order creation fails with empty items list."""
        order_service = OrderService(db_session)

        with pytest.raises(ValueError, match="at least one item"):
            await order_service.create_order(
                buyer_id=sample_buyer.id,
                items=[],
            )

    async def test_order_requires_positive_quantity(
        self, db_session, sample_buyer, sample_offer
    ):
        """Test that order creation fails with zero or negative quantity."""
        order_service = OrderService(db_session)

        # Zero quantity
        with pytest.raises(ValueError, match="Quantity must be positive"):
            await order_service.create_order(
                buyer_id=sample_buyer.id,
                items=[{"offer_id": sample_offer.id, "quantity": 0}],
            )

        # Negative quantity
        with pytest.raises(ValueError, match="Quantity must be positive"):
            await order_service.create_order(
                buyer_id=sample_buyer.id,
                items=[{"offer_id": sample_offer.id, "quantity": -5}],
            )

    async def test_order_requires_active_offers(
        self, db_session, sample_buyer, sample_offer
    ):
        """Test that order creation fails with inactive offers."""
        # Deactivate offer
        sample_offer.is_active = False
        await db_session.commit()

        order_service = OrderService(db_session)

        with pytest.raises(ValueError, match="Offers not active"):
            await order_service.create_order(
                buyer_id=sample_buyer.id,
                items=[{"offer_id": sample_offer.id, "quantity": 10}],
            )

    async def test_order_requires_existing_offers(
        self, db_session, sample_buyer
    ):
        """Test that order creation fails with non-existent offers."""
        order_service = OrderService(db_session)
        fake_offer_id = uuid4()

        with pytest.raises(ValueError, match="Offers not found"):
            await order_service.create_order(
                buyer_id=sample_buyer.id,
                items=[{"offer_id": fake_offer_id, "quantity": 10}],
            )

    async def test_order_requires_single_supplier(
        self,
        db_session,
        sample_buyer,
        sample_supplier,
        sample_city,
        sample_normalized_sku,
    ):
        """Test that order creation fails with offers from multiple suppliers (MVP constraint)."""
        from apps.api.models import Supplier, Offer

        # Create second supplier
        supplier2 = Supplier(
            name="Supplier 2",
            city_id=sample_city.id,
            status="active",
        )
        db_session.add(supplier2)
        await db_session.commit()

        # Create offer from second supplier
        offer2 = Offer(
            supplier_id=supplier2.id,
            normalized_sku_id=sample_normalized_sku.id,
            price_type="fixed",
            price_min=Decimal("50.00"),
            currency="RUB",
            unit="stem",
            is_active=True,
        )
        db_session.add(offer2)
        await db_session.commit()

        # Get offer from first supplier
        from sqlalchemy import select
        from apps.api.models import Offer as OfferModel

        result = await db_session.execute(
            select(OfferModel).where(OfferModel.supplier_id == sample_supplier.id).limit(1)
        )
        offer1 = result.scalar_one()

        order_service = OrderService(db_session)

        with pytest.raises(ValueError, match="same supplier"):
            await order_service.create_order(
                buyer_id=sample_buyer.id,
                items=[
                    {"offer_id": offer1.id, "quantity": 10},
                    {"offer_id": offer2.id, "quantity": 5},
                ],
            )

    async def test_order_confirm_requires_pending_status(
        self, db_session, sample_order
    ):
        """Test that order confirmation fails if not in pending status."""
        # Confirm order first time
        sample_order.status = "confirmed"
        await db_session.commit()

        order_service = OrderService(db_session)

        # Try to confirm again
        with pytest.raises(ValueError, match="cannot be confirmed"):
            await order_service.confirm_order(
                order_id=sample_order.id,
                supplier_id=sample_order.supplier_id,
            )

    async def test_order_confirm_requires_correct_supplier(
        self, db_session, sample_order, sample_city
    ):
        """Test that order confirmation fails if wrong supplier."""
        from apps.api.models import Supplier

        # Create different supplier
        other_supplier = Supplier(
            name="Other Supplier",
            city_id=sample_city.id,
            status="active",
        )
        db_session.add(other_supplier)
        await db_session.commit()

        order_service = OrderService(db_session)

        with pytest.raises(ValueError, match="does not belong to supplier"):
            await order_service.confirm_order(
                order_id=sample_order.id,
                supplier_id=other_supplier.id,
            )

    async def test_order_reject_requires_pending_status(
        self, db_session, sample_order
    ):
        """Test that order rejection fails if not in pending status."""
        # Reject order first time
        sample_order.status = "rejected"
        await db_session.commit()

        order_service = OrderService(db_session)

        # Try to reject again
        with pytest.raises(ValueError, match="cannot be rejected"):
            await order_service.reject_order(
                order_id=sample_order.id,
                supplier_id=sample_order.supplier_id,
                reason="Test reason",
            )

    async def test_order_calculation_uses_price_snapshot(
        self, db_session, sample_buyer, sample_offer
    ):
        """Test that order total is calculated correctly using offer price at order time."""
        order_service = OrderService(db_session)

        # Create order
        order = await order_service.create_order(
            buyer_id=sample_buyer.id,
            items=[
                {"offer_id": sample_offer.id, "quantity": 10},
            ],
        )

        # Check total calculation
        expected_total = sample_offer.price_min * 10
        assert order.total_amount == expected_total

        # Verify order item has price snapshot
        assert len(order.items) == 1
        assert order.items[0].unit_price == sample_offer.price_min
        assert order.items[0].total_price == expected_total

    async def test_order_calculation_with_range_price(
        self, db_session, sample_buyer, sample_supplier, sample_normalized_sku
    ):
        """Test that order calculation uses average price for range-type offers."""
        from apps.api.models import Offer

        # Create range-price offer
        offer = Offer(
            supplier_id=sample_supplier.id,
            normalized_sku_id=sample_normalized_sku.id,
            price_type="range",
            price_min=Decimal("40.00"),
            price_max=Decimal("60.00"),
            currency="RUB",
            unit="stem",
            is_active=True,
        )
        db_session.add(offer)
        await db_session.commit()

        order_service = OrderService(db_session)

        order = await order_service.create_order(
            buyer_id=sample_buyer.id,
            items=[{"offer_id": offer.id, "quantity": 10}],
        )

        # Check uses average price
        expected_unit_price = (Decimal("40.00") + Decimal("60.00")) / 2  # 50.00
        expected_total = expected_unit_price * 10

        assert order.items[0].unit_price == expected_unit_price
        assert order.total_amount == expected_total
