"""AgentAPIRateLimiter — async semaphore singleton for Perplexity API calls.

Enforces a minimum interval between calls to stay within Perplexity rate limits.

Tier auto-detection via PERPLEXITY_TIER env var:
    unset / 0 → 1 QPS (safe Tier 0 default)
    2         → 8 QPS (Perplexity Tier 2)
    other     → 1 QPS (fallback)

Priority levels (lower number = higher priority):
    1 = seed (intel-company — blocks everything downstream)
    2 = intelligence (Wave 1 spoke modules)
    3 = clusters (deep-research calls)
    4 = synthesis
    5 = background
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from collections.abc import AsyncGenerator

# QPS by tier
_TIER_QPS: dict[str, float] = {
    "0": 1.0,
    "2": 8.0,
}
_DEFAULT_QPS = 1.0


def _qps_from_env() -> float:
    tier = os.environ.get("PERPLEXITY_TIER", "0")
    return _TIER_QPS.get(tier, _DEFAULT_QPS)


class AgentAPIRateLimiter:
    """Singleton async rate limiter for all Agent API (Perplexity) calls.

    Usage::

        limiter = AgentAPIRateLimiter.get_instance()
        async with limiter.acquire(priority=1):
            response = await agent_api.research(...)
    """

    _instance: AgentAPIRateLimiter | None = None

    def __init__(self, qps: float = _DEFAULT_QPS) -> None:
        self.qps = qps
        self._min_interval: float = 1.0 / qps
        self._semaphore = asyncio.Semaphore(1)
        self._last_call_time: float = 0.0
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls, qps: float | None = None) -> AgentAPIRateLimiter:
        """Return the singleton instance, creating it if necessary.

        Args:
            qps: Override QPS. If None, reads PERPLEXITY_TIER env var.
                 Only used when creating a new instance.
        """
        if cls._instance is None:
            effective_qps = qps if qps is not None else _qps_from_env()
            cls._instance = cls(qps=effective_qps)
        return cls._instance

    @contextlib.asynccontextmanager
    async def acquire(self, priority: int = 3) -> AsyncGenerator[None, None]:
        """Async context manager that enforces the per-QPS interval.

        Callers block here until it is safe to make an API call. The
        semaphore ensures only one call is in-flight at a time; the
        minimum-interval check prevents bursting above the QPS limit.

        Args:
            priority: Call priority (1=highest, 5=lowest). Currently stored
                      for future priority-queue implementation; all callers
                      still queue via the semaphore in arrival order.
        """
        async with self._semaphore:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_call_time
                wait = self._min_interval - elapsed
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last_call_time = time.monotonic()
            yield
