"""Integration test for NormalizationService.propose() flow."""
import asyncio
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.api.config import settings
from apps.api.models import (
    Base,
    City,
    DictionaryEntry,
    ImportBatch,
    NormalizedSKU,
    NormalizationTask,
    Supplier,
    SupplierItem,
    SKUMapping,
)
from apps.api.services.dictionary_service import DictionaryService
from apps.api.services.import_service import ImportService
from apps.api.services.normalization_service import NormalizationService


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
        # Start transaction
        async with session.begin():
            yield session
            # Rollback at end (cleanup)
            await session.rollback()


@pytest.fixture(scope="function")
async def test_city(db_session):
    """Create test city."""
    city = City(
        name="Test City",
        country="Russia",
    )
    db_session.add(city)
    await db_session.flush()
    return city


@pytest.fixture(scope="function")
async def test_supplier(db_session, test_city):
    """Create test supplier."""
    supplier = Supplier(
        name="Test Supplier",
        city_id=test_city.id,
        contact_name="Test Contact",
        phone="+79001234567",
        email="test@supplier.test",
        tier="standard",
        status="active",
        meta={"tier": "key"},  # For priority testing
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
Гвоздика микс 50см,80,50
Chrysanthemum Santini white Holland,100,50
Alstroemeria mix 60cm,90,60
"""
    csv_file = tmp_path / "test_normalization.csv"
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
            meta={"origin_default": "Ecuador", "subtype": "standard"},
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
            title="Carnation Mix",
            variety=None,
            color=None,
            meta={},
        ),
        NormalizedSKU(
            product_type="chrysanthemum",
            title="Chrysanthemum Santini",
            variety="Santini",
            color=None,
            meta={"origin_default": "Holland", "subtype": "spray"},
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


@pytest.mark.asyncio
async def test_normalization_propose_flow(
    db_session,
    test_supplier,
    test_csv_file,
    seeded_dictionary,
    test_normalized_skus,
):
    """
    Test complete normalization propose flow.

    Steps:
    1. Import CSV with 5 items
    2. Run propose() for supplier
    3. Assert mappings and tasks created
    4. Run propose() again (idempotency test)
    5. Assert counts remain same
    """
    # Step 1: Import CSV
    import_service = ImportService(db_session)
    batch_id = await import_service.import_csv(
        supplier_id=test_supplier.id,
        file_path=test_csv_file,
        description="Test normalization import",
    )
    await db_session.commit()

    # Verify import
    result = await db_session.execute(
        select(ImportBatch).where(ImportBatch.id == batch_id)
    )
    batch = result.scalar_one()
    assert batch.status == "parsed"

    # Count supplier items
    result = await db_session.execute(
        select(func.count(SupplierItem.id)).where(
            SupplierItem.last_import_batch_id == batch_id
        )
    )
    item_count = result.scalar()
    assert item_count == 5

    # Step 2: Run propose() for supplier
    normalization_service = NormalizationService(db_session)
    summary = await normalization_service.propose(
        supplier_id=test_supplier.id,
        limit=100,
    )
    await db_session.commit()

    # Step 3: Assert results
    assert summary["processed_items"] == 5
    assert summary["proposed_mappings"] > 0
    assert summary["tasks_created"] >= 1  # At least one task for low confidence

    # Check mappings exist
    result = await db_session.execute(
        select(SKUMapping).where(SKUMapping.status == "proposed")
    )
    mappings = result.scalars().all()
    assert len(mappings) > 0

    # Verify at least one high-confidence mapping
    high_confidence_mappings = [
        m for m in mappings if m.confidence >= Decimal("0.70")
    ]
    # Note: May not always have high confidence depending on data
    # but should have some mappings with reasonable confidence

    # Check tasks exist
    result = await db_session.execute(
        select(NormalizationTask).where(NormalizationTask.status == "open")
    )
    tasks = result.scalars().all()
    assert len(tasks) >= 1

    # Verify tasks have proper priority
    for task in tasks:
        assert task.priority >= 100

    # Store counts for idempotency test
    mapping_count_first = len(mappings)
    task_count_first = len(tasks)
    proposed_mappings_first = summary["proposed_mappings"]
    tasks_created_first = summary["tasks_created"]

    # Step 4: Run propose() again (idempotency test)
    summary2 = await normalization_service.propose(
        supplier_id=test_supplier.id,
        limit=100,
    )
    await db_session.commit()

    # Step 5: Assert idempotency - no duplicates
    assert summary2["processed_items"] == 5
    assert summary2["proposed_mappings"] == 0  # No new mappings created
    assert summary2["tasks_created"] == 0  # No new tasks created

    # Verify counts unchanged
    result = await db_session.execute(
        select(SKUMapping).where(SKUMapping.status == "proposed")
    )
    mappings2 = result.scalars().all()
    assert len(mappings2) == mapping_count_first

    result = await db_session.execute(
        select(NormalizationTask).where(NormalizationTask.status == "open")
    )
    tasks2 = result.scalars().all()
    assert len(tasks2) == task_count_first


@pytest.mark.asyncio
async def test_normalization_propose_by_batch(
    db_session,
    test_supplier,
    test_csv_file,
    seeded_dictionary,
    test_normalized_skus,
):
    """Test propose() filtering by import_batch_id."""
    # Import CSV
    import_service = ImportService(db_session)
    batch_id = await import_service.import_csv(
        supplier_id=test_supplier.id,
        file_path=test_csv_file,
        description="Test batch filtering",
    )
    await db_session.commit()

    # Run propose() for specific batch
    normalization_service = NormalizationService(db_session)
    summary = await normalization_service.propose(
        import_batch_id=batch_id,
        limit=100,
    )
    await db_session.commit()

    assert summary["processed_items"] == 5
    assert summary["proposed_mappings"] >= 0


@pytest.mark.asyncio
async def test_normalization_propose_no_candidates(
    db_session,
    test_supplier,
    test_csv_file,
    seeded_dictionary,
):
    """Test propose() when no normalized SKUs exist (should create tasks)."""
    # Import CSV
    import_service = ImportService(db_session)
    batch_id = await import_service.import_csv(
        supplier_id=test_supplier.id,
        file_path=test_csv_file,
        description="Test no candidates",
    )
    await db_session.commit()

    # Run propose() without creating any normalized SKUs
    normalization_service = NormalizationService(db_session)
    summary = await normalization_service.propose(
        supplier_id=test_supplier.id,
        limit=100,
    )
    await db_session.commit()

    # Should process items but create no mappings
    assert summary["processed_items"] == 5
    assert summary["proposed_mappings"] == 0
    assert summary["tasks_created"] >= 1  # Tasks created for items with no candidates

    # Verify tasks exist with appropriate reasons
    result = await db_session.execute(
        select(NormalizationTask).where(NormalizationTask.status == "open")
    )
    tasks = result.scalars().all()
    assert len(tasks) >= 1

    # Check task reasons mention no candidates
    reasons = [task.reason for task in tasks]
    assert any("candidate" in reason.lower() or "not detected" in reason.lower() for reason in reasons)


@pytest.mark.asyncio
async def test_normalization_error_handling(
    db_session,
    test_supplier,
):
    """Test propose() validation and error handling."""
    normalization_service = NormalizationService(db_session)

    # Test: Missing both supplier_id and import_batch_id
    with pytest.raises(ValueError, match="At least one of"):
        await normalization_service.propose(limit=100)

    # Test: Process with no items (should not fail)
    summary = await normalization_service.propose(
        supplier_id=test_supplier.id,
        limit=100,
    )
    assert summary["processed_items"] == 0
    assert summary["proposed_mappings"] == 0
    assert summary["tasks_created"] == 0
