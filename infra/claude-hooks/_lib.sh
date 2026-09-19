#!/usr/bin/env bash
# Shared helpers for the Claude Code hooks in this directory.
# Hooks receive one JSON object on stdin; python3 is the only parser assumed.

repo_root() {
  # $CLAUDE_PROJECT_DIR is set by Claude Code; fall back to the script's own repo.
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    printf '%s\n' "$CLAUDE_PROJECT_DIR"
  else
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
  fi
}

# json_field <dotted.path> — read one field from the stdin JSON captured in $HOOK_INPUT.
json_field() {
  printf '%s' "${HOOK_INPUT:-}" | python3 -c '
import json, sys
try:
    node = json.load(sys.stdin)
    for key in sys.argv[1].split("."):
        node = node[key]
    print(node if not isinstance(node, bool) else str(node).lower())
except Exception:
    pass
' "$1"
}
