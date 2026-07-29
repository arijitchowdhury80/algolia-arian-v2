"""GeminiResearchClient — Gemini + Google-Search grounding research backend.

Drop-in alternative to AgentAPIClient (same ``research(...) -> AgentAPIResponse``
contract, reuses AgentAPIResponse) so ModuleExecutor can swap Perplexity →
Gemini without changing executor or playbooks. Chosen over Perplexity because
the VPS already has a paid/working Gemini key (Cass runs on it) and one provider
unifies the stack + the self-learning loop.

Read receipt (Google docs, 2026-06-29 —
ai.google.dev/gemini-api/docs/generate-content/google-search):
  endpoint: POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}
  request:  {"system_instruction": {"parts":[{"text": ...}]},
             "contents": [{"role":"user","parts":[{"text": ...}]}],
             "tools": [{"google_search": {}}],            # snake_case, verified verbatim
             "generationConfig": {"temperature": ..., "maxOutputTokens": ...}}
  response: candidates[0].content.parts[].text                         -> answer
            candidates[0].groundingMetadata.groundingChunks[].web.uri  -> citation URLs
            candidates[0].groundingMetadata.webSearchQueries           -> queries
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from prism_platform.v2.agent_api import AgentAPIResponse

logger = structlog.get_logger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class GeminiResearchClient:
    """Gemini generateContent client with Google-Search grounding.

    Mirrors AgentAPIClient so it is a drop-in research backend for ModuleExecutor.

    Args:
        api_key: Gemini (Google AI Studio) API key.
        model: Default Gemini model; used when the caller passes a non-Gemini
            model name (the executor passes Perplexity names like ``sonar-pro``).
        timeout: Request timeout in seconds.
    """

    #: Provider label, matching AgentAPIClient.provider so either backend can be
    #: logged without re-deriving the choice from settings.
    provider = "gemini"

    def __init__(
        self, api_key: str, model: str = DEFAULT_GEMINI_MODEL, timeout: float = 120.0
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._http = httpx.AsyncClient(
            timeout=timeout, headers={"Content-Type": "application/json"}
        )

    def _resolve_model(self, model: str) -> str:
        """Pass Gemini model names through; map anything else to the default.

        The executor supplies Perplexity model ids (``sonar-pro``) from its
        cost-tier map — those must never be forwarded to Gemini.
        """
        return model if model.startswith("gemini") else self._model

    @staticmethod
    def _build_payload(
        system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ) -> dict[str, Any]:
        """Build the generateContent request body with Google-Search grounding."""
        return {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        """Strip ```json ... ``` fences Gemini sometimes wraps JSON in."""
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            return "\n".join(lines)
        return content

    @classmethod
    def _parse_response(cls, data: dict[str, Any]) -> AgentAPIResponse:
        """Map a generateContent grounding response to AgentAPIResponse.

        Raises:
            ValueError: when the response carries no candidates.
        """
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned from Gemini API")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        content = "".join(p.get("text", "") for p in parts)
        content = cls._strip_code_fences(content)

        grounding = candidate.get("groundingMetadata", {}) or {}
        chunks = grounding.get("groundingChunks", []) or []
        citations = [
            c["web"]["uri"]
            for c in chunks
            if isinstance(c.get("web"), dict) and c["web"].get("uri")
        ]

        usage = data.get("usageMetadata", {}) or {}
        return AgentAPIResponse(
            content=content,
            citations=citations,
            usage_input_tokens=usage.get("promptTokenCount", 0),
            usage_output_tokens=usage.get("candidatesTokenCount", 0),
        )

    async def research(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "",
        temperature: float = 0.1,
        max_tokens: int = 8192,
    ) -> AgentAPIResponse:
        """Execute a grounded research call against Gemini generateContent.

        Args mirror AgentAPIClient.research so this is a drop-in backend.

        Raises:
            httpx.HTTPStatusError: on 4xx/5xx.
            ValueError: if Gemini returns no candidates.
        """
        resolved = self._resolve_model(model)
        url = f"{GEMINI_API_BASE}/{resolved}:generateContent?key={self._api_key}"
        payload = self._build_payload(system_prompt, user_prompt, temperature, max_tokens)

        logger.info(
            "GeminiResearch call",
            model=resolved,
            system_len=len(system_prompt),
            user_len=len(user_prompt),
        )
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()

        parsed = self._parse_response(resp.json())
        logger.info(
            "GeminiResearch response",
            model=resolved,
            content_len=len(parsed.content),
            citation_count=len(parsed.citations),
        )
        return parsed

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
