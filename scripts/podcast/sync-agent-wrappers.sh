#!/usr/bin/env bash
# sync-agent-wrappers.sh — keep infra/claude-agents/*.md byte-identical to
# their canonical .github/agents/*.agent.md counterparts.
#
# The canonical specs live under .github/agents/<name>.agent.md (tracked).
# Per-machine activation copies live under infra/claude-agents/<name>.md
# (tracked) and ~/.claude/agents/<name>.md or .claude/agents/<name>.md
# (gitignored — Claude Code reads these). This script reconciles the tracked
# pair only; the per-machine local copy is the user's responsibility.
#
# Modes:
#   ./sync-agent-wrappers.sh           Sync mode — copy .github → infra
#   ./sync-agent-wrappers.sh --check   Check mode — exit non-zero on drift
#                                       (intended for CI gating)
#
# The wrapper pair must remain identical because Claude Code routes by the
# infra/claude-agents/ copy at session start; if the canonical spec edits
# without a wrapper sync, the activated agent runs on stale text.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CANONICAL_DIR="${REPO_ROOT}/.github/agents"
WRAPPER_DIR="${REPO_ROOT}/infra/claude-agents"

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

# Iterate over EXISTING wrappers only. Activation (which canonical specs get
# a wrapper) is a deliberate per-repo decision recorded in infra/claude-agents/.
# To activate a new agent: manually `cp .github/agents/<name>.agent.md
# infra/claude-agents/<name>.md` once, then this script keeps it in sync.
for wrapper in "${WRAPPER_DIR}"/*.md; do
  [[ -e "$wrapper" ]] || continue
  name="$(basename "$wrapper" .md)"
  [[ "$name" == "_README" ]] && continue
  canonical="${CANONICAL_DIR}/${name}.agent.md"

  if [[ ! -f "$canonical" ]]; then
    # Wrapper exists with no canonical counterpart (e.g., ui-reviewer.md per
    # the README — self-contained wrapper, no .github/agents/ source).
    # Silently skip; do not flag as drift.
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
