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
#
# Idempotent — uses `security add-generic-password -U` which updates if the
# entry already exists.
#
# Naming convention rationale:
#   - Prefixed `azure-<app>-` so multiple apps coexist without collision.
#   - Region stored separately because some translator API calls need it as
#     an HTTP header, and the value isn't always derivable from the endpoint.

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

  store "translator-key1"               "$TR_KEY"
  store "translator-endpoint-text"      "$TR_TEXT_EP"
  store "translator-endpoint-document"  "$TR_DOC_EP"
  store "translator-region"             "$LOCATION"
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

  store "docintel-key1"     "$DI_KEY"
  store "docintel-endpoint" "$DI_EP"
  store "docintel-region"   "$LOCATION"
fi

# --- Storage ----------------------------------------------------------------
if [ "$ENABLE_STORAGE" = "true" ]; then
  echo "==> Storage account key → keychain"
  ST_KEY=$(az storage account keys list \
    --account-name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" \
    --query "[0].value" -o tsv)
  ST_EP="https://${STORAGE_ACCOUNT_NAME}.blob.core.windows.net/"

  store "storage-key1"     "$ST_KEY"
  store "storage-endpoint" "$ST_EP"
  store "storage-account"  "$STORAGE_ACCOUNT_NAME"
fi

echo
echo "Done. To read any value back later:"
echo "  security find-generic-password -s ${PREFIX}-translator-region -w"
echo
echo "To rotate a key in Azure and update the local copy:"
echo "  az cognitiveservices account keys regenerate \\"
echo "    --name <resource-name> --resource-group $RESOURCE_GROUP --key-name Key1"
echo "  ./store-keychain-keys.sh   # re-fetches and updates Keychain"
