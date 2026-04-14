"""Tests for intel-news v2 module."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from prism_platform.v2.modules.intel_news.config import INTEL_NEWS_CONFIG
from prism_platform.v2.modules.intel_news.schemas import NewsArticleV2, NewsV2Output
from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.types import ExecutionContextV2

PLAYBOOK_PATH = (
    Path(__file__).parent.parent.parent / "prism_platform/v2/modules/intel_news/playbook.md"
)


class TestNewsArticleV2:
    def test_valid_article(self) -> None:
        a = NewsArticleV2(
            headline="Dell invests $500M in AI experiences",
            source="Reuters",
            date="2025-11-15",
            url="https://reuters.com/dell-ai",
            summary="Dell announced a $500M AI investment.",
            category="technology",
            is_sell_signal=True,
            sell_signal_reason="AI investment often precedes search platform upgrade",
            urgency="high",
            urgency_reason="Major investment with 12-month deployment timeline announced",
        )
        assert a.urgency == "high"
        assert a.is_sell_signal is True

    def test_is_frozen(self) -> None:
        a = NewsArticleV2(headline="test", source="test", date="2025-01-01")
        with pytest.raises(ValidationError):
            a.headline = "changed"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            NewsArticleV2(
                headline="test",
                source="test",
                date="2025-01-01",
                bad="oops",  # type: ignore[call-arg]
            )

    def test_defaults_are_safe(self) -> None:
        a = NewsArticleV2(headline="test", source="test", date="2025-01-01")
        assert a.is_sell_signal is False
        assert a.urgency == "low"
        assert a.category == "other"


class TestNewsV2Output:
    def test_valid_output(self) -> None:
        out = NewsV2Output(
            domain="dell.com",
            news_narrative="Dell recently announced a major AI investment.",
        )
        assert out.domain == "dell.com"
        assert out.high_urgency_count == 0

    def test_narrative_required(self) -> None:
        with pytest.raises(ValidationError):
            NewsV2Output(domain="dell.com")  # type: ignore[call-arg]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            NewsV2Output(
                domain="dell.com",
                news_narrative="test",
                bad="oops",  # type: ignore[call-arg]
            )

    def test_generates_json_schema(self) -> None:
        schema = NewsV2Output.model_json_schema()
        assert "company_news" in schema["properties"]
        assert "outreach_angle" in schema["properties"]


class TestIntelNewsConfig:
    def test_name(self) -> None:
        assert INTEL_NEWS_CONFIG.name == "intel-news"

    def test_version(self) -> None:
        assert INTEL_NEWS_CONFIG.version.startswith("2.")

    def test_cache_ttl_short(self) -> None:
        # News staleness: 3-day cache is appropriate
        assert INTEL_NEWS_CONFIG.cache_ttl_days <= 7


class TestIntelNewsPlaybook:
    def test_playbook_exists(self) -> None:
        assert PLAYBOOK_PATH.exists()

    def test_execution_strategy_is_prospect_only(self) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(PLAYBOOK_PATH)
        assert meta.execution_strategy == "prospect-only"

    def test_playbook_resolves_executives(self) -> None:
        from prism_platform.v2.types import ExecutiveRef

        loader = PlaybookLoader()
        context = ExecutionContextV2(
            audit_id="t",
            account_domain="dell.com",
            company_name="Dell",
            industry="Tech",
            executives=[ExecutiveRef(name="Jeff Clarke", title="CEO")],
        )
        _, body = loader.load(PLAYBOOK_PATH)
        resolved = loader.resolve(body, context)
        assert "Jeff Clarke" in resolved
