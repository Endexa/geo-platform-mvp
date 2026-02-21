"""
Outbound AI Provider Rate Limiter

In-process rate limiter using asyncio primitives (semaphore + token bucket)
to enforce per-provider RPM and concurrency limits on outbound AI API calls.

Design choices:
- In-process, not Redis-backed. Provides back-pressure within a single worker
  process. Multi-worker coordination can be added later if needed.
- Fails CLOSED: if you cannot acquire the semaphore, the caller blocks
  (back-pressure). If the caller times out, the request fails -- which is
  correct because we'd rather fail than exceed provider limits and get banned.
"""

import asyncio
import time

from app.core.config import settings


class ProviderRateLimiter:
    """Per-provider rate limiter with concurrency cap and RPM pacing."""

    def __init__(self, provider: str, rpm: int, max_concurrent: int):
        self.provider = provider
        self.rpm = rpm
        self.interval = 60.0 / rpm  # seconds between requests
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a slot: blocks until both concurrency and RPM allow it."""
        await self.semaphore.acquire()
        async with self._lock:
            now = time.monotonic()
            wait_time = self._last_request + self.interval - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request = time.monotonic()

    def release(self) -> None:
        """Release the concurrency slot."""
        self.semaphore.release()

    async def __aenter__(self) -> "ProviderRateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *exc) -> None:
        self.release()


# ---------------------------------------------------------------------------
# Module-level registry -- lazily creates one limiter per provider
# ---------------------------------------------------------------------------

_limiters: dict[str, ProviderRateLimiter] = {}


def get_provider_limiter(provider: str) -> ProviderRateLimiter:
    """Return (or create) the rate limiter for *provider*.

    Provider configs come from settings.  Unknown providers get safe defaults
    (60 RPM, 10 concurrent).
    """
    if provider not in _limiters:
        config = {
            "openai": (settings.OPENAI_RPM, settings.OPENAI_MAX_CONCURRENT),
            "anthropic": (settings.ANTHROPIC_RPM, settings.ANTHROPIC_MAX_CONCURRENT),
            "perplexity": (settings.PERPLEXITY_RPM, settings.PERPLEXITY_MAX_CONCURRENT),
        }
        rpm, max_conc = config.get(provider, (60, 10))  # safe defaults
        _limiters[provider] = ProviderRateLimiter(provider, rpm, max_conc)
    return _limiters[provider]
