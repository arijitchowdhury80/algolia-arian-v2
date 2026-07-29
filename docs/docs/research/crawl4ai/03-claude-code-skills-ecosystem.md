# Claude Code Skills Ecosystem Research
# Fetched: 2026-05-03

## Overview

Skills are a mature ecosystem now (Anthropic released format Dec 2025).
They work across Claude Code, Codex, Gemini CLI, Cursor, Windsurf, Antigravity.
This is the standard unit of agent knowledge packaging.

## Key GitHub Repos to Study

### Official
- **anthropics/skills** — https://github.com/anthropics/skills
  Official Anthropic repo for Agent Skills. Study this first for canonical patterns.

### Community Collections
- **alirezarezvani/claude-skills** — https://github.com/alirezarezvani/claude-skills
  5,200+ stars. 232+ skills: engineering, marketing, product, compliance, C-level advisory.
  Best single source for reusable skill patterns.

- **VoltAgent/awesome-agent-skills** — https://github.com/VoltAgent/awesome-agent-skills
  1,000+ skills. Curated from official teams + community.

- **sickn33/antigravity-awesome-skills** — https://github.com/sickn33/antigravity-awesome-skills
  1,400+ skills. Includes installer CLI, bundles, workflows.

- **ComposioHQ/awesome-claude-skills** — https://github.com/ComposioHQ/awesome-claude-skills
  Curated list. Good for finding domain-specific skills.

- **travisvn/awesome-claude-skills** — https://github.com/travisvn/awesome-claude-skills
  Another curated list focused on Claude Code specifically.

- **glebis/claude-skills** — https://github.com/glebis/claude-skills
  Community collection for enhanced AI workflows.

### Workflow-Focused
- **shinpr/claude-code-workflows** — https://github.com/shinpr/claude-code-workflows
  Production-ready development workflows for Claude Code.
  Pattern: Analyze → Design → Plan → Implement → Verify phases in fresh agent contexts.

## Skill Format

```
my-skill/
  skill.md          # YAML frontmatter (name, description) + Markdown instructions
  scripts/          # optional shell/python scripts
  references/       # optional reference docs
```

skill.md structure:
```markdown
---
name: my-skill-name
description: When to invoke this skill (used for auto-routing)
---

# Skill Instructions

...the actual instructions Claude follows...
```

## Key Insight for PRISM

The ecosystem has 1,400+ skills but very few are domain-specific for:
- B2B sales intelligence gathering
- Prospect research pipelines
- Corporate website crawling patterns
- ATS/job board data extraction

This is our moat. We should:
1. Study the `anthropics/skills` repo for format + patterns
2. Borrow workflow patterns from `shinpr/claude-code-workflows`
3. Look at data/research skills in `alirezarezvani/claude-skills` for inspiration
4. Build PRISM-specific skills that encode our domain knowledge

## What to Borrow

From the workflow pattern:
- Analyze → Design → Plan → Implement → Verify is a good Temporal workflow analogy
- Each phase in a fresh agent context = each module gets a clean execution context
- Quality-fixer step = our validation layer (Perplexity cross-check)

From the skill structure:
- We already have this in our superpowers skills
- PRISM modules could be expressed as skills with playbooks embedded
- The `algolia-intel-*` skills in our stack already follow this pattern
