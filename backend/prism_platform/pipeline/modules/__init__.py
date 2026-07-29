"""Deterministic per-skill module executors.

Each module here replaces the claude -p agentic wrapper for one skill's data
collection step with plain Python: call the skill's real collect-*.py
script via subprocess, parse its real structured stdout, and decide
success/degraded/needs_human purely in code -- never as an LLM judgment
call. This is the fix for the class of bug where an agent, faced with a
failed/empty script result, "helpfully" improvised a fabricated answer
instead of failing loud (recorded incident: algolia-intel-traffic,
2026-07-06). gate()/self_heal/executioner don't care what produced a
skill's output files -- these modules are a deterministic alternative to
run-audit.sh's claude -p dispatch for the skills ported so far.
"""
