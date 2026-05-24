#!/usr/bin/env bash
# start-content-worktree.sh — create a typed content branch as a sibling git worktree.
#
# Per CLAUDE.md ("Worktree workflow"), every new piece of content is processed on its
# own typed branch off `develop`, AND that branch lives in its own working directory
# under <projects-root>/git-worktrees/<slug>/. This script wraps the two-step
# `git worktree add` + `--unset-upstream` so nobody re-trips the upstream foot-gun
# (without unset, `git push` from the new worktree would push content commits to
# origin/develop).
#
# Usage:
#   scripts/start-content-worktree.sh <category> <slug>
#
# Examples:
#   scripts/start-content-worktree.sh books   kitab-al-riyad
#   scripts/start-content-worktree.sh letters ayyuhal-walad
#   scripts/start-content-worktree.sh ""      some-unclassified-thing   # → draft/<slug>
#
# Where the worktree lands:
#   Mac Air     : ~/PROJECTS/git-worktrees/<slug>/
#   Mac Studio  : ~/Code/git-worktrees/<slug>/
# Detection is by which parent dir contains this repo's primary clone.
#
# Exit codes:
#   0 — created successfully (or already existed; idempotent)
#   1 — usage error / repo not found / git worktree add failed
set -euo pipefail

usage() {
    cat >&2 <<'EOF'
Usage: scripts/start-content-worktree.sh <category> <slug>

  <category>  One of: books | documents | lectures | articles | letters | interviews
              Empty string is allowed and yields the `draft/` fallback prefix.
  <slug>      Full kebab-cased slug. Never abbreviate (e.g. `kitab-al-riyad`,
              never `KaR`).

Creates the typed branch off origin/develop as a git worktree at:
  <projects-root>/git-worktrees/<slug>/

where <projects-root> is auto-detected as ~/PROJECTS or ~/Code based on
where this repo's primary clone lives.
EOF
    exit 1
}

[[ $# -eq 2 ]] || usage
category="$1"
slug="$2"

if [[ -z "$slug" ]]; then
    echo "start-content-worktree: slug must be non-empty" >&2
    exit 1
fi
if ! [[ "$slug" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
    echo "start-content-worktree: slug '$slug' must be lowercase-kebab-case" >&2
    exit 1
fi

# Resolve repo root (this script is at <repo>/scripts/, so parent of parent).
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

# Resolve <projects-root> from the PRIMARY clone, not from this script's location —
# the script may itself be running inside a worktree at <projects-root>/git-worktrees/<x>/,
# and naively using `dirname $repo_root` would produce nested git-worktrees/git-worktrees/.
# `git rev-parse --git-common-dir` always points at the primary `.git`; its parent IS
# the primary clone's working tree.
git_common_dir="$(git -C "$repo_root" rev-parse --git-common-dir)"
# Make it absolute if it isn't.
if [[ "$git_common_dir" != /* ]]; then
    git_common_dir="$(cd "$repo_root" && cd "$git_common_dir" && pwd)"
fi
primary_repo="$(dirname "$git_common_dir")"
projects_root="$(cd "$primary_repo/.." && pwd)"

# Map category → branch prefix (mirrors scripts/podcast/_branching.py).
case "$category" in
    books)      prefix="book" ;;
    documents)  prefix="doc" ;;
    lectures)   prefix="lecture" ;;
    articles)   prefix="article" ;;
    letters)    prefix="letter" ;;
    interviews) prefix="interview" ;;
    "")         prefix="draft" ;;
    *)
        echo "start-content-worktree: unknown category '$category'" >&2
        echo "  Allowed: books, documents, lectures, articles, letters, interviews, '' (→ draft)" >&2
        exit 1
        ;;
esac

branch="${prefix}/${slug}"
worktree_dir="${projects_root}/git-worktrees/${slug}"

# Fetch origin/develop so we branch from latest.
echo "==> Fetching origin/develop"
git -C "$repo_root" fetch origin develop --quiet

# Idempotent: if the worktree already exists at this path, just print and exit 0.
if [[ -d "$worktree_dir/.git" ]] || [[ -f "$worktree_dir/.git" ]]; then
    echo "==> Worktree already exists: $worktree_dir"
    echo "    Branch: $(git -C "$worktree_dir" symbolic-ref --short HEAD 2>/dev/null || echo 'detached')"
    echo ""
    echo "    cd $worktree_dir"
    exit 0
fi

# Branch already checked out at a DIFFERENT worktree path? Surface and exit 0.
# `git worktree list` lines look like:  /path/to/wt  abc1234 [branch-name]
existing_wt="$(git -C "$repo_root" worktree list --porcelain \
    | awk -v want="$branch" '
        /^worktree / { wt=$2 }
        /^branch /   { if ($2 == "refs/heads/" want) { print wt; exit } }
    ')"
if [[ -n "$existing_wt" ]]; then
    echo "==> Branch $branch is already checked out at: $existing_wt"
    echo "    Use that worktree directly:"
    echo ""
    echo "      cd $existing_wt"
    exit 0
fi

mkdir -p "${projects_root}/git-worktrees"

# Branch already exists locally? Check out into the new worktree instead of creating.
if git -C "$repo_root" rev-parse --verify --quiet "$branch" > /dev/null; then
    echo "==> Branch $branch already exists; checking out into worktree"
    git -C "$repo_root" worktree add "$worktree_dir" "$branch"
else
    echo "==> Creating $branch off origin/develop at $worktree_dir"
    git -C "$repo_root" worktree add -b "$branch" "$worktree_dir" origin/develop
fi

# Unset auto-upstream — `worktree add ... origin/develop` sets upstream to origin/develop,
# which would silently push content commits to develop on first push. Clear it so the
# first push is `git push -u origin <branch>` and creates the correct remote ref.
git -C "$worktree_dir" branch --unset-upstream || true

echo ""
echo "==> Ready."
echo "    Branch:   $branch"
echo "    Worktree: $worktree_dir"
echo ""
echo "    First push (when you have commits):"
echo "      git -C $worktree_dir push -u origin $branch"
echo ""
echo "    Switch to it:"
echo "      cd $worktree_dir"
