"""End-to-end test for intel-company v2 — proves the agentic pattern works.

Uses a realistic mocked Perplexity response to validate the full pipeline:
config → playbook → executor → API → schema → claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from prism_platform.v2.agent_api import AgentAPIClient, AgentAPIResponse
from prism_platform.v2.executor import ModuleExecutor
from prism_platform.v2.modules.intel_company.config import INTEL_COMPANY_CONFIG
from prism_platform.v2.modules.intel_company.schemas import CompanySeedOutput
from prism_platform.v2.types import ExecutionContextV2

PLAYBOOK_PATH = (
    Path(__file__).resolve().parents[2]
    / "prism_platform"
    / "v2"
    / "modules"
    / "intel_company"
    / "playbook.md"
)

# Realistic mock response matching CompanySeedOutput schema
REALISTIC_DELL_RESPONSE = json.dumps(
    {
        "legal_name": "Dell Technologies Inc.",
        "common_name": "Dell",
        "domain": "dell.com",
        "headquarters": "Round Rock, Texas, USA",
        "employee_count": 133000,
        "employee_count_source": "LinkedIn",
        "year_founded": 1984,
        "business_model": (
            "Dell Technologies designs, manufactures, and sells enterprise hardware including "
            "servers, storage, networking equipment, and personal computers. The company generates "
            "revenue through direct sales to enterprises and consumers, professional services, "
            "and software solutions through subsidiaries like VMware and Secureworks."
        ),
        "industry": "Enterprise Technology",
        "sub_vertical": "Hardware & Infrastructure",
        "is_public": True,
        "ticker": "DELL",
        "parent_company": None,
        "revenue_estimate": 88400000000.0,
        "revenue_source": "SEC 10-K FY2025",
        "executives": [
            {
                "full_name": "Michael Dell",
                "title": "Chairman & CEO",
                "role_classification": "economic_buyer",
                "linkedin_url": "https://www.linkedin.com/in/michaeldell",
                "tenure_description": "Since 1984",
                "previous_company": None,
            },
            {
                "full_name": "Yvonne McGill",
                "title": "Chief Financial Officer",
                "role_classification": "economic_buyer",
                "linkedin_url": None,
                "tenure_description": "Since 2022",
                "previous_company": "Dell (various roles)",
            },
            {
                "full_name": "Jeff Clarke",
                "title": "Vice Chairman & COO",
                "role_classification": "economic_buyer",
                "linkedin_url": None,
                "tenure_description": "Since 2021",
                "previous_company": None,
            },
            {
                "full_name": "John Roese",
                "title": "Global CTO",
                "role_classification": "technical_buyer",
                "linkedin_url": None,
                "tenure_description": "Since 2020",
                "previous_company": "Huawei",
            },
            {
                "full_name": "Jen Felch",
                "title": "Chief Digital Officer",
                "role_classification": "champion",
                "linkedin_url": None,
                "tenure_description": "Since 2019",
                "previous_company": None,
            },
        ],
        "competitors": [
            {
                "company_name": "HP Inc",
                "domain": "hp.com",
                "why_competitor": "Competes in PCs, printers, and enterprise hardware",
                "linkedin_url": None,
            },
            {
                "company_name": "Lenovo",
                "domain": "lenovo.com",
                "why_competitor": "Major PC and server manufacturer competing globally",
                "linkedin_url": None,
            },
            {
                "company_name": "Hewlett Packard Enterprise",
                "domain": "hpe.com",
                "why_competitor": "Competes in enterprise servers, storage, and networking",
                "linkedin_url": None,
            },
            {
                "company_name": "Cisco Systems",
                "domain": "cisco.com",
                "why_competitor": "Competes in networking and enterprise infrastructure",
                "linkedin_url": None,
            },
            {
                "company_name": "IBM",
                "domain": "ibm.com",
                "why_competitor": "Competes in enterprise IT services and infrastructure",
                "linkedin_url": None,
            },
        ],
        "product_categories": [
            "Laptops",
            "Desktops",
            "Servers",
            "Storage",
            "Networking",
            "Services",
        ],
        "company_linkedin_url": "https://www.linkedin.com/company/dell-technologies",
        "recent_headline": (
            "Dell Technologies reports strong Q4 FY2025 results driven by AI server demand"
        ),
    }
)


@pytest.mark.asyncio
async def test_intel_company_v2_full_pipeline() -> None:
    """Full pipeline: config → playbook → executor → API → schema → claims."""

    mock_response = AgentAPIResponse(
        content=REALISTIC_DELL_RESPONSE,
        citations=[
            "https://investors.delltechnologies.com/annual-report-2025",
            "https://www.dell.com/en-us/about",
            "https://www.linkedin.com/company/dell-technologies",
        ],
        usage_input_tokens=250,
        usage_output_tokens=800,
    )
    mock_api = AsyncMock(spec=AgentAPIClient)
    mock_api.research = AsyncMock(return_value=mock_response)

    context = ExecutionContextV2(
        audit_id=str(uuid4()),
        account_domain="dell.com",
        company_name="Dell Technologies",
        industry="Enterprise Technology",
        is_public=True,
        ticker="DELL",
    )

    executor = ModuleExecutor(agent_api=mock_api)
    result = await executor.execute(
        config=INTEL_COMPANY_CONFIG,
        context=context,
        output_schema=CompanySeedOutput,
        playbook_path=PLAYBOOK_PATH,
    )

    # Pattern proves: executor returns success
    assert result.status == "success", f"Expected success, got {result.status}: {result.errors}"
    assert result.module_name == "intel-company"
    assert result.module_version == "2.0.0"

    # Output validates against schema
    output = CompanySeedOutput.model_validate(result.output)
    assert output.legal_name == "Dell Technologies Inc."
    assert output.domain == "dell.com"
    assert output.is_public is True
    assert output.ticker == "DELL"
    assert output.revenue_estimate == 88400000000.0
    assert len(output.executives) >= 5
    assert len(output.competitors) >= 5

    # Role classification works
    ceo = next(e for e in output.executives if "CEO" in e.title)
    assert ceo.role_classification == "economic_buyer"
    cto = next(e for e in output.executives if "CTO" in e.title)
    assert cto.role_classification == "technical_buyer"

    # Claims generated
    assert len(result.claims) > 0
    assert all(c.module_origin == "intel-company" for c in result.claims)
    revenue_claim = next((c for c in result.claims if c.field_path == "revenue_estimate"), None)
    assert revenue_claim is not None

    # Citations passed through
    assert len(result.citations) == 3

    # Cost tracked
    assert result.llm_calls == 1
    assert result.input_tokens == 250
    assert result.output_tokens == 800

    # Verify the API was called with resolved playbook (no {domain} placeholder)
    call_args = mock_api.research.call_args
    user_prompt = call_args.kwargs.get(
        "user_prompt", call_args.args[1] if len(call_args.args) > 1 else ""
    )
    assert "dell.com" in user_prompt
    assert "{domain}" not in user_prompt


@pytest.mark.asyncio
async def test_intel_company_v2_handles_bad_response() -> None:
    """Executor gracefully handles API returning non-schema-compliant JSON."""

    bad_response = AgentAPIResponse(
        content='{"name": "Dell", "bad_field": true}',  # missing required fields
        citations=[],
        usage_input_tokens=10,
        usage_output_tokens=20,
    )
    mock_api = AsyncMock(spec=AgentAPIClient)
    mock_api.research = AsyncMock(return_value=bad_response)

    context = ExecutionContextV2(
        audit_id=str(uuid4()),
        account_domain="dell.com",
    )

    executor = ModuleExecutor(agent_api=mock_api)
    result = await executor.execute(
        config=INTEL_COMPANY_CONFIG,
        context=context,
        output_schema=CompanySeedOutput,
        playbook_path=PLAYBOOK_PATH,
    )

    assert result.status == "failed"
    assert len(result.errors) > 0
    assert any("legal_name" in e for e in result.errors)
