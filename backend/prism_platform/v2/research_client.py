"""Research-client factory — the one place the research provider is decided.

Before this module, all six call sites built ``AgentAPIClient`` (Perplexity)
directly. The provider was therefore hardcoded per site, ``ENRICHER_PROVIDER``
had no effect on module execution, and a dead Perplexity key took the entire
v2 pipeline down with no switch to flip. ``GeminiResearchClient`` already
existed as a drop-in but was wired nowhere.

Design rules:
- ``RESEARCH_PROVIDER`` selects the backend. It is deliberately separate from
  ``ENRICHER_PROVIDER`` (which governs synthesis/enrichment) so that setting a
  synthesis-only provider such as ``anthropic`` can never silently route
  grounded research to Perplexity — the exact bug this replaces.
- Unset means auto-detect, preferring Gemini: its Google-Search grounding is the
  cheaper equivalent of Perplexity's online search and the key is the one the
  rest of the stack already runs on.
- An unsupported or keyless selection raises. Silent fallback is what hid the
  original failure for weeks.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import structlog

from prism_platform.config import settings as default_settings
from prism_platform.v2.agent_api import AgentAPIClient, AgentAPIResponse
from prism_platform.v2.gemini_api import DEFAULT_GEMINI_MODEL, GeminiResearchClient

logger = structlog.get_logger(__name__)

#: Providers that can serve grounded web research (search + citations).
#: Chat-only providers are excluded on purpose — see the module docstring.
SUPPORTED_RESEARCH_PROVIDERS = ("gemini", "perplexity")

_KEY_ATTR = {"gemini": "gemini_api_key", "perplexity": "perplexity_api_key"}
_KEY_ENV = {"gemini": "GEMINI_API_KEY", "perplexity": "PERPLEXITY_API_KEY"}


class ResearchProviderError(RuntimeError):
    """Raised when no usable research provider can be resolved."""


@runtime_checkable
class ResearchClient(Protocol):
    """The contract ModuleExecutor depends on. Both backends satisfy it."""

    #: Which backend this is, for logging without re-deriving from settings.
    provider: str

    async def research(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = ...,
        temperature: float = ...,
        max_tokens: int = ...,
    ) -> AgentAPIResponse:  # pragma: no cover - structural type
        ...

    async def close(self) -> None:  # pragma: no cover - structural type
        ...


class ResearchSettings(Protocol):
    """The slice of Settings this module reads. Lets tests pass a stub."""

    research_provider: str
    gemini_api_key: str
    gemini_model: str
    perplexity_api_key: str


def _has_key(settings_obj: ResearchSettings, provider: str) -> bool:
    return bool(getattr(settings_obj, _KEY_ATTR[provider], "") or "")


def resolve_research_provider(settings_obj: ResearchSettings | None = None) -> str:
    """Decide which research backend to use.

    Args:
        settings_obj: Settings-like object exposing ``research_provider``,
            ``gemini_api_key`` and ``perplexity_api_key``. Defaults to the
            application settings.

    Returns:
        Either ``"gemini"`` or ``"perplexity"``.

    Raises:
        ResearchProviderError: if the explicit selection is unsupported, the
            selected provider has no key, or no provider has a key at all.
    """
    cfg = default_settings if settings_obj is None else settings_obj
    explicit = (getattr(cfg, "research_provider", "") or "").strip().lower()

    if explicit:
        if explicit not in SUPPORTED_RESEARCH_PROVIDERS:
            raise ResearchProviderError(
                f"RESEARCH_PROVIDER={explicit!r} cannot serve grounded research. "
                f"Supported: {', '.join(SUPPORTED_RESEARCH_PROVIDERS)}."
            )
        if not _has_key(cfg, explicit):
            raise ResearchProviderError(
                f"RESEARCH_PROVIDER={explicit!r} selected but {_KEY_ENV[explicit]} is not set."
            )
        return explicit

    for provider in SUPPORTED_RESEARCH_PROVIDERS:
        if _has_key(cfg, provider):
            return provider

    raise ResearchProviderError(
        "no research provider available — set GEMINI_API_KEY or PERPLEXITY_API_KEY."
    )


def make_research_client(
    timeout: float = 120.0, settings_obj: ResearchSettings | None = None
) -> ResearchClient:
    """Build the research client for the configured provider.

    Args:
        timeout: Per-request timeout in seconds. Callers pass the module's own
            ``config.timeout_seconds``.
        settings_obj: Settings-like override, for tests.

    Returns:
        A client satisfying :class:`ResearchClient`.

    Raises:
        ResearchProviderError: propagated from :func:`resolve_research_provider`.
    """
    cfg = default_settings if settings_obj is None else settings_obj
    provider = resolve_research_provider(cfg)

    if provider == "gemini":
        model = getattr(cfg, "gemini_model", "") or DEFAULT_GEMINI_MODEL
        logger.info("research client resolved", provider=provider, model=model)
        return GeminiResearchClient(api_key=cfg.gemini_api_key, model=model, timeout=timeout)

    logger.info("research client resolved", provider=provider)
    return AgentAPIClient(api_key=cfg.perplexity_api_key, timeout=timeout)
