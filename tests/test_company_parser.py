"""Tests for intel-company deterministic parser — citation extraction + JSON parsing."""

import pytest

from prism_platform.modules.intel_company.parser import (
    extract_citations,
    parse_perplexity_json,
    strip_citations,
)


class TestExtractCitations:
    def test_extracts_single_citation(self):
        text = '"employee_count": 3500, [cbinsights](https://www.cbinsights.com/company/jewson)'
        citations = extract_citations(text)
        assert len(citations) >= 1
        assert any(c["source_label"] == "cbinsights" for c in citations)
        assert any("cbinsights.com" in c["source_url"] for c in citations)

    def test_extracts_multiple_citations(self):
        text = (
            '"year_founded": 1836, [news.sky](https://news.sky.com/story/jewson) '
            '"parent_company": "STARK" [cvc](https://www.cvc.com/media/news/2022/)'
        )
        citations = extract_citations(text)
        assert len(citations) >= 2
        labels = {c["source_label"] for c in citations}
        assert "news.sky" in labels
        assert "cvc" in labels

    def test_no_citations_returns_empty(self):
        text = '{"legal_name": "Jewson Limited"}'
        citations = extract_citations(text)
        assert citations == []


class TestStripCitations:
    def test_strips_inline_citation(self):
        text = '"employee_count_source": "LinkedIn data [cbinsights](https://www.cbinsights.com/company/jewson)"'
        result = strip_citations(text)
        assert "[cbinsights]" not in result
        assert "cbinsights.com" not in result
        assert "LinkedIn data" in result

    def test_preserves_non_citation_brackets(self):
        text = '"product_categories": ["Building materials", "Timber"]'
        result = strip_citations(text)
        assert result == text


class TestParsePerplexityJson:
    def test_parses_minimal_valid_json(self):
        raw = """{
            "legal_name": "Jewson Limited",
            "common_name": "Jewson",
            "domain": "jewson.co.uk",
            "headquarters": "Coventry, England, UK",
            "business_model": "Jewson is a builders merchant supplying building materials to trade professionals across the UK through 500+ branches and online.",
            "industry": "Building materials distribution",
            "is_public": false,
            "executives": [],
            "competitors": [],
            "recent_news": [],
            "recent_blog_posts": []
        }"""
        profile, sources = parse_perplexity_json(raw)
        assert profile.legal_name == "Jewson Limited"
        assert profile.domain == "jewson.co.uk"
        assert profile.is_public is False

    def test_parses_json_with_citations_and_extracts_sources(self):
        raw = """{
            "legal_name": "Jewson Limited",
            "common_name": "Jewson",
            "domain": "jewson.co.uk",
            "headquarters": "Coventry, England, UK",
            "employee_count": 3500,
            "employee_count_source": "LinkedIn data [cbinsights](https://www.cbinsights.com/company/jewson)",
            "business_model": "Jewson is a builders merchant supplying building materials to trade professionals across the UK through 500+ branches and online.",
            "industry": "Building materials distribution",
            "is_public": false,
            "executives": [],
            "competitors": [],
            "recent_news": [],
            "recent_blog_posts": []
        }"""
        profile, sources = parse_perplexity_json(raw)
        assert profile.employee_count == 3500
        assert "cbinsights" not in (profile.employee_count_source or "")
        assert len(sources) >= 1
        assert any("cbinsights.com" in s["source_url"] for s in sources)

    def test_ignores_extra_fields(self):
        raw = """{
            "legal_name": "Jewson Limited",
            "common_name": "Jewson",
            "domain": "jewson.co.uk",
            "headquarters": "Coventry, England, UK",
            "business_model": "Jewson is a builders merchant supplying building materials to trade professionals across the UK through 500+ branches and online.",
            "industry": "Building materials distribution",
            "is_public": false,
            "executives": [],
            "competitors": [],
            "recent_news": [],
            "recent_blog_posts": [],
            "_notes": {"ownership": "Owned by STARK Group"}
        }"""
        profile, sources = parse_perplexity_json(raw)
        assert profile.legal_name == "Jewson Limited"

    def test_parses_executives_and_competitors(self):
        raw = """{
            "legal_name": "Jewson Limited",
            "common_name": "Jewson",
            "domain": "jewson.co.uk",
            "headquarters": "Coventry, England, UK",
            "business_model": "Jewson is a builders merchant supplying building materials to trade professionals across the UK through 500+ branches and online.",
            "industry": "Building materials distribution",
            "is_public": false,
            "executives": [
                {
                    "full_name": "John Carter",
                    "title": "CEO, STARK Building Materials UK",
                    "linkedin_url": "https://www.linkedin.com/in/john-carter-504655184",
                    "tenure_description": "Since 2023"
                }
            ],
            "competitors": [
                {
                    "company_name": "Travis Perkins",
                    "domain": "travisperkins.co.uk",
                    "why_competitor": "Large UK builders merchant",
                    "why_competitor": "Large UK builders merchant"
                }
            ],
            "recent_news": [],
            "recent_blog_posts": []
        }"""
        profile, sources = parse_perplexity_json(raw)
        assert len(profile.executives) == 1
        assert profile.executives[0].full_name == "John Carter"
        assert len(profile.competitors) == 1
        assert profile.competitors[0].domain == "travisperkins.co.uk"

    def test_strips_numbered_citations_from_ticker(self):
        raw = """{
            "legal_name": "Shopify Inc.[7]",
            "common_name": "Shopify",
            "domain": "shopify.com",
            "headquarters": "Ottawa, Ontario, Canada",
            "business_model": "Shopify provides e-commerce platform solutions enabling merchants to set up online stores, manage inventory, and process payments globally.",
            "industry": "E-commerce Platform",
            "is_public": true,
            "ticker": "SHOP[1][2]",
            "executives": [],
            "competitors": [],
            "recent_news": [],
            "recent_blog_posts": []
        }"""
        profile, sources = parse_perplexity_json(raw)
        assert profile.ticker == "SHOP"
        assert profile.legal_name == "Shopify Inc."

    def test_strips_parenthetical_noise_from_ticker(self):
        raw = """{
            "legal_name": "ContextLogic Inc.",
            "common_name": "Wish",
            "domain": "wish.com",
            "headquarters": "San Francisco, CA, USA",
            "business_model": "Wish operates a mobile-first e-commerce marketplace connecting global consumers with merchants offering affordable products.",
            "industry": "E-commerce Marketplace",
            "is_public": true,
            "ticker": "WISH (ContextLogic; changing post-sale)",
            "executives": [],
            "competitors": [],
            "recent_news": [],
            "recent_blog_posts": []
        }"""
        profile, sources = parse_perplexity_json(raw)
        assert profile.ticker == "WISH"
