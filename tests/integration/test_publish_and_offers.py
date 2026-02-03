"""Integration tests for publish and offers endpoints."""
import pytest
from decimal import Decimal
from httpx import AsyncClient
from pathlib import Path

from apps.api.main import app
from apps.api.models import (
    City,
    ImportBatch,
    NormalizedSKU,
    Offer,
    Supplier,
)
from apps.api.services.dictionary_service import DictionaryService
from apps.api.services.import_service import ImportService
from apps.api.services.normalization_service import NormalizationService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.api.config import settings


@pytest.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Create test database session with transaction rollback."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture(scope="function")
async def test_city(db_session):
    """Create test city."""
    city = City(name="Test City Publish", country="Russia")
    db_session.add(city)
    await db_session.flush()
    return city


@pytest.fixture(scope="function")
async def test_supplier(db_session, test_city):
    """Create test supplier."""
    supplier = Supplier(
        name="Test Supplier Publish",
        city_id=test_city.id,
        contact_name="Test Contact",
        phone="+79001234567",
        email="test@publish.test",
        tier="standard",
        status="active",
        meta={},
    )
    db_session.add(supplier)
    await db_session.flush()
    return supplier


@pytest.fixture(scope="function")
async def test_csv_file(tmp_path):
    """Create temporary test CSV file."""
    csv_content = """Name,Price,Length
Rose Explorer 60cm Ecuador,120,60
Rose Pink Floyd 70cm Kenya,150,70
Carnation mix 50cm,80,50
"""
    csv_file = tmp_path / "test_publish.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    return csv_file


@pytest.fixture(scope="function")
async def test_csv_file_2(tmp_path):
    """Create second test CSV file for re-publish test."""
    csv_content = """Name,Price,Length
Rose Explorer 60cm,115,60
Alstroemeria 60cm,90,60
"""
    csv_file = tmp_path / "test_publish_2.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    return csv_file


@pytest.fixture(scope="function")
async def seeded_dictionary(db_session):
    """Bootstrap dictionary with test data."""
    dict_service = DictionaryService(db_session)
    await dict_service.bootstrap()
    await db_session.flush()
    return True


@pytest.fixture(scope="function")
async def test_normalized_skus(db_session):
    """Create test normalized SKUs."""
    skus = [
        NormalizedSKU(
            product_type="rose",
            title="Rose Explorer",
            variety="Explorer",
            color=None,
            meta={},
        ),
        NormalizedSKU(
            product_type="rose",
            title="Rose Pink Floyd",
            variety="Pink Floyd",
            color="pink",
            meta={},
        ),
        NormalizedSKU(
            product_type="carnation",
            title="Carnation",
            variety=None,
            color=None,
            meta={},
        ),
        NormalizedSKU(
            product_type="alstroemeria",
            title="Alstroemeria",
            variety=None,
            color=None,
            meta={},
        ),
    ]
    for sku in skus:
        db_session.add(sku)
    await db_session.flush()
    return skus


@pytest.fixture(scope="function")
async def imported_and_confirmed(
    db_session,
    test_supplier,
    test_csv_file,
    seeded_dictionary,
    test_normalized_skus,
):
    """Import CSV, propose, and confirm at least one mapping."""
    # Import CSV
    import_service = ImportService(db_session)
    batch_id = await import_service.import_csv(
        supplier_id=test_supplier.id,
        file_path=test_csv_file,
        description="Test import for publish",
    )
    await db_session.commit()

    # Run normalization propose
    normalization_service = NormalizationService(db_session)
    await normalization_service.propose(supplier_id=test_supplier.id, limit=100)
    await db_session.commit()

    # Confirm first mapping via endpoint would be ideal, but for test fixture
    # we'll use direct DB manipulation
    from apps.api.models import SKUMapping, SupplierItem
    from sqlalchemy import update

    # Get first supplier item
    result = await db_session.execute(
        select(SupplierItem)
        .where(SupplierItem.supplier_id == test_supplier.id)
        .limit(1)
    )
    item = result.scalar_one()

    # Get first proposed mapping
    result = await db_session.execute(
        select(SKUMapping)
        .where(
            SKUMapping.supplier_item_id == item.id,
            SKUMapping.status == "proposed",
        )
        .limit(1)
    )
    mapping = result.scalar_one_or_none()

    if mapping:
        # Confirm it
        await db_session.execute(
            update(SKUMapping)
            .where(SKUMapping.supplier_item_id == item.id)
            .values(status="rejected")
        )
        mapping.status = "confirmed"
        mapping.method = "manual"
        mapping.confidence = Decimal("1.0")
        await db_session.commit()

    return batch_id


@pytest.fixture(scope="function")
async def client(db_session):
    """Create test HTTP client with database session override."""
    from apps.api.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_publish_flow(
    client,
    test_supplier,
    imported_and_confirmed,
    db_session,
):
    """Test POST /admin/publish/suppliers/{id} creates offers."""
    # Publish offers
    response = await client.post(
        f"/admin/publish/suppliers/{test_supplier.id}",
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "supplier_id" in data
    assert "import_batch_id" in data
    assert "offers_deactivated" in data
    assert "offers_created" in data
    assert "skipped_unmapped" in data

    assert data["supplier_id"] == str(test_supplier.id)
    assert data["offers_created"] > 0

    # Verify offers created in DB
    result = await db_session.execute(
        select(func.count(Offer.id)).where(
            Offer.supplier_id == test_supplier.id,
            Offer.is_active == True,
        )
    )
    count = result.scalar()
    assert count > 0
    assert count == data["offers_created"]


@pytest.mark.asyncio
async def test_query_offers(
    client,
    test_supplier,
    imported_and_confirmed,
    db_session,
):
    """Test GET /offers returns published offers."""
    # First publish
    await client.post(f"/admin/publish/suppliers/{test_supplier.id}")
    await db_session.commit()

    # Query offers
    response = await client.get("/offers")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "offers" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    # Should have at least one offer
    assert data["total"] > 0
    assert len(data["offers"]) > 0

    # Verify offer structure
    offer = data["offers"][0]
    assert "id" in offer
    assert "supplier" in offer
    assert "sku" in offer
    assert "price_min" in offer
    assert "published_at" in offer

    # Verify joined data
    assert offer["supplier"]["id"]
    assert offer["supplier"]["name"]
    assert offer["sku"]["id"]
    assert offer["sku"]["product_type"]
    assert offer["sku"]["title"]


@pytest.mark.asyncio
async def test_filter_offers_by_product_type(
    client,
    test_supplier,
    imported_and_confirmed,
    db_session,
):
    """Test GET /offers?product_type=rose filters correctly."""
    # Publish offers
    await client.post(f"/admin/publish/suppliers/{test_supplier.id}")
    await db_session.commit()

    # Query with filter
    response = await client.get("/offers", params={"product_type": "rose"})

    assert response.status_code == 200
    data = response.json()

    # All returned offers should be roses
    for offer in data["offers"]:
        assert offer["sku"]["product_type"] == "rose"


@pytest.mark.asyncio
async def test_filter_offers_by_price(
    client,
    test_supplier,
    imported_and_confirmed,
    db_session,
):
    """Test GET /offers?price_max=100 filters correctly."""
    # Publish offers
    await client.post(f"/admin/publish/suppliers/{test_supplier.id}")
    await db_session.commit()

    # Query with price filter
    response = await client.get("/offers", params={"price_max": 100})

    assert response.status_code == 200
    data = response.json()

    # All returned offers should have price_min <= 100
    for offer in data["offers"]:
        assert Decimal(offer["price_min"]) <= Decimal("100")


@pytest.mark.asyncio
async def test_republish_replaces_old_offers(
    client,
    test_supplier,
    test_csv_file_2,
    imported_and_confirmed,
    seeded_dictionary,
    test_normalized_skus,
    db_session,
):
    """Test re-publishing deactivates old offers and creates new ones."""
    # First publish
    response1 = await client.post(f"/admin/publish/suppliers/{test_supplier.id}")
    assert response1.status_code == 200
    data1 = response1.json()
    offers_created_first = data1["offers_created"]
    await db_session.commit()

    # Import second CSV
    import_service = ImportService(db_session)
    batch_id_2 = await import_service.import_csv(
        supplier_id=test_supplier.id,
        file_path=test_csv_file_2,
        description="Second import",
    )
    await db_session.commit()

    # Propose and confirm mappings for new batch
    normalization_service = NormalizationService(db_session)
    await normalization_service.propose(import_batch_id=batch_id_2, limit=100)
    await db_session.commit()

    # Confirm first mapping from new batch
    from apps.api.models import SKUMapping, SupplierItem
    from sqlalchemy import update

    result = await db_session.execute(
        select(SupplierItem)
        .where(SupplierItem.last_import_batch_id == batch_id_2)
        .limit(1)
    )
    item = result.scalar_one_or_none()

    if item:
        result = await db_session.execute(
            select(SKUMapping)
            .where(
                SKUMapping.supplier_item_id == item.id,
                SKUMapping.status == "proposed",
            )
            .limit(1)
        )
        mapping = result.scalar_one_or_none()

        if mapping:
            await db_session.execute(
                update(SKUMapping)
                .where(SKUMapping.supplier_item_id == item.id)
                .values(status="rejected")
            )
            mapping.status = "confirmed"
            mapping.method = "manual"
            mapping.confidence = Decimal("1.0")
            await db_session.commit()

    # Second publish
    response2 = await client.post(f"/admin/publish/suppliers/{test_supplier.id}")
    assert response2.status_code == 200
    data2 = response2.json()

    # Should deactivate old offers
    assert data2["offers_deactivated"] == offers_created_first

    # Should create new offers
    assert data2["offers_created"] > 0

    # Query active offers - should only return new ones
    response3 = await client.get("/offers", params={"supplier_id": str(test_supplier.id)})
    data3 = response3.json()

    assert data3["total"] == data2["offers_created"]

    # Verify old offers are deactivated in DB
    result = await db_session.execute(
        select(func.count(Offer.id)).where(
            Offer.supplier_id == test_supplier.id,
            Offer.is_active == False,
        )
    )
    deactivated_count = result.scalar()
    assert deactivated_count == offers_created_first


@pytest.mark.asyncio
async def test_search_offers_by_text(
    client,
    test_supplier,
    imported_and_confirmed,
    db_session,
):
    """Test GET /offers?q=explorer searches by text."""
    # Publish offers
    await client.post(f"/admin/publish/suppliers/{test_supplier.id}")
    await db_session.commit()

    # Search for "explorer"
    response = await client.get("/offers", params={"q": "explorer"})

    assert response.status_code == 200
    data = response.json()

    # Should return offers with "Explorer" in title or variety
    assert data["total"] > 0
    for offer in data["offers"]:
        sku = offer["sku"]
        text = f"{sku['title']} {sku['variety'] or ''}".lower()
        assert "explorer" in text


@pytest.mark.asyncio
async def test_publish_supplier_not_found(client):
    """Test POST /admin/publish/suppliers/{id} with non-existent supplier returns 404."""
    from uuid import uuid4

    response = await client.post(f"/admin/publish/suppliers/{uuid4()}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_publish_no_imports(client, test_supplier, db_session):
    """Test POST /admin/publish/suppliers/{id} with no imports returns 404."""
    # Try to publish without any imports
    response = await client.post(f"/admin/publish/suppliers/{test_supplier.id}")

    assert response.status_code == 404
    assert "no parsed imports" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_offers_pagination(
    client,
    test_supplier,
    imported_and_confirmed,
    db_session,
):
    """Test GET /offers pagination with limit and offset."""
    # Publish offers
    await client.post(f"/admin/publish/suppliers/{test_supplier.id}")
    await db_session.commit()

    # Get first page
    response1 = await client.get("/offers", params={"limit": 1, "offset": 0})
    data1 = response1.json()

    assert len(data1["offers"]) <= 1
    assert data1["limit"] == 1
    assert data1["offset"] == 0

    # Get second page
    if data1["total"] > 1:
        response2 = await client.get("/offers", params={"limit": 1, "offset": 1})
        data2 = response2.json()

        assert len(data2["offers"]) <= 1
        assert data2["offset"] == 1

        # Should be different offers
        if len(data1["offers"]) > 0 and len(data2["offers"]) > 0:
            assert data1["offers"][0]["id"] != data2["offers"][0]["id"]
