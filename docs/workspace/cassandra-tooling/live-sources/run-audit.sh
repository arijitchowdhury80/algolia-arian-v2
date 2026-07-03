#!/usr/bin/env bash
# PRISM executor — run the Algolia Search Audit headlessly via Claude CLI.
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
# Usage:  ./run-audit.sh <domain>            e.g. ./run-audit.sh petsmart.com
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
  echo "ERROR: domain required.  usage: $0 <domain>" >&2
  exit 64
fi
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
echo "PRISM audit -> ${DOMAIN} (slug=${SLUG}) — muscle: Scout + Gemini-grounded + chrome (browser)"

mkdir -p "${OUT_DIR}"

# Headless run. WebSearch is RETIRED — research goes through gemini_search.py (Bash) + Scout.
claude -p "Run the algolia-search-audit skill end-to-end for the prospect domain ${DOMAIN}. \
Acquisition of the company's own data (company context, executives, careers/jobs, IR) goes through SCOUT; \
open-web research (industry benchmarks, analyst quotes, news, competitor tech) goes through \
scripts/gemini_search.py (Gemini grounded Google search). Do NOT use WebSearch. No fabrication — a field \
with no grounded source stays blank. Produce all research files, browser screenshots, scoring, factcheck, \
and the full deliverable package under ${OUT_DIR}/ using ${SLUG} as the workspace slug." \
  "${MCP_ARGS[@]}" \
  --add-dir "${SKILLS_DIR}" \
  --add-dir "${OUT_DIR}" \
  --permission-mode acceptEdits \
  --allowed-tools "Read,Write,Edit,Bash,Glob,Grep,Skill,Task,mcp__chrome__*,mcp__apify__*,mcp__crossbeam__*" \
  --output-format text \
  2>&1 | tee "${OUT_DIR}/run.log"

echo "DONE -> ${OUT_DIR}"
