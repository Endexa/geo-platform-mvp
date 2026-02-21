"""
AI Response Cache Service

Redis-based caching for AI engine responses. Uses SHA-256 hashing of query
parameters for deterministic cache keys. Fails open on Redis errors -- a Redis
outage should never prevent AI calls from working, it just means no caching.

TTL defaults to 24h (AI_CACHE_TTL_SECONDS in settings).
"""

import hashlib
import json
from typing import Optional

import redis.asyncio as aioredis
from loguru import logger

from app.core.config import settings


class AICacheService:
    """Async Redis cache for AI engine responses."""

    def __init__(self, redis_url: str | None = None):
        self.redis: aioredis.Redis = aioredis.Redis.from_url(
            redis_url or settings.REDIS_URL,
            decode_responses=True,
        )

    def _make_key(
        self,
        engine: str,
        model: str,
        messages: list[dict],
        temperature: float,
    ) -> str:
        """Build a deterministic cache key from query parameters.

        JSON-serialises the parameters with sorted keys, then SHA-256 hashes
        the result.  Returns ``ai_cache:<hex_digest>``.
        """
        payload = json.dumps(
            {
                "engine": engine,
                "model": model,
                "messages": messages,
                "temperature": temperature,
            },
            sort_keys=True,
        )
        digest = hashlib.sha256(payload.encode()).hexdigest()
        return f"ai_cache:{digest}"

    async def get(
        self,
        engine: str,
        model: str,
        messages: list[dict],
        temperature: float = 0.0,
    ) -> Optional[dict]:
        """Look up a cached AI response.

        Returns the cached dict on hit, or ``None`` on miss / Redis error.
        Cache misses are acceptable on Redis outage (fail open).
        """
        key = self._make_key(engine, model, messages, temperature)
        try:
            raw = await self.redis.get(key)
            if raw is not None:
                logger.debug(f"Cache hit: {key[:30]}...")
                return json.loads(raw)
            return None
        except aioredis.RedisError as exc:
            logger.warning(f"Redis read error (failing open): {exc}")
            return None

    async def set(
        self,
        engine: str,
        model: str,
        messages: list[dict],
        temperature: float,
        response: dict,
    ) -> None:
        """Store an AI response in the cache.

        Uses ``setex`` with ``settings.AI_CACHE_TTL_SECONDS`` (default 86400 =
        24 h).  Cache write failures are non-fatal (logged and ignored).
        """
        key = self._make_key(engine, model, messages, temperature)
        try:
            await self.redis.setex(
                key,
                settings.AI_CACHE_TTL_SECONDS,
                json.dumps(response),
            )
            logger.debug(f"Cache set: {key[:30]}... (TTL={settings.AI_CACHE_TTL_SECONDS}s)")
        except aioredis.RedisError as exc:
            logger.warning(f"Redis write error (non-fatal): {exc}")

    async def get_stats(self) -> dict:
        """Return basic cache statistics (key count)."""
        try:
            keys_count = await self.redis.dbsize()
            return {"keys_count": keys_count}
        except aioredis.RedisError as exc:
            logger.warning(f"Redis stats error: {exc}")
            return {"keys_count": -1}

    async def close(self) -> None:
        """Close the Redis connection."""
        await self.redis.aclose()
