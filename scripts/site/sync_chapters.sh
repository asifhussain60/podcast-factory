#!/usr/bin/env bash
# sync_chapters.sh — one-way mirror from canonical memoir chapters into the site bundle.
#
# Source of truth: content/babu-memoir/chapters/
# Mirror:          site/chapters/  (bundled into the Cloudflare static-asset deploy)
#
# Run after every chapter finalization, before any site deploy. Idempotent.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$REPO_ROOT/content/babu-memoir/chapters"
DST="$REPO_ROOT/site/chapters"

if [[ ! -d "$SRC" ]]; then
  echo "ERROR: canonical chapter source missing: $SRC" >&2
  exit 1
fi

mkdir -p "$DST"

# Mirror only the chapter txt files (not snapshots, not scratchpad).
# Preserves timestamps. Removes any files in DST that no longer exist in SRC.
rsync -a --delete --include='*.txt' --exclude='*' "$SRC"/ "$DST"/

echo "Chapter mirror synced:"
ls -la "$DST"
