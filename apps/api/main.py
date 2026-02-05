"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.logging_config import get_logger, setup_logging
from apps.api.routers import (
    admin,
    auth,
    buyers,
    catalog,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info(
        "application_started",
        env=settings.app_env,
        db_host=settings.db_host,
        cors_origins=settings.cors_origins_list,
        rate_limit_enabled=settings.rate_limit_enabled,
    )
    yield
    # Shutdown
    logger.info("application_shutdown")


# Create FastAPI app with lifespan
app = FastAPI(
    title="B2B Flower Market Platform",
    description="Data-first wholesale flower marketplace API",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware - configurable via CORS_ORIGINS env variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Simple in-memory rate limiter
_rate_limit_store: dict[str, list[float]] = {}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting middleware."""
    if not settings.rate_limit_enabled:
        return await call_next(request)

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/health/ready"]:
        return await call_next(request)

    import time

    now = time.time()
    window = settings.rate_limit_window
    max_requests = settings.rate_limit_requests

    # Clean up old entries and check limit
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    # Remove timestamps outside the window
    _rate_limit_store[client_ip] = [
        ts for ts in _rate_limit_store[client_ip] if now - ts < window
    ]

    # Check if over limit
    if len(_rate_limit_store[client_ip]) >= max_requests:
        logger.warning("rate_limit_exceeded", client_ip=client_ip)
        return Response(
            content='{"detail": "Too many requests"}',
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": str(window)},
        )

    # Add current request
    _rate_limit_store[client_ip].append(now)

    return await call_next(request)


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
app.include_router(catalog.router, prefix="/admin/catalog", tags=["catalog"])  # Flower catalog management
