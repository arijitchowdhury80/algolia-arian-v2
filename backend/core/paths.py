"""Canonical filesystem roots, computed once.

Every path in the backend resolves from here. Nothing else in the codebase may
compute `Path(__file__).parents[N]` to find a repo root.

Why this module exists: before 2026-07-30 there were eight independent
`parents[N]` computations scattered across the backend. Each one encoded the
file's own depth in the tree, so every restructure silently broke a different
subset of them. Two such breaks shipped (the Scout path dependency and the docs
directory lift). Computing the roots once, in one file, means a future move
costs exactly one edit.

Layout this module assumes:

    prism/                <- REPO_ROOT
    ├── frontend/         <- FRONTEND_DIR
    ├── backend/          <- BACKEND_ROOT
    │   ├── core/         <- this file lives here
    │   ├── modules/      <- MODULES_ROOT
    │   └── server/
    └── docs/             <- DOCS_DIR
"""

from __future__ import annotations

import os
from pathlib import Path

# core/paths.py -> core/ -> backend/
BACKEND_ROOT: Path = Path(__file__).resolve().parent.parent

# backend/ -> prism/
REPO_ROOT: Path = BACKEND_ROOT.parent

DOCS_DIR: Path = REPO_ROOT / "docs"

# The product module tree (M1-M7).
MODULES_ROOT: Path = BACKEND_ROOT / "modules"

# Legacy home of the 17 flat v2 modules, still registered while they migrate
# into MODULES_ROOT one at a time. Delete this once the migration completes.
LEGACY_MODULES_ROOT: Path = BACKEND_ROOT / "prism_platform" / "v2" / "modules"

# Deep-research cluster playbooks (markdown), read by the executor.
CLUSTERS_DIR: Path = Path(__file__).resolve().parent / "clusters"

# Static assets served directly by the backend (the landing-intake wizard).
STATIC_DIR: Path = BACKEND_ROOT / "server" / "static"

# The frontend half. Overridable because the VPS may mount it elsewhere.
FRONTEND_DIR: Path = Path(os.environ.get("PRISM_FRONTEND_DIR") or (REPO_ROOT / "frontend"))


def repo_relative(path: Path | str) -> Path:
    """Resolve a repo-root-relative path to an absolute one."""
    return REPO_ROOT / path


__all__ = [
    "BACKEND_ROOT",
    "CLUSTERS_DIR",
    "DOCS_DIR",
    "FRONTEND_DIR",
    "LEGACY_MODULES_ROOT",
    "MODULES_ROOT",
    "REPO_ROOT",
    "STATIC_DIR",
    "repo_relative",
]
