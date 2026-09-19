#!/usr/bin/env bash
# PostToolUse (Edit|Write|MultiEdit): plan-dashboard snapshots stay live (Tier 0).
# Any edit to a plan/architecture/debt file or an agent spec regenerates the three
# snapshot JSONs the Astro Site reads. Advisory: a failure is reported, never blocks.
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
HOOK_INPUT="$(cat)"
file="$(json_field tool_input.file_path)"
[ -n "$file" ] || exit 0
case "$file" in
  */_workspace/plan/architecture.md | \
  */_workspace/plan/refactor/plan.md | \
  */_workspace/plan/refactor/plan.yaml | \
  */_workspace/plan/debt/pipeline-debt.md | \
  */infra/claude-agents/*.md) ;;
  *) exit 0 ;;
esac
root="$(repo_root)"
[ -d "$root/plan-dashboard/node_modules" ] || {
  echo "plan-snapshot-regen: plan-dashboard/node_modules missing; run 'cd plan-dashboard && npm install' then 'npm run snapshot'." >&2
  exit 0
}
if (cd "$root/plan-dashboard" && npm run --silent snapshot >/dev/null 2>&1); then
  echo "plan-snapshot-regen: snapshots rebuilt after editing ${file#"$root"/} — stage the JSONs with the edit."
else
  echo "plan-snapshot-regen: snapshot rebuild FAILED after editing ${file#"$root"/}; run 'cd plan-dashboard && npm run snapshot' and read the error." >&2
fi
exit 0
