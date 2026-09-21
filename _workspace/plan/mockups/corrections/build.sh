#!/usr/bin/env bash
# Refreshes the vendored copy of the LIVE Library stylesheet so this mock always
# renders with the real tokens, palettes and components — never a re-drawing of them.
# The only change is font URLs (absolute /fonts -> relative), so it opens from disk.
set -euo pipefail
cd "$(dirname "$0")"
SRC=../../../../listener
mkdir -p vendor
sed 's#url("/fonts/#url("./fonts/#g' "$SRC/app/styles/podcast-factory.css" > vendor/podcast-factory.css
sed 's#url("/fonts/#url("./fonts/#g' "$SRC/app/styles/library-rail.css" > vendor/library-rail.css
rm -rf vendor/fonts vendor/brand
cp -R "$SRC/public/fonts" vendor/fonts
cp -R "$SRC/public/brand" vendor/brand
echo "vendored from live listener/ at $(git -C "$SRC" rev-parse --short HEAD)"
