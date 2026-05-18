#!/usr/bin/env bash
# migrate-to-keyvault.sh — push existing Keychain entries to Azure Key Vault.
#
# Run this once, on your primary Mac, AFTER provisioning the Key Vault
# (i.e., after ENABLE_KEYVAULT="true" + ./provision-azure.sh).
#
# What this script does:
#   - Reads each azure-<app>-* entry from this Mac's Keychain
#   - Uploads it to $KEYVAULT_NAME as a secret with the same name
#   - Skips entries already in Key Vault with the same value (idempotent)
#
# After this script runs:
#   - Key Vault becomes the source of truth for Azure secrets
#   - Keychain on each Mac is a local cache, refreshed by store-keychain-keys.sh
#
# Re-running this script also works as the rotation pipeline:
#   1. Rotate the underlying Azure key (az cognitiveservices ... regenerate)
#   2. Run store-keychain-keys.sh to pull the new value into local Keychain
#   3. Run this script to push the new value into Key Vault
#   4. On other Macs: run store-keychain-keys.sh to refresh local Keychain

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/azure-config.env"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: $CONFIG_FILE not found." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"

if [ "${ENABLE_KEYVAULT:-false}" != "true" ]; then
  cat >&2 <<EOF
ERROR: ENABLE_KEYVAULT is not "true" in $CONFIG_FILE.

To enable:
  sed -i '' 's/ENABLE_KEYVAULT="false"/ENABLE_KEYVAULT="true"/' "$CONFIG_FILE"
  ./provision-azure.sh        # creates the Key Vault
  ./migrate-to-keyvault.sh    # re-run this script
EOF
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  echo "ERROR: az CLI not found." >&2
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "ERROR: not logged in. Run: az login" >&2
  exit 1
fi

if ! az keyvault show --name "$KEYVAULT_NAME" --output none 2>/dev/null; then
  cat >&2 <<EOF
ERROR: Key Vault '$KEYVAULT_NAME' not found.

Provision it first:
  ./provision-azure.sh
EOF
  exit 1
fi

PREFIX="azure-${APP_NAME}"

# Build the list of Keychain entries to migrate.
# Key Vault secret names must be alphanumeric or hyphens — our prefix already
# fits, so we use the same name on both sides.
ENTRIES=()
[ "$ENABLE_TRANSLATOR" = "true" ] && ENTRIES+=(
  "translator-key1"
  "translator-endpoint-text"
  "translator-endpoint-document"
  "translator-region"
)
[ "$ENABLE_DOCINTEL" = "true" ] && ENTRIES+=(
  "docintel-key1"
  "docintel-endpoint"
  "docintel-region"
)
[ "${ENABLE_SPEECH:-false}" = "true" ] && ENTRIES+=(
  "speech-key1"
  "speech-endpoint"
  "speech-region"
)
[ "$ENABLE_STORAGE" = "true" ] && ENTRIES+=(
  "storage-key1"
  "storage-endpoint"
  "storage-account"
)

echo "==> Pushing ${#ENTRIES[@]} secrets from Keychain → $KEYVAULT_NAME"

PUSHED=0
SKIPPED=0
MISSING=0

for entry in "${ENTRIES[@]}"; do
  service="${PREFIX}-${entry}"
  kv_name="${PREFIX}-${entry}"
  # Key Vault secret names can't contain underscores; ours don't, but guard anyway.
  kv_name="${kv_name//_/-}"

  # Read from Keychain
  if ! local_value=$(security find-generic-password -s "$service" -w 2>/dev/null); then
    echo "  MISS  $service (not in Keychain — skipping)"
    MISSING=$((MISSING + 1))
    continue
  fi

  # Compare with current Key Vault value, if any
  current_value=$(az keyvault secret show \
    --vault-name "$KEYVAULT_NAME" --name "$kv_name" \
    --query value -o tsv 2>/dev/null || true)

  if [ "$current_value" = "$local_value" ]; then
    echo "  SAME  $kv_name (already up to date)"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  # Push
  az keyvault secret set \
    --vault-name "$KEYVAULT_NAME" \
    --name "$kv_name" \
    --value "$local_value" \
    --output none
  echo "  PUSH  $kv_name"
  PUSHED=$((PUSHED + 1))
done

echo
echo "Summary: pushed $PUSHED · unchanged $SKIPPED · missing $MISSING"
echo
echo "To verify a value in Key Vault (no secret printed):"
echo "  az keyvault secret show --vault-name $KEYVAULT_NAME --name ${PREFIX}-translator-region --query value -o tsv"
echo
echo "Next: on every Mac (including this one), run:"
echo "  ./store-keychain-keys.sh"
echo "Once Key Vault is the source of truth, the store script should be updated"
echo "to read from Key Vault first (TODO when the migration is fully cut over)."
