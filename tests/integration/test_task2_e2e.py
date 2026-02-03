"""End-to-end integration test for Task 2 workflow.

Complete scenario: Import → Normalize → Confirm → Publish → Search
"""
import pytest
from decimal import Decimal
from httpx import AsyncClient
from pathlib import Path

from apps.api.main import app
from apps.api.models import (
    City,
    ImportBatch,
    Offer,
    SKUMapping,
    Supplier,
    SupplierItem,
)
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
async def test_task2_complete_workflow(client, db_session, tmp_path):
    """
    Test complete Task 2 workflow end-to-end.

    Steps:
    1. Create supplier
    2. Import CSV (5 items)
    3. Bootstrap dictionary
    4. Create normalized SKUs (4 SKUs)
    5. Run propose
    6. List tasks
    7. Confirm mappings (4 items)
    8. Verify confirmed mappings
    9. Publish offers
    10. Query offers (4 active)
    11. Filter offers
    12. Search offers
    13. Re-publish (idempotency)
    """
    # ========================================================================
    # Setup: Create city and supplier
    # ========================================================================
    city = City(name="Test City E2E", country="Russia")
    db_session.add(city)
    await db_session.flush()

    supplier = Supplier(
        name="Test Flower Base E2E",
        city_id=city.id,
        contact_name="Test Admin",
        phone="+79001112233",
        email="admin@e2e.test",
        tier="key",
        status="active",
        meta={},
    )
    db_session.add(supplier)
    await db_session.flush()
    supplier_id = supplier.id
    await db_session.commit()

    # ========================================================================
    # Step 1: Import CSV with 5 items
    # ========================================================================
    csv_content = """Name,Price,Length
Rose Explorer 60cm (Ecuador),120,60
Rose Mondial 50cm,95-99,50
Carnation Pink 70cm (Netherlands),45,70
Alstroemeria White 80cm,65,80
Rose Unknown Variety 60cm,100,60
"""
    csv_file = tmp_path / "test_e2e.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    # Upload CSV
    with open(csv_file, "rb") as f:
        response = await client.post(
            f"/admin/suppliers/{supplier_id}/imports/csv",
            files={"file": ("test.csv", f, "text/csv")},
        )

    assert response.status_code == 200
    import_data = response.json()
    import_batch_id = import_data["batch_id"]
    await db_session.commit()

    # Verify import
    result = await db_session.execute(
        select(ImportBatch).where(ImportBatch.id == import_batch_id)
    )
    batch = result.scalar_one()
    assert batch.status == "parsed"

    # Verify supplier_items created
    result = await db_session.execute(
        select(func.count(SupplierItem.id)).where(
            SupplierItem.supplier_id == supplier_id
        )
    )
    item_count = result.scalar()
    assert item_count == 5

    # ========================================================================
    # Step 2: Bootstrap dictionary
    # ========================================================================
    response = await client.post("/admin/dictionary/bootstrap")
    assert response.status_code == 200
    dict_data = response.json()
    assert dict_data["created"] > 0
    await db_session.commit()

    # ========================================================================
    # Step 3: Create normalized SKUs
    # ========================================================================
    skus = [
        {"product_type": "rose", "variety": "Explorer", "title": "Rose Explorer"},
        {"product_type": "rose", "variety": "Mondial", "title": "Rose Mondial"},
        {"product_type": "carnation", "variety": None, "title": "Carnation Standard"},
        {"product_type": "alstroemeria", "variety": "White", "title": "Alstroemeria White"},
    ]

    created_skus = []
    for sku_data in skus:
        response = await client.post("/admin/skus", json=sku_data)
        assert response.status_code == 200
        created_skus.append(response.json())

    await db_session.commit()
    assert len(created_skus) == 4

    # ========================================================================
    # Step 4: Run propose
    # ========================================================================
    response = await client.post(
        "/admin/normalization/propose",
        json={"supplier_id": str(supplier_id), "limit": 100},
    )

    assert response.status_code == 200
    propose_data = response.json()
    assert propose_data["processed_items"] == 5
    assert propose_data["proposed_mappings"] > 0
    assert propose_data["tasks_created"] >= 1  # At least "Unknown Variety"
    await db_session.commit()

    # ========================================================================
    # Step 5: List tasks
    # ========================================================================
    response = await client.get(
        "/admin/normalization/tasks",
        params={"status": "open", "limit": 50},
    )

    assert response.status_code == 200
    tasks_data = response.json()
    assert tasks_data["total"] >= 1
    assert len(tasks_data["tasks"]) >= 1

    # Verify task structure
    task = tasks_data["tasks"][0]
    assert "id" in task
    assert "supplier_item" in task
    assert "proposed_mappings" in task
    assert task["supplier_item"]["raw_name"]

    # ========================================================================
    # Step 6: Confirm mappings for 4 items (Explorer, Mondial, Pink, White)
    # ========================================================================
    # Get all supplier items
    result = await db_session.execute(
        select(SupplierItem).where(SupplierItem.supplier_id == supplier_id)
    )
    items = result.scalars().all()

    # Map items to SKUs based on name matching
    confirmations = []
    for item in items:
        name_lower = item.raw_name.lower()

        # Skip "Unknown Variety" - intentionally unmapped
        if "unknown" in name_lower:
            continue

        # Find matching SKU
        sku_id = None
        if "explorer" in name_lower:
            sku_id = created_skus[0]["id"]
        elif "mondial" in name_lower:
            sku_id = created_skus[1]["id"]
        elif "carnation" in name_lower or "pink" in name_lower:
            sku_id = created_skus[2]["id"]
        elif "alstroemeria" in name_lower:
            sku_id = created_skus[3]["id"]

        if sku_id:
            confirmations.append({
                "supplier_item_id": str(item.id),
                "normalized_sku_id": sku_id,
                "notes": f"E2E test confirmation for {item.raw_name}",
            })

    # Confirm each mapping
    for confirmation in confirmations:
        response = await client.post(
            "/admin/normalization/confirm",
            json=confirmation,
        )
        assert response.status_code == 200
        mapping_data = response.json()
        assert mapping_data["mapping"]["status"] == "confirmed"

    await db_session.commit()
    assert len(confirmations) == 4

    # ========================================================================
    # Step 7: Verify confirmed mappings
    # ========================================================================
    result = await db_session.execute(
        select(SKUMapping).where(
            SKUMapping.status == "confirmed",
        )
    )
    confirmed_mappings = result.scalars().all()
    assert len(confirmed_mappings) == 4

    # Verify uniqueness: only ONE confirmed per supplier_item
    confirmed_item_ids = {m.supplier_item_id for m in confirmed_mappings}
    assert len(confirmed_item_ids) == 4  # No duplicates

    # ========================================================================
    # Step 8: Publish offers
    # ========================================================================
    response = await client.post(f"/admin/publish/suppliers/{supplier_id}")

    assert response.status_code == 200
    publish_data = response.json()
    assert publish_data["offers_created"] == 4  # 4 mapped items
    assert publish_data["skipped_unmapped"] == 1  # Unknown Variety
    offers_created_first = publish_data["offers_created"]
    await db_session.commit()

    # ========================================================================
    # Step 9: Query offers
    # ========================================================================
    response = await client.get("/offers")

    assert response.status_code == 200
    offers_data = response.json()
    assert offers_data["total"] == 4
    assert len(offers_data["offers"]) == 4

    # Verify offer structure
    offer = offers_data["offers"][0]
    assert "id" in offer
    assert "supplier" in offer
    assert "sku" in offer
    assert offer["supplier"]["name"] == "Test Flower Base E2E"
    assert offer["sku"]["product_type"] in ["rose", "carnation", "alstroemeria"]
    assert offer["published_at"]

    # Verify all active
    for offer in offers_data["offers"]:
        # Check via DB that is_active=true
        result = await db_session.execute(
            select(Offer).where(Offer.id == offer["id"])
        )
        db_offer = result.scalar_one()
        assert db_offer.is_active is True

    # ========================================================================
    # Step 10: Filter offers by product_type
    # ========================================================================
    response = await client.get("/offers", params={"product_type": "rose"})

    assert response.status_code == 200
    rose_data = response.json()
    # Should have 2 roses (Explorer, Mondial)
    assert rose_data["total"] == 2

    for offer in rose_data["offers"]:
        assert offer["sku"]["product_type"] == "rose"

    # ========================================================================
    # Step 11: Filter offers by length
    # ========================================================================
    response = await client.get("/offers", params={"length_cm": 60})

    assert response.status_code == 200
    length_data = response.json()
    # Should have Explorer (60cm)
    assert length_data["total"] >= 1

    for offer in length_data["offers"]:
        assert offer["length_cm"] == 60

    # ========================================================================
    # Step 12: Search offers by text
    # ========================================================================
    response = await client.get("/offers", params={"q": "explorer"})

    assert response.status_code == 200
    search_data = response.json()
    # Should find Explorer
    assert search_data["total"] >= 1

    found_explorer = False
    for offer in search_data["offers"]:
        if "explorer" in offer["sku"]["title"].lower():
            found_explorer = True
            break
    assert found_explorer

    # ========================================================================
    # Step 13: Re-publish (idempotency and replace)
    # ========================================================================
    response = await client.post(f"/admin/publish/suppliers/{supplier_id}")

    assert response.status_code == 200
    republish_data = response.json()
    assert republish_data["offers_deactivated"] == offers_created_first
    assert republish_data["offers_created"] == 4  # Same count
    await db_session.commit()

    # Verify: still 4 active offers
    response = await client.get("/offers")
    assert response.status_code == 200
    final_data = response.json()
    assert final_data["total"] == 4

    # Verify old offers deactivated
    result = await db_session.execute(
        select(func.count(Offer.id)).where(
            Offer.supplier_id == supplier_id,
            Offer.is_active == False,
        )
    )
    deactivated_count = result.scalar()
    assert deactivated_count == offers_created_first

    # ========================================================================
    # ✅ END-TO-END TEST COMPLETE
    # ========================================================================
    print("\n✅ Task 2 end-to-end workflow completed successfully!")
    print(f"   - Imported: 5 items")
    print(f"   - Confirmed: 4 mappings")
    print(f"   - Published: 4 offers")
    print(f"   - Skipped: 1 unmapped item")
