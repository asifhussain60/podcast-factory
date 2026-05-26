#!/usr/bin/env bash
# bootstrap-llm-apis.sh — set up Anthropic (Claude) + Google (Gemini) on a new
# Mac for podcast-factory. Idempotent. Safe to re-run.
#
# What this script does:
#   1. Verifies `claude` CLI is installed and logged in (Max subscription).
#   2. Prompts you to paste the Gemini API key (silent — nothing echoes).
#   3. Stores the Gemini key under keychain service=gemini_api_key.
#   4. Runs verify-llm-apis.sh to confirm both providers are reachable.
#
# What this script does NOT do:
#   - Does not store an Anthropic API key. The pipeline uses the Max
#     subscription via `claude login`, not an API key. See ../README.md.
#   - Does not provision Google Cloud projects or billing. Those are
#     one-time manual setup in the Google Cloud console (see
#     ../README.md §"Provider 2 — Google (Gemini)").
#
# Where to get the Gemini key:
#   Open https://aistudio.google.com/apikey
#   Find the `podcast-factory` row
#   Click the copy icon (don't manually select — avoids trailing whitespace)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [1/3] Checking Claude Code authentication"
if ! command -v claude >/dev/null 2>&1; then
  cat >&2 <<EOF
ERROR: \`claude\` CLI not found on PATH.

Install:
  brew install --cask claude-code

Then run:
  claude login        # OAuth flow; sign in as asifhussain60@gmail.com (Max plan)

Then re-run this script.
EOF
  exit 1
fi
echo "    claude CLI present: $(claude --version 2>&1 | head -1)"
echo "    Note: this script does not test \`claude -p\` (would consume a call)."
echo "          Run verify-llm-apis.sh after this completes."

echo
echo "==> [2/3] Storing Gemini API key in keychain"

# Idempotent: delete any existing entry first, then add the new value.
# Suppresses the "not found" stderr on a fresh machine.
security delete-generic-password -s gemini_api_key -a "$USER" 2>/dev/null || true

# Silent prompt — nothing echoes while pasting.
# `read -rs` works in both bash and zsh.
echo
echo "    Paste your Gemini API key now. Nothing will appear on screen."
echo "    The key starts with AQ.Ab8... (newer format) or AIza... (older format)."
echo
read -rs -p "    Key: " GEMINI_KEY
echo

if [ -z "$GEMINI_KEY" ]; then
  echo "ERROR: empty input. Aborting." >&2
  exit 1
fi

# Basic sanity-check: keys should be 39 chars (AIza...) or 53 chars (AQ.Ab8...).
KEY_LEN=${#GEMINI_KEY}
if [ "$KEY_LEN" -lt 30 ] || [ "$KEY_LEN" -gt 100 ]; then
  echo "ERROR: key length $KEY_LEN is outside expected 30-100 char range." >&2
  echo "       Did you paste the entire key? Aborting." >&2
  unset GEMINI_KEY
  exit 1
fi

security add-generic-password -s gemini_api_key -a "$USER" -w "$GEMINI_KEY"
unset GEMINI_KEY
echo "    OK   keychain entry service=gemini_api_key account=$USER ($KEY_LEN chars)"

echo
echo "==> [3/3] Running verification probe"
echo
bash "$SCRIPT_DIR/verify-llm-apis.sh"
