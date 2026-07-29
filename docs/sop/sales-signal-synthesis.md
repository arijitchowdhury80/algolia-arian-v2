# SOP — Sales-Signal Synthesis (the "first-citizen, synthesize-hard" pass)

**Status:** active
**Owner code:** `generate-audit-data.py` (algolia-search-audit/scripts) — functions `lift_media_quotes()`, `lift_hiring_signals()`, `enrich_signals()`, `dedupe_merge_signals()`, `build_why_lead()`, `synthesize_signals()`.
**Owner doc:** `algolia-audit-report/SKILL.md` (Phase 5a-PATCH → "Sales-Signal Synthesis").
**Layer:** DATA / collation only. This SOP does NOT govern rendering.

---

## Why this exists (the Dell origin)

During the Dell audit the buying signals were treated as a raw dump: the same executive appeared five separate times (five near-identical scraped quotes), LinkedIn UI boilerplate leaked in as "quotes", nothing was scored, and an AE reading the deck could not tell which signal to open a call with. The instruction was to treat the buying signal as a **first-class citizen** and **synthesize hard** — turn the raw dump into a small set of clean, ranked, de-duplicated signals, each carrying a reason to lead with it.

That synthesis is deterministic (no LLM), so it runs in the collation code, not the prompt. The LLM writes raw signals; this pass cleans, scores, merges, and annotates them.

---

## The array this operates on: `intelligence_signals[]`

`intelligence_signals[]` in `{slug}-audit-data.json` is the single collated list of every buying signal. It is **preserved AND augmented** by the collation script — the LLM emits some entries, then the deterministic lifters append the rest, and the synthesis pass rewrites the whole array in place.

Signal `type` values in play: `earnings_quote`, `media_quote`, `executive_quote`, `hiring`, `hiring_signal`, `news_signal`, `social_signal`, `sec_risk`, `competitor`, `partner`.

---

## The process — four numbered steps (run in this order)

### 1. GATHER — one list from every intel output
Collect raw signals from social / news / hiring / investor / competitors into one list.
- The LLM synthesis writes some signals directly into `{slug}-audit-data.json`.
- `lift_hiring_signals(research_dir, hiring_obj)` converts the `hiring` object into `type='hiring'` signals (the renderer reads `intelligence_signals[type=='hiring']`, not the `hiring` object).
- `lift_media_quotes(research_dir)` lifts `media_quotes[]` from `11-investor-intelligence.json` into `type='media_quote'` signals.
- **Drop junk at the door.** UI-chrome and non-quote fragments (LinkedIn "Agree & Join", "Report this comment", author bios, cookie notices) are filtered in `lift_media_quotes` via `MEDIA_QUOTE_JUNK_MARKERS`. Conservative and deterministic — only obvious boilerplate.

### 2. SCORE — urgency + category (`enrich_signals`)
- `urgency_score` (int) = a type default (`URGENCY_BY_TYPE`) plus keyword boosts (leadership / CxO / funding language). Existing scores are never overwritten.
- `category_tag` = first match in `CATEGORY_KEYWORDS` (`ai_disruption`, `digital_transformation`, `cost_pressure`, `leadership_change`, `competitive_threat`, `tech_investment`, `expansion`), else `strategic_signal`.
- **Keyword matching uses a start word-boundary** (`_kw_hit`): the stem `ai` matches `ai` / `ai-native` but NOT `chairman` / `email`, while prefixes like `moderniz` / `appoint` still match their inflections. (This bug — `'ai'` matching inside `chairman` — mis-tagged Jeff Clarke's group as AI; fixed.)

### 3. DEDUPE / MERGE — collapse same-speaker quotes (`dedupe_merge_signals`)
- Quote-type signals (`media_quote`, `earnings_quote`, `executive_quote`, `exec`, `media`) that share the **same speaker** collapse into ONE grouped signal. Example: the multiple "Michael Dell, Chairman & CEO" quotes → one `CEO: AI priority` signal; the five John Roese quotes → one `CTO: AI priority (5 sourced statements)`.
- The individual quotes are preserved as nested `sub_quotes[]` (`{speaker, quote, source_url, source_name, source_date}`).
- The grouped signal takes the **max** member `urgency_score`, records `merged_count`, and synthesizes a headline: `<role>: <category> priority (<n> sourced statements)` where role is extracted from the speaker's title (CEO / CTO / CIO / CFO / …).
- **Conservative.** Only same-speaker quote-type signals merge. Event signals (news, hiring, competitor, partner) and unattributed quotes are never merged — each is a distinct event. A speaker with a single quote is left as a plain signal.

### 4. WHY_LEAD — the AE's reason to open with it (`build_why_lead`)
- Every signal gets a concise `why_lead` one-liner. Category-derived first (`WHY_LEAD_BY_CATEGORY`), signal-type fallback (`WHY_LEAD_BY_TYPE`), then a safe generic. Deterministic.

### Cross-cutting cleanup
- `drop_placeholder_fields` removes empty / placeholder string values (`''`, `-`, `—`, `n/a`, `null`, `[COLLECT_VIA_SKILL]`, `tbd`, …). No bare `—` angle entries ship.
- `_ensure_display_fields` guarantees each signal has a `text` (renderer reads `sig.text`) and a `badge_label` (schema requires one of `title` / `signal` / `badge_label` / `detail`). Backfill only.
- Bodyless signals (no readable text in any field) are dropped entirely.

---

## THE CONTRACT (data vs render — do not cross the line)

The synthesis is the **data** layer. It emits, per signal:

| Field | Meaning |
|---|---|
| `type` | signal type |
| `urgency_score` | int 1-10 (stable field — the render's tier + top-3 depend on it) |
| `category_tag` | one of the category tags above |
| `why_lead` | one-line AE lead reason |
| `text` / `badge_label` | display body + label (guaranteed present) |
| `source_url` / `source_name` / `source_date` / `confidence` | provenance |
| `sub_quotes[]` / `merged_count` | ONLY on grouped (merged) signals |

**Do NOT hardcode presentation into the data.** The render layer (index-template.html client JS) derives:
- the **tier** — RED ≥ 8, AMBER 6-7, GREEN ≤ 5 — from `urgency_score`;
- the **top-3 "key signals"** — the three highest `urgency_score`, color-coded.

Never write tier labels or a top-3 flag into the JSON. Keep `urgency_score` stable and let the template select. The template and `algolia-brand.css` are owned by a separate render process — this SOP must not touch them.

---

## Idempotency
`synthesize_signals()` is safe to re-run. Scores are only filled when absent; merged signals (already one-per-speaker) pass through unchanged; `why_lead` and display fields are recomputed harmlessly.

---

## Prevention heuristics (future me)
- **Substring keyword matching on short tokens is a landmine.** `'ai' in text` matches `chairman`, `campaign`, `certain`. Always use a start word-boundary for stems shorter than ~4 chars. See `_kw_hit`.
- **A speaker appearing N times is ONE priority, not N signals.** Merge by speaker before ranking, or the top-3 fills up with duplicates of the same person.
- **Scraped "quotes" are frequently UI chrome.** Filter LinkedIn / cookie / comment boilerplate at lift time, not after it has polluted the ranking.
- **Renderer field ≠ schema field.** The renderer reads `sig.text`; the schema wants `title|signal|badge_label|detail`. Guarantee both, or hiring signals render fine but fail `validate-json-schema.py`.
- **Data emits `urgency_score`; render owns tier + top-3.** If you find yourself writing a "tier" or "is_top_signal" field into the JSON, stop — that couples the data to one presentation.

---

## Divergence warning (2026-07-01)
There are TWO copies of `generate-audit-data.py`: `~/.agents/skills/...` (where this synthesis was implemented) and `~/.claude/skills/...` → the **arijit-skills repo** (the live pipeline path, per memory `reference-skills-symlinked-to-repo`). They have structurally diverged. For this synthesis to take effect in real audits, port it to the arijit-skills repo (the `.claude` symlink target) and commit. Verify which copy the VPS audit runner invokes before relying on either.
