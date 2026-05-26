#!/usr/bin/env bash
# tests/regression/run_all.sh — one-command regression-test runner.
#
# Run before committing anything in scripts/podcast/*.py, infra/claude-agents/*.md,
# or skills-staging/podcast/SKILL.md. Each test pins one lesson learned today
# so a future edit can't silently regress.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "▸ regression tests under tests/regression/"
/usr/bin/python3 -m unittest discover -s tests/regression -p "test_*.py" -v
rc=$?

if [[ $rc -eq 0 ]]; then
  echo ""
  echo "✓ all regression tests passed"
else
  echo ""
  echo "✗ regression suite FAILED (rc=$rc). Fix before committing."
fi

exit $rc
