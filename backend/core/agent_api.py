"""AgentAPIClient — thin wrapper around Perplexity's chat completions API.

Supports two presets:
- pro-search (sonar-pro): fast, single-step research for seed phase
- deep-research (sonar-deep-research): multi-step autonomous research for clusters

Returns structured AgentAPIResponse with content, citations, and usage metadata.
"""

from __future__ import annotations

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

COST_TIER_MODELS = {
    "pro-search": "sonar-pro",
    "deep-research": "sonar-deep-research",
}


class AgentAPIResponse(BaseModel):
    """Parsed response from a Perplexity API call."""

    model_config = ConfigDict(frozen=True)

    content: str = Field(description="Response text (JSON or free-form)")
    citations: list[str] = Field(default_factory=list, description="Citation URLs from Perplexity")
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0


class AgentAPIClient:
    """Perplexity API client for research calls.

    Args:
        api_key: Perplexity API key.
        timeout: Request timeout in seconds.
    """

    #: Provider label, so callers can log which backend actually ran without
    #: re-deriving it from settings (which can raise).
    provider = "perplexity"

    def __init__(self, api_key: str, timeout: float = 120.0) -> None:
        self._api_key = api_key
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def research(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "sonar-pro",
        temperature: float = 0.1,
        max_tokens: int = 8192,
    ) -> AgentAPIResponse:
        """Execute a research call against the Perplexity API.

        Args:
            system_prompt: System message (agent identity + constraints).
            user_prompt: User message (resolved playbook content).
            model: Perplexity model ID (sonar-pro, sonar-deep-research).
            temperature: Sampling temperature. Low for factual research.
            max_tokens: Maximum response tokens.

        Returns:
            AgentAPIResponse with content, citations, and usage.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses.
            ValueError: If Perplexity returns no choices.
        """
        logger.info(
            "AgentAPI research call",
            model=model,
            system_len=len(system_prompt),
            user_len=len(user_prompt),
        )

        resp = await self._http.post(
            PERPLEXITY_API_URL,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "return_citations": True,
            },
        )
        resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices returned from Perplexity API")

        content = choices[0].get("message", {}).get("content", "")
        content = self._strip_code_fences(content)

        citations = data.get("citations", [])
        usage = data.get("usage", {})

        logger.info(
            "AgentAPI response received",
            model=model,
            content_len=len(content),
            citation_count=len(citations),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )

        return AgentAPIResponse(
            content=content,
            citations=citations,
            usage_input_tokens=usage.get("prompt_tokens", 0),
            usage_output_tokens=usage.get("completion_tokens", 0),
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        """Strip markdown code fences if Perplexity wraps JSON in ```json ... ```."""
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            return "\n".join(lines)
        return content
