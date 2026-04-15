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

    logger.info(
        "[Registry] all v2 modules registered",
        count=len(V2_MODULE_REGISTRY),
        modules=list(V2_MODULE_REGISTRY.keys()),
    )
