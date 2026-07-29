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

from prism_platform.v2.agent_api import AgentAPIClient
from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.types import ClaimRegistryEntry, ExecutionContextV2, ModuleConfig

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


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
        agent_api: AgentAPIClient instance for making research calls.
    """

    def __init__(self, agent_api: AgentAPIClient) -> None:
        self._api = agent_api
        self._playbook_loader = PlaybookLoader()

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

            # Step 3: Call Agent API
            response = await self._api.research(
                system_prompt=system_prompt,
                user_prompt=resolved_prompt,
                model=self._model_for_tier(config.cost_tier),
            )

            # Step 4: Parse JSON
            try:
                raw_data = json.loads(response.content)
            except json.JSONDecodeError as e:
                return self._fail_result(
                    config,
                    start_ns,
                    errors=[f"JSON parse failed: {e}"],
                    llm_calls=1,
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
                    llm_calls=1,
                    input_tokens=response.usage_input_tokens,
                    output_tokens=response.usage_output_tokens,
                )

            output_dict = validated.model_dump()

            # Step 6: Generate claim registry
            claims = self._build_claims(output_dict, config.name, response.citations)

            duration_ms = (time.monotonic_ns() - start_ns) // 1_000_000

            logger.info(
                "ModuleExecutor.execute completed",
                module=config.name,
                domain=context.account_domain,
                status="success",
                duration_ms=duration_ms,
                claim_count=len(claims),
            )

            return ModuleExecutorResult(
                module_name=config.name,
                module_version=config.version,
                status="success",
                output=output_dict,
                claims=claims,
                citations=response.citations,
                duration_ms=duration_ms,
                llm_calls=1,
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
