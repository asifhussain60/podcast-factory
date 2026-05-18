#!/usr/bin/env bash
# provision-azure.sh — one-shot Azure provisioning for the Journal app
# (and any sibling app — parameterize via azure-config.env).
#
# Pre-reqs (run these once, interactively, before invoking this script):
#   1. brew install azure-cli                # macOS Homebrew
#   2. az login                              # browser OAuth into your tenant
#   3. cp azure-config.template.env azure-config.env
#   4. edit azure-config.env to match the app you're provisioning
#
# What this script does:
#   - Sources azure-config.env
#   - Verifies az CLI is logged in and the right subscription is active
#   - Creates the resource group (idempotent)
#   - Creates Translator, Document Intelligence, Storage, Key Vault as
#     enabled by the config flags
#   - Creates blob containers inside the storage account
#   - Prints endpoints + the exact commands you'll need next
#
# Idempotent — re-running only updates what's different. Safe to re-run after
# editing the config.

set -euo pipefail

# --- Resolve paths ----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/azure-config.env"
TEMPLATE_FILE="$SCRIPT_DIR/azure-config.template.env"

# --- Load config ------------------------------------------------------------
if [ ! -f "$CONFIG_FILE" ]; then
  cat >&2 <<EOF
ERROR: $CONFIG_FILE not found.

Copy the template and edit it for your app:
  cp "$TEMPLATE_FILE" "$CONFIG_FILE"
  \$EDITOR "$CONFIG_FILE"

Then re-run this script.
EOF
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"

# --- Sanity checks ----------------------------------------------------------
if ! command -v az >/dev/null 2>&1; then
  echo "ERROR: az CLI not in PATH. Install with: brew install azure-cli" >&2
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "ERROR: not logged in. Run: az login" >&2
  exit 1
fi

CURRENT_SUB=$(az account show --query id -o tsv)
if [ "$CURRENT_SUB" != "$SUBSCRIPTION_ID" ]; then
  echo "==> Switching active subscription to $SUBSCRIPTION_ID"
  az account set --subscription "$SUBSCRIPTION_ID"
fi

echo "==> App:           $APP_NAME ($APP_DESCRIPTION)"
echo "==> Subscription:  $(az account show --query name -o tsv) ($SUBSCRIPTION_ID)"
echo "==> Region:        $LOCATION"
echo "==> Resource group: $RESOURCE_GROUP"
echo

# --- Resource group ---------------------------------------------------------
echo "==> [1/5] Resource group: $RESOURCE_GROUP"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none
echo "    OK"

# --- Translator -------------------------------------------------------------
if [ "$ENABLE_TRANSLATOR" = "true" ]; then
  echo "==> [2/5] Translator: $TRANSLATOR_NAME (SKU $TRANSLATOR_SKU)"
  az cognitiveservices account create \
    --name "$TRANSLATOR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --kind TextTranslation \
    --sku "$TRANSLATOR_SKU" \
    --yes \
    --output none
  echo "    OK"
else
  echo "==> [2/5] Translator: SKIPPED (ENABLE_TRANSLATOR=false)"
fi

# --- Document Intelligence --------------------------------------------------
if [ "$ENABLE_DOCINTEL" = "true" ]; then
  echo "==> [3/6] Document Intelligence: $DOCINTEL_NAME (SKU $DOCINTEL_SKU)"
  az cognitiveservices account create \
    --name "$DOCINTEL_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --kind FormRecognizer \
    --sku "$DOCINTEL_SKU" \
    --yes \
    --output none
  echo "    OK"
else
  echo "==> [3/6] Document Intelligence: SKIPPED (ENABLE_DOCINTEL=false)"
fi

# --- Speech (Cognitive Services Speech-to-Text) -----------------------------
if [ "${ENABLE_SPEECH:-false}" = "true" ]; then
  echo "==> [4/6] Speech: $SPEECH_NAME (SKU $SPEECH_SKU)"
  az cognitiveservices account create \
    --name "$SPEECH_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --kind SpeechServices \
    --sku "$SPEECH_SKU" \
    --yes \
    --output none
  echo "    OK"
else
  echo "==> [4/6] Speech: SKIPPED (ENABLE_SPEECH=false)"
fi

# --- Storage + containers ---------------------------------------------------
if [ "$ENABLE_STORAGE" = "true" ]; then
  echo "==> [5/6] Storage account: $STORAGE_ACCOUNT_NAME (SKU $STORAGE_SKU)"

  # Check global uniqueness BEFORE create (saves a confusing error).
  AVAIL=$(az storage account check-name --name "$STORAGE_ACCOUNT_NAME" \
            --query nameAvailable -o tsv)
  if [ "$AVAIL" != "true" ]; then
    # Already exists in our subscription? That's fine.
    if az storage account show --name "$STORAGE_ACCOUNT_NAME" \
         --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null; then
      echo "    (already exists in $RESOURCE_GROUP — reusing)"
    else
      echo "ERROR: storage account name '$STORAGE_ACCOUNT_NAME' is taken by another Azure tenant." >&2
      echo "       Edit STORAGE_ACCOUNT_NAME in $CONFIG_FILE and re-run." >&2
      exit 1
    fi
  else
    az storage account create \
      --name "$STORAGE_ACCOUNT_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --location "$LOCATION" \
      --sku "$STORAGE_SKU" \
      --kind StorageV2 \
      --allow-blob-public-access false \
      --min-tls-version TLS1_2 \
      --output none
    echo "    OK"
  fi

  # Containers — use AAD auth (you're already az login'd, no need for keys).
  for container in $STORAGE_CONTAINERS; do
    echo "==>       Container: $container"
    az storage container create \
      --name "$container" \
      --account-name "$STORAGE_ACCOUNT_NAME" \
      --auth-mode login \
      --output none
  done
  echo "    OK"
else
  echo "==> [5/6] Storage: SKIPPED (ENABLE_STORAGE=false)"
fi

# --- Key Vault (optional) ---------------------------------------------------
if [ "$ENABLE_KEYVAULT" = "true" ]; then
  echo "==> [6/6] Key Vault: $KEYVAULT_NAME"
  az keyvault create \
    --name "$KEYVAULT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --enable-rbac-authorization true \
    --output none
  echo "    OK"

  # Grant the current user RBAC permissions to read/write secrets.
  USER_ID=$(az ad signed-in-user show --query id -o tsv)
  KV_ID=$(az keyvault show --name "$KEYVAULT_NAME" --query id -o tsv)
  az role assignment create \
    --role "Key Vault Secrets Officer" \
    --assignee "$USER_ID" \
    --scope "$KV_ID" \
    --output none 2>/dev/null || true
  echo "    Granted Key Vault Secrets Officer to current user"
else
  echo "==> [6/6] Key Vault: SKIPPED (ENABLE_KEYVAULT=false)"
fi

# --- Summary + next steps ---------------------------------------------------
echo
echo "============================================================"
echo "  Provisioning complete."
echo "============================================================"
echo
echo "Resources in $RESOURCE_GROUP ($LOCATION):"
az resource list --resource-group "$RESOURCE_GROUP" \
  --query "[].{Name:name, Type:type}" --output table

echo
echo "Next steps:"
echo
echo "  1. Store API keys in Mac Keychain:"
echo "       ./store-keychain-keys.sh"
echo
echo "  2. Set up the monthly budget (cannot be automated for personal MSA):"
echo "       Open: https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/budgets"
echo "       Name:     $BUDGET_NAME"
echo "       Amount:   \$$BUDGET_AMOUNT_USD / month"
echo "       Alerts:   $BUDGET_THRESHOLDS percent → $ALERT_EMAIL"
echo
echo "  3. Verify endpoints:"
if [ "$ENABLE_TRANSLATOR" = "true" ]; then
  TR_EP=$(az cognitiveservices account show --name "$TRANSLATOR_NAME" \
            --resource-group "$RESOURCE_GROUP" --query properties.endpoint -o tsv 2>/dev/null || echo "(not yet ready)")
  echo "       Translator (document): $TR_EP"
fi
if [ "$ENABLE_DOCINTEL" = "true" ]; then
  DI_EP=$(az cognitiveservices account show --name "$DOCINTEL_NAME" \
            --resource-group "$RESOURCE_GROUP" --query properties.endpoint -o tsv 2>/dev/null || echo "(not yet ready)")
  echo "       Document Intelligence: $DI_EP"
fi
if [ "${ENABLE_SPEECH:-false}" = "true" ]; then
  # Fast Transcription uses the region-based endpoint, not the per-resource one.
  echo "       Speech:                https://${LOCATION}.api.cognitive.microsoft.com"
fi
if [ "$ENABLE_STORAGE" = "true" ]; then
  echo "       Storage:               https://${STORAGE_ACCOUNT_NAME}.blob.core.windows.net/"
fi
echo
echo "Done."
