"""Landing Page Intake — static extraction config.

No ModuleConfig/registry entry here on purpose: this is not a pipeline-DAG
module (no cost_tier, no composes, no LLM playbook -- see schemas.py
docstring). It is exposed via server/api/routers/landing_pages.py,
following the audits.py CRUD-router pattern, not modules.py's execute-module
pattern (that route is wired to the Perplexity-backed research pipeline).

Caps below exist so the wizard's candidate list stays scannable -- per
docs/workspace/custom-landing-page/archive/dell-01-design-thinking.md's own
"tier inflation risk" note: cut to the highest-signal items, don't dump the
whole report.
"""

from __future__ import annotations

MAX_FINDING_CANDIDATES = 8
MAX_CASE_STUDY_CANDIDATES = 5
