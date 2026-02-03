"""Integration tests for order flow end-to-end."""
import pytest
from decimal import Decimal
from httpx import AsyncClient


@pytest.mark.asyncio
class TestOrderFlow:
    """Test complete order workflow via API endpoints."""

    async def test_create_buyer_via_api(self, client: AsyncClient, sample_city):
        """Test POST /admin/buyers - create new buyer."""
        response = await client.post(
            "/admin/buyers",
            json={
                "name": "Test Flower Shop",
                "phone": "+79001234567",
                "email": "shop@example.com",
                "address": "123 Main St",
                "city_id": str(sample_city.id),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Flower Shop"
        assert data["phone"] == "+79001234567"
        assert data["status"] == "active"
        assert "id" in data

    async def test_list_buyers_via_api(self, client: AsyncClient, sample_buyer):
        """Test GET /admin/buyers - list buyers."""
        response = await client.get("/admin/buyers")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Find our buyer
        buyer_found = any(b["id"] == str(sample_buyer.id) for b in data)
        assert buyer_found

    async def test_get_buyer_by_id(self, client: AsyncClient, sample_buyer):
        """Test GET /admin/buyers/{buyer_id} - get buyer details."""
        response = await client.get(f"/admin/buyers/{sample_buyer.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_buyer.id)
        assert data["name"] == sample_buyer.name
        assert data["phone"] == sample_buyer.phone

    async def test_create_order_via_api(
        self, client: AsyncClient, sample_buyer, sample_offer
    ):
        """Test POST /orders - create order."""
        response = await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [
                    {"offer_id": str(sample_offer.id), "quantity": 15}
                ],
                "delivery_address": "456 Oak Street",
                "notes": "Please deliver in the morning",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify order structure
        assert data["buyer_id"] == str(sample_buyer.id)
        assert data["supplier_id"] == str(sample_offer.supplier_id)
        assert data["status"] == "pending"
        assert Decimal(data["total_amount"]) == sample_offer.price_min * 15
        assert data["currency"] == sample_offer.currency
        assert data["delivery_address"] == "456 Oak Street"
        assert data["notes"] == "Please deliver in the morning"

        # Verify items
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["offer_id"] == str(sample_offer.id)
        assert item["quantity"] == 15
        assert Decimal(item["unit_price"]) == sample_offer.price_min
        assert Decimal(item["total_price"]) == sample_offer.price_min * 15

        # Verify relationships loaded
        assert "buyer" in data
        assert data["buyer"]["name"] == sample_buyer.name
        assert "supplier" in data

    async def test_list_orders_for_buyer(
        self, client: AsyncClient, sample_buyer, sample_offer
    ):
        """Test GET /orders?buyer_id={id} - list buyer's orders."""
        # Create order first
        create_response = await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [{"offer_id": str(sample_offer.id), "quantity": 10}],
            },
        )
        assert create_response.status_code == 201
        order_id = create_response.json()["id"]

        # List orders
        response = await client.get(f"/orders?buyer_id={sample_buyer.id}")

        assert response.status_code == 200
        data = response.json()

        assert "orders" in data
        assert "total" in data
        assert data["total"] >= 1

        # Find our order
        order_found = any(o["id"] == order_id for o in data["orders"])
        assert order_found

    async def test_get_order_details(
        self, client: AsyncClient, sample_buyer, sample_offer
    ):
        """Test GET /orders/{order_id} - get order details."""
        # Create order
        create_response = await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [{"offer_id": str(sample_offer.id), "quantity": 20}],
            },
        )
        order_id = create_response.json()["id"]

        # Get details
        response = await client.get(f"/orders/{order_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order_id
        assert data["status"] == "pending"
        assert len(data["items"]) == 1

    async def test_supplier_list_orders(
        self, client: AsyncClient, sample_buyer, sample_offer, sample_supplier
    ):
        """Test GET /admin/suppliers/{supplier_id}/orders - supplier views their orders."""
        # Create order
        create_response = await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [{"offer_id": str(sample_offer.id), "quantity": 10}],
            },
        )
        assert create_response.status_code == 201

        # Supplier lists orders
        response = await client.get(f"/admin/suppliers/{sample_supplier.id}/orders")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Verify order structure
        order = data[0]
        assert "id" in order
        assert "buyer" in order
        assert order["status"] == "pending"
        assert "items_count" in order

    async def test_supplier_confirm_order(
        self, client: AsyncClient, sample_buyer, sample_offer, sample_supplier
    ):
        """Test POST /admin/suppliers/{supplier_id}/orders/confirm - supplier confirms order."""
        # Create order
        create_response = await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [{"offer_id": str(sample_offer.id), "quantity": 10}],
            },
        )
        order_id = create_response.json()["id"]

        # Supplier confirms
        response = await client.post(
            f"/admin/suppliers/{sample_supplier.id}/orders/confirm",
            json={"order_id": order_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == order_id
        assert data["status"] == "confirmed"
        assert data["confirmed_at"] is not None
        assert data["rejected_at"] is None

    async def test_supplier_reject_order(
        self, client: AsyncClient, sample_buyer, sample_offer, sample_supplier
    ):
        """Test POST /admin/suppliers/{supplier_id}/orders/reject - supplier rejects order."""
        # Create order
        create_response = await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [{"offer_id": str(sample_offer.id), "quantity": 10}],
            },
        )
        order_id = create_response.json()["id"]

        # Supplier rejects
        response = await client.post(
            f"/admin/suppliers/{sample_supplier.id}/orders/reject",
            json={
                "order_id": order_id,
                "reason": "Out of stock",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == order_id
        assert data["status"] == "rejected"
        assert data["rejected_at"] is not None
        assert data["rejection_reason"] == "Out of stock"

    async def test_supplier_order_metrics(
        self, client: AsyncClient, sample_buyer, sample_offer, sample_supplier
    ):
        """Test GET /admin/suppliers/{supplier_id}/orders/metrics - supplier views metrics."""
        # Create multiple orders
        await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [{"offer_id": str(sample_offer.id), "quantity": 10}],
            },
        )

        # Get metrics
        response = await client.get(
            f"/admin/suppliers/{sample_supplier.id}/orders/metrics"
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_orders" in data
        assert "pending" in data
        assert "confirmed" in data
        assert "rejected" in data
        assert "cancelled" in data
        assert "total_revenue" in data

        assert data["total_orders"] >= 1
        assert isinstance(data["total_revenue"], str)  # Decimal serialized as string

    async def test_admin_order_metrics(
        self, client: AsyncClient, sample_buyer, sample_offer
    ):
        """Test GET /admin/orders/metrics - admin views global metrics."""
        # Create order
        await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [{"offer_id": str(sample_offer.id), "quantity": 10}],
            },
        )

        # Get global metrics
        response = await client.get("/admin/orders/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "total_orders" in data
        assert "pending" in data
        assert "confirmed" in data
        assert "rejected" in data
        assert "total_revenue" in data

        assert data["total_orders"] >= 1

    async def test_order_status_transitions(
        self, client: AsyncClient, sample_buyer, sample_offer, sample_supplier
    ):
        """Test order status workflow: pending → confirmed."""
        # 1. Create order (pending)
        create_response = await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [{"offer_id": str(sample_offer.id), "quantity": 10}],
            },
        )
        assert create_response.status_code == 201
        order_id = create_response.json()["id"]

        # 2. Verify pending
        get_response = await client.get(f"/orders/{order_id}")
        assert get_response.json()["status"] == "pending"

        # 3. Confirm order
        confirm_response = await client.post(
            f"/admin/suppliers/{sample_supplier.id}/orders/confirm",
            json={"order_id": order_id},
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "confirmed"

        # 4. Verify confirmed
        final_response = await client.get(f"/orders/{order_id}")
        assert final_response.json()["status"] == "confirmed"

    async def test_order_validation_errors(
        self, client: AsyncClient, sample_buyer
    ):
        """Test order creation validation errors."""
        from uuid import uuid4

        # Non-existent offer
        response = await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [{"offer_id": str(uuid4()), "quantity": 10}],
            },
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

        # Non-existent buyer
        response = await client.post(
            "/orders",
            json={
                "buyer_id": str(uuid4()),
                "items": [{"offer_id": str(uuid4()), "quantity": 10}],
            },
        )
        assert response.status_code == 400

        # Empty items
        response = await client.post(
            "/orders",
            json={
                "buyer_id": str(sample_buyer.id),
                "items": [],
            },
        )
        assert response.status_code == 400
