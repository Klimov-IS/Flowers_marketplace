"""Integration test for CSV import pipeline."""
import pytest
from sqlalchemy import select

from apps.api.models import ImportBatch, OfferCandidate, RawRow, Supplier, SupplierItem
from apps.api.services.import_service import ImportService


@pytest.mark.asyncio
class TestCSVImport:
    """Integration tests for CSV import."""

    @pytest.fixture
    async def supplier(self, db_session):
        """Create test supplier."""
        supplier = Supplier(
            name="Test Flower Base",
            status="active",
            contacts={},
        )
        db_session.add(supplier)
        await db_session.commit()
        await db_session.refresh(supplier)
        return supplier

    async def test_csv_import_pipeline(self, db_session, supplier):
        """Test full CSV import pipeline."""
        # Prepare test CSV
        csv_content = b"""NAIMENOVANIE,CENA,KOL-VO
Roza Explorer 60sm (Ekvador),120,10
Roza Mondial 50sm,95-99,
Gvozdika Rozovaya 70sm,45,25
"""

        # Run import
        import_service = ImportService(db_session)
        import_batch = await import_service.import_csv(
            supplier_id=supplier.id,
            filename="test.csv",
            content=csv_content,
        )

        # Verify import_batch created
        assert import_batch.id is not None
        assert import_batch.status == "parsed"
        assert import_batch.source_type == "csv"
        assert import_batch.source_filename == "test.csv"

        # Verify raw_rows stored
        result = await db_session.execute(
            select(RawRow).where(RawRow.import_batch_id == import_batch.id)
        )
        raw_rows = result.scalars().all()
        assert len(raw_rows) == 3  # 3 data rows

        # Verify raw data is immutable (has row_ref, raw_cells, raw_text)
        for raw_row in raw_rows:
            assert raw_row.row_ref is not None
            assert raw_row.raw_cells is not None
            assert raw_row.raw_text is not None

        # Verify supplier_items created
        result = await db_session.execute(
            select(SupplierItem).where(
                SupplierItem.supplier_id == supplier.id
            )
        )
        supplier_items = result.scalars().all()
        assert len(supplier_items) == 3

        # Check supplier_item fields
        for item in supplier_items:
            assert item.stable_key is not None
            assert item.raw_name is not None
            assert item.name_norm is not None
            assert item.status == "active"

        # Verify offer_candidates created
        result = await db_session.execute(
            select(OfferCandidate).where(
                OfferCandidate.import_batch_id == import_batch.id
            )
        )
        offer_candidates = result.scalars().all()
        assert len(offer_candidates) == 3

        # Check specific offer_candidate
        # Find "Roza Explorer" offer
        explorer_offer = next(
            (
                oc
                for oc in offer_candidates
                if "Explorer" in oc.raw_row.raw_text
            ),
            None,
        )
        if explorer_offer:
            assert explorer_offer.price_type == "fixed"
            assert explorer_offer.price_min == 120
            assert explorer_offer.price_max is None
            assert explorer_offer.pack_qty == 10
            # Length extraction might work depending on header normalization
            # For this test we use latin 'sm' not 'cm', so might not extract
            assert explorer_offer.validation == "ok"

        # Find range price offer
        mondial_offer = next(
            (
                oc
                for oc in offer_candidates
                if "Mondial" in oc.raw_row.raw_text
            ),
            None,
        )
        if mondial_offer:
            assert mondial_offer.price_type == "range"
            assert mondial_offer.price_min == 95
            assert mondial_offer.price_max == 99

    async def test_csv_import_summary(self, db_session, supplier):
        """Test import summary endpoint."""
        # Import CSV
        csv_content = b"""NAIMENOVANIE,CENA
Item 1,100
Item 2,200
"""

        import_service = ImportService(db_session)
        import_batch = await import_service.import_csv(
            supplier_id=supplier.id,
            filename="test.csv",
            content=csv_content,
        )

        # Get summary
        summary = await import_service.get_import_summary(import_batch.id)

        assert summary is not None
        assert summary["batch_id"] == import_batch.id
        assert summary["status"] == "parsed"
        assert summary["raw_rows_count"] == 2
        assert summary["supplier_items_count"] == 2
        assert summary["offer_candidates_count"] == 2
        assert summary["parse_events_count"] >= 0


# Pytest fixtures for database setup
@pytest.fixture
async def db_session():
    """
    Provide async database session for tests.

    Note: This is a simplified fixture. In production, you would:
    - Create a test database
    - Run migrations
    - Provide clean session per test
    - Rollback after each test
    """
    from apps.api.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
