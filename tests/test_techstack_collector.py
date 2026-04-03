"""Integration test for intel-techstack collector -- calls real BuiltWith API."""

from __future__ import annotations

import pytest

from prism_platform.config import settings
from prism_platform.modules.intel_techstack.collector import TechStackCollector
from prism_platform.modules.intel_techstack.schemas import TechStackOutput

pytestmark = pytest.mark.skipif(
    not settings.builtwith_api_key,
    reason="BUILTWITH_API_KEY not set -- skipping integration test",
)


@pytest.mark.asyncio
async def test_collect_dell_com() -> None:
    """Call BuiltWith with dell.com and verify we get real technology data."""
    collector = TechStackCollector()
    output, sources = await collector.collect_all("dell.com")

    # Must return a valid TechStackOutput
    assert isinstance(output, TechStackOutput)

    # Dell.com should have plenty of technologies
    assert len(output.all_technologies) >= 3, (
        f"Expected at least 3 technologies, got {len(output.all_technologies)}"
    )

    # Summary should be populated
    assert output.tech_stack_summary != ""

    # Must have at least 1 source for provenance
    assert len(sources) >= 1

    # All technologies should have Name keys
    for tech in output.all_technologies:
        assert "Name" in tech
