#!/usr/bin/env bash
# SessionStart: put the current site-work state in front of every new conversation.
# Source of truth is _workspace/plan/site-work-status.md; update it at the end of any
# site-work session. Stdout from a SessionStart hook is added to the model's context.
source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
status="$(repo_root)/_workspace/plan/site-work-status.md"
[ -f "$status" ] || exit 0
echo "## Current site-work status (from _workspace/plan/site-work-status.md)"
head -n 60 "$status"
exit 0
