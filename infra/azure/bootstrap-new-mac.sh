#!/usr/bin/env bash
# bootstrap-new-mac.sh — one-command Azure bootstrap for a new Mac.
#
# Assumes you have already:
#   1. Installed Homebrew
#   2. Installed Cowork desktop app + signed in
#   3. Cloned the journal repo (you're running this from inside it)
#
# Does everything else:
#   - Verifies az + git are installed
#   - Runs az login if not logged in
#   - Confirms the subscription matches azure-config.env
#   - Fetches Azure secrets into Mac Keychain (Key Vault if enabled, else direct)
#   - Verifies the full stack is reachable
#   - Prints next manual steps (if any)
#
# Idempotent. Safe to re-run after partial failures.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/azure-config.env"

# --- Sanity checks ----------------------------------------------------------
echo "==> [1/7] Checking prerequisites"

missing=()
command -v brew >/dev/null 2>&1 || missing+=("brew (https://brew.sh)")
command -v git  >/dev/null 2>&1 || missing+=("git")
command -v az   >/dev/null 2>&1 || missing+=("azure-cli (brew install azure-cli)")

if [ ${#missing[@]} -gt 0 ]; then
  echo "ERROR: missing prerequisites:" >&2
  for m in "${missing[@]}"; do echo "  · $m" >&2; done
  echo "" >&2
  echo "Install them, then re-run this script." >&2
  exit 1
fi
echo "    brew, git, az  →  OK"

# --- Config file present? ---------------------------------------------------
if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: $CONFIG_FILE not found." >&2
  echo "       Are you in the right repo? cd to journal/ and try again." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"
echo "    azure-config.env loaded  →  app=$APP_NAME  rg=$RESOURCE_GROUP  region=$LOCATION"

# --- Azure login -----------------------------------------------------------
echo
echo "==> [2/7] Azure login"

if ! az account show >/dev/null 2>&1; then
  echo "    Not logged in — opening browser…"
  az login --output none
fi

CURRENT_SUB=$(az account show --query id -o tsv)
if [ "$CURRENT_SUB" != "$SUBSCRIPTION_ID" ]; then
  echo "    Switching to subscription $SUBSCRIPTION_ID"
  az account set --subscription "$SUBSCRIPTION_ID"
fi

CURRENT_NAME=$(az account show --query name -o tsv)
echo "    Active: $CURRENT_NAME ($SUBSCRIPTION_ID)  →  OK"

# --- Resource group reachable? ---------------------------------------------
echo
echo "==> [3/7] Resource group reachable"

if ! az group show --name "$RESOURCE_GROUP" --output none 2>/dev/null; then
  cat >&2 <<EOF
ERROR: resource group '$RESOURCE_GROUP' not found in subscription $SUBSCRIPTION_ID.

Either:
  · You logged in with the wrong account (try: az logout && az login)
  · The Azure stack was never provisioned (run: ./provision-azure.sh)
  · Someone deleted the resource group (recreate with: ./provision-azure.sh)
EOF
  exit 1
fi
echo "    $RESOURCE_GROUP  →  OK"

# --- Fetch keys to Keychain ------------------------------------------------
echo
echo "==> [4/7] Fetching API keys → macOS Keychain"
"$SCRIPT_DIR/store-keychain-keys.sh"

# --- Verify whole stack ----------------------------------------------------
echo
echo "==> [5/7] Verifying stack integrity"
if "$SCRIPT_DIR/verify-azure.sh"; then
  echo "    All checks passed."
else
  echo "ERROR: verification failed. See output above." >&2
  exit 1
fi

# --- Install Claude Code skills + agent wrappers ---------------------------
echo
echo "==> [6/7] Installing Claude Code skills + agent wrappers"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -x "$REPO_ROOT/scripts/install-claude-skills.sh" ]; then
  "$REPO_ROOT/scripts/install-claude-skills.sh"
else
  echo "    SKIP scripts/install-claude-skills.sh not found or not executable"
  echo "         (expected at $REPO_ROOT/scripts/install-claude-skills.sh)"
fi

# --- Next steps (manual, can't be automated from a script) -----------------
echo
echo "==> [7/7] Manual next steps"
echo
echo "    Azure side: DONE. Skills can read keys from Keychain now."
echo "    Skills side: DONE. /journal and /podcast SKILL.md mirrored;"
echo "                       .claude/agents/ wrappers installed."
echo
echo "    Cowork side (one-time per Mac):"
echo "      · Restart Cowork so it picks up the new skill registrations"
echo "      · Confirm /podcast appears in the slash menu"
echo
echo "    Test the skills with a small action before starting any large workflow."
echo
echo "    Optional — static-site hosting via Cloudflare Pages:"
echo "      · Install asif-deploy: clone github.com/asifhussain60/asif-deploy"
echo "        and run ./infra/setup.sh — fire-and-forget."
