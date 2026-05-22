#!/usr/bin/env bash
# install-claude-skills.sh — materialize tracked Claude Code skill content
# into the per-machine runtime locations.
#
# What this script does:
#   1. Copies `infra/claude-agents/*.md` (excluding _README.md) into
#      `.claude/agents/<name>.md` so Claude Code can invoke each agent via
#      `subagent_type=<name>`.
#   2. Mirrors `skills-staging/{journal,podcast}/SKILL.md` into the Claude Code
#      runtime skills directory (default `~/Library/Application Support/
#      Claude/skills/<name>/SKILL.md`; override with $CLAUDE_SKILLS_DIR).
#
# Idempotent. Overwrites existing files (the wrappers are deterministic
# content; if you've hand-edited `.claude/agents/<name>.md` and want it durable,
# move the change into `infra/claude-agents/<name>.md` and re-run this script).
#
# Flags:
#   --dry-run   Print what would be copied without writing
#   --force     (default) Overwrite without prompting
#   --skills-dir <path>
#               Override the runtime skills directory
#
# Exit codes:
#   0  — all copies succeeded
#   1  — an underlying copy or directory operation failed
#   2  — bad invocation (unknown flag, repo state mismatch)

set -euo pipefail

# ─── Resolve paths ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AGENTS_SRC="$REPO_ROOT/infra/claude-agents"
AGENTS_DST="$REPO_ROOT/.claude/agents"

SKILLS_SRC="$REPO_ROOT/skills-staging"
DEFAULT_SKILLS_DIR="$HOME/Library/Application Support/Claude/skills"
SKILLS_DST="${CLAUDE_SKILLS_DIR:-$DEFAULT_SKILLS_DIR}"

# ─── Parse args ─────────────────────────────────────────────────────────────
DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --force)   shift ;;  # default behavior; flag kept for clarity
    --skills-dir) SKILLS_DST="$2"; shift 2 ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "ERROR: unknown flag: $1" >&2
      exit 2
      ;;
  esac
done

# ─── Sanity checks ─────────────────────────────────────────────────────────
if [ ! -d "$AGENTS_SRC" ]; then
  echo "ERROR: $AGENTS_SRC not found — wrong repo, or wrappers missing." >&2
  exit 2
fi
if [ ! -d "$SKILLS_SRC" ]; then
  echo "ERROR: $SKILLS_SRC not found — wrong repo, or skills missing." >&2
  exit 2
fi

run() {
  if [ "$DRY_RUN" = "1" ]; then
    echo "    DRY  $*"
  else
    eval "$@"
  fi
}

echo "==> Install Claude Code skills (dry-run=$DRY_RUN)"
echo "    agents:  $AGENTS_SRC  →  $AGENTS_DST"
echo "    skills:  $SKILLS_SRC  →  $SKILLS_DST"

# ─── 1. Agent wrappers → .claude/agents/ ────────────────────────────────────
echo
echo "==> [1/2] Agent wrappers"
run "mkdir -p '$AGENTS_DST'"

agent_count=0
for src in "$AGENTS_SRC"/*.md; do
  [ -f "$src" ] || continue
  name=$(basename "$src")
  # Skip the README — it documents the directory, not a wrapper.
  if [ "$name" = "_README.md" ]; then
    continue
  fi
  dst="$AGENTS_DST/$name"
  run "cp '$src' '$dst'"
  echo "    OK   $name"
  agent_count=$((agent_count + 1))
done
echo "    Installed $agent_count wrapper(s)."

# ─── 2. Skill files → Claude Code skills dir ───────────────────────────────
echo
echo "==> [2/2] Skill files (SKILL.md)"
run "mkdir -p '$SKILLS_DST'"

# Auto-discover every subdir under skills-staging/ that ships a SKILL.md.
# Replaces the old hardcoded `for skill_dir in journal podcast` list, which
# went stale each time a new skill landed (podcast-blueprint, clean-commit,
# repo-surgeon, tell-me, usage-auditor, cowork-brief were all tracked but
# never installed under the old hardcoded list).
skill_count=0
for skill_path in "$SKILLS_SRC"/*/SKILL.md; do
  [ -f "$skill_path" ] || continue
  skill_dir=$(basename "$(dirname "$skill_path")")
  dst_dir="$SKILLS_DST/$skill_dir"
  dst="$dst_dir/SKILL.md"
  run "mkdir -p '$dst_dir'"
  run "cp '$skill_path' '$dst'"
  echo "    OK   $skill_dir/SKILL.md"
  skill_count=$((skill_count + 1))
done
echo "    Installed $skill_count skill(s)."

echo
if [ "$DRY_RUN" = "1" ]; then
  echo "Dry-run complete. Re-run without --dry-run to apply."
else
  echo "Done. Restart Cowork to pick up new skill registrations."
fi
