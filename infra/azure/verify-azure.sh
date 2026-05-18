#!/usr/bin/env bash
# verify-azure.sh — health check for the Azure stack.
#
# Runs read-only checks against every resource the provisioning script
# creates, plus the Keychain entries the store script writes. Exits non-zero
# if anything is missing or unreachable.
#
# Run anytime you want to confirm the stack is intact, or after a key
# rotation / region migration / new-Mac setup.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/azure-config.env"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: $CONFIG_FILE not found." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"

PREFIX="azure-${APP_NAME}"
PASS=0
FAIL=0

check() {
  # $1 = label, $2 = command (as a string evaluated via sh -c)
  if eval "$2" >/dev/null 2>&1; then
    echo "  PASS  $1"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $1"
    FAIL=$((FAIL + 1))
  fi
}

echo "==> Azure account"
check "az logged in"                   "az account show"
check "subscription matches config"    "[ \"\$(az account show --query id -o tsv)\" = \"$SUBSCRIPTION_ID\" ]"

echo "==> Resource group"
check "$RESOURCE_GROUP exists"         "az group show --name $RESOURCE_GROUP"

if [ "$ENABLE_TRANSLATOR" = "true" ]; then
  echo "==> Translator"
  check "$TRANSLATOR_NAME exists"      "az cognitiveservices account show --name $TRANSLATOR_NAME --resource-group $RESOURCE_GROUP"
  check "Keychain: translator-key1"    "security find-generic-password -s ${PREFIX}-translator-key1"
fi

if [ "$ENABLE_DOCINTEL" = "true" ]; then
  echo "==> Document Intelligence"
  check "$DOCINTEL_NAME exists"        "az cognitiveservices account show --name $DOCINTEL_NAME --resource-group $RESOURCE_GROUP"
  check "Keychain: docintel-key1"      "security find-generic-password -s ${PREFIX}-docintel-key1"
fi

if [ "${ENABLE_SPEECH:-false}" = "true" ]; then
  echo "==> Speech"
  check "$SPEECH_NAME exists"          "az cognitiveservices account show --name $SPEECH_NAME --resource-group $RESOURCE_GROUP"
  check "Keychain: speech-key1"        "security find-generic-password -s ${PREFIX}-speech-key1"
  check "Keychain: speech-endpoint"    "security find-generic-password -s ${PREFIX}-speech-endpoint"
  check "Keychain: speech-region"      "security find-generic-password -s ${PREFIX}-speech-region"
fi

if [ "$ENABLE_STORAGE" = "true" ]; then
  echo "==> Storage"
  check "$STORAGE_ACCOUNT_NAME exists" "az storage account show --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP"
  for c in $STORAGE_CONTAINERS; do
    check "container: $c"              "az storage container show --name $c --account-name $STORAGE_ACCOUNT_NAME --auth-mode login"
  done
fi

if [ "$ENABLE_KEYVAULT" = "true" ]; then
  echo "==> Key Vault"
  check "$KEYVAULT_NAME exists"        "az keyvault show --name $KEYVAULT_NAME"
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "All checks passed ($PASS / $((PASS + FAIL)))."
  exit 0
else
  echo "$FAIL check(s) FAILED. See output above." >&2
  exit 1
fi
