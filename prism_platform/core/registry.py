"""PRISM Module Registry -- central map of all available modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from prism_platform.core.module import ModuleInterface

logger = structlog.get_logger(__name__)

MODULE_REGISTRY: dict[str, ModuleInterface] = {}


def register_module(module: ModuleInterface) -> None:
    """Register a module instance in the global registry."""
    MODULE_REGISTRY[module.name] = module
    logger.info("[Registry] module registered", module=module.name, version=module.version)


def register_all_modules() -> None:
    """Import and register all known PRISM modules."""
    from prism_platform.modules.intel_company.module import CompanyModule
    from prism_platform.modules.intel_financial_private.module import FinancialPrivateModule
    from prism_platform.modules.intel_financial_public.module import FinancialPublicModule
    from prism_platform.modules.intel_hiring.module import HiringModule
    from prism_platform.modules.intel_industry.module import IndustryModule
    from prism_platform.modules.intel_investor.module import InvestorModule
    from prism_platform.modules.intel_news.module import NewsModule
    from prism_platform.modules.intel_partner.module import PartnerModule
    from prism_platform.modules.intel_social.module import SocialModule
    from prism_platform.modules.intel_techstack.module import TechStackModule
    from prism_platform.modules.intel_traffic.module import TrafficModule

    register_module(CompanyModule())
    register_module(TechStackModule())
    register_module(FinancialPrivateModule())
    register_module(FinancialPublicModule())
    register_module(InvestorModule())
    register_module(NewsModule())
    register_module(TrafficModule())
    register_module(HiringModule())
    register_module(SocialModule())
    register_module(IndustryModule())
    register_module(PartnerModule())

    from prism_platform.modules.intel_competitors.module import CompetitorsModule
    from prism_platform.modules.intel_queries.module import QueriesModule
    from prism_platform.modules.synth_business_case.module import BusinessCaseModule

    register_module(CompetitorsModule())
    register_module(QueriesModule())
    register_module(BusinessCaseModule())

    from prism_platform.modules.synth_sales_plays.module import SalesPlaysModule

    register_module(SalesPlaysModule())

    from prism_platform.modules.insights_engine.module import InsightsModule

    register_module(InsightsModule())

    from prism_platform.modules.campaign_abx.module import CampaignModule

    register_module(CampaignModule())

    from prism_platform.modules.audit_report.module import AuditReportModule

    register_module(AuditReportModule())

    from prism_platform.modules.audit_browser.module import BrowserModule

    register_module(BrowserModule())

    from prism_platform.modules.audit_factcheck.module import FactcheckModule

    register_module(FactcheckModule())
