#!/usr/bin/env bash
# start-session.sh — runnable from any branch on any machine.
# Reads the per-machine operator file from origin/develop, switches to
# the assigned book branch, pulls latest, prints next_action + orchestrator
# state. Safe to run on either Mac Air or Mac Studio.
#
# Usage:
#   bash _workspace/plan/operators/start-session.sh
#
# Requires:
#   - ~/.machine-id containing either `mac-studio-primary` or `macbook-air-secondary`
#   - jq, git on PATH
#   - clean working tree on the current branch
#
# Exit codes:
#   0 = ready (sitting on the right branch, next_action printed)
#   1 = pre-flight failed (working tree dirty, machine-id missing, etc.)
#   2 = no assigned book (machine is IDLE; print claim instructions)

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "ERROR: not inside a git repo" >&2; exit 1;
}
cd "$REPO_ROOT"

# ── 1. Identify the machine ──────────────────────────────────────────
MACHINE_ID_FILE="$HOME/.machine-id"
if [ ! -f "$MACHINE_ID_FILE" ]; then
  echo "ERROR: $MACHINE_ID_FILE missing" >&2
  echo "  Set it once per machine:" >&2
  echo "    Mac Air:    echo macbook-air-secondary > ~/.machine-id" >&2
  echo "    Mac Studio: echo mac-studio-primary > ~/.machine-id" >&2
  exit 1
fi
MACHINE_ID="$(tr -d '[:space:]' < "$MACHINE_ID_FILE")"
case "$MACHINE_ID" in
  mac-studio-primary|macbook-air-secondary) ;;
  *) echo "ERROR: unknown machine_id '$MACHINE_ID' in $MACHINE_ID_FILE" >&2; exit 1 ;;
esac
echo "▸ machine: $MACHINE_ID"

# ── 2. Pre-flight: clean working tree ────────────────────────────────
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: working tree is dirty. Commit or stash before starting a session." >&2
  echo "  Current branch: $(git rev-parse --abbrev-ref HEAD)" >&2
  git status --short >&2
  exit 1
fi
CURRENT_BRANCH_START="$(git rev-parse --abbrev-ref HEAD)"
echo "▸ starting branch: $CURRENT_BRANCH_START"

# ── 3. Sync develop (the operator file's source of truth) ────────────
echo "▸ syncing develop from remote..."
git fetch --quiet --all --prune
git checkout --quiet develop
git pull --quiet --ff-only origin develop
echo "  develop @ $(git rev-parse --short HEAD)"

# ── 4. Read this machine's operator file from develop ────────────────
OPERATOR_FILE="_workspace/plan/operators/${MACHINE_ID}.md"
if [ ! -f "$OPERATOR_FILE" ]; then
  echo "ERROR: operator file not found: $OPERATOR_FILE on develop" >&2
  echo "  This should have been set up at machine bootstrap." >&2
  exit 1
fi

# Parse frontmatter (between leading --- and second ---)
FRONTMATTER="$(awk '/^---$/{c++; next} c==1' "$OPERATOR_FILE")"

extract() {
  # extract a single-line value: extract <key>
  echo "$FRONTMATTER" | awk -v k="$1:" '$1==k { for(i=2;i<=NF;i++) printf "%s%s", (i>2 ? OFS : ""), $i; print ""; exit }' \
    | tr -d '"' | sed 's/^ *//;s/ *$//'
}

ASSIGNED_BRANCH="$(extract current_branch)"
ASSIGNED_BOOK="$(extract current_book)"
ASSIGNED_BOOK_DIR="$(extract current_book_dir)"
STATUS_TAG="$(extract status_tag)"
CURRENT_PHASE="$(extract current_phase)"

echo "▸ assignment from $OPERATOR_FILE:"
echo "    branch:     ${ASSIGNED_BRANCH:-(none — IDLE)}"
echo "    book:       ${ASSIGNED_BOOK:-(none)}"
echo "    status_tag: ${STATUS_TAG:-(none)}"
echo "    phase:      ${CURRENT_PHASE:-(none)}"

# ── 5. IDLE machine? Tell operator to claim from queue ───────────────
if [ -z "$ASSIGNED_BRANCH" ] || [ "$ASSIGNED_BRANCH" = "(none)" ]; then
  echo ""
  echo "▸ No in-flight book assigned to this machine."
  echo "  See _workspace/plan/book-queue.md → 'Queue' section → claim protocol."
  exit 2
fi

# ── 6. Switch to the assigned book branch ────────────────────────────
echo ""
echo "▸ switching to $ASSIGNED_BRANCH..."
if ! git rev-parse --verify "$ASSIGNED_BRANCH" >/dev/null 2>&1; then
  echo "  branch doesn't exist locally; checking out from origin"
  git checkout --quiet -b "$ASSIGNED_BRANCH" "origin/$ASSIGNED_BRANCH"
else
  git checkout --quiet "$ASSIGNED_BRANCH"
fi
git pull --quiet --ff-only origin "$ASSIGNED_BRANCH" 2>/dev/null || true
echo "  now on:  $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD)"

# ── 7. Print orchestrator state for the assigned book ────────────────
if [ -n "$ASSIGNED_BOOK_DIR" ] && [ -d "$ASSIGNED_BOOK_DIR" ]; then
  STATE_FILE="${ASSIGNED_BOOK_DIR}/_system/orchestrator-state.json"
  if [ -f "$STATE_FILE" ]; then
    echo ""
    echo "▸ orchestrator state:"
    jq -r '"    phase: \(.phase) / \(.phase_status)\n    last_completed: \(.last_completed_phase)\n    last_error: \(.last_error)"' "$STATE_FILE"
  fi
fi

# ── 8. Print next_action ─────────────────────────────────────────────
echo ""
echo "▸ next_action (from $OPERATOR_FILE):"
awk '/^next_action: \|$/{flag=1; next} /^[a-z_]+:/{flag=0} flag {print "    " $0}' "$OPERATOR_FILE" \
  | head -20

echo ""
echo "▸ response format reference:"
echo "    _workspace/plan/response-conventions.md (read once per session if you haven't)"

echo ""
echo "▸ ready."
exit 0
