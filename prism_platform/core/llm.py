"""PRISM LLM Client Factory — universal provider abstraction for enrichers.

Every enricher calls `get_instructor_client()` to get an Instructor-wrapped
LLM client. The provider is selected from config (ENRICHER_PROVIDER) or
auto-detected from whichever API key is set.

Supported providers:
  - anthropic: Claude via Anthropic SDK
  - openai: GPT models via OpenAI SDK
  - gemini: Gemini via Google GenAI SDK
  - openrouter: Any model via OpenRouter (OpenAI-compatible API)

Usage in enrichers:
    from prism_platform.core.llm import create_completion

    result = create_completion(
        response_model=MySchema,
        messages=[{"role": "user", "content": prompt}],
    )
"""

from __future__ import annotations

from typing import Any

import instructor
import structlog

from prism_platform.config import settings

logger = structlog.get_logger(__name__)

# Cache the client so we don't re-create on every call
_cached_client: Any | None = None
_cached_provider: str | None = None


def get_instructor_client() -> Any:
    """Get an Instructor-wrapped LLM client for the configured provider.

    Returns a client that supports `client.messages.create(...)` (Anthropic)
    or `client.chat.completions.create(...)` (OpenAI/Gemini/OpenRouter).

    The client is cached for the lifetime of the process.

    Returns:
        Instructor-wrapped client.

    Raises:
        ValueError: If the provider is not supported or API key is missing.
    """
    global _cached_client, _cached_provider

    provider = settings.get_enricher_provider()

    if _cached_client is not None and _cached_provider == provider:
        return _cached_client

    logger.info("Initializing LLM client", provider=provider, model=settings.get_enricher_model())

    if provider == "anthropic":
        _cached_client = _init_anthropic()
    elif provider == "openai":
        _cached_client = _init_openai()
    elif provider == "gemini":
        _cached_client = _init_gemini()
    elif provider == "openrouter":
        _cached_client = _init_openrouter()
    else:
        raise ValueError(f"Unsupported enricher provider: {provider}")

    _cached_provider = provider
    return _cached_client


def get_model_name() -> str:
    """Get the model name for the current provider."""
    return settings.get_enricher_model()


def get_provider_name() -> str:
    """Get the current provider name."""
    return settings.get_enricher_provider()


def is_anthropic() -> bool:
    """Check if the current provider is Anthropic (uses messages.create)."""
    return settings.get_enricher_provider() == "anthropic"


def get_max_tokens() -> int:
    """Get the max_tokens value appropriate for the provider."""
    return 4096


def create_completion(
    response_model: Any,
    messages: list[dict[str, Any]],
    max_retries: int = 3,
    **kwargs: Any,
) -> Any:
    """Universal completion call that works with any provider.

    Handles the API difference between Anthropic (client.messages.create)
    and OpenAI/Gemini/OpenRouter (client.chat.completions.create).

    Args:
        response_model: Pydantic model class for structured output.
        messages: List of message dicts with 'role' and 'content' keys.
        max_retries: Number of Instructor retries on validation failure.
        **kwargs: Additional keyword arguments passed to the create call.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ValueError: If the provider is not supported or API key is missing.
        instructor.exceptions.InstructorRetryException: After exhausting retries.
    """
    client = get_instructor_client()
    model = get_model_name()

    if is_anthropic():
        return client.messages.create(
            model=model,
            max_tokens=get_max_tokens(),
            response_model=response_model,
            max_retries=max_retries,
            messages=messages,
            **kwargs,
        )
    else:
        return client.chat.completions.create(
            model=model,
            response_model=response_model,
            max_retries=max_retries,
            messages=messages,
            **kwargs,
        )


def _init_anthropic() -> Any:
    """Initialize Anthropic Claude via Instructor."""
    from anthropic import Anthropic

    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    client = Anthropic(api_key=settings.anthropic_api_key)
    wrapped = instructor.from_anthropic(client)
    logger.info("Anthropic client initialized", model=settings.get_enricher_model())
    return wrapped


def _init_openai() -> Any:
    """Initialize OpenAI via Instructor."""
    from openai import OpenAI

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=settings.openai_api_key)
    wrapped = instructor.from_openai(client)
    logger.info("OpenAI client initialized", model=settings.get_enricher_model())
    return wrapped


def _init_gemini() -> Any:
    """Initialize Google Gemini via Instructor."""
    from google import genai

    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    genai_client = genai.Client(api_key=settings.gemini_api_key)
    wrapped = instructor.from_genai(client=genai_client)
    logger.info("Gemini client initialized", model=settings.get_enricher_model())
    return wrapped


def _init_openrouter() -> Any:
    """Initialize OpenRouter via Instructor (OpenAI-compatible API)."""
    from openai import OpenAI

    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not set")

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    wrapped = instructor.from_openai(client)
    logger.info("OpenRouter client initialized", model=settings.get_enricher_model())
    return wrapped
