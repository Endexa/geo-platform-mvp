from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api import analysis, optimization, brand_voice, dashboard, integrations, geo_datapoints, auth, audit, competitors, recommendations, brands, payments, reports, chat
from app.core.middleware import (
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    AuditLogMiddleware,
    RequestSizeLimitMiddleware,
    SQLInjectionProtectionMiddleware,
    ErrorSanitizationMiddleware,
    APIVersionMiddleware,
)
from loguru import logger
import sys

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL
)
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    compression="zip",
    level=settings.LOG_LEVEL
)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="GEO Platform API for Generative Engine Optimization - Enterprise Security Edition",
    docs_url=f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_PREFIX}/redoc" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
)

# Security Middleware Stack (order matters!)
# 1. Error sanitization (outermost)
app.add_middleware(ErrorSanitizationMiddleware)

# 2. Request size limits
app.add_middleware(RequestSizeLimitMiddleware)

# 3. Security headers
if settings.ENABLE_SECURITY_HEADERS:
    app.add_middleware(SecurityHeadersMiddleware)

# 4. Logging and audit
if settings.ENABLE_AUDIT_LOGGING:
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(AuditLogMiddleware)

# 5. SQL injection protection
app.add_middleware(SQLInjectionProtectionMiddleware)

# 6. API versioning
app.add_middleware(APIVersionMiddleware)

# 7. GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 8. Trusted host (production only)
if settings.ENVIRONMENT == "production":
    allowed_hosts = [origin.replace("https://", "").replace("http://", "") for origin in settings.CORS_ORIGINS]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# 9. CORS (should be last in security stack)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-*"],
    max_age=settings.CORS_MAX_AGE,
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred",
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "type": type(exc).__name__
            }
        )

# Include routers
app.include_router(
    analysis.router,
    prefix=f"{settings.API_V1_PREFIX}/analysis",
    tags=["analysis"]
)
app.include_router(
    optimization.router,
    prefix=f"{settings.API_V1_PREFIX}/optimization",
    tags=["optimization"]
)
app.include_router(
    brand_voice.router,
    prefix=f"{settings.API_V1_PREFIX}/voice",
    tags=["brand-voice"]
)
app.include_router(
    dashboard.router,
    prefix=f"{settings.API_V1_PREFIX}/dashboard",
    tags=["dashboard"]
)
app.include_router(
    integrations.router,
    prefix=f"{settings.API_V1_PREFIX}/integrations",
    tags=["integrations"]
)
app.include_router(
    payments.router,
    prefix=f"{settings.API_V1_PREFIX}/payments",
    tags=["payments"],
)
app.include_router(reports.router, tags=["reports"])
app.include_router(
    geo_datapoints.router,
    prefix=f"{settings.API_V1_PREFIX}/geo-datapoints",
    tags=["geo-datapoints"]
)
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["auth"]
)
app.include_router(
    audit.router,
    prefix=settings.API_V1_PREFIX,
)
app.include_router(competitors.router)
app.include_router(recommendations.router)
app.include_router(brands.router)
app.include_router(chat.router, tags=["chat"])


@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Security features enabled: headers={settings.ENABLE_SECURITY_HEADERS}, audit={settings.ENABLE_AUDIT_LOGGING}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("Shutting down application")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else "disabled",
        "security": {
            "rate_limiting": settings.ENABLE_RATE_LIMITING,
            "audit_logging": settings.ENABLE_AUDIT_LOGGING,
            "security_headers": settings.ENABLE_SECURITY_HEADERS,
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION
    }


@app.get("/security-info")
async def security_info():
    """Security configuration info (for debugging only)"""
    if settings.ENVIRONMENT != "development":
        return {"detail": "Endpoint not available in production"}

    return {
        "rate_limiting": {
            "enabled": settings.ENABLE_RATE_LIMITING,
            "free_tier": settings.RATE_LIMIT_FREE_TIER,
            "pro_tier": settings.RATE_LIMIT_PRO_TIER,
            "enterprise_tier": settings.RATE_LIMIT_ENTERPRISE_TIER,
        },
        "request_limits": {
            "max_request_size": f"{settings.MAX_REQUEST_SIZE / 1024 / 1024}MB",
            "max_upload_size": f"{settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB",
        },
        "password_policy": {
            "min_length": settings.PASSWORD_MIN_LENGTH,
            "require_uppercase": settings.PASSWORD_REQUIRE_UPPERCASE,
            "require_lowercase": settings.PASSWORD_REQUIRE_LOWERCASE,
            "require_digits": settings.PASSWORD_REQUIRE_DIGITS,
            "require_special": settings.PASSWORD_REQUIRE_SPECIAL,
        },
        "features": {
            "api_keys": settings.ENABLE_API_KEYS,
            "webhooks": settings.ENABLE_WEBHOOKS,
            "metrics": settings.ENABLE_METRICS,
        }
    }
