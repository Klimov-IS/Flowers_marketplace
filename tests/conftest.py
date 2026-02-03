"""Shared pytest fixtures for all tests."""
import pytest
from decimal import Decimal
from httpx import AsyncClient, ASGITransport

from apps.api.main import app


# Database session fixture
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


# HTTP client fixture
@pytest.fixture
async def client(db_session):
    """Provide async HTTP client for API tests."""
    # Override get_db dependency to use test session
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

    # Clean up
    app.dependency_overrides.clear()


# City fixture
@pytest.fixture
async def sample_city(db_session):
    """Create a test city."""
    from apps.api.models import City

    city = City(
        name="Test City",
        country="RU",
    )
    db_session.add(city)
    await db_session.commit()
    await db_session.refresh(city)
    return city


# Supplier fixture
@pytest.fixture
async def sample_supplier(db_session, sample_city):
    """Create a test supplier."""
    from apps.api.models import Supplier

    supplier = Supplier(
        name="Test Flower Supplier",
        city_id=sample_city.id,
        status="active",
        contacts={},
    )
    db_session.add(supplier)
    await db_session.commit()
    await db_session.refresh(supplier)
    return supplier


# Buyer fixture
@pytest.fixture
async def sample_buyer(db_session, sample_city):
    """Create a test buyer."""
    from apps.api.models import Buyer

    buyer = Buyer(
        name="Test Flower Shop",
        phone="+79001112233",
        email="test@shop.com",
        address="123 Test St",
        city_id=sample_city.id,
        status="active",
    )
    db_session.add(buyer)
    await db_session.commit()
    await db_session.refresh(buyer)
    return buyer


# NormalizedSKU fixture
@pytest.fixture
async def sample_normalized_sku(db_session):
    """Create a test normalized SKU."""
    from apps.api.models import NormalizedSKU

    sku = NormalizedSKU(
        flower="rose",
        variety="Explorer",
        color="red",
        length=60,
        unit="stem",
        origin_country="Ecuador",
        status="active",
    )
    db_session.add(sku)
    await db_session.commit()
    await db_session.refresh(sku)
    return sku


# Offer fixture
@pytest.fixture
async def sample_offer(db_session, sample_supplier, sample_normalized_sku):
    """Create a test offer."""
    from apps.api.models import Offer

    offer = Offer(
        supplier_id=sample_supplier.id,
        normalized_sku_id=sample_normalized_sku.id,
        price_type="fixed",
        price_min=Decimal("100.00"),
        price_max=None,
        currency="RUB",
        unit="stem",
        pack_qty=10,
        is_active=True,
    )
    db_session.add(offer)
    await db_session.commit()
    await db_session.refresh(offer)
    return offer


# Order fixture
@pytest.fixture
async def sample_order(db_session, sample_buyer, sample_supplier, sample_offer):
    """Create a test order."""
    from apps.api.models import Order, OrderItem

    order = Order(
        buyer_id=sample_buyer.id,
        supplier_id=sample_supplier.id,
        status="pending",
        total_amount=Decimal("1000.00"),
        currency="RUB",
    )
    db_session.add(order)
    await db_session.flush()

    # Add order item
    order_item = OrderItem(
        order_id=order.id,
        offer_id=sample_offer.id,
        normalized_sku_id=sample_offer.normalized_sku_id,
        quantity=10,
        unit_price=Decimal("100.00"),
        total_price=Decimal("1000.00"),
    )
    db_session.add(order_item)

    await db_session.commit()
    await db_session.refresh(order, ["items"])
    return order
