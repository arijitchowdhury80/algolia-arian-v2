"""PRISM v2 Module Registry — the single source of truth for all registered modules.

Every module is a ModuleHandle: config + output schema + playbook path +
an optional post_execute hook for side effects (e.g. writing to the accounts table).

The registry is populated at startup via register_all_v2_modules().
The Temporal run_module activity and the /api/v1/modules router both pull from here.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

from prism_platform.v2.types import ExecutionContextV2, ModuleConfig

logger = structlog.get_logger(__name__)

# Type alias for the optional post-execute side-effect hook.
# Called after a successful module execution.
# Uses Any for the result type to avoid a circular import with executor.py.
PostExecuteFn = Callable[[Any, ExecutionContextV2], Awaitable[None]]

# Type alias for the optional deterministic Track-1 collector.
# Called BEFORE the LLM Track-2 call. Gathers structured data from APIs/Scout
# (no LLM) and returns a dict merged into context.upstream_results, where the
# playbook can reference it as {upstream_<key>}. Collector failure is non-fatal.
CollectorFn = Callable[[ExecutionContextV2], Awaitable[dict[str, Any]]]

# Central registry — populated by register_all_v2_modules() at startup.
V2_MODULE_REGISTRY: dict[str, ModuleHandle] = {}


@dataclass
class ModuleHandle:
    """Everything needed to invoke a v2 module.

    The registry stores one of these per registered module.
    The executor, activities, and API router all use this handle.
    """

    config: ModuleConfig
    output_schema: type[BaseModel]
    playbook_path: Path
    post_execute: PostExecuteFn | None = None
    collector: CollectorFn | None = None

    # ── Convenience properties forwarding from config ──────────────────────

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def version(self) -> str:
        return self.config.version

    @property
    def description(self) -> str:
        return self.config.description

    @property
    def layer(self) -> str:
        return self.config.layer

    async def health_check(self) -> bool:
        """True if the Perplexity API key is configured."""
        from prism_platform.config import settings

        has_key = bool(settings.perplexity_api_key)
        if not has_key:
            logger.warning("health_check: PERPLEXITY_API_KEY not set", module=self.name)
        return has_key


# ── Registration helpers ────────────────────────────────────────────────────


def register_v2_module(handle: ModuleHandle) -> None:
    """Add a module to the global registry."""
    V2_MODULE_REGISTRY[handle.name] = handle
    logger.info(
        "[Registry] v2 module registered",
        name=handle.name,
        version=handle.version,
        layer=handle.layer,
    )


_MODULES_ROOT = Path(__file__).parent / "modules"


def register_all_v2_modules() -> None:
    """Import every v2 module and register it.

    Only modules with a complete implementation (config + playbook + schema)
    are registered here. Unbuilt modules are simply absent from the registry
    — the Temporal workflow handles the 'unknown module' case gracefully.
    """
    # ── intel-company (seed) ────────────────────────────────────────────────
    from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
    from prism_platform.v2.modules.intel_company.hooks import intel_company_post_execute
    from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput

    register_v2_module(
        ModuleHandle(
            config=INTEL_COMPANY_CONFIG,
            output_schema=CompanySeedOutput,
            playbook_path=_MODULES_ROOT / "intel_company" / "playbook.md",
            post_execute=intel_company_post_execute,
        )
    )

    # ── intel-techstack ─────────────────────────────────────────────────────
    from prism_platform.v2.modules.intel_techstack.config import INTEL_TECHSTACK_CONFIG
    from prism_platform.v2.modules.intel_techstack.schemas import TechStackV2Output

    register_v2_module(
        ModuleHandle(
            config=INTEL_TECHSTACK_CONFIG,
            output_schema=TechStackV2Output,
            playbook_path=_MODULES_ROOT / "intel_techstack" / "playbook.md",
        )
    )

    # ── intel-traffic ───────────────────────────────────────────────────────
    from prism_platform.v2.modules.intel_traffic.config import INTEL_TRAFFIC_CONFIG
    from prism_platform.v2.modules.intel_traffic.schemas import TrafficV2Output

    register_v2_module(
        ModuleHandle(
            config=INTEL_TRAFFIC_CONFIG,
            output_schema=TrafficV2Output,
            playbook_path=_MODULES_ROOT / "intel_traffic" / "playbook.md",
        )
    )

    # ── intel-financial-public ──────────────────────────────────────────────
    from prism_platform.v2.modules.intel_financial_public.config import (
        INTEL_FINANCIAL_PUBLIC_CONFIG,
    )
    from prism_platform.v2.modules.intel_financial_public.schemas import (
        FinancialPublicV2Output,
    )

    register_v2_module(
        ModuleHandle(
            config=INTEL_FINANCIAL_PUBLIC_CONFIG,
            output_schema=FinancialPublicV2Output,
            playbook_path=_MODULES_ROOT / "intel_financial_public" / "playbook.md",
        )
    )

    # ── intel-financial-private ─────────────────────────────────────────────
    from prism_platform.v2.modules.intel_financial_private.config import (
        INTEL_FINANCIAL_PRIVATE_CONFIG,
    )
    from prism_platform.v2.modules.intel_financial_private.schemas import (
        FinancialPrivateV2Output,
    )

    register_v2_module(
        ModuleHandle(
            config=INTEL_FINANCIAL_PRIVATE_CONFIG,
            output_schema=FinancialPrivateV2Output,
            playbook_path=_MODULES_ROOT / "intel_financial_private" / "playbook.md",
        )
    )

    # ── intel-news ──────────────────────────────────────────────────────────
    from prism_platform.v2.modules.intel_news.config import INTEL_NEWS_CONFIG
    from prism_platform.v2.modules.intel_news.schemas import NewsV2Output

    register_v2_module(
        ModuleHandle(
            config=INTEL_NEWS_CONFIG,
            output_schema=NewsV2Output,
            playbook_path=_MODULES_ROOT / "intel_news" / "playbook.md",
        )
    )

    # ── intel-hiring ────────────────────────────────────────────────────────
    from prism_platform.v2.modules.intel_hiring.config import INTEL_HIRING_CONFIG
    from prism_platform.v2.modules.intel_hiring.schemas import HiringV2Output

    register_v2_module(
        ModuleHandle(
            config=INTEL_HIRING_CONFIG,
            output_schema=HiringV2Output,
            playbook_path=_MODULES_ROOT / "intel_hiring" / "playbook.md",
        )
    )

    # ── intel-competitors (Track-1 Scout vendor detection + Track-2 LLM) ────
    from prism_platform.v2.modules.intel_competitors.collector import (
        collect as intel_competitors_collect,
    )
    from prism_platform.v2.modules.intel_competitors.config import INTEL_COMPETITORS_CONFIG
    from prism_platform.v2.modules.intel_competitors.schemas import CompetitorsV2Output

    register_v2_module(
        ModuleHandle(
            config=INTEL_COMPETITORS_CONFIG,
            output_schema=CompetitorsV2Output,
            playbook_path=_MODULES_ROOT / "intel_competitors" / "playbook.md",
            collector=intel_competitors_collect,
        )
    )

    # ── intel-partner (Track-1 static partner table + Track-2 LLM) ─────────
    from prism_platform.v2.modules.intel_partner.collector import (
        intel_partner_collector,
    )
    from prism_platform.v2.modules.intel_partner.config import INTEL_PARTNER_CONFIG
    from prism_platform.v2.modules.intel_partner.schemas import PartnerV2Output

    register_v2_module(
        ModuleHandle(
            config=INTEL_PARTNER_CONFIG,
            output_schema=PartnerV2Output,
            playbook_path=_MODULES_ROOT / "intel_partner" / "playbook.md",
            collector=intel_partner_collector,
        )
    )

    # ── intel-industry (LLM-only — vertical benchmarks, trends, analyst quotes) ─
    from prism_platform.v2.modules.intel_industry.config import INTEL_INDUSTRY_CONFIG
    from prism_platform.v2.modules.intel_industry.schemas import IndustryIntelOutput

    register_v2_module(
        ModuleHandle(
            config=INTEL_INDUSTRY_CONFIG,
            output_schema=IndustryIntelOutput,
            playbook_path=_MODULES_ROOT / "intel_industry" / "playbook.md",
            # No collector — this is the one justified pure-LLM module.
            # Vertical benchmarks and analyst quotes have no structured API.
        )
    )

    # ── intel-queries (Track-1 pure-Python generation, Wave 1C) ────────────
    from prism_platform.v2.modules.intel_queries.collector import (
        collect as intel_queries_collect,
    )
    from prism_platform.v2.modules.intel_queries.config import INTEL_QUERIES_CONFIG
    from prism_platform.v2.modules.intel_queries.schemas import QueryIntelOutput

    register_v2_module(
        ModuleHandle(
            config=INTEL_QUERIES_CONFIG,
            output_schema=QueryIntelOutput,
            playbook_path=_MODULES_ROOT / "intel_queries" / "playbook.md",
            collector=intel_queries_collect,
        )
    )

    # ── intel-investor (Track-1 Yahoo Finance + Track-2 LLM quote extraction) ─
    from prism_platform.v2.modules.intel_investor.collector import (
        collect as intel_investor_collect,
    )
    from prism_platform.v2.modules.intel_investor.config import INTEL_INVESTOR_CONFIG
    from prism_platform.v2.modules.intel_investor.schemas import InvestorIntelOutput

    register_v2_module(
        ModuleHandle(
            config=INTEL_INVESTOR_CONFIG,
            output_schema=InvestorIntelOutput,
            playbook_path=_MODULES_ROOT / "intel_investor" / "playbook.md",
            collector=intel_investor_collect,
        )
    )

    # ── intel-social (Track-1 Apify scraping + Track-2 LLM relevance scoring) ─
    from prism_platform.v2.modules.intel_social.collector import (
        collect as intel_social_collect,
    )
    from prism_platform.v2.modules.intel_social.config import INTEL_SOCIAL_CONFIG
    from prism_platform.v2.modules.intel_social.schemas import SocialIntelOutput

    register_v2_module(
        ModuleHandle(
            config=INTEL_SOCIAL_CONFIG,
            output_schema=SocialIntelOutput,
            playbook_path=_MODULES_ROOT / "intel_social" / "playbook.md",
            collector=intel_social_collect,
        )
    )

    # ── synth-business-case (Wave 5 — pure synthesis from upstream intel) ───
    from prism_platform.v2.modules.synth_business_case.config import (
        SYNTH_BUSINESS_CASE_CONFIG,
    )
    from prism_platform.v2.modules.synth_business_case.schemas import BusinessCaseOutput

    register_v2_module(
        ModuleHandle(
            config=SYNTH_BUSINESS_CASE_CONFIG,
            output_schema=BusinessCaseOutput,
            playbook_path=_MODULES_ROOT / "synth_business_case" / "playbook.md",
            # No collector — reads upstream via composes + {upstream_*} injection.
        )
    )

    # ── synth-sales-plays (Wave 5 — pure synthesis; composes synth-business-case) ─
    from prism_platform.v2.modules.synth_sales_plays.config import (
        SYNTH_SALES_PLAYS_CONFIG,
    )
    from prism_platform.v2.modules.synth_sales_plays.schemas import SalesPlaysOutput

    register_v2_module(
        ModuleHandle(
            config=SYNTH_SALES_PLAYS_CONFIG,
            output_schema=SalesPlaysOutput,
            playbook_path=_MODULES_ROOT / "synth_sales_plays" / "playbook.md",
        )
    )

    # ── campaign-abx (Wave 5 — pure synthesis; composes both synth modules) ─
    from prism_platform.v2.modules.campaign_abx.config import CAMPAIGN_ABX_CONFIG
    from prism_platform.v2.modules.campaign_abx.schemas import CampaignOutput

    register_v2_module(
        ModuleHandle(
            config=CAMPAIGN_ABX_CONFIG,
            output_schema=CampaignOutput,
            playbook_path=_MODULES_ROOT / "campaign_abx" / "playbook.md",
        )
    )

    # ── audit-report (Wave 6 — final deliverable; pure synthesis from all upstream) ─
    from prism_platform.v2.modules.audit_report.config import AUDIT_REPORT_CONFIG
    from prism_platform.v2.modules.audit_report.schemas import AuditReportOutput

    register_v2_module(
        ModuleHandle(
            config=AUDIT_REPORT_CONFIG,
            output_schema=AuditReportOutput,
            playbook_path=_MODULES_ROOT / "audit_report" / "playbook.md",
        )
    )

    logger.info(
        "[Registry] all v2 modules registered",
        count=len(V2_MODULE_REGISTRY),
        modules=list(V2_MODULE_REGISTRY.keys()),
    )
