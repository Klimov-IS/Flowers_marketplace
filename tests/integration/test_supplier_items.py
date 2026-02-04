"""Integration test for supplier items endpoint (Seller Cabinet API)."""
from decimal import Decimal

import pytest
from sqlalchemy import select

from apps.api.models import ImportBatch, Supplier
from apps.api.models.items import OfferCandidate, SupplierItem


@pytest.mark.asyncio
class TestSupplierItemsEndpoint:
    """Integration tests for GET /admin/suppliers/{id}/items endpoint."""

    @pytest.fixture
    async def supplier(self, db_session):
        """Create test supplier."""
        supplier = Supplier(
            name="Test Flower Supplier",
            status="active",
            contacts={},
        )
        db_session.add(supplier)
        await db_session.commit()
        await db_session.refresh(supplier)
        return supplier

    @pytest.fixture
    async def import_batch(self, db_session, supplier):
        """Create test import batch."""
        batch = ImportBatch(
            supplier_id=supplier.id,
            source_type="csv",
            source_filename="test_price.csv",
            status="parsed",
        )
        db_session.add(batch)
        await db_session.commit()
        await db_session.refresh(batch)
        return batch

    @pytest.fixture
    async def supplier_items_with_variants(self, db_session, supplier, import_batch):
        """Create test supplier items with offer candidates."""
        # Item 1: Rose with multiple variants
        item1 = SupplierItem(
            supplier_id=supplier.id,
            stable_key="rose_avalanche_ec",
            raw_name="Роза Аваланш",
            name_norm="роза аваланш",
            attributes={
                "origin_country": "EC",
                "colors": ["белый"],
            },
            status="active",
            last_import_batch_id=import_batch.id,
        )
        db_session.add(item1)
        await db_session.flush()

        # Variants for item1
        variants1 = [
            OfferCandidate(
                supplier_item_id=item1.id,
                import_batch_id=import_batch.id,
                length_cm=40,
                pack_type="bak",
                pack_qty=25,
                price_type="fixed",
                price_min=Decimal("62.00"),
                stock_qty=50,
                validation="ok",
            ),
            OfferCandidate(
                supplier_item_id=item1.id,
                import_batch_id=import_batch.id,
                length_cm=40,
                pack_type="pack",
                pack_qty=10,
                price_type="fixed",
                price_min=Decimal("67.00"),
                stock_qty=80,
                validation="ok",
            ),
            OfferCandidate(
                supplier_item_id=item1.id,
                import_batch_id=import_batch.id,
                length_cm=60,
                pack_type="bak",
                pack_qty=25,
                price_type="fixed",
                price_min=Decimal("95.00"),
                stock_qty=30,
                validation="ok",
            ),
        ]
        for v in variants1:
            db_session.add(v)

        # Item 2: Carnation with colors
        item2 = SupplierItem(
            supplier_id=supplier.id,
            stable_key="carnation_mix_nl",
            raw_name="Гвоздика Микс",
            name_norm="гвоздика микс",
            attributes={
                "origin_country": "NL",
                "colors": ["красный", "розовый", "белый"],
            },
            status="active",
            last_import_batch_id=import_batch.id,
        )
        db_session.add(item2)
        await db_session.flush()

        # Single variant for item2
        variant2 = OfferCandidate(
            supplier_item_id=item2.id,
            import_batch_id=import_batch.id,
            length_cm=70,
            pack_type="pack",
            pack_qty=20,
            price_type="fixed",
            price_min=Decimal("45.00"),
            stock_qty=100,
            validation="ok",
        )
        db_session.add(variant2)

        await db_session.commit()
        await db_session.refresh(item1)
        await db_session.refresh(item2)

        return [item1, item2]

    async def test_get_supplier_items_basic(self, client, supplier, supplier_items_with_variants):
        """Test basic retrieval of supplier items."""
        response = await client.get(f"/admin/suppliers/{supplier.id}/items")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

        assert data["total"] == 2
        assert data["page"] == 1
        assert data["per_page"] == 50
        assert len(data["items"]) == 2

    async def test_get_supplier_items_with_aggregation(self, client, supplier, supplier_items_with_variants):
        """Test that items have correctly aggregated variant data."""
        response = await client.get(f"/admin/suppliers/{supplier.id}/items")
        data = response.json()

        # Find Rose item
        rose_item = next((i for i in data["items"] if "Аваланш" in i["raw_name"]), None)
        assert rose_item is not None

        # Check aggregation
        assert rose_item["origin_country"] == "EC"
        assert rose_item["colors"] == ["белый"]
        assert rose_item["length_min"] == 40
        assert rose_item["length_max"] == 60
        assert float(rose_item["price_min"]) == 62.00
        assert float(rose_item["price_max"]) == 95.00
        assert rose_item["stock_total"] == 160  # 50 + 80 + 30
        assert rose_item["variants_count"] == 3
        assert len(rose_item["variants"]) == 3

    async def test_get_supplier_items_with_search(self, client, supplier, supplier_items_with_variants):
        """Test search functionality."""
        # Search for Rose
        response = await client.get(f"/admin/suppliers/{supplier.id}/items?q=роза")
        data = response.json()

        assert data["total"] == 1
        assert "Аваланш" in data["items"][0]["raw_name"]

        # Search for Carnation
        response = await client.get(f"/admin/suppliers/{supplier.id}/items?q=гвоздика")
        data = response.json()

        assert data["total"] == 1
        assert "Гвоздика" in data["items"][0]["raw_name"]

        # Search with no results
        response = await client.get(f"/admin/suppliers/{supplier.id}/items?q=тюльпан")
        data = response.json()

        assert data["total"] == 0
        assert len(data["items"]) == 0

    async def test_get_supplier_items_pagination(self, client, supplier, supplier_items_with_variants):
        """Test pagination."""
        # First page with 1 item
        response = await client.get(f"/admin/suppliers/{supplier.id}/items?page=1&per_page=1")
        data = response.json()

        assert data["total"] == 2
        assert data["page"] == 1
        assert data["per_page"] == 1
        assert len(data["items"]) == 1

        # Second page
        response = await client.get(f"/admin/suppliers/{supplier.id}/items?page=2&per_page=1")
        data = response.json()

        assert data["total"] == 2
        assert data["page"] == 2
        assert len(data["items"]) == 1

    async def test_get_supplier_items_not_found(self, client):
        """Test 404 for non-existent supplier."""
        from uuid import uuid4

        response = await client.get(f"/admin/suppliers/{uuid4()}/items")
        assert response.status_code == 404

    async def test_variant_details(self, client, supplier, supplier_items_with_variants):
        """Test that variant details are correctly returned."""
        response = await client.get(f"/admin/suppliers/{supplier.id}/items")
        data = response.json()

        # Find carnation item (has single variant)
        carnation = next((i for i in data["items"] if "Гвоздика" in i["raw_name"]), None)
        assert carnation is not None

        assert carnation["variants_count"] == 1
        variant = carnation["variants"][0]

        assert variant["length_cm"] == 70
        assert variant["pack_type"] == "pack"
        assert variant["pack_qty"] == 20
        assert float(variant["price"]) == 45.00
        assert variant["stock"] == 100
        assert variant["validation"] == "ok"

    async def test_multiple_colors(self, client, supplier, supplier_items_with_variants):
        """Test that multiple colors are returned correctly."""
        response = await client.get(f"/admin/suppliers/{supplier.id}/items")
        data = response.json()

        # Find carnation item (has multiple colors)
        carnation = next((i for i in data["items"] if "Гвоздика" in i["raw_name"]), None)
        assert carnation is not None

        assert len(carnation["colors"]) == 3
        assert "красный" in carnation["colors"]
        assert "розовый" in carnation["colors"]
        assert "белый" in carnation["colors"]


# Pytest fixtures for database setup
@pytest.fixture
async def db_session():
    """Provide async database session for tests."""
    from apps.api.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    """Provide async HTTP client for API tests."""
    from httpx import ASGITransport, AsyncClient

    from apps.api.database import get_db
    from apps.api.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
