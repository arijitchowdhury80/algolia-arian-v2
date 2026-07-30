"""SynthesisClient — Track 3 reconciliation engine.

Takes raw data from Track 1 (WebFetch) and Track 2 (Perplexity),
sends it to the enricher LLM (Gemini by default) with the synthesis
playbook, and returns reconciled structured output.

The synthesis LLM does NOT search the web — it only reconciles
data that was already gathered. This makes it cheap and fast.

Supports: Gemini (via google-genai), with fallback architecture for
Anthropic/OpenAI if needed later.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import structlog
from google import genai
from pydantic import BaseModel

from core.config import settings

logger = structlog.get_logger(__name__)


class SynthesisResult(BaseModel):
    """Result from the synthesis step."""

    status: str  # "success" or "failed"
    output: dict[str, Any] | None = None
    raw_response: str = ""
    duration_ms: int = 0
    model_used: str = ""
    error: str | None = None


class SynthesisClient:
    """Calls the enricher LLM to reconcile Track 1 + Track 2 outputs.

    Uses the provider configured in settings (ENRICHER_PROVIDER / ENRICHER_MODEL).
    Defaults to Gemini gemini-3.1-flash-lite-preview if GEMINI_API_KEY is set.
    """

    def __init__(self) -> None:
        self._provider: str | None = None
        self._model: str | None = None

    def _resolve_provider(self) -> tuple[str, str]:
        if self._provider is None:
            self._provider = settings.get_enricher_provider()
            self._model = settings.get_enricher_model()
            logger.info(
                "SynthesisClient initialized",
                provider=self._provider,
                model=self._model,
            )
        return self._provider, self._model  # type: ignore[return-value]

    async def synthesize(
        self,
        playbook_path: Path,
        template_vars: dict[str, str],
        output_schema: type[BaseModel],
    ) -> SynthesisResult:
        """Run the synthesis playbook through the enricher LLM.

        Args:
            playbook_path: Path to the synthesis playbook markdown file.
            template_vars: Variables to resolve in the playbook template
                           (e.g., upstream_leadership_page, upstream_perplexity_output).
            output_schema: Pydantic model for the expected output (used in system prompt).

        Returns:
            SynthesisResult with reconciled output or error.
        """
        provider, model = self._resolve_provider()
        start = time.monotonic()

        # Load and resolve the playbook
        raw_playbook = playbook_path.read_text(encoding="utf-8")

        # Strip YAML frontmatter
        if raw_playbook.startswith("---"):
            parts = raw_playbook.split("---", 2)
            if len(parts) >= 3:
                raw_playbook = parts[2].strip()

        # Resolve template variables
        resolved = raw_playbook
        for key, value in template_vars.items():
            placeholder = "{" + key + "}"
            resolved = resolved.replace(placeholder, value or "(no data available)")

        # Build system prompt with schema
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        system_prompt = (
            "You are a data reconciliation engine for PRISM, an enterprise prospect intelligence platform. "
            "You merge data from multiple sources into a single verified output. "
            "Return ONLY a valid JSON object matching this schema — no markdown, no commentary.\n\n"
            f"Output schema:\n```json\n{schema_json}\n```"
        )

        try:
            if provider == "gemini":
                return await self._call_gemini(system_prompt, resolved, start)
            else:
                # Fallback: use Perplexity (wasteful but works)
                return await self._call_perplexity(system_prompt, resolved, start)

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("Synthesis failed", error=str(exc), provider=provider)
            return SynthesisResult(
                status="failed",
                duration_ms=duration_ms,
                model_used=model,
                error=str(exc),
            )

    async def _call_gemini(
        self, system_prompt: str, user_prompt: str, start: float
    ) -> SynthesisResult:
        """Call Gemini via google-genai SDK."""
        client = genai.Client(api_key=settings.gemini_api_key)

        response = await client.aio.models.generate_content(
            model=self._model,
            contents=f"{system_prompt}\n\n---\n\n{user_prompt}",
            config={
                "temperature": 0.1,
                "max_output_tokens": 8192,
            },
        )

        duration_ms = int((time.monotonic() - start) * 1000)
        raw_text = response.text or ""
        raw_text = self._strip_code_fences(raw_text)

        logger.info(
            "Gemini synthesis response",
            model=self._model,
            response_len=len(raw_text),
            duration_ms=duration_ms,
        )

        # Parse JSON
        try:
            output = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.error("Synthesis JSON parse failed", error=str(exc), raw=raw_text[:500])
            return SynthesisResult(
                status="failed",
                raw_response=raw_text,
                duration_ms=duration_ms,
                model_used=self._model,
                error=f"JSON parse error: {exc}",
            )

        return SynthesisResult(
            status="success",
            output=output,
            raw_response=raw_text,
            duration_ms=duration_ms,
            model_used=self._model,
        )

    async def _call_perplexity(
        self, system_prompt: str, user_prompt: str, start: float
    ) -> SynthesisResult:
        """Fallback: call Perplexity for synthesis (not ideal — it will search the web)."""
        from core.agent_api import AgentAPIClient

        api = AgentAPIClient(
            api_key=settings.perplexity_api_key,
            timeout=120.0,
        )

        try:
            response = await api.research(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="sonar",  # Cheapest model for synthesis
                temperature=0.1,
            )
        finally:
            await api.close()

        duration_ms = int((time.monotonic() - start) * 1000)
        raw_text = response.content

        try:
            output = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return SynthesisResult(
                status="failed",
                raw_response=raw_text,
                duration_ms=duration_ms,
                model_used="sonar",
                error=f"JSON parse error: {exc}",
            )

        return SynthesisResult(
            status="success",
            output=output,
            raw_response=raw_text,
            duration_ms=duration_ms,
            model_used="sonar",
        )

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        """Strip markdown code fences if LLM wraps JSON in ```json ... ```."""
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            return "\n".join(lines)
        return content
