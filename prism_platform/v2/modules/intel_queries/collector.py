"""Intel Queries Track-1 collector — pure Python query generation.

Generates the browser-audit test-query set from structured upstream data:
  - intel-company  → product_categories, common_name (brand), subsidiaries
  - intel-traffic  → top_organic_keywords

NO LLM. NO external API. Deterministic: same upstream data → same queries.

The result is merged into context.upstream_results under ``query_set``
so the (minimal) playbook can reference it as ``{upstream_query_set}``
if Track-2 ever runs. The collector ALSO returns the full QueryIntelOutput
dict so the executor can parse it directly as the module's final output
(intel-queries has no meaningful Track-2 residual).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import structlog

from prism_platform.v2.types import ExecutionContextV2

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Static seed tables
# ---------------------------------------------------------------------------

# Colloquial synonyms for common product nouns.
# Only cover terms broad enough to appear across retail verticals.
_SYNONYM_MAP: dict[str, str] = {
    "shoes": "kicks",
    "sneakers": "kicks",
    "trainers": "kicks",
    "handbag": "purse",
    "handbags": "purses",
    "sunglasses": "shades",
    "eyeglasses": "specs",
    "trousers": "pants",
    "jacket": "coat",
    "jumper": "sweater",
    "perfume": "fragrance",
    "sofa": "couch",
    "television": "tv",
    "laptop": "notebook",
    "mobile": "phone",
    "smartphone": "phone",
    "headphones": "cans",
    "earphones": "earbuds",
    "watch": "timepiece",
}

# Navigational / non-product queries that every retail site should handle.
_NON_PRODUCT_QUERIES: list[str] = [
    "returns policy",
    "store locator",
    "gift cards",
    "customer service",
    "size guide",
    "order tracking",
]

# Gibberish strings guaranteed to return zero results on any sane search engine.
# Fixed — do not randomize. Determinism is a hard requirement.
_ZERO_RESULTS_STRINGS: list[str] = [
    "xqzpfk",
    "asdfghjkl",
    "zzznoresult",
]

# Specific-product modifiers applied to each broad category.
# Kept small — just enough to produce plausible combinations.
_SPECIFIC_MODIFIERS: list[str] = [
    "women's",
    "men's",
    "kids'",
    "waterproof",
    "sustainable",
    "under £50",
    "under $100",
    "best",
    "new",
    "sale",
]

# NLP conversational templates. {category} is replaced with the broad category.
_NLP_TEMPLATES: list[str] = [
    "what {category} should I buy",
    "best {category} for everyday use",
    "help me find a {category}",
    "I'm looking for a good {category}",
]


# ---------------------------------------------------------------------------
# Typo injection — deterministic, position-based
# ---------------------------------------------------------------------------

def _inject_typo(word: str) -> str:
    """Return a single-character typo variant of *word*.

    Strategy (deterministic, fixed positions):
    1. If word length >= 4: swap chars at positions 1 and 2 (0-indexed).
    2. If word length == 3: drop the middle character.
    3. If word length <= 2: double the last character.

    Same input always produces the same output — no randomness.
    """
    if len(word) >= 4:
        chars = list(word)
        chars[1], chars[2] = chars[2], chars[1]
        return "".join(chars)
    if len(word) == 3:
        return word[0] + word[2]
    # len <= 2: double last char
    return word + word[-1]


def _typo_for_phrase(phrase: str) -> str:
    """Inject a typo into the *first substantive word* of a multi-word phrase.

    'First substantive' = first word with length >= 3, skipping short function
    words like 'a', 'an', 'the', 'of'. Falls back to the first word if none qualify.
    """
    words = phrase.split()
    skip = {"a", "an", "the", "of", "in", "on", "at", "to", "by", "or", "and"}
    target_idx = 0
    for i, w in enumerate(words):
        if len(w) >= 3 and w.lower() not in skip:
            target_idx = i
            break
    words[target_idx] = _inject_typo(words[target_idx])
    return " ".join(words)


# ---------------------------------------------------------------------------
# Query generators
# ---------------------------------------------------------------------------

def _generate_broad_category(categories: list[str]) -> list[dict[str, str]]:
    return [
        {"text": cat.lower(), "type": "broad_category", "source": "product_categories"}
        for cat in categories
    ]


def _generate_specific_product(categories: list[str]) -> list[dict[str, str]]:
    """One specific variant per category, cycling through modifiers."""
    items = []
    for i, cat in enumerate(categories):
        modifier = _SPECIFIC_MODIFIERS[i % len(_SPECIFIC_MODIFIERS)]
        items.append({
            "text": f"{modifier} {cat.lower()}",
            "type": "specific_product",
            "source": "product_categories",
        })
    return items


def _generate_nlp_conversational(categories: list[str]) -> list[dict[str, str]]:
    """One NLP query per category, cycling through templates."""
    items = []
    for i, cat in enumerate(categories):
        template = _NLP_TEMPLATES[i % len(_NLP_TEMPLATES)]
        items.append({
            "text": template.format(category=cat.lower()),
            "type": "nlp_conversational",
            "source": "product_categories",
        })
    return items


def _generate_typo_variants(broad_queries: list[str]) -> list[dict[str, str]]:
    """Inject typos into the first 3 broad category queries (deterministic)."""
    items = []
    for phrase in broad_queries[:3]:
        items.append({
            "text": _typo_for_phrase(phrase),
            "type": "typo_variant",
            "source": "product_categories",
        })
    return items


def _generate_synonym_colloquial(categories: list[str]) -> list[dict[str, str]]:
    """Replace a known noun in each category with its colloquial synonym.

    Skips a category if no known synonym matches any word in it.
    Produces at most one synonym query per matched category.
    """
    items = []
    seen: set[str] = set()
    for cat in categories:
        cat_lower = cat.lower()
        for formal, colloquial in _SYNONYM_MAP.items():
            if formal in cat_lower and colloquial not in seen:
                synonymized = cat_lower.replace(formal, colloquial)
                items.append({
                    "text": synonymized,
                    "type": "synonym_colloquial",
                    "source": "product_categories",
                })
                seen.add(colloquial)
                break
    return items


def _generate_non_product_content() -> list[dict[str, str]]:
    return [
        {"text": q, "type": "non_product_content", "source": "static"}
        for q in _NON_PRODUCT_QUERIES
    ]


def _generate_brand_subbrand(
    brand: str,
    subbrands: list[str],
) -> list[dict[str, str]]:
    """Brand name alone + one brand+subbrand combination per sub-brand (up to 3)."""
    items: list[dict[str, str]] = []
    if brand:
        items.append({"text": brand.lower(), "type": "brand_subbrand", "source": "brand"})
    for subbrand in subbrands[:3]:
        if subbrand and subbrand.lower() != brand.lower():
            items.append({
                "text": f"{brand.lower()} {subbrand.lower()}",
                "type": "brand_subbrand",
                "source": "brand",
            })
    return items


def _generate_zero_results_gibberish() -> list[dict[str, str]]:
    return [
        {"text": s, "type": "zero_results_gibberish", "source": "static"}
        for s in _ZERO_RESULTS_STRINGS
    ]


def _generate_keyword_queries(keywords: list[str]) -> list[dict[str, str]]:
    """Emit top organic keywords as additional broad_category queries.

    These supplement the product_categories input — labelled separately
    by source so they're traceable back to intel-traffic.
    """
    return [
        {"text": kw.lower(), "type": "broad_category", "source": "top_organic_keywords"}
        for kw in keywords[:5]
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def collect(context: ExecutionContextV2) -> dict[str, Any]:
    """Generate the test-query set from upstream intel-company + intel-traffic.

    Never raises — returns an empty (but valid) query set on any failure.
    """
    domain = context.account_domain
    company_name = context.company_name or domain

    # ── Hydrate from upstream ──────────────────────────────────────────────
    company_data: dict[str, Any] = context.upstream_results.get("intel-company", {})
    traffic_data: dict[str, Any] = context.upstream_results.get("intel-traffic", {})

    product_categories: list[str] = company_data.get("product_categories", [])
    subbrands: list[str] = [
        s.get("name", "") for s in company_data.get("subsidiaries", [])
        if s.get("name")
    ]
    top_keywords: list[str] = traffic_data.get("top_organic_keywords", [])

    # Graceful degradation: if no product categories at all, seed with the
    # brand name so we still produce something meaningful.
    if not product_categories and company_name:
        product_categories = [company_name]
        logger.warning(
            "[intel-queries] no product_categories from intel-company, seeding with brand name",
            domain=domain,
            fallback=company_name,
        )

    # ── Generate per-type ─────────────────────────────────────────────────
    raw: list[dict[str, str]] = []
    broad = _generate_broad_category(product_categories)
    raw.extend(broad)
    raw.extend(_generate_specific_product(product_categories))
    raw.extend(_generate_nlp_conversational(product_categories))
    raw.extend(_generate_typo_variants([q["text"] for q in broad]))
    raw.extend(_generate_synonym_colloquial(product_categories))
    raw.extend(_generate_non_product_content())
    raw.extend(_generate_brand_subbrand(company_name, subbrands))
    raw.extend(_generate_zero_results_gibberish())
    raw.extend(_generate_keyword_queries(top_keywords))

    # ── Deduplicate (preserve order, case-insensitive) ────────────────────
    seen_texts: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in raw:
        key = item["text"].lower().strip()
        if key not in seen_texts:
            seen_texts.add(key)
            deduped.append(item)

    coverage: dict[str, int] = dict(Counter(q["type"] for q in deduped))
    total = len(deduped)

    logger.info(
        "[intel-queries] Track-1 generation complete",
        domain=domain,
        total_queries=total,
        coverage=coverage,
        had_categories=bool(product_categories),
        had_keywords=bool(top_keywords),
    )

    query_set = {
        "domain": domain,
        "queries": deduped,
        "query_coverage": coverage,
        "total_queries": total,
    }

    return {"query_set": query_set}
