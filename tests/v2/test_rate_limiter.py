"""Tests for AgentAPIRateLimiter — async semaphore singleton.

RED → GREEN cycle: tests are written before implementation.
"""

from __future__ import annotations

import os
import time
from unittest.mock import patch

import pytest

from prism_platform.v2.rate_limiter import AgentAPIRateLimiter

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    """Reset singleton between tests so state doesn't leak."""
    AgentAPIRateLimiter._instance = None
    yield
    AgentAPIRateLimiter._instance = None


# ---------------------------------------------------------------------------
# Singleton behaviour
# ---------------------------------------------------------------------------


def test_singleton_returns_same_instance() -> None:
    """get_instance() always returns the same object."""
    a = AgentAPIRateLimiter.get_instance()
    b = AgentAPIRateLimiter.get_instance()
    assert a is b


def test_singleton_reset_returns_fresh_instance() -> None:
    """After reset, get_instance() returns a new object."""
    first = AgentAPIRateLimiter.get_instance()
    AgentAPIRateLimiter._instance = None
    second = AgentAPIRateLimiter.get_instance()
    assert first is not second


# ---------------------------------------------------------------------------
# QPS configuration
# ---------------------------------------------------------------------------


def test_default_qps_is_one() -> None:
    """Without env var, limiter defaults to 1 QPS (Tier 0 safety default)."""
    with patch.dict(os.environ, {}, clear=True):
        AgentAPIRateLimiter._instance = None
        limiter = AgentAPIRateLimiter.get_instance()
    assert limiter.qps == 1.0


def test_tier2_env_var_sets_eight_qps() -> None:
    """PERPLEXITY_TIER=2 sets QPS to 8."""
    with patch.dict(os.environ, {"PERPLEXITY_TIER": "2"}):
        AgentAPIRateLimiter._instance = None
        limiter = AgentAPIRateLimiter.get_instance()
    assert limiter.qps == 8.0


def test_unknown_tier_falls_back_to_one_qps() -> None:
    """Unknown PERPLEXITY_TIER value falls back to 1 QPS."""
    with patch.dict(os.environ, {"PERPLEXITY_TIER": "99"}):
        AgentAPIRateLimiter._instance = None
        limiter = AgentAPIRateLimiter.get_instance()
    assert limiter.qps == 1.0


# ---------------------------------------------------------------------------
# Acquire / release
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acquire_returns_without_error() -> None:
    """acquire() completes normally and releases the semaphore."""
    limiter = AgentAPIRateLimiter.get_instance()
    async with limiter.acquire():
        pass  # Should not raise


@pytest.mark.asyncio
async def test_acquire_is_reentrant_sequentially() -> None:
    """Two sequential acquire() calls both complete successfully."""
    limiter = AgentAPIRateLimiter.get_instance(qps=100.0)  # high QPS so no real delay
    results: list[int] = []

    async with limiter.acquire():
        results.append(1)

    async with limiter.acquire():
        results.append(2)

    assert results == [1, 2]


@pytest.mark.asyncio
async def test_rate_limiter_enforces_minimum_interval() -> None:
    """Two calls back-to-back take at least 1/QPS seconds apart."""
    limiter = AgentAPIRateLimiter.get_instance(qps=10.0)  # 100ms min interval
    times: list[float] = []

    async def make_call() -> None:
        async with limiter.acquire():
            times.append(time.monotonic())

    # Run two calls back to back
    await make_call()
    await make_call()

    assert len(times) == 2
    gap = times[1] - times[0]
    # Should be at least 90ms (100ms - 10ms tolerance)
    assert gap >= 0.09, f"Gap was only {gap:.3f}s, expected >= 0.09s"


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acquire_accepts_priority_arg() -> None:
    """acquire() accepts an optional priority argument without error."""
    limiter = AgentAPIRateLimiter.get_instance()
    async with limiter.acquire(priority=1):
        pass
    async with limiter.acquire(priority=5):
        pass
