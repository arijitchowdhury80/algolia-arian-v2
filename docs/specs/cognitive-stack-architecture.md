# The Cognitive Stack: Architecture for an AI-Native Build Engine

**Date:** 2026-04-13
**Status:** Approved for implementation
**Authors:** Arijit Chowdhury, Claude (Architect)
**Scope:** Cross-project operating system for AI-assisted software development
**Provenance:** Brainstorm session synthesizing 4 skill ecosystems: personal SOPs (Obsidian vault), Superpowers v5.0.7, pm-skills (Pawel Huryn), awesome-design-skills (bergside/typeui.sh)

---

## 1. Executive Summary

This document defines a six-layer cognitive stack that transforms how AI assistants build software. The stack composes four independent skill ecosystems into a unified system where every phase of work, from "I have an idea" to "it shipped and we learned from it," is covered by structured, enforceable, invocable skills.

The core insight: most AI-assisted development has strong execution (write code, run tests) but weak thinking (decide what to build), weak standards enforcement (hope Claude remembers the rules), and no learning loop (ship and forget). The cognitive stack fills all three gaps.

Three problems this architecture solves:

1. **CLAUDE.md is bloated.** The PIP project's CLAUDE.md embeds ~400 lines of SOP content (error handling examples, Pydantic rules, logging standards). This duplicates vault content, wastes context window on every message, and drifts from the source of truth.

2. **Skills don't know your standards.** Superpowers enforces TDD discipline but doesn't know about YOUR 3-layer test strategy, YOUR mock adapter pattern, or YOUR "Definition of Done" checklist. Generic process without specific quality criteria.

3. **No thinking layer.** The gap between "I have an idea" and "I start coding" is filled by ad-hoc chat sessions. No structured frameworks for deciding WHAT to build, testing assumptions, or analyzing risk before committing to implementation.

---

## 2. The Architecture

Six layers, each with a distinct cognitive function. Lower layers are always-on. Upper layers are invoked per-task.

```
+---------------------------------------------------+
|  Layer 6: BUILD ENGINE (future)                   |
|  Developer Agent + QA Agent + Dispatcher          |
|  The machine that builds autonomously             |
+---------------------------------------------------+
|  Layer 5: DOMAIN SKILLS                           |
|  algolia-audit-*, algolia-intel-*                 |
|  Domain-specific execution                        |
+---------------------------------------------------+
|  Layer 4: PROCESS SKILLS (superpowers)            |
|  TDD, debugging, verification, planning           |
|  + design-review (to be created)                  |
|  HOW you build. Discipline enforcement.           |
+---------------------------------------------------+
|  Layer 3: STANDARDS SKILLS                        |
|  coding, testing, writing, uiux                   |
|  + aesthetics library (from awesome-design)       |
|  WHAT good looks like. Quality gates.             |
+---------------------------------------------------+
|  Layer 2: THINKING SKILLS                         |
|  PRD, pre-mortem, assumptions, strategy, OST      |
|  + design-thinking (to be created)                |
|  WHAT to build and WHY. Decision frameworks.      |
+---------------------------------------------------+
|  Layer 1: IDENTITY (CLAUDE.md, slim)              |
|  Who I am, cardinal rules, pointers               |
|  50 lines, not 400. Always loaded.                |
+---------------------------------------------------+
```

### The Cognitive Function of Each Layer

| Layer | Question It Answers | When It Activates | Source |
|-------|--------------------|--------------------|--------|
| 1. Identity | "Who am I in this project?" | Always loaded, every message | CLAUDE.md (slimmed) |
| 2. Thinking | "What should we build and why?" | Before any new feature, module, or product decision | Adapted from pm-skills |
| 3. Standards | "Does this meet our quality bar?" | At validation checkpoints during work | Vault SOPs, wrapped as skills |
| 4. Process | "Am I following the right workflow?" | During implementation | Superpowers (unmodified) |
| 5. Domain | "How do I execute this specific task?" | During domain-specific work | Algolia/PRISM skills |
| 6. Build Engine | "Can the machine build this autonomously?" | When tasks are well-specified enough for agents | Developer + QA + Dispatcher (future) |

---

## 3. Layer 1: Identity (CLAUDE.md)

### The Problem

The PIP CLAUDE.md is ~400 lines. Over half is SOP content: full code examples for error handling, logging standards with level guides, Pydantic rules with 5 sub-rules, naming conventions for 4 languages, security standards, performance standards, documentation standards. This content:

- **Wastes context.** Loaded on every message whether relevant or not.
- **Duplicates the vault.** CodingSOPs.md says "max 20 lines per function." CLAUDE.md says "max 50 lines." They've already diverged.
- **Doesn't enforce.** Claude reads it at session start, then may or may not follow it. No checkpoints, no validation, no blocking.

### The Design

CLAUDE.md becomes identity-only. ~50 lines. No code examples. No SOP content.

**What stays:**
- Who you are (co-founder-level technical partner)
- Cardinal rules (7 non-negotiable principles)
- Project context (what is PRISM, what phase are we in)
- Pointers to standards skills ("invoke standards:coding before writing code")
- Pointers to thinking skills ("invoke thinking:prd before writing specs")

**What moves out:**
- Error handling examples --> standards:coding skill (reads CodingSOPs.md)
- Logging standards --> standards:coding skill
- Pydantic rules --> standards:coding skill
- Naming conventions --> standards:coding skill
- Testing standards --> standards:testing skill
- Writing standards --> standards:writing skill
- Frontend standards --> standards:uiux skill
- Security, performance, documentation --> standards:coding skill

### Drift Prevention

The vault SOPs are the single source of truth. Standards skills READ the vault at invocation time. CLAUDE.md never contains SOP content. This eliminates the duplication that causes drift.

---

## 4. Layer 2: Thinking Skills

### The Problem

The gap between "I have an idea" and "I start building" is currently filled by ad-hoc Claude Chat sessions. No structured frameworks. No assumption testing. No risk analysis. The result: architecture redesigns (v1 to v2), wasted effort on wrong approaches, and decisions that aren't documented until after the fact.

### The Design

Seven thinking skills adapted from Pawel Huryn's pm-skills (MIT license), plus one new skill for design thinking. Each encodes a proven framework and walks through it step by step.

#### 4.1 Skills Adapted from pm-skills

| Skill Name | Framework Source | What It Does | When to Invoke |
|------------|-----------------|-------------|----------------|
| `thinking:prd` | create-prd (Huryn) | 8-section PRD: Summary, Background, Objective, Segments, Value Props, Solution, Assumptions, Release | Before any new module, feature, or product |
| `thinking:pre-mortem` | pre-mortem (Huryn, Meta/Instagram) | Risk analysis: Tigers (real risks), Paper Tigers (overblown concerns), Elephants (unspoken worries). Classifies as launch-blocking, fast-follow, or track. | Before committing to any architecture or implementation |
| `thinking:assumptions` | identify-assumptions-new + prioritize-assumptions (Teresa Torres, Dan Olsen) | Identify assumptions across 8 risk categories (Value, Usability, Viability, Feasibility, Ethics, GTM, Strategy, Team). Prioritize via Impact x Risk matrix. | During brainstorming, before building |
| `thinking:ost` | opportunity-solution-tree (Teresa Torres) | Outcome --> Opportunities --> Solutions --> Experiments. Prevents building the wrong thing by forcing opportunity mapping before solution selection. | For product-level decisions, feature prioritization |
| `thinking:strategy` | product-strategy (Huryn, 9-section canvas) | Vision, Segments, Costs, Value Props, Trade-offs, Metrics, Growth, Capabilities, Defensibility. | For product-level strategy (PRISM itself, new products) |
| `thinking:value-prop` | value-proposition (Huryn, JTBD 6-part) | Who, Why, What Before, How, What After, Alternatives. | For any user-facing output, positioning, sales narrative |
| `thinking:lean-canvas` | lean-canvas (Ash Maurya) | Problem, Solution, UVP, Unfair Advantage, Segments, Channels, Revenue, Costs, Metrics. Quick hypothesis testing. | For new product ideas before committing resources |

#### 4.2 New Skill: thinking:design-thinking

This skill does not exist in any repo. It fills the frontend equivalent of PRD/pre-mortem.

**Framework (6 questions before any UI work):**

1. **User Mental Model.** How does the user think about this? What metaphor are they carrying? What do they expect to see? A user who thinks "dashboard" expects cards and metrics. A user who thinks "report" expects narrative flow.

2. **Information Architecture.** What is the hierarchy of information? What is most important? What is supporting? Map content to the emphasis tier framework (Hero / Primary / Secondary / Supporting) before selecting components.

3. **Interaction Flow.** What is the happy path? Where can the user get lost? What are the 3 most common actions? Design for those 3 actions to be effortless. Everything else can require effort.

4. **Cognitive Load Budget.** How many things can the user process at once in this view? Research says 4 plus or minus 1 chunks. Count the distinct information groups on the page. If you exceed 5, split or collapse.

5. **Emotional Journey.** What should the user FEEL at each step? An audit report should build from concern ("your search scores 3/10") to confidence ("here's what Algolia fixes") to urgency ("your competitors already moved"). Map the emotional arc before choosing components.

6. **Design Pre-Mortem.** What makes a user bounce in the first 5 seconds? What looks "generic AI"? What breaks on mobile? What fails in dark mode? What is inaccessible? Run the Tigers/Paper Tigers/Elephants analysis on the UI specifically.

### The Thinking Flow

When a new feature, module, or product arrives, the thinking skills activate in sequence:

```
Idea arrives
  |
  v
thinking:strategy ---- "Does this fit the product strategy?"
  |
  v
thinking:value-prop --- "What's the JTBD? Who/Why/How/What after?"
  |
  v
thinking:assumptions -- "What are we assuming? Which are riskiest?"
  |
  v
thinking:ost ---------- "Outcome > Opportunities > Solutions > Experiments"
  |
  v
thinking:prd ---------- "Write the spec (8 sections)"
  |
  v
thinking:pre-mortem --- "Tigers? Paper Tigers? Elephants?"
  |
  v
[If UI work] thinking:design-thinking --- "Mental model? IA? Flow? Load? Emotion? Pre-mortem?"
  |
  v
Ready for implementation planning
```

Not every feature needs all 7 steps. A small bug fix skips straight to implementation. A new product needs all of them. The developer uses judgment.

---

## 5. Layer 3: Standards Skills

### The Problem

SOPs exist in the Obsidian vault. They're well-written and comprehensive. But they're passive. Claude has to be told "go read CodingSOPs.md" and then hope it follows every rule. No checkpoints. No validation. No blocking.

Meanwhile, CLAUDE.md copies SOP content to get it "always loaded," but this creates duplication, context waste, and drift.

### The Design

Standards skills are NOT copies of SOPs. They are thin wrappers that:
1. READ the relevant vault SOP at invocation time (always current, single source of truth)
2. Extract validation criteria from the SOP
3. Check current work against those criteria
4. Block or flag violations

They are validation gates, not reference documents.

#### 5.1 Standards Skills Catalog

| Skill | Vault Source | What It Validates |
|-------|-------------|-------------------|
| `standards:coding` | Standards/CodingSOPs.md | Error handling (try/catch on all external calls), logging (structured, leveled, mandatory), SOLID principles, DRY, naming conventions, function rules (max 20 lines, max 3 params, type hints), comments (why not what), formatting (ruff, mypy), security (no secrets), git commits |
| `standards:testing` | Standards/TestingSOPs.md | TDD (test first always), 3 test layers (unit/integration/contract), test file structure, test naming convention, what to test, what NOT to test, mock strategy (adapter injection), Definition of Done (6 checkboxes) |
| `standards:writing` | Standards/WritingSOPs.md | No em-dashes (zero, universal), no AI tells (12 banned constructions), concrete over abstract, active voice, one idea per sentence, through-line, pyramid structure, named over generic, voice register, AI-assisted writing rules |
| `standards:uiux` | Standards/UIUXDesignSOP/ (10 files) | Component rules (cards, tables, navigation, badges, data-viz, layout, animations, interactive), brand compliance (Algolia vs generic), emphasis tier framework, accessibility (WCAG 2.2 AA), responsive design, dark mode |

#### 5.2 Aesthetics Library (from awesome-design-skills)

In addition to the standards skills above, the stack includes a library of design language specifications cherry-picked from bergside/awesome-design-skills. These are NOT validation gates. They are aesthetic DNA: token sets, typography, colors, and component styling rules for specific visual directions.

| Aesthetic | When to Use |
|-----------|------------|
| `aesthetic:dashboard` | PRISM dashboards, data-heavy views. Dark theme, IBM Plex Sans, glass panels, modular grids. |
| `aesthetic:enterprise` | Enterprise-facing UIs, AE/BDR tools. Clean, high-contrast, Ubuntu font, structured layouts. |
| `aesthetic:editorial` | Audit reports, leave-behinds. Magazine-quality presentation of findings. |
| `aesthetic:clean` or `aesthetic:minimal` | Simple tools, single-purpose views. Maximum signal, minimum noise. |
| `aesthetic:professional` | Default fallback when no specific aesthetic fits. |

These compose with the frontend-design skill: the frontend-design skill says WHICH component to use (via decision matrix). The aesthetic says HOW that component should look and feel.

#### 5.3 How Standards Skills Work (Technical)

```
Invocation: standards:coding
  |
  Step 1: Read ~/...Obsidian/.../Standards/CodingSOPs.md
  |
  Step 2: Extract validation criteria as checklist
  |
  Step 3: Review current work (files changed in this session)
  |
  Step 4: For each criterion:
  |         - PASS: criterion met
  |         - WARN: criterion partially met, flag for attention
  |         - FAIL: criterion violated, block until fixed
  |
  Step 5: Report results with file:line references
```

The skill reads the vault SOP every time. If the SOP is updated (e.g., function max length changes from 20 to 30 lines), the next invocation picks up the change. No re-deployment. No sync. Single source of truth.

---

## 6. Layer 4: Process Skills (Superpowers)

### The Design

Superpowers skills remain **unmodified and generic**. They handle workflow discipline: TDD red-green-refactor, systematic debugging, verification-before-completion, writing plans, executing plans, brainstorming, code review, git worktrees.

They are community-maintained (currently at v5.0.7) and will continue to evolve. The cognitive stack does NOT fork them. Instead, it composes them with standards skills at checkpoints.

#### 6.1 Composition: The Double Superpower

This is where the multiplicative effect happens. Process skills invoke standards skills at natural checkpoint moments:

**TDD Workflow (superpowers:test-driven-development):**
```
RED: Write failing test
  +-- CHECKPOINT: standards:testing validates test structure
      (3 layers? correct naming? mock adapter pattern?)

GREEN: Write minimal code to pass
  +-- CHECKPOINT: standards:coding validates implementation
      (error handling? logging? types? function length?)

REFACTOR: Clean up
  +-- CHECKPOINT: standards:coding validates quality
      (DRY? naming? SOLID?)
```

**Code Review (superpowers:requesting-code-review):**
```
Review pass:
  +-- CHECKPOINT: standards:coding (full validation)
  +-- CHECKPOINT: standards:testing (coverage, contract tests, Definition of Done)
  +-- CHECKPOINT: standards:writing (docstrings, comments, no AI tells)
  +-- CHECKPOINT: standards:uiux (if frontend changes)
```

**Brainstorming (superpowers:brainstorming):**
```
Before presenting design:
  +-- CHECKPOINT: thinking:assumptions (what are we assuming?)
  +-- CHECKPOINT: thinking:pre-mortem (what could go wrong?)
```

**Frontend Work (frontend-design + aesthetics):**
```
Before coding:
  +-- CHECKPOINT: thinking:design-thinking (mental model, IA, flow, load, emotion)

During coding:
  +-- CHECKPOINT: standards:uiux (component rules, accessibility, dark mode)
  +-- LOAD: aesthetic:dashboard (or whichever aesthetic applies)

After coding:
  +-- CHECKPOINT: process:design-review (visual quality, responsiveness, generic AI detection)
```

**Single Superpower:** Process enforcement OR standards enforcement.
**Double Superpower:** Process enforcement x Standards enforcement, composed at checkpoints. The process skill ensures you follow the right workflow. The standards skill ensures the output meets YOUR definition of quality. Neither alone gives you what both together give you.

#### 6.2 New Process Skill: process:design-review

This skill does not exist in superpowers. It fills the frontend equivalent of code review.

**Design Review Checklist:**
1. Does the UI match the intended aesthetic (by name, e.g., "dashboard" or "editorial")?
2. Does the emphasis tier assignment hold? (Only 1 Hero per section? Primary content is actually primary?)
3. Does the layout work at 375px, 768px, 1024px, 1280px?
4. Does dark mode work without broken contrast or invisible elements?
5. Does it pass WCAG 2.2 AA? (Keyboard navigation, focus states, color contrast, screen reader labels)
6. Would a user recognize this as "designed" rather than "generated"? (The generic AI detection question)
7. Does the interaction flow match the thinking:design-thinking analysis?

---

## 7. Layer 5: Domain Skills

Existing Algolia/PRISM skills. No changes needed from this architecture. They operate at the execution level, above the cognitive infrastructure.

- `algolia-intel-*` (12 research modules)
- `algolia-audit-*` (browser testing, scoring, reports, factcheck)
- `algolia-synth-*` (business case, sales plays)
- `algolia-campaign-*` (ABX outreach)

These skills already follow the module-as-agent pattern defined in the PRISM unified architecture. The cognitive stack provides the infrastructure BENEATH them: thinking skills decide what to build, standards skills validate quality, process skills enforce discipline.

---

## 8. Layer 6: Build Engine (Future)

The machine that builds autonomously. Three agents:

- **Developer Agent.** Receives a task specification. Follows the cognitive stack: reads standards skills, follows process skills, produces code that passes all validation gates.
- **QA Agent.** Receives the developer's output. Validates against standards skills. Writes tests per standards:testing. Runs the verification-before-completion process.
- **Dispatcher Agent.** Reads the TODO list. Assigns tasks to Developer/QA pairs. Tracks progress. Handles dependencies and sequencing.

This layer is Phase 6 of the implementation plan. It requires Layers 1-4 to be solid before it can operate, because the agents need enforceable standards and processes to follow autonomously.

---

## 9. Backend/Frontend Parity

The cognitive stack maintains structural parity between backend and frontend at every layer. Every cognitive function exists for both:

| Cognitive Function | Backend | Frontend |
|-------------------|---------|----------|
| **Thinking** | PRD, pre-mortem, OST, assumptions, strategy, value-prop | Design thinking (mental model, IA, interaction flow, cognitive load, emotional journey, design pre-mortem) |
| **Standards** | CodingSOPs, TestingSOPs, WritingSOPs | UIUXDesignSOP + aesthetics library (design language specifications) |
| **Process** | TDD, debugging, verification, code review | Design review, visual regression, a11y audit, generic AI detection |
| **Execution** | Superpowers workflows | frontend-design skill + ui-architect + aesthetic skins |

If a new cognitive function is added to one side, the other side must be evaluated for the equivalent.

---

## 10. Context Orchestration

### The Problem

Six layers of skills. If every task loads thinking skills + standards skills + process skills + domain skills + aesthetics library, the context window drowns in instructions.

### The Loading Protocol

**Always loaded (Layer 1):** CLAUDE.md (~50 lines). Identity, cardinal rules, pointers. Present in every message.

**Loaded on task start (Layer 4):** The relevant process skill. If you're coding, TDD loads. If you're debugging, systematic-debugging loads. One process skill at a time.

**Loaded at checkpoints (Layer 3):** Standards skills load when invoked by process skills at checkpoint moments. standards:coding loads during GREEN phase of TDD. standards:testing loads during RED phase. They don't persist; they validate and release.

**Loaded on demand (Layer 2):** Thinking skills load when starting a new feature or product decision. They run their framework, produce an artifact (PRD, pre-mortem analysis, OST), and release. The artifact persists on disk; the skill releases context.

**Loaded on domain work (Layer 5):** Domain skills load for specific audit/research tasks. One domain skill at a time.

**Dormant (Layer 6):** Build engine agents are separate processes. They don't share the main context window.

### The Rule

No more than 2 skills loaded simultaneously: one process skill (Layer 4) and one standards/thinking skill (Layer 2-3) at the checkpoint. Everything else loads sequentially.

### The Workspace: Working Memory for Complex Tasks

Skills produce artifacts. Thinking skills produce specs, risk analyses, assumption maps. Process skills produce test results, verification evidence. When a task involves multiple skills in sequence (PRD then pre-mortem then plan then TDD), the context window fills up and compaction erases intermediate state. The next skill loses the previous skill's output. The chain breaks.

**The workspace solves this.** It is a per-feature directory in the repo where every skill writes its output to disk as it completes. The next skill reads from disk, not from context. Compaction can't erase what's on disk.

**Location:** `docs/workspace/{feature-name}/` in the repo.

Why the repo, not the vault:
- Claude reads and writes rapidly during active work. No Google Drive sync latency.
- Right next to the code being built. Zero path complexity.
- Git-tracked, so you can see how thinking evolved across drafts.
- Clearly temporary. Cleaned up when the feature ships.

**Structure:**

```
docs/workspace/{feature-name}/
  01-strategy.md           <- thinking:strategy output
  02-value-prop.md         <- thinking:value-prop output
  03-assumptions.md        <- thinking:assumptions output
  04-prd.md                <- thinking:prd output
  05-pre-mortem.md         <- thinking:pre-mortem output
  06-design-thinking.md    <- thinking:design-thinking output (if frontend)
  scratchpad.md            <- free-form notes, partial decisions, open questions
  _status.md               <- current step, what's done, what's next, what to re-read
```

**How skills use the workspace:**

1. Before running, read `_status.md` to understand where we are and what came before.
2. Read any numbered outputs from previous steps that are relevant to the current step.
3. Produce output. Write it to the next numbered file.
4. Update `_status.md` with: what just completed, what's next, which files to read.

If compaction happens between steps, Claude reads `_status.md` and reconstructs context from the workspace files. Nothing is lost.

**The scratchpad.md file** captures anything in-flight: partial ideas, questions to revisit, things Claude noticed but hasn't acted on, context that needs to survive compaction but doesn't fit in a structured output. This is the "whiteboard" of the workspace.

**When the feature ships: selective archival.**

Not everything in the workspace is worth keeping. Most of it produced a finished deliverable (spec, plan) that already lives in `docs/specs/`. The protocol:

1. Final deliverables (spec, plan) are already in `docs/specs/`. Nothing to move.
2. Review the workspace: any decisions or reasoning NOT captured in the deliverable?
   - YES: Promote those specific files to the vault at `Projects/PRISM/Workspace-Archive/{feature-name}/`.
   - NO: The deliverable has everything. Nothing to archive.
3. Delete the workspace: `rm -rf docs/workspace/{feature-name}/`

The vault stays clean: curated knowledge, not scratchpad noise. The repo stays practical: active workspaces during development, cleaned up after.

---

## 11. The Learning Loop

### The Problem

The stack covers thinking (before building), process (during building), and verification (after building). But it has no retrospective. After something ships and runs, how does the system learn whether the thinking was right?

### The Design

A lightweight post-implementation review that runs after major milestones. Not a separate skill. A protocol:

1. **Revisit assumptions.** Pull up the thinking:assumptions output from before building. Which assumptions held? Which broke? What did we learn?
2. **Revisit the pre-mortem.** Which Tigers materialized? Which were Paper Tigers in hindsight? Which Elephants became real problems?
3. **Update the vault.** If a pattern emerged (e.g., "Perplexity Agent API consistently underperforms on financial data"), add it to the relevant SOP or architecture doc.
4. **Update memory.** Save the lesson as a feedback memory so future sessions benefit.

This loop closes the circuit: Thinking --> Building --> Shipping --> Learning --> Better Thinking.

---

## 12. Implementation Phases

| Phase | What | Effort | Impact | Depends On |
|-------|------|--------|--------|------------|
| **0** | This design doc (you're reading it) | Done | Foundation. Everything references this. | Nothing |
| **1** | Slim CLAUDE.md (400 --> 50 lines) | 1 hour | Immediate. Saves context every message. Eliminates SOP duplication. | Phase 0 |
| **2** | Build 4 standards skills (coding, testing, writing, uiux) | 1 session | Quality gates become invocable. Replace the SOP content removed from CLAUDE.md. | Phase 1 |
| **3** | Adapt 7 PM thinking skills | 1 session | The "what to build and why" layer activates. Structured decision-making before building. | Phase 0 |
| **4** | Build thinking:design-thinking + cherry-pick 5 aesthetic skins | 1 session | Frontend parity. Design decisions get the same rigor as backend. | Phase 3 |
| **5** | Wire composition (process skills invoke standards skills at checkpoints) | 1 session | Double superpower activates. TDD invokes standards:testing. Code review invokes standards:coding. | Phases 2 + 4 |
| **6** | Build engine (developer + QA + dispatcher agents) | Multiple sessions | The machine builds autonomously. | Phases 1-5 |

Phases 1-2 are the critical path. They deliver the highest-impact change (context savings + quality enforcement) with the lowest effort. Phases 3-4 can run in parallel with Phase 2.

---

## 13. Sources and Provenance

| Source | What We Take | License | How We Use It |
|--------|-------------|---------|---------------|
| **Personal SOPs (Obsidian vault)** | CodingSOPs.md, TestingSOPs.md, WritingSOPs.md, FolderStructure.md, UIUXDesignSOP/ (10 files), Architecture/Manifesto.md | Private | Standards skills read these at runtime. Single source of truth. |
| **Superpowers v5.0.7** (claude-plugins-official) | TDD, debugging, verification, brainstorming, planning, code review, git worktrees | License in plugin | Used unmodified. Composed with standards skills at checkpoints. Not forked. |
| **pm-skills** (phuryn/pm-skills) | 7 of 65 skills: create-prd, pre-mortem, identify-assumptions-new, prioritize-assumptions, opportunity-solution-tree, product-strategy, value-proposition | MIT | Adapted to our context. Installed as thinking:* skills. |
| **awesome-design-skills** (bergside/awesome-design-skills) | 5 of 58 aesthetic skins: dashboard, enterprise, editorial, clean/minimal, professional | MIT | Cherry-picked. Installed as aesthetic:* references. |
| **awesome-design-md** (VoltAgent/awesome-design-md) | Concept only (brand-quality benchmarks). Content moved to external URLs. | MIT | Reference, not installed. "Build this like Linear" as a meaningful instruction. |
| **superdesign** (superdesigndev/superdesign) | Nothing. VS Code extension, not a knowledge resource. | N/A | Skipped. |
| **frontend-design** (claude-plugins-official) | 52-component design system with emphasis tiers, brand toggle, decision matrix | License in plugin | Used as-is. Composed with aesthetics library and standards:uiux. |

---

## 14. Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Six-layer architecture (Identity, Thinking, Standards, Process, Domain, Build Engine) | Each layer has a distinct cognitive function. Merging them loses the distinction. Composing them at checkpoints creates the multiplicative "double superpower" effect. |
| 2 | CLAUDE.md slim-down (400 --> 50 lines) | SOP content in CLAUDE.md duplicates the vault, wastes context, and drifts from the source of truth. Move to on-demand standards skills. |
| 3 | Standards skills read vault SOPs at runtime | Single source of truth. No duplication. No sync. No drift. SOP updates are picked up on next invocation. |
| 4 | Superpowers used unmodified, not forked | Superpowers is community-maintained and evolving (v5.0.7). Forking creates maintenance burden and drift. Composition via checkpoints preserves updatability. |
| 5 | 7 of 65 pm-skills adapted (not all) | Most pm-skills target team PMs with sprints, retros, and stakeholder ceremonies. Solo builder-architect context needs only thinking frameworks, not team processes. |
| 6 | 5 of 58 design aesthetics cherry-picked | Full library is noise. Selected aesthetics match actual use cases: dashboards, enterprise UIs, reports, minimal tools. |
| 7 | thinking:design-thinking created new (not from any repo) | No existing repo provides the frontend equivalent of PRD/pre-mortem. The 6-question framework (mental model, IA, interaction flow, cognitive load, emotional journey, design pre-mortem) fills this gap. |
| 8 | process:design-review created new | No existing repo provides the frontend equivalent of code review. The 7-point checklist (aesthetic match, emphasis tiers, responsive, dark mode, a11y, generic AI detection, flow match) fills this gap. |
| 9 | Max 2 skills loaded simultaneously | Context window management. One process skill + one standards/thinking skill at checkpoints. Sequential loading for everything else. |
| 10 | Learning loop as protocol, not skill | Lightweight post-implementation review. Revisit assumptions, revisit pre-mortem, update vault, update memory. Runs after major milestones, not every task. |
| 11 | Backend/frontend parity as architectural constraint | Every cognitive function (thinking, standards, process, execution) must exist for both backend and frontend. If a new function is added to one side, evaluate the other. |
| 12 | Build engine requires Layers 1-4 solid first | Autonomous agents need enforceable standards and processes. Building the engine before the standards exist produces agents that build fast but build wrong. |
| 13 | Workspace in repo, archive in vault | Workspace needs fast read/write during active work (no Drive sync latency). Archive is curated knowledge worth keeping. Different lifecycles, different locations. Selective archival: only promote workspace files that contain reasoning not captured in the final deliverable. |

---

## 15. Open Questions

1. **Standards skill invocation protocol.** Should process skills invoke standards skills automatically (always), or should the developer choose when to invoke? Automatic is safer but heavier. On-demand is lighter but discipline-dependent.

2. **Aesthetic composition with frontend-design.** The frontend-design skill has its own theme system (algolia/generic/custom). How do the awesome-design-skills aesthetics layer on top? Override the theme? Supplement it? Replace it for specific projects?

3. **Thinking skill depth calibration.** Not every feature needs 7 thinking steps. A bug fix needs zero. A new product needs all 7. Where are the thresholds? Who decides?

4. **Cross-project portability.** This architecture is designed for PRISM but the layers are project-agnostic. Standards skills read project-specific SOPs. Thinking skills are universal. Can this be packaged for other developers?

5. **Skill versioning.** When Superpowers updates from 5.0.7 to 6.0, how do we verify that composition still works? When vault SOPs change, how do we verify standards skills still validate correctly?

---

## 16. The Thesis

Most developers using AI assistants have one enforcement surface: either process workflows (how you work) or quality standards (what good looks like). Having both, composed at runtime checkpoints, creates a multiplicative effect. The process skill ensures discipline. The standards skill ensures YOUR definition of quality. Neither alone gives you what both together give you.

Add a thinking layer before building and a learning loop after shipping, and you have a complete cognitive operating system: the machine that thinks before it builds, enforces quality while it builds, verifies after it builds, and learns from what it built.

This is the cognitive stack. It's the machine that builds the machine.
