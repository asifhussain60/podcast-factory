#!/usr/bin/env bash
# Stop: the runtime gate. When plan-dashboard/ changed this turn and a dev server is
# already up on :4322, run the deterministic smoke sweep (zero model spend) and block
# the stop with its output if any route errors. Never starts a server itself and never
# loops: it stands down when Claude Code says a stop hook is already active.
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
HOOK_INPUT="$(cat)"
[ "$(json_field stop_hook_active)" = "true" ] && exit 0
root="$(repo_root)"
cd "$root" || exit 0
git status --porcelain -- plan-dashboard 2>/dev/null | grep -q . || exit 0
lsof -nP -iTCP:4322 -sTCP:LISTEN >/dev/null 2>&1 || exit 0
if out="$(cd plan-dashboard && npm run --silent smoke 2>&1)"; then
  exit 0
fi
{
  echo "site-health smoke FAILED after changes under plan-dashboard/ — fix before finishing:"
  printf '%s\n' "$out" | tail -n 40
} >&2
exit 2
