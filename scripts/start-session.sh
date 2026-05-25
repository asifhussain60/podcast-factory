#!/usr/bin/env bash
# start-session.sh — single-machine session bootstrap.
#
# Replaces the previous multi-machine version that read ~/.machine-id,
# routed to assigned book branches, and surfaced cross-machine queue state.
# Post-2026-05-23 single-machine model: develop is the working branch,
# new books just land at content/drafts/<slug>/ directly.
#
# Usage:
#   bash scripts/start-session.sh
#
# Exit codes:
#   0 = ready (synced with origin, working tree clean)
#   1 = pre-flight failed (working tree dirty or not in a git repo)

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "ERROR: not inside a git repo" >&2
  exit 1
}
cd "$REPO_ROOT"

# ── 1. Working tree must be clean before sync ─────────────────────────
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: working tree is dirty. Commit or stash first." >&2
  echo "  Branch: $(git rev-parse --abbrev-ref HEAD)" >&2
  git status --short >&2
  exit 1
fi

# ── 2. Fetch + fast-forward develop ───────────────────────────────────
echo "▸ fetching origin"
git fetch --all --prune --quiet

CURRENT="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT" != "develop" ]; then
  echo "▸ switching to develop (was: $CURRENT)"
  git checkout --quiet develop
fi

BEHIND="$(git rev-list --count develop..origin/develop)"
if [ "$BEHIND" -gt 0 ]; then
  echo "▸ fast-forwarding $BEHIND commit(s) from origin/develop"
  git merge --ff-only origin/develop
fi

# ── 3. Sync agent activation copies (caught 2026-05-24 — `.claude/agents/`
#      was 2 weeks stale and broke per-chapter authoring silently). The
#      sync script writes to .github/agents/ AND .claude/agents/ from the
#      canonical infra/claude-agents/. Quiet mode: only output on drift. ─
SYNC_OUT="$(bash scripts/podcast/sync-agent-wrappers.sh 2>&1)"
if echo "$SYNC_OUT" | grep -q "synced\|created"; then
  echo "▸ synced agent activation copies:"
  echo "$SYNC_OUT" | grep -E "^(synced|created)" | sed 's/^/  /'
fi

# ── 4. Regression test gate — run the systemic-fix suite. Anything red
#      means the codebase is in a known-broken state; surface it now
#      before the user runs a phase that depends on the fix being live. ─
if ! /usr/bin/python3 -m unittest discover -s tests/regression -p "test_*.py" >/dev/null 2>&1; then
  echo
  echo "⚠ regression tests are RED — run \`bash tests/regression/run_all.sh\` for detail." >&2
  echo "  Continuing session anyway, but treat any pipeline failure as suspect."
fi

# ── 5. Surface state ──────────────────────────────────────────────────
echo
echo "▸ ready on develop"
echo "  $(git log --oneline -1)"
echo

# ── 5a. Watchdog status — surface any running or recently-stopped watchdogs ──
WATCHDOG_FOUND=0
for sentinel in content/drafts/*/_system/watchdog.json; do
  [[ -f "$sentinel" ]] || continue
  WATCHDOG_FOUND=1
  WD_SLUG=$(jq -r '.slug' "$sentinel" 2>/dev/null)
  WD_PID=$(jq -r '.pid' "$sentinel" 2>/dev/null)
  WD_START=$(jq -r '.started' "$sentinel" 2>/dev/null)
  WD_DIR="$(dirname "$sentinel")"
  WD_PHASE=$(jq -r '.phase' "$WD_DIR/orchestrator-state.json" 2>/dev/null)
  WD_STATUS=$(jq -r '.phase_status' "$WD_DIR/orchestrator-state.json" 2>/dev/null)
  WD_DONE=$(jq -r '.phases."per-chapter".completed_slugs | length' "$WD_DIR/orchestrator-state.json" 2>/dev/null)
  WD_TOTAL=$(ls "$(dirname "$WD_DIR")/chapter-contracts/" 2>/dev/null | wc -l | tr -d ' ')
  if kill -0 "$WD_PID" 2>/dev/null; then
    echo "▸ watchdog RUNNING: $WD_SLUG"
    echo "  PID $WD_PID · phase=$WD_PHASE/$WD_STATUS · ${WD_DONE}/${WD_TOTAL} chapters done"
    echo "  log: _workspace/logs/orchestrator-$WD_SLUG.log"
  else
    echo "▸ watchdog STOPPED: $WD_SLUG (PID $WD_PID gone · started $WD_START)"
    echo "  phase=$WD_PHASE/$WD_STATUS · ${WD_DONE}/${WD_TOTAL} chapters done"
    if [[ "$WD_PHASE" != "done" ]] && ! { [[ "$WD_PHASE" == "finalize" ]] && [[ "$WD_STATUS" == "halted" ]]; }; then
      echo "  ⚠ book not yet complete — relaunch: bash scripts/podcast/watch_orchestrator.sh $WD_SLUG"
    else
      echo "  ✓ complete"
    fi
  fi
  echo
done
if [[ "$WATCHDOG_FOUND" -eq 0 ]]; then
  echo "▸ books in flight:"
  ls content/drafts/ 2>/dev/null | sed 's/^/  - /'
  echo
fi

echo "▸ next actions (pick any):"
echo "  - new book:        python3 scripts/podcast/orchestrate_book.py <pdf>  (initial launch; watchdog auto-spawns on first --resume)"
echo "  - resume book:     bash scripts/podcast/watch_orchestrator.sh <slug>"
echo "  - check a book:    python3 scripts/podcast/orchestrate_book.py --status <slug>"
echo "  - publish a book:  python3 scripts/podcast/publish_to_library.py <slug> --dry-run"
echo "  - run reader:      cd podcast-reader && npm run dev"

exit 0
