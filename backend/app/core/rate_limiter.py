from fastapi import HTTPException, Request, status
from typing import Optional
import redis
import time
from app.core.config import settings
from loguru import logger


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"

# Redis connection
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class RateLimiter:
    """Advanced rate limiter with multiple strategies"""

    def __init__(
        self,
        requests: int = 100,
        window: int = 60,
        identifier: str = "ip"
    ):
        """
        Initialize rate limiter

        Args:
            requests: Number of requests allowed
            window: Time window in seconds
            identifier: What to use for rate limiting ('ip', 'user', 'api_key')
        """
        self.requests = requests
        self.window = window
        self.identifier = identifier

    async def __call__(self, request: Request):
        """Check rate limit"""

        # Determine identifier
        if self.identifier == "ip":
            key = f"rate_limit:ip:{_client_ip(request)}"
        elif self.identifier == "user":
            # Extract user ID from token if present
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                # You would decode token here to get user_id
                key = f"rate_limit:user:{token[:20]}"  # Using token prefix
            else:
                key = f"rate_limit:ip:{_client_ip(request)}"
        elif self.identifier == "api_key":
            api_key = request.headers.get("X-API-Key", "")
            key = f"rate_limit:api:{api_key[:20]}"
        else:
            key = f"rate_limit:global:{_client_ip(request)}"

        try:
            # Sliding window counter
            current_time = int(time.time())
            window_key = f"{key}:{current_time // self.window}"

            # Get current count
            current_count = redis_client.get(window_key)

            if current_count is None:
                # First request in this window
                redis_client.setex(window_key, self.window, 1)
                remaining = self.requests - 1
            else:
                current_count = int(current_count)

                if current_count >= self.requests:
                    # Rate limit exceeded
                    logger.warning(
                        f"Rate limit exceeded for {key}. "
                        f"Count: {current_count}/{self.requests}"
                    )

                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "Rate limit exceeded",
                            "retry_after": self.window,
                            "limit": self.requests,
                            "window": self.window
                        }
                    )

                # Increment counter
                redis_client.incr(window_key)
                remaining = self.requests - current_count - 1

            # Add rate limit headers to response
            request.state.rate_limit_limit = self.requests
            request.state.rate_limit_remaining = remaining
            request.state.rate_limit_reset = (current_time // self.window + 1) * self.window

        except redis.RedisError as e:
            # If Redis is down, log error but don't block requests
            logger.error(f"Redis error in rate limiter: {str(e)}")
            # In production, you might want to fail closed (block requests)


class TierBasedRateLimiter:
    """Rate limiter that varies limits based on subscription tier"""

    TIER_LIMITS = {
        "free": {"requests": 10, "window": 60},      # 10 req/min
        "pro": {"requests": 100, "window": 60},       # 100 req/min
        "enterprise": {"requests": 1000, "window": 60}  # 1000 req/min
    }

    async def __call__(self, request: Request):
        """Apply tier-based rate limiting"""

        # Extract user tier (you would get this from authenticated user)
        # For now, default to free tier
        tier = getattr(request.state, "user_tier", "free")

        limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["free"])

        limiter = RateLimiter(
            requests=limits["requests"],
            window=limits["window"],
            identifier="user"
        )

        await limiter(request)


class IPRateLimiter:
    """Aggressive rate limiter for suspicious IPs"""

    BLOCKED_IPS = set()  # In production, use Redis Set

    async def __call__(self, request: Request):
        """Check if IP is blocked or exceeding global limits"""

        ip = _client_ip(request)

        # Check if IP is blocked
        if ip in self.BLOCKED_IPS:
            logger.warning(f"Blocked IP attempted access: {ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Apply aggressive global limit
        key = f"ip_limiter:{ip}"

        try:
            # Allow 1000 requests per hour
            count = redis_client.get(key)

            if count is None:
                redis_client.setex(key, 3600, 1)
            else:
                count = int(count)
                if count >= 1000:
                    logger.warning(f"IP {ip} exceeded global limit: {count} requests")
                    # Auto-block after sustained abuse
                    if count >= 2000:
                        self.BLOCKED_IPS.add(ip)
                        logger.error(f"IP {ip} auto-blocked due to abuse")

                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests from this IP"
                    )

                redis_client.incr(key)

        except redis.RedisError:
            # Fail open if Redis is down
            pass


class EndpointRateLimiter:
    """Rate limiter for specific expensive endpoints"""

    def __init__(self, requests: int = 5, window: int = 300):
        """
        Args:
            requests: Number of requests allowed (default: 5)
            window: Time window in seconds (default: 5 minutes)
        """
        self.requests = requests
        self.window = window

    async def __call__(self, request: Request):
        """Apply endpoint-specific rate limit"""

        endpoint = request.url.path
        identifier = _client_ip(request)

        key = f"endpoint_limit:{endpoint}:{identifier}"

        try:
            count = redis_client.get(key)

            if count is None:
                redis_client.setex(key, self.window, 1)
            else:
                count = int(count)
                if count >= self.requests:
                    logger.warning(
                        f"Endpoint rate limit exceeded: {endpoint} by {identifier}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded for this endpoint. Try again in {self.window} seconds."
                    )

                redis_client.incr(key)

        except redis.RedisError as e:
            logger.error(f"Redis error: {str(e)}")


# Pre-configured rate limiters for common use cases
standard_rate_limit = RateLimiter(requests=100, window=60, identifier="ip")
strict_rate_limit = RateLimiter(requests=10, window=60, identifier="ip")
analysis_rate_limit = EndpointRateLimiter(requests=3, window=300)  # 3 analyses per 5 min
optimization_rate_limit = EndpointRateLimiter(requests=10, window=60)  # 10 optimizations per min
upload_rate_limit = EndpointRateLimiter(requests=5, window=3600)  # 5 uploads per hour
integration_rate_limit = EndpointRateLimiter(requests=20, window=60)  # 20 integrations per min
