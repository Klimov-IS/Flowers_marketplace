"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.api.auth.dependencies import get_current_supplier
from apps.api.config import settings
from apps.api.logging_config import get_logger, setup_logging
from apps.api.routers import (
    admin,
    admin_products,
    auth,
    buyers,
    catalog,
    dictionary,
    health,
    normalization,
    offers,
    orders,
    products,
    publish,
    skus,
    supplier_orders,
    telegram,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    # Security warning: check secret_key in production
    if settings.app_env == "production" and settings.secret_key == "dev-secret-key-change-in-production":
        logger.critical(
            "INSECURE_SECRET_KEY",
            message="Default secret_key detected in production! Set SECRET_KEY in .env immediately.",
        )

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
# Auth guard for all /admin/* endpoints — requires authenticated supplier
_supplier_auth = [Depends(get_current_supplier)]

app.include_router(health.router, tags=["health"])
app.include_router(auth.router)  # /auth/* - authentication endpoints
app.include_router(admin.router, prefix="/admin", tags=["admin"], dependencies=_supplier_auth)
app.include_router(dictionary.router, prefix="/admin/dictionary", tags=["dictionary"], dependencies=_supplier_auth)
app.include_router(skus.router, prefix="/admin/skus", tags=["skus"], dependencies=_supplier_auth)
app.include_router(normalization.router, prefix="/admin/normalization", tags=["normalization"], dependencies=_supplier_auth)
app.include_router(publish.router, prefix="/admin/publish", tags=["publish"], dependencies=_supplier_auth)
app.include_router(buyers.router, tags=["buyers"])  # Buyer management (has own auth)
app.include_router(orders.router, tags=["orders"])  # Retail order endpoints
app.include_router(supplier_orders.router, prefix="/admin", tags=["supplier-orders"], dependencies=_supplier_auth)
app.include_router(offers.router, tags=["offers"])  # No prefix - public endpoint (legacy)
app.include_router(products.router, tags=["products"])  # New public catalog
app.include_router(admin_products.router, prefix="/admin", tags=["admin-products"], dependencies=_supplier_auth)
app.include_router(catalog.router, prefix="/admin/catalog", tags=["catalog"], dependencies=_supplier_auth)
app.include_router(telegram.router)  # Internal Telegram bot API (has own token auth)

# Static file serving for uploaded photos
import os
_uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(os.path.join(_uploads_dir, "photos"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")
