"""Integration tests for normalization endpoints."""
import pytest
from decimal import Decimal
from httpx import AsyncClient
from pathlib import Path

from apps.api.main import app
from apps.api.models import (
    City,
    DictionaryEntry,
    ImportBatch,
    NormalizedSKU,
    NormalizationTask,
    SKUMapping,
    Supplier,
    SupplierItem,
)
from apps.api.services.dictionary_service import DictionaryService
from apps.api.services.import_service import ImportService
from sqlalchemy import select
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
    city = City(name="Test City Norm", country="Russia")
    db_session.add(city)
    await db_session.flush()
    return city


@pytest.fixture(scope="function")
async def test_supplier(db_session, test_city):
    """Create test supplier."""
    supplier = Supplier(
        name="Test Supplier Norm",
        city_id=test_city.id,
        contact_name="Test Contact",
        phone="+79001234567",
        email="test@normalization.test",
        tier="standard",
        status="active",
        meta={"tier": "key"},
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
Chrysanthemum Santini white Holland,100,50
Alstroemeria 60cm,90,60
"""
    csv_file = tmp_path / "test_norm_endpoints.csv"
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
            meta={"origin_default": "Ecuador"},
        ),
        NormalizedSKU(
            product_type="rose",
            title="Rose Pink Floyd",
            variety="Pink Floyd",
            color="pink",
            meta={"origin_default": "Kenya"},
        ),
        NormalizedSKU(
            product_type="carnation",
            title="Carnation",
            variety=None,
            color=None,
            meta={},
        ),
        NormalizedSKU(
            product_type="chrysanthemum",
            title="Chrysanthemum Santini",
            variety="Santini",
            color=None,
            meta={"subtype": "spray"},
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
async def imported_batch(db_session, test_supplier, test_csv_file, seeded_dictionary):
    """Import CSV and return batch_id."""
    import_service = ImportService(db_session)
    batch_id = await import_service.import_csv(
        supplier_id=test_supplier.id,
        file_path=test_csv_file,
        description="Test import for endpoints",
    )
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
async def test_propose_endpoint_success(
    client,
    test_supplier,
    imported_batch,
    test_normalized_skus,
    db_session,
):
    """Test POST /admin/normalization/propose with supplier_id."""
    # Call propose endpoint
    response = await client.post(
        "/admin/normalization/propose",
        json={
            "supplier_id": str(test_supplier.id),
            "limit": 100,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "processed_items" in data
    assert "proposed_mappings" in data
    assert "tasks_created" in data

    # Should process 5 items
    assert data["processed_items"] == 5

    # Should create some mappings
    assert data["proposed_mappings"] > 0

    # Verify mappings created in DB
    result = await db_session.execute(
        select(SKUMapping).where(SKUMapping.status == "proposed")
    )
    mappings = result.scalars().all()
    assert len(mappings) > 0


@pytest.mark.asyncio
async def test_propose_endpoint_no_filters(client):
    """Test POST /admin/normalization/propose without filters returns 400."""
    response = await client.post(
        "/admin/normalization/propose",
        json={"limit": 100},
    )

    assert response.status_code == 400
    assert "at least one of" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_propose_endpoint_supplier_not_found(client):
    """Test POST /admin/normalization/propose with non-existent supplier returns 404."""
    from uuid import uuid4

    response = await client.post(
        "/admin/normalization/propose",
        json={
            "supplier_id": str(uuid4()),
            "limit": 100,
        },
    )

    assert response.status_code == 404
    assert "supplier not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_tasks_endpoint(
    client,
    test_supplier,
    imported_batch,
    test_normalized_skus,
    db_session,
):
    """Test GET /admin/normalization/tasks returns enriched tasks."""
    # First run propose to create tasks
    await client.post(
        "/admin/normalization/propose",
        json={
            "supplier_id": str(test_supplier.id),
            "limit": 100,
        },
    )
    await db_session.commit()

    # List tasks
    response = await client.get(
        "/admin/normalization/tasks",
        params={"status": "open", "limit": 50},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "tasks" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    # Should have at least one task
    assert data["total"] > 0
    assert len(data["tasks"]) > 0

    # Verify task structure
    task = data["tasks"][0]
    assert "id" in task
    assert "supplier_item_id" in task
    assert "reason" in task
    assert "priority" in task
    assert "status" in task
    assert "supplier_item" in task
    assert "proposed_mappings" in task
    assert "sample_raw_rows" in task

    # Verify supplier_item details
    assert task["supplier_item"]["id"]
    assert task["supplier_item"]["raw_name"]
    assert task["supplier_item"]["name_norm"]


@pytest.mark.asyncio
async def test_list_tasks_filter_by_supplier(
    client,
    test_supplier,
    imported_batch,
    test_normalized_skus,
    db_session,
):
    """Test GET /admin/normalization/tasks with supplier_id filter."""
    # Run propose
    await client.post(
        "/admin/normalization/propose",
        json={"supplier_id": str(test_supplier.id), "limit": 100},
    )
    await db_session.commit()

    # List tasks filtered by supplier
    response = await client.get(
        "/admin/normalization/tasks",
        params={"supplier_id": str(test_supplier.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 0


@pytest.mark.asyncio
async def test_confirm_mapping_endpoint(
    client,
    test_supplier,
    imported_batch,
    test_normalized_skus,
    db_session,
):
    """Test POST /admin/normalization/confirm creates confirmed mapping."""
    # Run propose to create mappings
    await client.post(
        "/admin/normalization/propose",
        json={"supplier_id": str(test_supplier.id), "limit": 100},
    )
    await db_session.commit()

    # Get a task with mappings
    response = await client.get(
        "/admin/normalization/tasks",
        params={"status": "open", "limit": 1},
    )
    data = response.json()
    assert len(data["tasks"]) > 0

    task = data["tasks"][0]
    supplier_item_id = task["supplier_item_id"]
    assert len(task["proposed_mappings"]) > 0
    sku_id = task["proposed_mappings"][0]["normalized_sku_id"]

    # Confirm mapping
    confirm_response = await client.post(
        "/admin/normalization/confirm",
        json={
            "supplier_item_id": supplier_item_id,
            "normalized_sku_id": sku_id,
            "notes": "Test confirmation",
        },
    )

    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()

    # Verify response
    assert "mapping" in confirm_data
    mapping = confirm_data["mapping"]
    assert mapping["status"] == "confirmed"
    assert mapping["confidence"] == "1.0"
    assert mapping["method"] == "manual"
    assert mapping["notes"] == "Test confirmation"

    # Verify in DB: only one confirmed mapping exists
    result = await db_session.execute(
        select(SKUMapping).where(
            SKUMapping.supplier_item_id == supplier_item_id,
            SKUMapping.status == "confirmed",
        )
    )
    confirmed_mappings = result.scalars().all()
    assert len(confirmed_mappings) == 1

    # Verify task marked as done
    result = await db_session.execute(
        select(NormalizationTask).where(
            NormalizationTask.supplier_item_id == supplier_item_id
        )
    )
    tasks = result.scalars().all()
    for t in tasks:
        assert t.status == "done"


@pytest.mark.asyncio
async def test_confirm_mapping_rejects_old_mappings(
    client,
    test_supplier,
    imported_batch,
    test_normalized_skus,
    db_session,
):
    """Test POST /admin/normalization/confirm rejects old mappings when confirming new one."""
    # Run propose
    await client.post(
        "/admin/normalization/propose",
        json={"supplier_id": str(test_supplier.id), "limit": 100},
    )
    await db_session.commit()

    # Get task with multiple mappings
    response = await client.get(
        "/admin/normalization/tasks",
        params={"status": "open", "limit": 1},
    )
    data = response.json()
    task = data["tasks"][0]
    supplier_item_id = task["supplier_item_id"]

    # Confirm first SKU
    if len(task["proposed_mappings"]) > 0:
        sku_id_1 = task["proposed_mappings"][0]["normalized_sku_id"]
        await client.post(
            "/admin/normalization/confirm",
            json={
                "supplier_item_id": supplier_item_id,
                "normalized_sku_id": sku_id_1,
                "notes": "First confirmation",
            },
        )
        await db_session.commit()

        # Confirm second SKU (should reject first)
        if len(task["proposed_mappings"]) > 1:
            sku_id_2 = task["proposed_mappings"][1]["normalized_sku_id"]
            response2 = await client.post(
                "/admin/normalization/confirm",
                json={
                    "supplier_item_id": supplier_item_id,
                    "normalized_sku_id": sku_id_2,
                    "notes": "Second confirmation",
                },
            )

            assert response2.status_code == 200
            await db_session.commit()

            # Verify only second mapping is confirmed
            result = await db_session.execute(
                select(SKUMapping).where(
                    SKUMapping.supplier_item_id == supplier_item_id,
                    SKUMapping.status == "confirmed",
                )
            )
            confirmed = result.scalars().all()
            assert len(confirmed) == 1
            assert confirmed[0].normalized_sku_id == sku_id_2

            # Verify first mapping is rejected
            result = await db_session.execute(
                select(SKUMapping).where(
                    SKUMapping.supplier_item_id == supplier_item_id,
                    SKUMapping.normalized_sku_id == sku_id_1,
                )
            )
            old_mapping = result.scalar_one()
            assert old_mapping.status == "rejected"


@pytest.mark.asyncio
async def test_propose_idempotency(
    client,
    test_supplier,
    imported_batch,
    test_normalized_skus,
    db_session,
):
    """Test POST /admin/normalization/propose is idempotent."""
    # First run
    response1 = await client.post(
        "/admin/normalization/propose",
        json={"supplier_id": str(test_supplier.id), "limit": 100},
    )
    assert response1.status_code == 200
    data1 = response1.json()
    await db_session.commit()

    # Second run (should not create duplicates)
    response2 = await client.post(
        "/admin/normalization/propose",
        json={"supplier_id": str(test_supplier.id), "limit": 100},
    )
    assert response2.status_code == 200
    data2 = response2.json()

    # Second run should process items but create no new mappings
    assert data2["processed_items"] == data1["processed_items"]
    assert data2["proposed_mappings"] == 0
    assert data2["tasks_created"] == 0


@pytest.mark.asyncio
async def test_confirm_nonexistent_item_returns_404(client, test_normalized_skus):
    """Test POST /admin/normalization/confirm with non-existent item returns 404."""
    from uuid import uuid4

    response = await client.post(
        "/admin/normalization/confirm",
        json={
            "supplier_item_id": str(uuid4()),
            "normalized_sku_id": str(test_normalized_skus[0].id),
            "notes": "Test",
        },
    )

    assert response.status_code == 404
    assert "item not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_confirm_nonexistent_sku_returns_404(
    client,
    test_supplier,
    imported_batch,
    db_session,
):
    """Test POST /admin/normalization/confirm with non-existent SKU returns 404."""
    from uuid import uuid4

    # Get a supplier item
    result = await db_session.execute(
        select(SupplierItem).where(SupplierItem.supplier_id == test_supplier.id).limit(1)
    )
    item = result.scalar_one()

    response = await client.post(
        "/admin/normalization/confirm",
        json={
            "supplier_item_id": str(item.id),
            "normalized_sku_id": str(uuid4()),
            "notes": "Test",
        },
    )

    assert response.status_code == 404
    assert "sku not found" in response.json()["detail"].lower()
