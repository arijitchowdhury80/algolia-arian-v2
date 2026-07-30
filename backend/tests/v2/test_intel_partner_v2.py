"""Tests for intel-partner v2 module.

Focus: pure-logic units — partner table lookup, schema validation, config,
and playbook existence.  No mocks, no fabricated data.  The collector is
deterministic (pure Python dict lookup), so these tests are fast and require
no external calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.playbook import PlaybookLoader
from core.types import ExecutionContextV2
from prism_platform.v2.modules.intel_partner.collector import (
    _match_partners,
    _normalise,
    intel_partner_collector,
)
from prism_platform.v2.modules.intel_partner.config import INTEL_PARTNER_CONFIG
from prism_platform.v2.modules.intel_partner.partner_table import (
    ALGOLIA_PARTNER_TABLE,
    PARTNER_LOOKUP_KEYS,
)
from prism_platform.v2.modules.intel_partner.schemas import (
    PartnerV2Output,
    SIRelationship,
    TechPartner,
)

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent / "prism_platform/v2/modules/intel_partner/playbook.md"
)


# ── Partner table ────────────────────────────────────────────────────────────


class TestPartnerTable:
    def test_all_entries_have_required_keys(self) -> None:
        required = {"partner_name", "integration_type", "integration_doc_url", "algolia_connector"}
        for key, entry in ALGOLIA_PARTNER_TABLE.items():
            assert required.issubset(entry.keys()), f"Entry '{key}' missing required keys"

    def test_integration_types_are_valid(self) -> None:
        valid: set[str] = {"commerce_platform", "analytics", "crm"}
        for key, entry in ALGOLIA_PARTNER_TABLE.items():
            assert entry["integration_type"] in valid, (
                f"Entry '{key}' has invalid integration_type '{entry['integration_type']}'"
            )

    def test_lookup_keys_sorted_longest_first(self) -> None:
        for i in range(len(PARTNER_LOOKUP_KEYS) - 1):
            assert len(PARTNER_LOOKUP_KEYS[i]) >= len(PARTNER_LOOKUP_KEYS[i + 1]), (
                "PARTNER_LOOKUP_KEYS must be sorted longest-first to prevent short-key shadowing"
            )

    def test_all_keys_present_in_lookup_list(self) -> None:
        assert set(PARTNER_LOOKUP_KEYS) == set(ALGOLIA_PARTNER_TABLE.keys())

    def test_known_partners_present(self) -> None:
        # Spot-check the platforms specified in the task brief.
        expected_partner_names = {
            "Adobe Commerce (Magento)",  # via "magento" key
            "Salesforce Commerce Cloud",  # via "sfcc" or full name
            "Shopify",
            "SAP Commerce Cloud",  # via "sap commerce" key
            "commercetools",
            "BigCommerce",
            "Salesforce",  # CRM
            "SAP",  # CRM
        }
        all_partner_names = {v["partner_name"] for v in ALGOLIA_PARTNER_TABLE.values()}
        for expected in expected_partner_names:
            assert expected in all_partner_names, f"Missing partner: {expected}"


# ── _normalise helper ────────────────────────────────────────────────────────


class TestNormalise:
    def test_lowercases_and_strips(self) -> None:
        assert _normalise("  Shopify  ") == "shopify"

    def test_non_string_returns_empty(self) -> None:
        assert _normalise(None) == ""
        assert _normalise(123) == ""
        assert _normalise([]) == ""

    def test_empty_string(self) -> None:
        assert _normalise("") == ""


# ── _match_partners helper ───────────────────────────────────────────────────


class TestMatchPartners:
    def test_exact_key_match(self) -> None:
        results = _match_partners("shopify", detected_via="ecommerce_platform")
        assert len(results) == 1
        assert results[0]["partner_name"] == "Shopify"
        assert results[0]["integration_type"] == "commerce_platform"
        assert results[0]["detected_via"] == "ecommerce_platform"
        assert results[0]["raw_detected_value"] == "shopify"

    def test_substring_match(self) -> None:
        # Platform string contains the key as a substring.
        results = _match_partners("shopify plus", detected_via="ecommerce_platform")
        assert any(r["partner_name"] == "Shopify" for r in results)

    def test_sfcc_alias_matches_sfcc_partner(self) -> None:
        results = _match_partners("sfcc storefront", detected_via="ecommerce_platform")
        assert any(r["partner_name"] == "Salesforce Commerce Cloud" for r in results)

    def test_full_name_and_alias_deduplicated(self) -> None:
        # "salesforce commerce cloud" contains both the full key and the "sfcc" alias would
        # not appear, but "salesforce" key is also a substring — dedup should prevent two
        # Salesforce Commerce Cloud entries.
        results = _match_partners("salesforce commerce cloud", detected_via="ecommerce_platform")
        names = [r["partner_name"] for r in results]
        # "Salesforce Commerce Cloud" should appear once only.
        assert names.count("Salesforce Commerce Cloud") == 1

    def test_no_match_returns_empty(self) -> None:
        results = _match_partners("custom-built platform", detected_via="ecommerce_platform")
        assert results == []

    def test_magento_maps_to_adobe_commerce(self) -> None:
        results = _match_partners("magento 2", detected_via="ecommerce_platform")
        assert any(r["partner_name"] == "Adobe Commerce (Magento)" for r in results)

    def test_sap_commerce_maps_to_sap_commerce_cloud(self) -> None:
        results = _match_partners("sap commerce cloud", detected_via="ecommerce_platform")
        assert any(r["partner_name"] == "SAP Commerce Cloud" for r in results)


# ── intel_partner_collector ──────────────────────────────────────────────────


class TestIntelPartnerCollector:
    """Tests for the async collector function.

    These are pure-logic tests — no real network calls because the collector
    only does dict lookups against the static partner table.
    """

    def _make_context(self, techstack: dict) -> ExecutionContextV2:
        return ExecutionContextV2(
            audit_id="test-001",
            account_domain="example.com",
            company_name="Example Co",
            upstream_results={"intel-techstack": techstack},
        )

    @pytest.mark.asyncio
    async def test_shopify_detected(self) -> None:
        ctx = self._make_context({"ecommerce_platform": "Shopify"})
        result = await intel_partner_collector(ctx)
        detection = result["partner_tech_detection"]
        assert detection["has_algolia_partner_overlap"] is True
        names = [p["partner_name"] for p in detection["tech_partners"]]
        assert "Shopify" in names

    @pytest.mark.asyncio
    async def test_no_techstack_upstream_returns_empty(self) -> None:
        ctx = ExecutionContextV2(
            audit_id="test-002",
            account_domain="example.com",
        )
        result = await intel_partner_collector(ctx)
        detection = result["partner_tech_detection"]
        assert detection["has_algolia_partner_overlap"] is False
        assert detection["tech_partners"] == []

    @pytest.mark.asyncio
    async def test_unknown_platform_returns_empty(self) -> None:
        ctx = self._make_context({"ecommerce_platform": "WooCommerce"})
        result = await intel_partner_collector(ctx)
        detection = result["partner_tech_detection"]
        assert detection["has_algolia_partner_overlap"] is False
        assert detection["tech_partners"] == []

    @pytest.mark.asyncio
    async def test_sfcc_detected_via_alias(self) -> None:
        ctx = self._make_context({"ecommerce_platform": "SFCC"})
        result = await intel_partner_collector(ctx)
        detection = result["partner_tech_detection"]
        assert detection["has_algolia_partner_overlap"] is True
        names = [p["partner_name"] for p in detection["tech_partners"]]
        assert "Salesforce Commerce Cloud" in names

    @pytest.mark.asyncio
    async def test_deduplication_across_fields(self) -> None:
        # "salesforce" appears in both ecommerce_platform and crm_platform.
        ctx = self._make_context(
            {
                "ecommerce_platform": "Salesforce Commerce Cloud",
                "crm_platform": "Salesforce",
            }
        )
        result = await intel_partner_collector(ctx)
        detection = result["partner_tech_detection"]
        partner_names = [p["partner_name"] for p in detection["tech_partners"]]
        # "Salesforce" (CRM) and "Salesforce Commerce Cloud" should each appear once.
        assert partner_names.count("Salesforce") <= 1
        assert partner_names.count("Salesforce Commerce Cloud") <= 1

    @pytest.mark.asyncio
    async def test_result_shape(self) -> None:
        ctx = self._make_context({"ecommerce_platform": "Shopify"})
        result = await intel_partner_collector(ctx)
        assert "partner_tech_detection" in result
        detection = result["partner_tech_detection"]
        assert "tech_partners" in detection
        assert "has_algolia_partner_overlap" in detection
        assert "detection_method" in detection
        assert "techstack_fields_probed" in detection
        assert detection["detection_method"] == "static_partner_table"

    @pytest.mark.asyncio
    async def test_detected_via_field_recorded(self) -> None:
        ctx = self._make_context({"ecommerce_platform": "commercetools"})
        result = await intel_partner_collector(ctx)
        detection = result["partner_tech_detection"]
        partner = detection["tech_partners"][0]
        assert partner["detected_via"] == "ecommerce_platform"
        assert partner["raw_detected_value"] == "commercetools"


# ── Schemas ──────────────────────────────────────────────────────────────────


class TestTechPartner:
    def test_valid_partner(self) -> None:
        p = TechPartner(
            partner_name="Shopify",
            integration_type="commerce_platform",
            integration_doc_url="https://www.algolia.com/integrations/shopify/",
            detected_via="ecommerce_platform",
            raw_detected_value="Shopify",
        )
        assert p.partner_name == "Shopify"
        assert p.integration_type == "commerce_platform"

    def test_is_frozen(self) -> None:
        p = TechPartner(
            partner_name="Shopify",
            integration_type="commerce_platform",
            integration_doc_url="https://www.algolia.com/integrations/shopify/",
            detected_via="ecommerce_platform",
            raw_detected_value="Shopify",
        )
        with pytest.raises(ValidationError):
            p.partner_name = "changed"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            TechPartner(
                partner_name="Shopify",
                integration_type="commerce_platform",
                integration_doc_url="https://www.algolia.com/integrations/shopify/",
                detected_via="ecommerce_platform",
                raw_detected_value="Shopify",
                bad_field="oops",  # type: ignore[call-arg]
            )

    def test_invalid_integration_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TechPartner(
                partner_name="Shopify",
                integration_type="payments",  # type: ignore[arg-type]
                integration_doc_url="https://example.com",
                detected_via="ecommerce_platform",
                raw_detected_value="shopify",
            )


class TestSIRelationship:
    def test_valid_si(self) -> None:
        si = SIRelationship(
            firm_name="Accenture",
            relationship_type="implementation partner",
            evidence="Accenture press release from 2024 citing SFCC build for ACME Corp.",
            confidence="confirmed",
            algolia_relevance="Accenture has a dedicated SFCC/Algolia connector practice.",
        )
        assert si.confidence == "confirmed"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            SIRelationship(
                firm_name="Accenture",
                relationship_type="implementation partner",
                evidence="Press release",
                confidence="confirmed",
                algolia_relevance="Relevant.",
                bad="oops",  # type: ignore[call-arg]
            )


class TestPartnerV2Output:
    def test_minimal_valid_output(self) -> None:
        out = PartnerV2Output(
            domain="example.com",
            partner_narrative="Example Corp runs Shopify and has an Accenture partnership.",
        )
        assert out.domain == "example.com"
        assert out.has_algolia_partner_overlap is False
        assert out.tech_partners == []
        assert out.si_relationships == []
        assert out.actionable_motions == []

    def test_domain_is_required(self) -> None:
        with pytest.raises(ValidationError):
            PartnerV2Output(  # type: ignore[call-arg]
                partner_narrative="test",
            )

    def test_partner_narrative_is_required(self) -> None:
        with pytest.raises(ValidationError):
            PartnerV2Output(domain="example.com")  # type: ignore[call-arg]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            PartnerV2Output(
                domain="example.com",
                partner_narrative="test",
                bad="oops",  # type: ignore[call-arg]
            )

    def test_generates_json_schema(self) -> None:
        schema = PartnerV2Output.model_json_schema()
        assert "tech_partners" in schema["properties"]
        assert "si_relationships" in schema["properties"]
        assert "partner_narrative" in schema["properties"]
        assert "actionable_motions" in schema["properties"]
        assert "has_algolia_partner_overlap" in schema["properties"]

    def test_full_output_with_partners(self) -> None:
        partner = TechPartner(
            partner_name="Shopify",
            integration_type="commerce_platform",
            integration_doc_url="https://www.algolia.com/integrations/shopify/",
            detected_via="ecommerce_platform",
            raw_detected_value="Shopify",
        )
        si = SIRelationship(
            firm_name="Accenture",
            relationship_type="implementation partner",
            evidence="Accenture 2024 case study.",
            confidence="likely",
            algolia_relevance="Accenture SFCC practice can accelerate the deal.",
        )
        out = PartnerV2Output(
            domain="example.com",
            tech_partners=[partner],
            si_relationships=[si],
            partner_narrative="Example Corp is on Shopify with Accenture as SI.",
            actionable_motions=["Engage Accenture SFCC practice to co-sell."],
            has_algolia_partner_overlap=True,
        )
        assert len(out.tech_partners) == 1
        assert len(out.si_relationships) == 1
        assert out.has_algolia_partner_overlap is True


# ── Config ───────────────────────────────────────────────────────────────────


class TestIntelPartnerConfig:
    def test_name(self) -> None:
        assert INTEL_PARTNER_CONFIG.name == "intel-partner"

    def test_version(self) -> None:
        assert INTEL_PARTNER_CONFIG.version.startswith("2.")

    def test_layer_is_intelligence(self) -> None:
        assert INTEL_PARTNER_CONFIG.layer == "intelligence"

    def test_cost_tier(self) -> None:
        assert INTEL_PARTNER_CONFIG.cost_tier == "pro-search"

    def test_composes_includes_techstack(self) -> None:
        assert "intel-techstack" in INTEL_PARTNER_CONFIG.composes

    def test_composes_includes_company(self) -> None:
        assert "intel-company" in INTEL_PARTNER_CONFIG.composes


# ── Playbook ─────────────────────────────────────────────────────────────────


class TestIntelPartnerPlaybook:
    def test_playbook_exists(self) -> None:
        assert PLAYBOOK_PATH.exists()

    def test_execution_strategy_is_prospect_only(self) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "prospect-only"

    def test_playbook_references_partner_detection_upstream(self) -> None:
        playbook_text = PLAYBOOK_PATH.read_text()
        assert "upstream_partner_tech_detection" in playbook_text

    def test_playbook_resolves_domain_and_company(self) -> None:
        loader = PlaybookLoader()
        context = ExecutionContextV2(
            audit_id="t",
            account_domain="acme.com",
            company_name="ACME Corp",
            industry="Retail",
        )
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "ACME Corp" in resolved
        assert "acme.com" in resolved
