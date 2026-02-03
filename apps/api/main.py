"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.logging_config import get_logger, setup_logging
from apps.api.routers import (
    admin,
    auth,
    buyers,
    dictionary,
    health,
    normalization,
    offers,
    orders,
    publish,
    skus,
    supplier_orders,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="B2B Flower Market Platform",
    description="Data-first wholesale flower marketplace API",
    version="0.2.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(auth.router)  # /auth/* - authentication endpoints
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(dictionary.router, prefix="/admin/dictionary", tags=["dictionary"])
app.include_router(skus.router, prefix="/admin/skus", tags=["skus"])
app.include_router(normalization.router, prefix="/admin/normalization", tags=["normalization"])
app.include_router(publish.router, prefix="/admin/publish", tags=["publish"])
app.include_router(buyers.router, tags=["buyers"])  # Admin buyer management
app.include_router(orders.router, tags=["orders"])  # Retail order endpoints (no prefix)
app.include_router(supplier_orders.router, prefix="/admin", tags=["supplier-orders"])  # Supplier order management
app.include_router(offers.router, tags=["offers"])  # No prefix - public endpoint


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        "application_started",
        env=settings.app_env,
        db_host=settings.db_host,
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("application_shutdown")
