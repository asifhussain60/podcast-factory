#!/usr/bin/env bash
# sync-develop.sh — keep localhost in step with `develop` the moment its local
# ref moves, so the Podcast Factory Astro Site and the Listener dev server
# never lag behind what was just committed, merged, or checked out.
#
# Called from three hook entry points (post-commit, post-merge,
# post-checkout) rather than duplicated in each, because "was that commit ON
# develop" is one guard, not three.
#
# Deliberately does NOT start or restart either dev server. Vite/React
# Router already hot-reloads on file changes, so a server that is already
# running picks up new commits on its own; forcing a restart from a git hook
# risks colliding with however it was actually launched. The two things that
# do NOT self-update by file-watching are what this actually runs:
#   1. the Astro Site's generated snapshot JSONs (a build step, not a watch)
#   2. the Listener's local D1 schema (a migration, not a file)
#
# Advisory only — never fails the underlying git operation. A commit, merge,
# or checkout must never be blocked by a snapshot regen or a migration apply;
# a failure here is printed and swallowed, not propagated.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$REPO_ROOT" ] || exit 0

branch="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)"
[ "$branch" = "develop" ] || exit 0

# --- Astro Site snapshots -----------------------------------------------------
DASH_DIR="$REPO_ROOT/plan-dashboard"
if [ -f "$DASH_DIR/package.json" ] && command -v npm >/dev/null 2>&1; then
  if OUTPUT="$(cd "$DASH_DIR" && npm run --silent snapshot 2>&1)"; then
    echo "sync-develop: Astro Site snapshots regenerated"
  else
    echo "sync-develop: snapshot regen FAILED (non-blocking):" >&2
    echo "$OUTPUT" >&2
  fi
  if pgrep -f 'plan-dashboard.*node' >/dev/null 2>&1; then
    touch "$DASH_DIR/.snapshot-version" 2>/dev/null || true
  fi
fi

# --- Listener local schema ----------------------------------------------------
LISTENER_DIR="$REPO_ROOT/listener"
if [ -f "$LISTENER_DIR/package.json" ] && command -v npx >/dev/null 2>&1; then
  if OUTPUT="$(cd "$LISTENER_DIR" && npx wrangler d1 migrations apply podcast-listener --local 2>&1)"; then
    if grep -qi "no migrations to apply" <<<"$OUTPUT"; then
      : # already current — nothing worth printing every time
    else
      echo "sync-develop: Listener local D1 schema updated"
    fi
  else
    echo "sync-develop: local D1 migration FAILED (non-blocking):" >&2
    echo "$OUTPUT" >&2
  fi
fi

exit 0
