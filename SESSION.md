# SESSION.md — PRISM About-page splash + hub restructure + Cassandra + vault update

**Status:** About/splash page redesign DONE + LIVE; site restructured (About = `/`); Cassandra rename +
portrait done; detect-search vendored; Wave-2 unblocked. All 3 repos pushed/synced. **Vault wiki update
was running in a background fork at persist time** (verify on resume).

**Last updated:** 2026-06-30

---

## RESUME ACTION (do first, in order)
1. Read this file + `memory/MEMORY.md`.
2. **Verify the vault fork finished.** A fork was writing the PRISM wiki at
   `~/Library/CloudStorage/GoogleDrive-arijit.chowdhury@algolia.com/My Drive/AI-Docs/Obsidian/ArijitOS-Brain/Projects/PRISM/`
   (6 new ADRs dated 2026-06-30, dev-log entries, `wiki/entities/` pages for prism/scout/hermes/cassandra/
   detect-search/gemini/yfinance/chrome, a `right-tool-for-each-job` concept, index/log/open-questions updates).
   Check `wiki/decisions/` for the 2026-06-30-*.md files + that `wiki/entities/` exists. If incomplete,
   finish via record-knowledge "record this".
3. Use `dangerouslyDisableSandbox:true` on every VPS bash (`ssh chowmes-vps`).
4. Work the PENDING items below.

---

## WHAT SHIPPED THIS SESSION (all live + pushed, prism-hub `feat/prism-vps-hosting`)

### The About / splash page (the big work) — repo `~/prism-hub`, file `index.html`
Demo centerpiece for Friday (200 people). Built ENTIRELY as static vanilla HTML/CSS/JS (NO React/GSAP/
Tailwind — the site is static + auto-deployed). Pieces:
- **Premium prism hero** — glassy gradient prism, glowing refracted spectrum, traveling light beam,
  shimmer (SVG + CSS anim, reduced-motion guard). Replaced the flat wireframe.
- **Inside-the-audit tour** — auto-cycling cross-fade of FULL audit screenshots (Overview→Research→
  Search Audit→Business Case→Sales Actions→chat), 3.8s, hover-pause. `assets/tour/*.png` (full-viewport
  WITH the audit's own chrome — user preferred this over cropped). NO external pill tabs (they duplicated
  the screenshot's own tab bar).
- **MagicBento deliverables** — vanilla port: spotlight + reactive border-glow + 3D tilt + magnetism +
  particles + ripple, LIGHT theme. Bento layout (deck wide, chat-agent featured/dark/wide).
- **Glowing-edge role cards** (AE/BDR/Leader) — pointer-following conic glow + halo, masked to the arc
  nearest cursor. Top colored accent lines REMOVED.
- **Shared animated-grid background** — `assets/grid-bg.js` (one lib); index + about + audits show the
  same pulsing grid. About bands made transparent so the grid shows through.
- **Plain-English copy** — rewrote Hermes/Cassandra + skills sections (dropped jargon: claude-cli, agent
  runtime, grounding gate, report-QA, keyless). Skill count `~23` → `22`.
- **NO EM DASHES** on `/` and `/reports/` (grammar rewritten). Global rule [[feedback-no-em-dashes]].
  Audit report pages LEFT with em dashes (user: "let them be").
- Section order set by user: Who it's for → What it produces → How it works → Inside the audit →
  The skills → The execution layer.

### Site restructure (routing)
- `/` serves the **About splash** (was the reports list). Hero CTA "Browse the audits" + topbar
  "Reports" → `/reports/`.
- `/reports/` = audit list (old index; card links absolutized `/{slug}/`; "About" → `/`).
- `/about/` = redirect to `/`. Canonical About content lives in ROOT `index.html`; `about/index.html`
  is the redirect stub.
- Audit-page logos still link to `/` (= About). OPEN: point to `/reports/`? (template + 16-page render).

### GitHub → VPS auto-deploy
Push to `origin/feat/prism-vps-hosting` → GitHub webhook → `prism-deploy-hook.service` (Node) →
`git pull /opt/prism-hub` → live in seconds. No scp. [[reference-prism-hub-autodeploy]].

### Cassandra (rename + portrait + housekeeping)
- Rename **Cass → Cassandra** everywhere incl SOUL.md + AGENTS.md (`/root/.hermes-prism/`, sudo; 0
  standalone "Cass"). SOUL frozen per session → **all Hermes sessions wiped** so new chats use new SOUL.
- Portrait: 4 via Imagen 4 on the VPS gemini key; user picked **cass-2**. SPA chat avatar
  `/assets/cassandra.png` (live). Telegram avatar DONE (user uploaded `cassandra-telegram-640x360.png`
  via BotFather, 2026-06-30). Same face on SPA + Telegram now.
- `sessions.auto_prune: true`, `retention_days: 7` in config.yaml (restarted). No custom cron.
- [[reference-vps-image-gen-imagen-telegram-avatar]].

### detect-search
Vendored into `arijit-skills/skills/detect-search/` (pushed to main); `~/.claude/skills/detect-search`
is a SYMLINK into the repo (backup `.prelink-bak-20260629`). Runs on VPS (`--full-tech` → Algolia on
petsmart, 14 categories).

### Wave-2 SimilarWeb blocker — RESOLVED
User manually captured logged-in SimilarWeb screenshots (10 tabs × 7 companies: dell, footlocker, jbl,
michaelkors, thenorthface, torrid, autozone) at `PIP/docs/temp/similarweb-wave2/`. Traffic now comes
from those screenshots, not the dead API. Wave-2 audits fully keyless + runnable.
[[feedback-wave2-blocker-similarweb-mcp]].

---

## DECISIONS LOCKED THIS SESSION
- About = splash at `/`; reports → `/reports/`; `/about/` redirects.
- Port any sent React/shadcn/GSAP component to **vanilla** (static site). [[feedback-port-react-to-vanilla]]
- No em dashes in reader-facing copy. [[feedback-no-em-dashes]]
- Cassandra (never "Cass"); cass-2 portrait; auto_prune 7d.
- Audit report pages keep their em dashes.

## PENDING / NOT DONE (no false claims)
- **Vault fork** — verify it completed (resume step 2).
- ~~Telegram avatar~~ — DONE (user uploaded `cassandra-telegram-640x360.png` via BotFather 2026-06-30).
- **Audit-page logos** → decide `/` vs `/reports/`.
- **Wave-2 e2e audits** (7) — NOT run; now unblocked. "Cassandra runs audit e2e" chat-trigger NOT built.
- **OAuth token rotation** — not done (older item).
- Audit pages still have em dashes (intentional).

## KEY FILES
- `~/prism-hub/index.html` (About splash, canonical) · `reports/index.html` (audit list) ·
  `about/index.html` (redirect) · `assets/grid-bg.js` · `assets/cassandra.png` ·
  `assets/cassandra-telegram-640x360.png` · `assets/tour/*.png` · `chat-widget.js`.
  Unused: `assets/parallax/*.png` (failed parallax), `assets/covers/*.png`, `assets/cass-candidates/`.
- VPS: `/opt/prism-hub` (git auto-pull) · `/opt/prism-deploy-hook/` · `/root/.hermes-prism/`
  (SOUL.md, AGENTS.md, config.yaml).
- Vault: `Projects/PRISM/` (wiki).

## REPOS (all synced at persist)
- prism-hub `feat/prism-vps-hosting` · PIP `feat/prism-e2e-cycle` · arijit-skills `feat/gemini-grounded-search`

---

## HANDOFF BOOTSTRAP (paste into a fresh session)
> Resuming PRISM. Read `/Users/arijitchowdhury/Dropbox/AI-Development/PIP/SESSION.md` + its `memory/MEMORY.md`
> first. FIRST verify the vault wiki fork finished (Projects/PRISM/ — 6 ADRs dated 2026-06-30 +
> wiki/entities/); finish it if not. Use `dangerouslyDisableSandbox:true` on every `ssh chowmes-vps`.
> Rules: port React components to vanilla (static site); NO em dashes in copy; right tool per job
> (Scout/Gemini/detect-search/yfinance/chrome); no fabrication. Then work the PENDING list.
