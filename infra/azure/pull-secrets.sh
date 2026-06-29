#!/usr/bin/env bash
# pull-secrets.sh — new-machine bootstrap: Key Vault → local macOS Keychain.
#
# Run once on any new Mac after cloning the repo and running `az login`.
# Pulls every secret from Key Vault and writes it to the local Keychain
# using the exact naming convention the pipeline scripts expect.
#
# Usage:
#   cd infra/azure && bash pull-secrets.sh
#
# Idempotent — safe to re-run after partial failures or key rotation.
# After a key rotation: rotate in Azure portal → run migrate-to-keyvault.sh
# on the primary Mac → run this script on every other Mac.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/azure-config.env"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: $CONFIG_FILE not found. Are you in the right repo?" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"

# ── Prerequisites ─────────────────────────────────────────────────────────────

if ! command -v az >/dev/null 2>&1; then
  echo "ERROR: az CLI not found. Install with: brew install azure-cli" >&2
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "Not logged in to Azure — opening browser..."
  az login --output none
fi

CURRENT_SUB=$(az account show --query id -o tsv)
if [ "$CURRENT_SUB" != "$SUBSCRIPTION_ID" ]; then
  echo "Switching to subscription $SUBSCRIPTION_ID..."
  az account set --subscription "$SUBSCRIPTION_ID"
fi

if [ "${ENABLE_KEYVAULT:-false}" != "true" ]; then
  echo "ERROR: ENABLE_KEYVAULT is not 'true' in $CONFIG_FILE." >&2
  echo "       Set ENABLE_KEYVAULT=\"true\" and provision the vault first." >&2
  exit 1
fi

if ! az keyvault show --name "$KEYVAULT_NAME" --output none 2>/dev/null; then
  echo "ERROR: Key Vault '$KEYVAULT_NAME' not found in subscription $SUBSCRIPTION_ID." >&2
  echo "       Run migrate-to-keyvault.sh on the primary Mac first." >&2
  exit 1
fi

echo "==> Key Vault: $KEYVAULT_NAME  ($(az keyvault show --name "$KEYVAULT_NAME" --query properties.vaultUri -o tsv))"
echo "==> Destination: macOS Keychain"
echo

# ── Pull helper ───────────────────────────────────────────────────────────────

PULLED=0
SKIPPED=0
MISSING=0

pull() {
  local kv_name="$1"       # secret name in Key Vault
  local keychain_name="$2" # service name to write into macOS Keychain

  local value
  if ! value=$(az keyvault secret show \
      --vault-name "$KEYVAULT_NAME" --name "$kv_name" \
      --query value -o tsv 2>/dev/null); then
    echo "  MISS  $kv_name (not in Key Vault — skipping)"
    MISSING=$((MISSING + 1))
    return
  fi

  # Check if local Keychain already has the same value (avoid unnecessary writes)
  local existing
  existing=$(security find-generic-password -s "$keychain_name" -w 2>/dev/null || true)
  if [ "$existing" = "$value" ]; then
    echo "  SAME  $keychain_name"
    SKIPPED=$((SKIPPED + 1))
    return
  fi

  security add-generic-password -U -a "$USER" -s "$keychain_name" -w "$value"
  echo "  OK    $keychain_name"
  PULLED=$((PULLED + 1))
}

PREFIX="azure-${APP_NAME}"

# ── Azure service secrets ─────────────────────────────────────────────────────

[ "$ENABLE_TRANSLATOR" = "true" ] && {
  echo "==> Translator"
  pull "${PREFIX}-translator-key1"              "${PREFIX}-translator-key1"
  pull "${PREFIX}-translator-endpoint-text"     "${PREFIX}-translator-endpoint-text"
  pull "${PREFIX}-translator-endpoint-document" "${PREFIX}-translator-endpoint-document"
  pull "${PREFIX}-translator-region"            "${PREFIX}-translator-region"
}

[ "$ENABLE_DOCINTEL" = "true" ] && {
  echo "==> Document Intelligence"
  pull "${PREFIX}-docintel-key1"     "${PREFIX}-docintel-key1"
  pull "${PREFIX}-docintel-endpoint" "${PREFIX}-docintel-endpoint"
  pull "${PREFIX}-docintel-region"   "${PREFIX}-docintel-region"
}

[ "${ENABLE_SPEECH:-false}" = "true" ] && {
  echo "==> Speech"
  pull "${PREFIX}-speech-key1"     "${PREFIX}-speech-key1"
  pull "${PREFIX}-speech-endpoint" "${PREFIX}-speech-endpoint"
  pull "${PREFIX}-speech-region"   "${PREFIX}-speech-region"
}

[ "${ENABLE_STORAGE:-false}" = "true" ] && {
  echo "==> Storage"
  pull "${PREFIX}-storage-key1"     "${PREFIX}-storage-key1"
  pull "${PREFIX}-storage-endpoint" "${PREFIX}-storage-endpoint"
  pull "${PREFIX}-storage-account"  "${PREFIX}-storage-account"
}

[ "${ENABLE_LANGUAGE:-false}" = "true" ] && {
  echo "==> Language (TextAnalytics)"
  pull "${PREFIX}-language-key1"     "${PREFIX}-language-key1"
  pull "${PREFIX}-language-endpoint" "${PREFIX}-language-endpoint"
  pull "${PREFIX}-language-region"   "${PREFIX}-language-region"
}

[ "${ENABLE_OPENAI:-false}" = "true" ] && {
  echo "==> Azure OpenAI (DALL-E)"
  pull "${PREFIX}-openai-key1"             "${PREFIX}-openai-key1"
  pull "${PREFIX}-openai-endpoint"         "${PREFIX}-openai-endpoint"
  pull "${PREFIX}-openai-region"           "${PREFIX}-openai-region"
  pull "${PREFIX}-openai-dalle-deployment" "${PREFIX}-openai-dalle-deployment"
}

# ── LLM API keys ─────────────────────────────────────────────────────────────

echo "==> LLM API keys"
pull "llm-gemini-api-key"    "gemini_api_key"
pull "llm-anthropic-api-key" "anthropic_api_key"

# ── Summary ───────────────────────────────────────────────────────────────────

echo
echo "Summary: pulled $PULLED · already current $SKIPPED · missing in vault $MISSING"
echo

if [ "$MISSING" -gt 0 ]; then
  echo "⚠  $MISSING secret(s) were not found in Key Vault."
  echo "   On the primary Mac, run: cd infra/azure && bash migrate-to-keyvault.sh"
  echo "   Then re-run this script."
  echo
fi

echo "Verifying pipeline credentials..."
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PY="$REPO_ROOT/.venv/bin/python3"
# Prefer the venv Python (has anthropic + google-genai for the full 9/9 check);
# fall back to system python3 if the venv hasn't been set up yet.
PY="${VENV_PY:-python3}"
[ -x "$VENV_PY" ] && PY="$VENV_PY"
if [ -f "$REPO_ROOT/scripts/podcast/test_azure_connectivity.py" ]; then
  "$PY" "$REPO_ROOT/scripts/podcast/test_azure_connectivity.py" && echo "✓ Azure connectivity OK"
else
  echo "  (test_azure_connectivity.py not found — skipping live check)"
fi
