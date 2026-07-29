"""ModuleExecutor — the generic harness that runs any v2 module.

Execution flow:
1. Load and resolve playbook (replace {domain}, {company_name}, etc.)
2. Build system prompt from ModuleConfig
3. Call AgentAPIClient with resolved playbook as user prompt
4. Parse JSON response
5. Validate against Pydantic output schema
6. Generate claim registry entries
7. Return ModuleExecutorResult

The executor does NOT know what any module researches. It follows
config (which constraints), playbook (what instructions), and
schema (what shape). Pure plumbing.

Execution strategies (Decision 3 — Phase 2):
- prospect-only: single call for the prospect domain
- comparative:   single call with all companies in context (for gap analysis)
- per-company:   fan-out — one call per company (prospect + each competitor)
"""

from __future__ import annotations

import json
import time
from copy import copy
from pathlib import Path
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from prism_platform.v2.agent_api import AgentAPIResponse
from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.research_client import ResearchClient
from prism_platform.v2.types import ClaimRegistryEntry, ExecutionContextV2, ModuleConfig

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def _loads_tolerant(content: str) -> Any:
    """Parse model-produced JSON, allowing raw control characters in strings.

    LLMs routinely emit literal newlines and tabs inside string values. Strict
    ``json.loads`` rejects those even though the payload is otherwise valid, and
    which provider escapes them is an implementation detail we do not control.
    ``strict=False`` accepts them; genuine syntax errors still raise.
    """
    return json.loads(content, strict=False)


class ModuleExecutorResult(BaseModel):
    """Standard return type from the ModuleExecutor."""

    model_config = ConfigDict(extra="forbid")

    module_name: str
    module_version: str
    status: str  # "success", "partial", "failed"
    output: dict[str, Any] = Field(default_factory=dict)
    claims: list[ClaimRegistryEntry] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ModuleExecutor:
    """Generic harness that runs any v2 module.

    Args:
        agent_api: Any research backend satisfying the ResearchClient contract
            (Gemini or Perplexity). Build it with ``make_research_client()``
            rather than constructing a provider directly.
    """

    def __init__(self, agent_api: ResearchClient) -> None:
        self._api = agent_api
        self._playbook_loader = PlaybookLoader()

    @staticmethod
    def _usability(response: AgentAPIResponse, requires_citations: bool) -> int:
        """Rank a response so the better of two attempts can be picked.

        2 = parseable and sourced, 1 = parseable but unsourced, 0 = unusable
        (no content, or content that is not valid JSON). When citations are not
        required, any parseable content ranks as fully usable.

        Unparseable JSON counts as unusable because it is just as intermittent as
        an empty answer: across three live runs a different set of modules failed
        with mid-document JSON errors each time, and the same prompts parsed
        cleanly on a later call.
        """
        if not response.content.strip():
            return 0
        try:
            _loads_tolerant(response.content)
        except json.JSONDecodeError:
            return 0
        if not requires_citations or response.citations:
            return 2
        return 1

    async def _research_with_retry(
        self,
        config: ModuleConfig,
        context: ExecutionContextV2,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[AgentAPIResponse, int]:
        """Call the backend, retrying once if the first answer is not fully usable.

        Returns the better of the attempts and the number of calls made. Picking
        the better one matters: an empty or unsourced first attempt must not be
        kept over a usable retry.
        """
        model = self._model_for_tier(config.cost_tier)
        first = await self._api.research(
            system_prompt=system_prompt, user_prompt=user_prompt, model=model
        )
        first_rank = self._usability(first, config.requires_citations)
        if first_rank == 2:
            return first, 1

        logger.warning(
            "research answer not fully usable — retrying once",
            module=config.name,
            domain=context.account_domain,
            had_content=bool(first.content.strip()),
            citation_count=len(first.citations),
        )
        retry = await self._api.research(
            system_prompt=system_prompt, user_prompt=user_prompt, model=model
        )
        best = retry if self._usability(retry, config.requires_citations) > first_rank else first
        return best, 2

    async def execute(
        self,
        config: ModuleConfig,
        context: ExecutionContextV2,
        output_schema: type[T],
        playbook_path: Path,
    ) -> ModuleExecutorResult:
        """Execute a module using its config, playbook, and schema.

        Args:
            config: ModuleConfig defining the agent's identity and constraints.
            context: ExecutionContextV2 with runtime data (domain, findings, etc.).
            output_schema: Pydantic model class to validate the response against.
            playbook_path: Path to the playbook.md file.

        Returns:
            ModuleExecutorResult with validated output or errors.
        """
        start_ns = time.monotonic_ns()

        logger.info(
            "ModuleExecutor.execute started",
            module=config.name,
            version=config.version,
            domain=context.account_domain,
        )

        try:
            # Step 1: Load and resolve playbook
            _, body = self._playbook_loader.load(playbook_path)
            resolved_prompt = self._playbook_loader.resolve(body, context)

            # Step 2: Build system prompt from config
            system_prompt = self._build_system_prompt(config, output_schema)

            # Step 3: Call the research backend, retrying once if the first answer
            # is unusable. Two intermittent failure modes justify this, both seen
            # live: a provider can return HTTP 200 with no content at all, and
            # search grounding is non-deterministic, so the same module comes back
            # sourced on one call and unsourced on the next.
            response, llm_calls = await self._research_with_retry(
                config=config,
                context=context,
                system_prompt=system_prompt,
                user_prompt=resolved_prompt,
            )

            if not response.content.strip():
                return self._fail_result(
                    config,
                    start_ns,
                    errors=[
                        "provider returned an empty response twice — no content to "
                        "parse (this is a provider fault, not malformed JSON)"
                    ],
                    llm_calls=llm_calls,
                    input_tokens=response.usage_input_tokens,
                    output_tokens=response.usage_output_tokens,
                )

            # Step 4: Parse JSON
            try:
                raw_data = _loads_tolerant(response.content)
            except json.JSONDecodeError as e:
                return self._fail_result(
                    config,
                    start_ns,
                    errors=[f"JSON parse failed: {e}"],
                    llm_calls=llm_calls,
                    input_tokens=response.usage_input_tokens,
                    output_tokens=response.usage_output_tokens,
                )

            # Step 5: Validate against Pydantic schema
            try:
                validated = output_schema.model_validate(raw_data)
            except ValidationError as e:
                field_errors = [
                    f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                    for err in e.errors()
                ]
                return self._fail_result(
                    config,
                    start_ns,
                    errors=[f"Schema validation failed: {err}" for err in field_errors],
                    llm_calls=llm_calls,
                    input_tokens=response.usage_input_tokens,
                    output_tokens=response.usage_output_tokens,
                )

            output_dict = validated.model_dump()

            # Step 6: Generate claim registry
            claims = self._build_claims(output_dict, config.name, response.citations)

            # Step 7: Evidence gate. The output is kept either way — it may well be
            # correct — but unsourced claims must not be reported as clean success,
            # or nothing downstream can tell evidenced data from asserted data.
            unsourced = config.requires_citations and not response.citations
            status = "partial" if unsourced else "success"
            errors = (
                [
                    "no sources returned after a retry — output is unverified and "
                    "must not be presented as evidenced"
                ]
                if unsourced
                else []
            )

            duration_ms = (time.monotonic_ns() - start_ns) // 1_000_000

            log = logger.warning if unsourced else logger.info
            log(
                "ModuleExecutor.execute completed",
                module=config.name,
                domain=context.account_domain,
                status=status,
                duration_ms=duration_ms,
                claim_count=len(claims),
                citation_count=len(response.citations),
            )

            return ModuleExecutorResult(
                module_name=config.name,
                module_version=config.version,
                status=status,
                output=output_dict,
                claims=claims,
                citations=response.citations,
                errors=errors,
                duration_ms=duration_ms,
                llm_calls=llm_calls,
                input_tokens=response.usage_input_tokens,
                output_tokens=response.usage_output_tokens,
            )

        except Exception as e:
            logger.exception(
                "ModuleExecutor.execute failed",
                module=config.name,
                domain=context.account_domain,
            )
            return self._fail_result(
                config,
                start_ns,
                errors=[f"{type(e).__name__}: {e}"],
            )

    async def execute_strategy(
        self,
        config: ModuleConfig,
        context: ExecutionContextV2,
        output_schema: type[T],
        playbook_path: Path,
    ) -> list[ModuleExecutorResult]:
        """Execute a module using the playbook's declared execution_strategy.

        Strategies:
        - prospect-only:  Single call for the prospect domain. Returns 1 result.
        - comparative:    Single call with all competitor domains injected into
                          the context. Returns 1 result.
        - per-company:    Fan-out — one call for the prospect, one per competitor.
                          Returns N+1 results (prospect + N competitors).

        Each call in a fan-out gets a context with account_domain swapped to
        the company being researched, so {domain} resolves correctly.

        Args:
            config: ModuleConfig defining the agent's identity and constraints.
            context: ExecutionContextV2 with runtime data.
            output_schema: Pydantic model class to validate responses against.
            playbook_path: Path to the playbook.md file.

        Returns:
            List of ModuleExecutorResult — always at least 1 element.
        """
        meta, _ = self._playbook_loader.load(playbook_path)
        strategy = meta.execution_strategy

        if strategy == "per-company":
            return await self._execute_per_company(config, context, output_schema, playbook_path)

        # prospect-only and comparative both make a single call
        result = await self.execute(config, context, output_schema, playbook_path)
        return [result]

    async def _execute_per_company(
        self,
        config: ModuleConfig,
        context: ExecutionContextV2,
        output_schema: type[T],
        playbook_path: Path,
    ) -> list[ModuleExecutorResult]:
        """Fan-out: one execute() call per company (prospect + competitors)."""
        companies: list[tuple[str, str]] = [(context.company_name, context.account_domain)]
        for comp in context.competitors:
            companies.append((comp.name, comp.domain))

        results: list[ModuleExecutorResult] = []
        for company_name, domain in companies:
            # Shallow-copy context, override domain + company_name for this company
            per_company_context = copy(context)
            object.__setattr__(per_company_context, "account_domain", domain)
            object.__setattr__(per_company_context, "company_name", company_name)

            result = await self.execute(config, per_company_context, output_schema, playbook_path)
            results.append(result)

        return results

    def _build_system_prompt(self, config: ModuleConfig, schema: type[BaseModel]) -> str:
        """Build the system prompt from config and output schema."""
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        return (
            f"You are {config.description}. "
            f"Module: {config.name} v{config.version}.\n\n"
            "Return your response as a single valid JSON object matching this schema exactly. "
            "No markdown, no commentary before or after the JSON.\n\n"
            f"JSON Schema:\n{schema_json}\n\n"
            "Rules:\n"
            "- Every fact must have a source. Cite with URLs.\n"
            "- Numbers must be raw values (88400000000.0 not '$88.4B').\n"
            "- Dates in YYYY-MM-DD format.\n"
            "- Do not fabricate URLs — only use URLs you actually found.\n"
        )

    @staticmethod
    def _model_for_tier(cost_tier: str) -> str:
        """Map cost tier to Perplexity model ID."""
        mapping = {
            "pro-search": "sonar-pro",
            "deep-research": "sonar-deep-research",
        }
        return mapping.get(cost_tier, "sonar-pro")

    @staticmethod
    def _build_claims(
        output: dict[str, Any],
        module_name: str,
        citations: list[str],
    ) -> list[ClaimRegistryEntry]:
        """Auto-generate claim registry entries from output fields."""
        claims: list[ClaimRegistryEntry] = []
        fallback_url = citations[0] if citations else "no-citation"

        for key, value in output.items():
            if value is None or value == "" or isinstance(value, (list, dict)):
                continue
            claims.append(
                ClaimRegistryEntry(
                    statement=f"{key} = {value}",
                    source_url=fallback_url,
                    evidence_tier="WEBSEARCH",
                    module_origin=module_name,
                    field_path=key,
                )
            )

        return claims

    def _fail_result(
        self,
        config: ModuleConfig,
        start_ns: int,
        errors: list[str],
        llm_calls: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> ModuleExecutorResult:
        """Build a failed ModuleExecutorResult."""
        duration_ms = (time.monotonic_ns() - start_ns) // 1_000_000
        return ModuleExecutorResult(
            module_name=config.name,
            module_version=config.version,
            status="failed",
            errors=errors,
            duration_ms=duration_ms,
            llm_calls=llm_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
