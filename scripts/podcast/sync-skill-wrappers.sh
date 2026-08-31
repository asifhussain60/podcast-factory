#!/usr/bin/env bash
# sync-skill-wrappers.sh — keep .claude/skills/<name>/SKILL.md byte-identical to
# their canonical skills-staging/<name>/SKILL.md counterparts, for the subset of
# skills-staging entries that are Claude-Code-NATIVE project skills.
#
# Most skills-staging/ entries are NOT for here: install-claude-skills.sh mirrors
# skills-staging/*/SKILL.md into the global Cowork skills directory instead. A
# skill belongs in THIS sync only when it is meant to be discovered by Claude Code
# directly, project-scoped, via `.claude/skills/<name>/SKILL.md` — the mechanism
# Claude Code itself reads. Which names those are is declared in
# `.repo-audit/profile.yaml` under `project_skills:`, the same way `apps:` and
# `size_gates:` declare facts a probe cannot infer.
#
# Before this script existed, two project skills (podcast-factory-deploy,
# challenge-my-request) were authored directly under the gitignored
# `.claude/skills/` with no tracked source anywhere — invisible to git, to the
# skill registry, and to repo-surgeon's own health check, on a repo whose stated
# model is "machine-agnostic" (CLAUDE.md). A skill that only exists on one
# machine's untracked directory does not survive a fresh clone.
#
# Canonical source: skills-staging/<name>/SKILL.md (tracked).
# Generated runtime copy: .claude/skills/<name>/SKILL.md (gitignored — Claude
# Code reads this directly; same split as .claude/agents/ for agent specs).
#
# Modes:
#   ./sync-skill-wrappers.sh           Sync mode — copy skills-staging -> .claude/skills
#   ./sync-skill-wrappers.sh --check   Check mode — exit non-zero on drift

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAGING_DIR="${REPO_ROOT}/skills-staging"
RUNTIME_DIR="${REPO_ROOT}/.claude/skills"
PROFILE="${REPO_ROOT}/.repo-audit/profile.yaml"

mode="${1:-sync}"
case "${mode}" in
  sync|--sync)  mode=sync ;;
  check|--check) mode=check ;;
  -h|--help)
    echo "usage: $(basename "$0") [sync|--check]"
    exit 0
    ;;
  *)
    echo "unknown mode: ${mode}" >&2
    echo "usage: $(basename "$0") [sync|--check]" >&2
    exit 2
    ;;
esac

if [[ ! -f "$PROFILE" ]]; then
  echo "ERROR: $PROFILE not found — wrong repo, or contract missing." >&2
  exit 2
fi

# Minimal YAML read: `project_skills:` is a flat list of bare names, one per
# `  - name` line, immediately under that key. No general YAML parser needed for
# a shape this narrow, and this script has no Python/PyYAML dependency by design
# (it must run from a pre-commit hook, same bar as sync-agent-wrappers.sh).
# `mapfile` is bash 4+; macOS ships bash 3.2 (see sync-agent-wrappers.sh's own
# note on this), so build the array with a plain while-read loop instead.
PROJECT_SKILLS=()
while IFS= read -r line; do
  [[ -n "$line" ]] && PROJECT_SKILLS+=("$line")
done < <(awk '
  /^project_skills:/ { in_block=1; next }
  in_block && /^[a-zA-Z_]/ { in_block=0 }
  in_block && /^[[:space:]]*-[[:space:]]/ {
    sub(/^[[:space:]]*-[[:space:]]*/, "");
    gsub(/[[:space:]]*#.*/, "");
    gsub(/[[:space:]]+$/, "");
    if (length($0) > 0) print
  }
' "$PROFILE")

if [[ "${#PROJECT_SKILLS[@]}" -eq 0 ]]; then
  echo "no project_skills declared in ${PROFILE#${REPO_ROOT}/} — nothing to sync"
  exit 0
fi

drift_count=0

# FORWARD SWEEP — every declared project skill must have a canonical source and
# a byte-identical runtime copy.
for name in "${PROJECT_SKILLS[@]}"; do
  canonical="${STAGING_DIR}/${name}/SKILL.md"
  runtime="${RUNTIME_DIR}/${name}/SKILL.md"

  if [[ ! -f "$canonical" ]]; then
    echo "MISSING CANONICAL: ${canonical#${REPO_ROOT}/} (declared in project_skills but no SKILL.md)" >&2
    drift_count=$((drift_count + 1))
    continue
  fi

  if [[ "$mode" == "check" ]]; then
    if [[ ! -f "$runtime" ]] || ! cmp -s "$canonical" "$runtime"; then
      echo "DRIFT:   ${runtime#${REPO_ROOT}/}" >&2
      drift_count=$((drift_count + 1))
    fi
  else
    mkdir -p "$(dirname "$runtime")"
    if [[ ! -f "$runtime" ]] || ! cmp -s "$canonical" "$runtime"; then
      cp "$canonical" "$runtime"
      echo "synced   ${runtime#${REPO_ROOT}/}"
    fi
  fi
done

# REVERSE SWEEP — anything under .claude/skills/ with no entry in project_skills
# (or no canonical source at all) is an orphan: it exists nowhere in git, so
# nothing here ever regenerates it and nothing else will ever notice it drifted.
if [[ -d "$RUNTIME_DIR" ]]; then
  for skill_dir in "$RUNTIME_DIR"/*/; do
    [[ -d "$skill_dir" ]] || continue
    name="$(basename "$skill_dir")"
    declared=0
    for p in "${PROJECT_SKILLS[@]}"; do
      [[ "$p" == "$name" ]] && declared=1 && break
    done
    if [[ "$declared" -eq 0 ]]; then
      echo "ORPHAN:  .claude/skills/${name}/SKILL.md (not declared in project_skills — either add it to the contract or remove the directory)" >&2
      drift_count=$((drift_count + 1))
    fi
  done
fi

if [[ "$mode" == "check" ]]; then
  if [[ $drift_count -gt 0 ]]; then
    echo "" >&2
    echo "${drift_count} project skill(s) drifted or undeclared. Run: bash $0" >&2
    exit 1
  fi
  echo "project skill mirrors clean (${#PROJECT_SKILLS[@]} declared)."
else
  echo "done."
fi
