"""Static Algolia partner table — pure Python dict, no external calls.

Maps the canonical name of each platform (lowercase, normalised) to its
Algolia partnership metadata.  The collector cross-references this table
against the detected tech stack from intel-techstack.

Maintenance notes:
- Add new partners here; the collector picks them up automatically.
- ``integration_type`` uses the three values defined in the schema:
  ``"commerce_platform"`` | ``"analytics"`` | ``"crm"``.
- ``integration_doc_url`` should point to the real Algolia docs page when
  available; use the partners index page as a placeholder when not.
"""

from __future__ import annotations

# The keys are lowercase canonical tokens used for fuzzy matching against
# the detected platform strings coming from intel-techstack.
ALGOLIA_PARTNER_TABLE: dict[str, dict[str, str]] = {
    # ── Commerce platforms ──────────────────────────────────────────────────
    "adobe commerce": {
        "partner_name": "Adobe Commerce",
        "integration_type": "commerce_platform",
        "integration_doc_url": "https://www.algolia.com/integrations/adobe-commerce/",
        "algolia_connector": "magento2-algolia",
    },
    "magento": {
        "partner_name": "Adobe Commerce (Magento)",
        "integration_type": "commerce_platform",
        "integration_doc_url": "https://www.algolia.com/integrations/adobe-commerce/",
        "algolia_connector": "magento2-algolia",
    },
    "salesforce commerce cloud": {
        "partner_name": "Salesforce Commerce Cloud",
        "integration_type": "commerce_platform",
        "integration_doc_url": "https://www.algolia.com/integrations/salesforce-commerce-cloud/",
        "algolia_connector": "salesforce-commerce-cloud-algolia",
    },
    "sfcc": {
        "partner_name": "Salesforce Commerce Cloud",
        "integration_type": "commerce_platform",
        "integration_doc_url": "https://www.algolia.com/integrations/salesforce-commerce-cloud/",
        "algolia_connector": "salesforce-commerce-cloud-algolia",
    },
    "shopify": {
        "partner_name": "Shopify",
        "integration_type": "commerce_platform",
        "integration_doc_url": "https://www.algolia.com/integrations/shopify/",
        "algolia_connector": "shopify-algolia",
    },
    "sap commerce": {
        "partner_name": "SAP Commerce Cloud",
        "integration_type": "commerce_platform",
        "integration_doc_url": "https://www.algolia.com/partners/sap/",
        "algolia_connector": "sap-commerce-algolia",
    },
    "hybris": {
        "partner_name": "SAP Commerce Cloud (Hybris)",
        "integration_type": "commerce_platform",
        "integration_doc_url": "https://www.algolia.com/partners/sap/",
        "algolia_connector": "sap-commerce-algolia",
    },
    "commercetools": {
        "partner_name": "commercetools",
        "integration_type": "commerce_platform",
        "integration_doc_url": "https://www.algolia.com/integrations/commercetools/",
        "algolia_connector": "commercetools-algolia",
    },
    "bigcommerce": {
        "partner_name": "BigCommerce",
        "integration_type": "commerce_platform",
        "integration_doc_url": "https://www.algolia.com/integrations/bigcommerce/",
        "algolia_connector": "bigcommerce-algolia",
    },
    # ── CRM / CDP ───────────────────────────────────────────────────────────
    "salesforce": {
        "partner_name": "Salesforce",
        "integration_type": "crm",
        "integration_doc_url": "https://www.algolia.com/partners/salesforce/",
        "algolia_connector": "salesforce-algolia",
    },
    "sap": {
        "partner_name": "SAP",
        "integration_type": "crm",
        "integration_doc_url": "https://www.algolia.com/partners/sap/",
        "algolia_connector": "sap-algolia",
    },
}

# Lookup tokens sorted longest-first so that more-specific keys match before
# shorter overlapping ones (e.g. "salesforce commerce cloud" beats "salesforce").
PARTNER_LOOKUP_KEYS: list[str] = sorted(ALGOLIA_PARTNER_TABLE.keys(), key=len, reverse=True)
