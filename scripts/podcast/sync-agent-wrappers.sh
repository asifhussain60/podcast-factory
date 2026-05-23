#!/usr/bin/env bash
# sync-agent-wrappers.sh — keep .github/agents/*.agent.md byte-identical to
# their canonical infra/claude-agents/*.md counterparts.
#
# Canonical direction FLIPPED 2026-05-23 per AU-X2-002 in audit report
# 2026-05-23-204940-podcast-auditor.md. New agents (podcast-auditor,
# podcast-challenger, podcast-extract, slide-deck-challenger) had been
# landing in infra/claude-agents/ directly, bypassing the old sync from
# .github/. Source-of-truth is now infra/; .github/ wrappers are
# auto-generated from it.
#
# The canonical specs live under infra/claude-agents/<name>.md (tracked).
# CI / GitHub-tooling wrappers live under .github/agents/<name>.agent.md
# (tracked; auto-generated). Per-machine activation copies under
# ~/.claude/agents/<name>.md or .claude/agents/<name>.md (gitignored —
# Claude Code reads these). This script reconciles the tracked pair only;
# the per-machine local copy is the user's responsibility.
#
# Modes:
#   ./sync-agent-wrappers.sh           Sync mode — copy infra → .github
#   ./sync-agent-wrappers.sh --check   Check mode — exit non-zero on drift
#                                       (intended for CI gating)
#
# The wrapper pair must remain identical because Claude Code routes by the
# infra/claude-agents/ copy at session start; .github/ exists for
# GitHub-side tooling (Actions, code-review bots) that look in .github/.
# If the canonical edits without a wrapper sync, downstream consumers run
# on stale text.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CANONICAL_DIR="${REPO_ROOT}/infra/claude-agents"
WRAPPER_DIR="${REPO_ROOT}/.github/agents"

mode="${1:-sync}"
case "${mode}" in
  sync|--sync)  mode=sync ;;
  check|--check) mode=check ;;
  -h|--help)
    echo "usage: $(basename "$0") [sync|--check]"
    exit 0
    ;;
  *)
    echo "unknown mode: ${mode}" >&2
    echo "usage: $(basename "$0") [sync|--check]" >&2
    exit 2
    ;;
esac

drift_count=0
created_count=0

# Iterate over EVERY canonical spec under infra/claude-agents/. For each:
# - If the .github/ wrapper is missing, create it (sync mode) or flag (check mode).
# - If the wrapper exists but differs, sync it (sync mode) or flag (check mode).
# This ensures new agents (e.g., podcast-auditor) propagate automatically.
mkdir -p "${WRAPPER_DIR}"
for canonical in "${CANONICAL_DIR}"/*.md; do
  [[ -e "$canonical" ]] || continue
  name="$(basename "$canonical" .md)"
  [[ "$name" == "_README" ]] && continue
  wrapper="${WRAPPER_DIR}/${name}.agent.md"

  if [[ ! -f "$wrapper" ]]; then
    if [[ "$mode" == "check" ]]; then
      echo "MISSING: ${wrapper#${REPO_ROOT}/}" >&2
      drift_count=$((drift_count + 1))
    else
      cp "$canonical" "$wrapper"
      echo "created  ${wrapper#${REPO_ROOT}/}"
      created_count=$((created_count + 1))
    fi
    continue
  fi

  if ! cmp -s "$canonical" "$wrapper"; then
    if [[ "$mode" == "check" ]]; then
      echo "DRIFT:   ${wrapper#${REPO_ROOT}/}" >&2
      drift_count=$((drift_count + 1))
    else
      cp "$canonical" "$wrapper"
      echo "synced   ${wrapper#${REPO_ROOT}/}"
    fi
  fi
done

if [[ "$mode" == "check" ]]; then
  if [[ $drift_count -gt 0 ]]; then
    echo "" >&2
    echo "${drift_count} wrapper(s) drifted from canonical." >&2
    echo "Run: scripts/podcast/sync-agent-wrappers.sh" >&2
    exit 1
  fi
  echo "all wrappers in sync"
fi

if [[ "$mode" == "sync" && $created_count -gt 0 ]]; then
  echo ""
  echo "${created_count} new wrapper(s) created. Commit them to .github/agents/ so CI sees them."
fi
