#!/usr/bin/env python3
"""Render a project's Notebook chapter from its vault manifest.

Reads Projects/<name>/notebook-manifest.yml, pulls the mapped source files,
skips anything not tagged classification: safe, converts markdown to HTML,
wraps in the shared brand shell, writes to ~/prism/notebook/<chapter>/.

Usage: python3 scripts/render-notebook.py <path-to-manifest.yml>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import markdown
import yaml

VAULT = Path.home() / "Dropbox/AI-Development/Obsidian/Arijit-Second-Brain"
# Resolved from this file rather than hardcoded: frontend/ and backend/ are siblings
# in one repo now, so the same paths work on the laptop and on the VPS (/opt/prism).
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_REPO = REPO_ROOT / "backend"
NOTEBOOK_OUT = REPO_ROOT / "frontend" / "notebook"

SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title} — The Notebook</title>
<link rel="stylesheet" href="/notebook/shared/brand-tokens.css">
<link rel="stylesheet" href="/notebook/shared/notebook.css">
</head>
<body>
<header class="notebook-header">
  <a href="/notebook/" class="notebook-home">The Notebook</a>
  <nav class="notebook-nav">{nav}</nav>
</header>
<main class="notebook-content">
{body}
</main>
<footer class="notebook-footer">Rendered from the internal vault. Source-traced, not freshly authored.</footer>
</body>
</html>
"""


def resolve_source(source: str) -> Path:
    # Manifest sources are either repo-relative or vault-relative. "backend/" is the
    # current prefix; "PIP/" is still accepted so existing manifests keep working
    # after the repo was renamed from PIP to prism.
    if source.startswith("backend/"):
        return BACKEND_REPO / source[len("backend/") :]
    if source.startswith("PIP/"):
        return BACKEND_REPO / source[len("PIP/") :]
    return VAULT / source


def read_source(path: Path) -> str:
    if path.is_dir():
        parts = []
        for f in sorted(path.glob("*.md")):
            parts.append(f"## {f.stem}\n\n{f.read_text(encoding='utf-8')}")
        return "\n\n---\n\n".join(parts)
    return path.read_text(encoding="utf-8")


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)


def render_section(section: dict, nav_html: str) -> None:
    if section.get("classification") != "safe":
        print(f"  SKIP {section['id']} (classification={section.get('classification')}) — {section.get('note', 'not tagged safe')}")
        return

    src = resolve_source(section["source"])
    if not src.exists():
        print(f"  MISSING source for {section['id']}: {src}")
        return

    raw = strip_frontmatter(read_source(src))
    body_html = markdown.markdown(raw, extensions=["tables", "fenced_code"])
    page = SHELL.format(title=section["title"], nav=nav_html, body=body_html)

    out_dir = NOTEBOOK_OUT / section["_chapter"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{section['id']}.html"
    out_file.write_text(page, encoding="utf-8")
    print(f"  OK    {section['id']} <- {src} -> {out_file}")


def render_chapter_index(chapter: str, title: str, sections: list[dict]) -> None:
    links = "\n".join(
        f'<li><a href="/notebook/{chapter}/{s["id"]}.html">{s["title"]}</a></li>'
        for s in sections
        if s.get("classification") == "safe"
    )
    body = f"<h1>{title}</h1>\n<ul class='notebook-toc'>{links}</ul>"
    page = SHELL.format(title=title, nav="", body=body)
    out_dir = NOTEBOOK_OUT / chapter
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    print(f"  OK    {chapter}/index.html")


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: render-notebook.py <manifest.yml>")
        sys.exit(1)

    manifest_path = Path(sys.argv[1])
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    chapter = manifest["chapter"]
    title = manifest["title"]
    sections = manifest["sections"]

    print(f"Rendering chapter '{chapter}' from {manifest_path}")
    nav_html = " ".join(
        f'<a href="/notebook/{chapter}/{s["id"]}.html">{s["title"]}</a>'
        for s in sections
        if s.get("classification") == "safe"
    )
    for s in sections:
        s["_chapter"] = chapter
        render_section(s, nav_html)

    render_chapter_index(chapter, title, sections)
    print("Done.")


if __name__ == "__main__":
    main()
