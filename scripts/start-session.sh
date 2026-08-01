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

# ── 0. Python environment check ───────────────────────────────────────
VENV_PYTHON="$REPO_ROOT/.venv/bin/python3"
if [ -x "$VENV_PYTHON" ]; then
  if [ "${VIRTUAL_ENV:-}" != "$REPO_ROOT/.venv" ]; then
    echo "▸ venv not active — pipeline commands need it. Run:"
    echo "    source .venv/bin/activate"
    echo "  Then re-run:  bash scripts/start-session.sh"
    echo "  (one-time per terminal session)"
    echo
  fi
else
  echo "⚠ .venv not found — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  echo
fi

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
if ! "$VENV_PYTHON" -m unittest discover -s tests/regression -p "test_*.py" >/dev/null 2>&1; then
  echo
  echo "⚠ regression tests are RED — run \`bash tests/regression/run_all.sh\` for detail." >&2
  echo "  Continuing session anyway, but treat any pipeline failure as suspect."
fi

# ── 4b. Claude auth warm-up — trigger token auto-refresh now so the pipeline
#       never hits an "OAuth access token expired" gate mid-run. The Claude CLI
#       uses a refresh token (long-lived) to get a new access token automatically;
#       this ping ensures that refresh happens here rather than mid-orchestration.
#       Strip ANTHROPIC_API_KEY to force Max OAuth (same as the pipeline does). ─
if command -v claude &>/dev/null; then
  if env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
       claude -p --output-format json "pong" >/dev/null 2>&1; then
    echo "▸ claude auth   OK"
  else
    echo "⚠ claude auth   STALE — run: claude login"
  fi
fi

# ── 4c. CI health — a workflow that has been red for a WHILE ──────────
#      The `lint` workflow failed on 60 consecutive runs on develop between
#      2026-07-27 and 2026-08-01 — zero successes, dozens of pushes, no signal
#      anyone acted on. Six gates were not running that whole time, including
#      the runtime smoke job. It surfaced only because an unrelated post-merge
#      audit happened to look at CI. Nothing was watching. (RCA-009, AI-2.)
#
#      Reported HERE rather than as a scheduled workflow because this is the
#      moment a human is about to start work — which is where it would have
#      been caught on day one.
#
#      Threshold is 3 consecutive completed failures, so a single flaky run
#      stays quiet: the signal has to mean "this is broken", not "CI hiccuped".
#      In-progress runs are skipped rather than breaking the streak, so a red
#      workflow currently re-running is still reported.
CI_RED_STREAK=3
if command -v gh &>/dev/null && command -v jq &>/dev/null; then
  CI_RUNS=$(gh run list --branch develop --limit 40 \
              --json workflowName,conclusion,status,createdAt 2>/dev/null || true)
  if [[ -n "${CI_RUNS:-}" && "$CI_RUNS" != "[]" ]]; then
    CI_RED=$(printf '%s' "$CI_RUNS" | jq -r --argjson min "$CI_RED_STREAK" '
      [ .[] | select(.status == "completed") ]
      | group_by(.workflowName)
      | map(
          (sort_by(.createdAt) | reverse) as $runs
          | ([ $runs[] | .conclusion == "failure" ] | index(false)) as $firstOk
          | { workflow: $runs[0].workflowName,
              streak:   ($firstOk // ($runs | length)),
              since:    ( $runs[ (($firstOk // ($runs|length)) - 1) ].createdAt // "" ) }
        )
      | map(select(.streak >= $min))
      | .[] | "\(.workflow)|\(.streak)|\(.since)"
    ' 2>/dev/null || true)
    if [[ -n "${CI_RED:-}" ]]; then
      echo
      echo "⚠ CI has been RED on develop — not a one-off:" >&2
      while IFS='|' read -r wf streak since; do
        [[ -n "$wf" ]] || continue
        # `since` is the oldest failure INSIDE the 40-run window, so the streak
        # may reach further back than this — say "at least", never overstate.
        echo "    $wf — $streak consecutive failures, at least since ${since%T*}" >&2
      done <<< "$CI_RED"
      echo "  Inspect: gh run list --branch develop --workflow <name>" >&2
      echo "           gh run view <id> --log-failed"
    fi
  fi
fi

# ── 5. Surface state ──────────────────────────────────────────────────
echo
echo "▸ ready on develop"
echo "  $(git log --oneline -1)"
echo

# ── 5a. Watchdog status — surface any running or recently-stopped watchdogs ──
WATCHDOG_FOUND=0
# Bucket-grouped layout: content/<Bucket>/<slug>/_system/watchdog.json
for sentinel in content/*/*/_system/watchdog.json; do
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
  # Scan bucket-grouped layout for books with an orchestrator state
  find content -mindepth 3 -maxdepth 3 -name "orchestrator-state.json" 2>/dev/null \
    | while read -r f; do
        slug=$(jq -r '.slug // empty' "$f" 2>/dev/null)
        phase=$(jq -r '.phase // "?"' "$f" 2>/dev/null)
        status=$(jq -r '.phase_status // "?"' "$f" 2>/dev/null)
        echo "  - ${slug:-$(dirname "$f" | xargs basename)}  [${phase}/${status}]"
      done
  echo
fi

echo "▸ next actions (pick any):"
echo "  - new book:        python3 scripts/podcast/orchestrate_book.py <pdf>  (initial launch; watchdog auto-spawns on first --resume)"
echo "  - resume book:     bash scripts/podcast/watch_orchestrator.sh <slug>"
echo "  - check a book:    python3 scripts/podcast/orchestrate_book.py --status <slug>"
echo "  - publish a book:  python3 scripts/podcast/publish_to_library.py <slug> --dry-run"
echo "  - run the site:    cd plan-dashboard && npm run dev"
echo
echo "  NOTE: pipeline commands require the venv — run 'source .venv/bin/activate' first"

exit 0
