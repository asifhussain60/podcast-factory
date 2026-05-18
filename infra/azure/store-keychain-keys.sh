#!/usr/bin/env bash
# store-keychain-keys.sh — fetch API keys from Azure and store them in
# macOS Keychain with consistent naming.
#
# Pre-reqs:
#   1. provision-azure.sh has already run successfully
#   2. You are logged in: az login
#   3. azure-config.env exists with the same values used to provision
#
# What this script does:
#   - Sources azure-config.env (same file used by provision-azure.sh)
#   - For each enabled resource, fetches Key 1 + endpoint via az CLI
#   - Stores entries in the macOS login keychain under names like:
#       azure-<app>-translator-key1
#       azure-<app>-translator-endpoint-document
#       azure-<app>-translator-region
#       azure-<app>-docintel-key1
#       azure-<app>-docintel-endpoint
#       azure-<app>-docintel-region
#       azure-<app>-speech-key1
#       azure-<app>-speech-endpoint
#       azure-<app>-speech-region
#
# Idempotent — uses `security add-generic-password -U` which updates if the
# entry already exists.
#
# Naming convention rationale:
#   - Prefixed `azure-<app>-` so multiple apps coexist without collision.
#   - Region stored separately because some translator API calls need it as
#     an HTTP header, and the value isn't always derivable from the endpoint.
#
# Source-of-truth priority (per docs/multi-mac-runbook.md Phase 2):
#   - When ENABLE_KEYVAULT="true" AND the Key Vault is reachable, fetch each
#     secret from Key Vault FIRST (single rotation point across all Macs).
#   - Fall back to direct Azure-resource queries when Key Vault is unavailable
#     or returns a miss (also the bootstrap path on the very first Mac, before
#     Phase 2 has been run).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/azure-config.env"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: $CONFIG_FILE not found. Run provision-azure.sh first." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"

if ! command -v az >/dev/null 2>&1; then
  echo "ERROR: az CLI not in PATH. brew install azure-cli" >&2
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "ERROR: not logged in. Run: az login" >&2
  exit 1
fi

PREFIX="azure-${APP_NAME}"

# Resolve whether Key Vault is the active source-of-truth for this run.
USE_KEYVAULT=0
if [ "${ENABLE_KEYVAULT:-false}" = "true" ]; then
  if az keyvault show --name "$KEYVAULT_NAME" --output none 2>/dev/null; then
    USE_KEYVAULT=1
    echo "==> Source-of-truth: Key Vault ($KEYVAULT_NAME)"
  else
    echo "==> Source-of-truth: Azure resources (Key Vault enabled in config but '$KEYVAULT_NAME' unreachable)"
  fi
else
  echo "==> Source-of-truth: Azure resources (ENABLE_KEYVAULT=false)"
fi

# Try to read a single secret from Key Vault. Echoes the value on success;
# returns non-zero on miss/unreachable so the caller can fall back.
kv_read() {
  # $1 = key vault secret name (must match the keychain service suffix exactly)
  local kv_name="${PREFIX}-$1"
  az keyvault secret show \
    --vault-name "$KEYVAULT_NAME" --name "$kv_name" \
    --query value -o tsv 2>/dev/null
}

store() {
  # $1 = keychain service name suffix, $2 = value
  local service="$PREFIX-$1"
  local value="$2"
  if [ -z "$value" ]; then
    echo "    SKIP $service (no value returned)"
    return
  fi
  security add-generic-password -U -a "$USER" -s "$service" -w "$value"
  echo "    OK   $service"
}

# KV-then-Azure helper: prefer Key Vault for this entry; fall back to the
# direct-Azure value the caller already fetched. When KV is the SoT but is
# missing the entry, print a NOTE so the user can resolve the drift via
# `migrate-to-keyvault.sh`.
kv_then_az() {
  # $1 = suffix (e.g., "translator-key1"), $2 = fallback value (already
  # fetched from the Azure resource by the caller)
  local suffix="$1"
  local fallback="$2"
  if [ "$USE_KEYVAULT" = "1" ]; then
    local kv_value
    kv_value=$(kv_read "$suffix" || true)
    if [ -n "$kv_value" ]; then
      store "$suffix" "$kv_value"
      return
    fi
    echo "    NOTE $PREFIX-$suffix missing from Key Vault (using direct fetch — consider re-running migrate-to-keyvault.sh)"
  fi
  store "$suffix" "$fallback"
}

# --- Translator -------------------------------------------------------------
if [ "$ENABLE_TRANSLATOR" = "true" ]; then
  echo "==> Translator keys → keychain"
  TR_KEY=$(az cognitiveservices account keys list \
    --name "$TRANSLATOR_NAME" --resource-group "$RESOURCE_GROUP" \
    --query key1 -o tsv)
  TR_DOC_EP=$(az cognitiveservices account show \
    --name "$TRANSLATOR_NAME" --resource-group "$RESOURCE_GROUP" \
    --query properties.endpoint -o tsv)
  # The text-translation endpoint is the global service, not the per-resource one.
  TR_TEXT_EP="https://api.cognitive.microsofttranslator.com/"

  kv_then_az "translator-key1"               "$TR_KEY"
  kv_then_az "translator-endpoint-text"      "$TR_TEXT_EP"
  kv_then_az "translator-endpoint-document"  "$TR_DOC_EP"
  kv_then_az "translator-region"             "$LOCATION"
fi

# --- Document Intelligence --------------------------------------------------
if [ "$ENABLE_DOCINTEL" = "true" ]; then
  echo "==> Document Intelligence keys → keychain"
  DI_KEY=$(az cognitiveservices account keys list \
    --name "$DOCINTEL_NAME" --resource-group "$RESOURCE_GROUP" \
    --query key1 -o tsv)
  DI_EP=$(az cognitiveservices account show \
    --name "$DOCINTEL_NAME" --resource-group "$RESOURCE_GROUP" \
    --query properties.endpoint -o tsv)

  kv_then_az "docintel-key1"     "$DI_KEY"
  kv_then_az "docintel-endpoint" "$DI_EP"
  kv_then_az "docintel-region"   "$LOCATION"
fi

# --- Speech (Cognitive Services Speech-to-Text) -----------------------------
if [ "${ENABLE_SPEECH:-false}" = "true" ]; then
  echo "==> Speech keys → keychain"
  SP_KEY=$(az cognitiveservices account keys list \
    --name "$SPEECH_NAME" --resource-group "$RESOURCE_GROUP" \
    --query key1 -o tsv)
  # Fast Transcription uses the region-based endpoint, not the per-resource one.
  SP_EP="https://${LOCATION}.api.cognitive.microsoft.com"

  kv_then_az "speech-key1"     "$SP_KEY"
  kv_then_az "speech-endpoint" "$SP_EP"
  kv_then_az "speech-region"   "$LOCATION"
fi

# --- Storage ----------------------------------------------------------------
if [ "$ENABLE_STORAGE" = "true" ]; then
  echo "==> Storage account key → keychain"
  ST_KEY=$(az storage account keys list \
    --account-name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" \
    --query "[0].value" -o tsv)
  ST_EP="https://${STORAGE_ACCOUNT_NAME}.blob.core.windows.net/"

  kv_then_az "storage-key1"     "$ST_KEY"
  kv_then_az "storage-endpoint" "$ST_EP"
  kv_then_az "storage-account"  "$STORAGE_ACCOUNT_NAME"
fi

echo
echo "Done. To read any value back later:"
echo "  security find-generic-password -s ${PREFIX}-translator-region -w"
echo
echo "To rotate a key in Azure and update the local copy:"
echo "  az cognitiveservices account keys regenerate \\"
echo "    --name <resource-name> --resource-group $RESOURCE_GROUP --key-name Key1"
echo "  ./store-keychain-keys.sh   # re-fetches and updates Keychain"
