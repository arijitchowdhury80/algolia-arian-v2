"""PlaybookLoader — reads playbook.md files and resolves template variables.

Playbooks are markdown files with YAML frontmatter. The body contains
research instructions with template variables like {domain}, {company_name},
{competitors} that are resolved from the ExecutionContextV2 at runtime.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict

from prism_platform.v2.types import ExecutionContextV2

logger = structlog.get_logger(__name__)

# Match YAML frontmatter between --- delimiters
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class PlaybookMeta(BaseModel):
    """Parsed YAML frontmatter from a playbook.md file."""

    model_config = ConfigDict(extra="ignore")

    name: str
    version: str
    description: str = ""
    cost_tier: str = "pro-search"
    execution_strategy: str = "per-company"
    composes: list[str] = []


class PlaybookLoader:
    """Loads and resolves playbook markdown files."""

    def load(self, path: Path) -> tuple[PlaybookMeta, str]:
        """Load a playbook.md file and parse its frontmatter.

        Args:
            path: Absolute path to the playbook.md file.

        Returns:
            Tuple of (PlaybookMeta, body_text).

        Raises:
            FileNotFoundError: If the playbook file doesn't exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"Playbook not found: {path}")

        raw = path.read_text(encoding="utf-8")
        meta, body = self._split_frontmatter(raw)

        logger.info(
            "Playbook loaded",
            path=str(path),
            name=meta.name,
            version=meta.version,
        )

        return meta, body

    def resolve(self, body: str, context: ExecutionContextV2) -> str:
        """Resolve template variables in a playbook body.

        Substitutes {domain}, {company_name}, {industry}, {ticker}, etc.
        from the ExecutionContextV2. Unknown variables are preserved as-is.

        Args:
            body: Raw playbook body text with {variable} placeholders.
            context: The execution context providing variable values.

        Returns:
            Resolved playbook text.
        """
        variables: dict[str, str] = {
            "domain": context.account_domain,
            "company_name": context.company_name,
            "industry": context.industry,
            "ticker": context.ticker or "",
            "is_public": str(context.is_public),
        }

        if context.competitors:
            comp_lines = [f"- {c.name} ({c.domain})" for c in context.competitors]
            variables["competitors"] = "\n".join(comp_lines)

        if context.executives:
            exec_lines = [f"- {e.name}, {e.title}" for e in context.executives]
            variables["executives"] = "\n".join(exec_lines)

        resolved = self._safe_substitute(body, variables)

        logger.debug(
            "Playbook resolved",
            domain=context.account_domain,
            variables_applied=list(variables.keys()),
        )

        return resolved

    @staticmethod
    def _split_frontmatter(raw: str) -> tuple[PlaybookMeta, str]:
        """Split a markdown file into YAML frontmatter and body."""
        match = FRONTMATTER_RE.match(raw)
        if not match:
            return PlaybookMeta(name="unknown", version="0.0.0"), raw

        yaml_text = match.group(1)
        meta_dict: dict[str, Any] = {}
        for line in yaml_text.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, _, value = line.partition(":")
                value = value.strip().strip("'\"")
                if value == "[]":
                    meta_dict[key.strip()] = []
                elif value.startswith("["):
                    items = value.strip("[]").split(",")
                    meta_dict[key.strip()] = [i.strip().strip("'\"") for i in items if i.strip()]
                else:
                    meta_dict[key.strip()] = value

        body = raw[match.end():]
        return PlaybookMeta.model_validate(meta_dict), body

    @staticmethod
    def _safe_substitute(template: str, variables: dict[str, str]) -> str:
        """Substitute {key} placeholders, preserving unknown variables."""
        def replacer(match: re.Match[str]) -> str:
            key = match.group(1)
            return variables.get(key, match.group(0))

        return re.sub(r"\{(\w+)\}", replacer, template)
