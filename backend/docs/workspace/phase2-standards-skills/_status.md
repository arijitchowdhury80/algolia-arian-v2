# Phase 2: Standards Skills

## Current Step
All 4 skills built and live in Claude Code.

## Skills Built
1. [x] standards-coding - ~/.claude/skills/standards-coding/SKILL.md
2. [x] standards-testing - ~/.claude/skills/standards-testing/SKILL.md
3. [x] standards-writing - ~/.claude/skills/standards-writing/SKILL.md
4. [x] standards-uiux - ~/.claude/skills/standards-uiux/SKILL.md

## How They Work
- Each reads the vault SOP at invocation time (single source of truth)
- Validates current work against SOP criteria
- Reports PASS / WARN / FAIL per criterion
- Blocks on FAILs (must fix before proceeding)
- User-invocable via /standards-coding, /standards-testing, etc.
- Also invocable proactively by Claude at checkpoints

## Next
- Update CLAUDE.md to reference skills instead of vault paths
- Test each skill by invoking it
- Phase 3: Adapt PM thinking skills
