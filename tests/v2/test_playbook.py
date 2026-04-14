"""Tests for PlaybookLoader — .md → resolved prompt."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from prism_platform.v2.playbook import PlaybookLoader
from prism_platform.v2.types import ExecutionContextV2

SAMPLE_PLAYBOOK = """---
name: intel-company
version: 2.0.0
description: Company seed intelligence
cost_tier: pro-search
execution_strategy: per-company
composes: []
---

## Objective
Research the company at {domain} and produce a comprehensive identity card.

## Data Collection
Discover: {company_name} legal name, headquarters, employee count, revenue.

## Competitors
Identify 5-7 direct competitors to {domain}.
"""


class TestPlaybookLoader:
    """PlaybookLoader — markdown to resolved prompt."""

    @pytest.fixture
    def playbook_dir(self, tmp_path: Path) -> Path:
        pb_file = tmp_path / "playbook.md"
        pb_file.write_text(SAMPLE_PLAYBOOK)
        return tmp_path

    @pytest.fixture
    def context(self) -> ExecutionContextV2:
        return ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="dell.com",
            company_name="Dell Technologies",
            industry="Enterprise Technology",
            is_public=True,
            ticker="DELL",
        )

    def test_load_parses_frontmatter(self, playbook_dir: Path) -> None:
        loader = PlaybookLoader()
        meta, _ = loader.load(playbook_dir / "playbook.md")
        assert meta.name == "intel-company"
        assert meta.version == "2.0.0"
        assert meta.cost_tier == "pro-search"

    def test_load_returns_body(self, playbook_dir: Path) -> None:
        loader = PlaybookLoader()
        _, body = loader.load(playbook_dir / "playbook.md")
        assert "{domain}" in body
        assert "## Objective" in body

    def test_resolve_substitutes_variables(
        self, playbook_dir: Path, context: ExecutionContextV2
    ) -> None:
        loader = PlaybookLoader()
        _, body = loader.load(playbook_dir / "playbook.md")
        resolved = loader.resolve(body, context)
        assert "dell.com" in resolved
        assert "Dell Technologies" in resolved
        assert "{domain}" not in resolved
        assert "{company_name}" not in resolved

    def test_resolve_preserves_unknown_variables(self, playbook_dir: Path) -> None:
        ctx = ExecutionContextV2(
            audit_id=str(uuid4()),
            account_domain="test.com",
        )
        loader = PlaybookLoader()
        body = "Research {domain} and check {nonexistent_var}"
        resolved = loader.resolve(body, ctx)
        assert "test.com" in resolved
        assert "{nonexistent_var}" in resolved  # preserved, not crashed

    def test_load_missing_file_raises(self) -> None:
        loader = PlaybookLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(Path("/nonexistent/playbook.md"))
