#!/usr/bin/env bash
# PRISM executor v2 — run the Algolia Search Audit headlessly via Claude CLI.
#
# STAGED, NOT DEPLOYED. v2 of the live /opt/prism-executor/run-audit.sh (see
# docs/workspace/cassandra-tooling/live-sources/run-audit.sh for the exact code
# this conforms to / extends). Deploy plan: docs/workspace/cassandra-tooling/DEPLOY-PLAN.md.
#
# READ RECEIPT (protocol-read-receipt.md): the live script's positional-arg
# contract is `run-audit.sh <domain>` (live-sources/run-audit.sh:24-30) and its
# `claude -p` invocation is one hardcoded prompt string + a fixed --allowed-tools
# list (live-sources/run-audit.sh:68-80). v2 keeps `<domain>` as arg 1
# UNCHANGED (drop-in compatible with the live runner's v1 `["...", RUN_AUDIT,
# job["domain"]]` call) and ADDS optional --phase/--skill/--skip flags parsed
# AFTER it, which swap the hardcoded full-run prompt for a targeted one.
#
# Muscle (right tool for the job):
#   - Scout (127.0.0.1:8421)            → acquire the TARGET's own data (company, careers/jobs, IR)
#   - Gemini-grounded Google search     → open-web research (scripts/gemini_search.py)
#   - claude-cli algolia-* skills       → the audit engine (orchestrated by the run)
#   - chrome MCP                        → live browser search testing
#
# Auth: Claude SUBSCRIPTION via CLAUDE_CODE_OAUTH_TOKEN (the pay-per-token API key is
#       credit-empty — and would OVERRIDE the token, so we unset it).
#
# Usage:
#   ./run-audit.sh <domain>                              full pipeline (unchanged v1 behaviour)
#   ./run-audit.sh <domain> --phase traffic               only the named phase
#   ./run-audit.sh <domain> --skill algolia-intel-traffic only the named skill
#   ./run-audit.sh <domain> --skip similarweb-login       full run, skip a named step
# Output: audits/<slug>/   (research files, browser screenshots, deliverables)
set -euo pipefail

EXEC_DIR="/opt/prism-executor"
SKILLS_DIR="/home/chowmesadmin/.claude/skills"     # claude-cli skill discovery path
OAUTH_ENV="${EXEC_DIR}/.claude-oauth.env"          # CLAUDE_CODE_OAUTH_TOKEN
RUN_ENV="${EXEC_DIR}/.run.env"                      # GEMINI_API_KEY + SCOUT_API_KEY/URL
MCP_CONFIG="${EXEC_DIR}/.mcp.json"
MCP_ENV="${EXEC_DIR}/.mcp.env"

DOMAIN="${1:-}"
if [[ -z "${DOMAIN}" ]]; then
  echo "ERROR: domain required.  usage: $0 <domain> [--phase <name>|--skill <name>] [--skip <name>]" >&2
  exit 64
fi
# Reject anything that looks like a flag (e.g. --help, -h, a typo'd/unknown
# flag) instead of silently treating it as a domain and launching a real
# audit against garbage input. No valid domain starts with '-'.
if [[ "${DOMAIN}" == -* ]]; then
  echo "ERROR: '${DOMAIN}' looks like a flag, not a domain.  usage: $0 <domain> [--phase <name>|--skill <name>] [--skip <name>]" >&2
  exit 64
fi
shift || true

# --- v2: optional targeted-run flags (default = full run, v1-identical) ---
PHASE=""
SKILL=""
SKIP=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --phase) PHASE="${2:-}"; shift 2 ;;
    --skill) SKILL="${2:-}"; shift 2 ;;
    --skip)  SKIP="${2:-}"; shift 2 ;;
    *) echo "WARNING: ignoring unknown arg '$1'" >&2; shift ;;
  esac
done
if [[ -n "${PHASE}" && -n "${SKILL}" ]]; then
  echo "ERROR: --phase and --skill are mutually exclusive." >&2
  exit 64
fi
case "${PHASE}" in
  ""|research|browser|report|factcheck) : ;;
  *) echo "ERROR: --phase must be one of research|browser|report|factcheck (got '${PHASE}')." >&2; exit 64 ;;
esac

SLUG="$(echo "${DOMAIN}" | sed -E 's#^https?://##; s#^www\.##; s#/.*$##; s#\.[a-z.]+$##; s#[^a-zA-Z0-9]+#-#g' | tr 'A-Z' 'a-z')"
OUT_DIR="${EXEC_DIR}/audits/${SLUG}"

# --- auth: subscription token, NOT the dead API key ---
if [[ ! -f "${OAUTH_ENV}" ]]; then
  echo "ERROR: ${OAUTH_ENV} missing — run 'claude setup-token' as chowmesadmin and save CLAUDE_CODE_OAUTH_TOKEN there." >&2
  exit 69
fi
unset ANTHROPIC_API_KEY                 # API key would override the subscription token
set -a
source "${OAUTH_ENV}"
[[ -f "${RUN_ENV}" ]] && source "${RUN_ENV}"
set +a
: "${CLAUDE_CODE_OAUTH_TOKEN:?CLAUDE_CODE_OAUTH_TOKEN not set in ${OAUTH_ENV}}"
: "${GEMINI_API_KEY:?GEMINI_API_KEY not set in ${RUN_ENV} (open-web research muscle)}"
: "${SCOUT_API_KEY:?SCOUT_API_KEY not set in ${RUN_ENV} (acquisition muscle)}"
export SCOUT_URL="${SCOUT_URL:-http://127.0.0.1:8421}"
export ALGOLIA_AUDIT_DIR="${EXEC_DIR}/audits"

# The browser-testing wave is a long-running background task and can legitimately take
# 60+ minutes (WAF cooldowns, retries). claude -p's default 600s background-task ceiling
# force-terminates it early, then the script still exits 0 with no audit-data.json produced
# (false-success). Wait indefinitely instead.
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0

# --- MCP: chrome (browser test) + apify (Google-News scraper) ONLY. ---
# No BuiltWith (removed — tech/vendor detection = detect-search network oracle + Scout
# source-scan). No Algolia MCP (no role in a prospect audit). No Yahoo MCP (yfinance is
# public — collect-financials.py uses it directly). APIFY_TOKEN (if set) feeds collect-news.
MCP_ARGS=()
if [[ -f "${MCP_CONFIG}" ]]; then
  MCP_ARGS=(--mcp-config "${MCP_CONFIG}" --strict-mcp-config)
  [[ -f "${MCP_ENV}" ]] && { set -a; source "${MCP_ENV}"; set +a; }
fi

mkdir -p "${OUT_DIR}"

# --- v2: build the prompt. Full run (PHASE/SKILL both empty) is byte-identical
# to the v1 prompt. A targeted run swaps in a scoped instruction on top of the
# same guardrails (Scout/Gemini muscle, no fabrication, workspace slug) — the
# orchestrator SKILL.md already understands --phase/--skill at the prompt
# level per its "Recovery Commands" convention (airtight plan §1.1).
BASE_GUARDRAILS="Acquisition of the company's own data (company context, executives, careers/jobs, IR) goes through SCOUT; \
open-web research (industry benchmarks, analyst quotes, news, competitor tech) goes through \
scripts/gemini_search.py (Gemini grounded Google search). Do NOT use WebSearch. No fabrication — a field \
with no grounded source stays blank. Use ${SLUG} as the workspace slug; write everything under ${OUT_DIR}/."

# SimilarWeb HITL mark-and-continue (plan §3.2): the traffic step needs a logged-in
# SimilarWeb session that this headless box doesn't have. Rather than fail the whole
# run, the skill is instructed to emit a literal, greppable marker and move on — the
# runner's detect_needs_human() watches for exactly this line to mark the module
# `needs_human` and let the rest of the audit continue.
SIMILARWEB_HITL="If the traffic/SimilarWeb step cannot complete because it requires an interactive login \
(no valid API key, or a login wall), do NOT fail or abort the run. Instead print the exact line \
'NEEDS_HUMAN:similarweb:login required for traffic data' on its own line, leave that section \
honestly marked incomplete in the output data (never fabricate traffic numbers), and continue on \
to the remaining sections/skills."

# Skill-level progress markers (new in v2, consumed by the runner's
# detect_skill_states()): before/after invoking each algolia-intel-*/algolia-audit-*
# skill, print '>>> SKILL START: <skill-name>' / '>>> SKILL DONE: <skill-name>' on
# their own lines so the runner can report granular per-skill status while the
# audit is still running.
SKILL_MARKERS="Before invoking each algolia-intel-* or algolia-audit-* skill, print the exact line \
'>>> SKILL START: <skill-name>' (using its real skill name, e.g. 'algolia-intel-traffic'); after it \
finishes, print '>>> SKILL DONE: <skill-name>'. Emit both lines even if that skill's step needs a human \
(print SKILL DONE after the NEEDS_HUMAN marker, not instead of it)."

if [[ -n "${SKILL}" ]]; then
  echo "PRISM audit -> ${DOMAIN} (slug=${SLUG}) — TARGETED skill run: ${SKILL}"
  PROMPT="Run ONLY the '${SKILL}' skill (not the full audit pipeline) for the prospect domain ${DOMAIN}, \
against the EXISTING workspace at ${OUT_DIR}/ (do not re-run other skills or re-scaffold the workspace; \
update just this skill's output file(s) in place). ${BASE_GUARDRAILS} ${SIMILARWEB_HITL} ${SKILL_MARKERS}"
elif [[ -n "${PHASE}" ]]; then
  echo "PRISM audit -> ${DOMAIN} (slug=${SLUG}) — TARGETED phase run: ${PHASE}"
  PROMPT="Run ONLY the '${PHASE}' phase of the algolia-search-audit skill (not the full pipeline) for the \
prospect domain ${DOMAIN}, against the EXISTING workspace at ${OUT_DIR}/ (do not re-run other phases or \
re-scaffold the workspace). ${BASE_GUARDRAILS} ${SIMILARWEB_HITL} ${SKILL_MARKERS}"
else
  echo "PRISM audit -> ${DOMAIN} (slug=${SLUG}) — muscle: Scout + Gemini-grounded + chrome (browser)"
  PROMPT="Run the algolia-search-audit skill end-to-end for the prospect domain ${DOMAIN}. \
${BASE_GUARDRAILS} Produce all research files, browser screenshots, scoring, factcheck, \
and the full deliverable package under ${OUT_DIR}/ using ${SLUG} as the workspace slug. \
${SIMILARWEB_HITL} ${SKILL_MARKERS}"
fi

if [[ -n "${SKIP}" ]]; then
  PROMPT="${PROMPT} Skip the '${SKIP}' step entirely this run (it was already handled / is intentionally excluded)."
fi

# Headless run. WebSearch is RETIRED — research goes through gemini_search.py (Bash) + Scout.
claude -p "${PROMPT}" \
  "${MCP_ARGS[@]}" \
  --add-dir "${SKILLS_DIR}" \
  --add-dir "${OUT_DIR}" \
  --permission-mode acceptEdits \
  --allowed-tools "Read,Write,Edit,Bash,Glob,Grep,Skill,Task,mcp__chrome__*,mcp__apify__*,mcp__crossbeam__*" \
  --output-format text \
  2>&1 | tee "${OUT_DIR}/run.log"

echo "DONE -> ${OUT_DIR}"
