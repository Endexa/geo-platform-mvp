from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Callable
import time
import uuid
from loguru import logger
from app.core.config import settings
import json


def _client_ip(request: Request) -> str:
    """Safely get client IP, returning 'unknown' when request.client is None (e.g. in tests)."""
    return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.openai.com; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=()"
        )

        # Remove server header
        if "Server" in response.headers:
            del response.headers["Server"]

        # Add rate limit headers if present
        if hasattr(request.state, "rate_limit_limit"):
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
            response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
            response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests for audit purposes"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": _client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
            }
        )

        # Time the request
        start_time = time.time()

        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            raise


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Detailed audit logging for security-sensitive operations"""

    SENSITIVE_ENDPOINTS = [
        "/api/v1/analysis/analyze",
        "/api/v1/voice/config",
        "/api/v1/integrations/",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is a sensitive endpoint
        is_sensitive = any(
            request.url.path.startswith(endpoint)
            for endpoint in self.SENSITIVE_ENDPOINTS
        )

        if is_sensitive:
            # Log detailed audit information
            audit_data = {
                "timestamp": time.time(),
                "request_id": getattr(request.state, "request_id", "unknown"),
                "method": request.method,
                "path": request.url.path,
                "client_ip": _client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
                "user_id": getattr(request.state, "user_id", "anonymous"),
            }

            logger.info(f"Audit log: {json.dumps(audit_data)}")

        response = await call_next(request)
        return response


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Restrict access to specific IPs (for admin endpoints)"""

    ADMIN_ENDPOINTS = [
        "/api/v1/admin",
    ]

    WHITELISTED_IPS = set(getattr(settings, "WHITELISTED_IPS", []))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is an admin endpoint
        is_admin = any(
            request.url.path.startswith(endpoint)
            for endpoint in self.ADMIN_ENDPOINTS
        )

        if is_admin and self.WHITELISTED_IPS:
            client_ip = _client_ip(request)

            if client_ip not in self.WHITELISTED_IPS:
                logger.warning(f"Unauthorized admin access attempt from {client_ip}")

                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied"}
                )

        response = await call_next(request)
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent memory exhaustion"""

    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")

        if content_length:
            content_length = int(content_length)

            if content_length > self.MAX_REQUEST_SIZE:
                logger.warning(
                    f"Request too large: {content_length} bytes from {_client_ip(request)}"
                )

                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request too large. Maximum size: {self.MAX_REQUEST_SIZE / 1024 / 1024}MB"
                    }
                )

        response = await call_next(request)
        return response


class SQLInjectionProtectionMiddleware(BaseHTTPMiddleware):
    """Detect potential SQL injection attempts in query parameters"""

    SQL_KEYWORDS = [
        "union", "select", "insert", "update", "delete", "drop",
        "create", "alter", "exec", "execute", "script", "javascript"
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check query parameters
        query_string = str(request.url.query).lower()

        for keyword in self.SQL_KEYWORDS:
            if keyword in query_string:
                logger.warning(
                    f"Potential SQL injection detected in query: {query_string} "
                    f"from {_client_ip(request)}"
                )

                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request"}
                )

        response = await call_next(request)
        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS validation"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin")

        # Validate origin against whitelist
        if origin and origin not in settings.CORS_ORIGINS:
            # Log suspicious origin
            logger.warning(f"Request from unauthorized origin: {origin}")

        response = await call_next(request)
        return response


class ErrorSanitizationMiddleware(BaseHTTPMiddleware):
    """Sanitize error messages to prevent information disclosure"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response

        except Exception as e:
            # Log the full error internally
            logger.error(
                f"Unhandled exception",
                extra={
                    "error": str(e),
                    "type": type(e).__name__,
                    "path": request.url.path
                }
            )

            # Return sanitized error to client
            if settings.ENVIRONMENT == "production":
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "An internal error occurred",
                        "request_id": getattr(request.state, "request_id", "unknown")
                    }
                )
            else:
                # In development, show more details
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Internal server error",
                        "error": str(e),
                        "type": type(e).__name__
                    }
                )


class APIVersionMiddleware(BaseHTTPMiddleware):
    """API versioning and deprecation warnings"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check API version
        if "/api/v1/" not in request.url.path and request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid API version. Use /api/v1/"}
            )

        response = await call_next(request)

        # Add API version to response
        response.headers["X-API-Version"] = "1.0"

        return response
