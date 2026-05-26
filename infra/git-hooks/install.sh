#!/usr/bin/env bash
# Idempotent installer for the podcast-factory git hooks.
#
# Symlinks infra/git-hooks/pre-commit into .git/hooks/pre-commit so future
# commits run the DR-009 enforcement.

set -e

repo_root="$(git rev-parse --show-toplevel)"
src="$repo_root/infra/git-hooks/pre-commit"
dst="$repo_root/.git/hooks/pre-commit"

if [ ! -f "$src" ]; then
    echo "install.sh: source hook not found at $src" >&2
    exit 1
fi

# Ensure source is executable.
chmod +x "$src"

# Remove any existing hook (file or symlink) and replace with a symlink.
if [ -e "$dst" ] || [ -L "$dst" ]; then
    rm -f "$dst"
fi

ln -s "$src" "$dst"

echo "install.sh: symlinked $dst -> $src"
echo "install.sh: pre-commit hook active"
