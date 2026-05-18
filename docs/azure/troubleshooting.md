# Troubleshooting — Symptom-Driven Fix Guide

Find your symptom below, follow the fix. Most of these are pitfalls we
actually hit during the 2026-05-18 setup — captured here so future-you
doesn't re-discover them.

---

## Provisioning errors

### `az: command not found`

Azure CLI isn't installed.

```sh
brew install azure-cli
```

### `Please run 'az login' to setup account`

Not logged in (or session expired).

```sh
az login
```

A browser tab opens. Pick the account you used to create the Azure
subscription (`asifhussain60@msn.com` for the journal app).

### `The subscription is not registered to use namespace 'Microsoft.CognitiveServices'`

Azure resource providers need to be enabled the first time a subscription
uses them. The script doesn't do this automatically because it usually only
happens once per subscription.

```sh
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.KeyVault

# Wait ~30 seconds, then re-run
./provision-azure.sh
```

### `The storage account named 'X' is already taken`

Storage account names are **globally unique across all of Azure**. The
script checks before creating, but if you hit this, somebody else (in a
different tenant) owns that name.

Fix: edit `azure-config.env` and change `STORAGE_ACCOUNT_NAME` to
something else — add random digits, your initials, the date, anything to
make it unique. Then re-run.

### `Invalid resource name 'jounralpodcaststorage'` (or similar typo)

Storage account names cannot be renamed after creation. If you typo'd:

```sh
az storage account delete \
  --name <wrong-name> \
  --resource-group rg-journal-ai \
  --yes

# Fix STORAGE_ACCOUNT_NAME in azure-config.env, then:
./provision-azure.sh
```

### `Free F0 tier already exists in this region`

You can only have **one Free F0 of each Cognitive Services kind per region
per subscription**. If the script bails here, you either already have one
(possibly orphaned from a deleted experiment), or you actually need to use
Standard.

```sh
# Find the existing F0:
az cognitiveservices account list --output table | grep -i F0

# Either delete it:
az cognitiveservices account delete --name <existing> --resource-group <existing-rg>

# Or change DOCINTEL_SKU="S0" in azure-config.env and re-run.
```

---

## Azure portal pitfalls — the Marketplace tile trap

**Symptom:** when you search for "Document Intelligence" or "Storage" in
the portal Marketplace, you see tiles like:

- "Document Intelligence Platform" by Stealth Labs LTD
- "AI Easy Translator" by Sýkora IT
- Various "Pig Latin Translator" and similar joke offerings

These are **third-party Azure Applications** that wrap the real Microsoft
service in a managed-application bundle. They are NOT what you want:

- They cost more (Stealth Labs Doc Intel is $100/month minimum)
- They have different validation rules (e.g., no hyphens in names)
- They prefix every parameter with their own naming conventions
- You can't easily extract the underlying Microsoft service from them

**Fix:** use deep links to the native Microsoft resource forms. The
provisioning script uses `az cli` so it bypasses this entirely. If you're
clicking through the portal:

| Resource | Deep link |
|----------|-----------|
| Document Intelligence | `https://portal.azure.com/#create/Microsoft.CognitiveServicesFormRecognizer` |
| Storage Account | `https://portal.azure.com/#create/Microsoft.StorageAccount-ARM` |
| Translator | Top portal search bar → "Translators" (under **Services**, not Marketplace) |
| Budget | `https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/budgets` |

The tell for the real Microsoft service:
- Publisher: **Microsoft** (not "Stealth Labs LTD" / "Sýkora IT" / etc.)
- Type label: **Azure Service** (not "Azure Application" / "Managed Application" / "SaaS")

---

## Keychain script errors

### `read: -p: no coprocess`

You're on zsh (default on modern macOS) and using bash syntax. The
provisioning scripts use `#!/usr/bin/env bash` so they run in bash — this
error only appears when you copy a one-off command into a zsh prompt.

The zsh-correct equivalent of `read -s -p "prompt: " VAR` is:

```sh
read -s "VAR?prompt: "
```

### `security: SecKeychainItemCreateFromContent error -25299`

A Keychain entry with that name already exists and the `-U` (update) flag
wasn't passed. The `store-keychain-keys.sh` script always passes `-U`, so
you'll only hit this if running `security add-generic-password` manually.

```sh
# Force-update an existing entry:
security add-generic-password -U -a "$USER" -s <service-name> -w <value>
```

### `security: find-generic-password: The specified item could not be found`

Keychain doesn't have that entry yet. Either:

```sh
# 1. Run the storage script (creates all entries from config)
./store-keychain-keys.sh

# 2. Or add one manually:
security add-generic-password -a "$USER" -s azure-journal-translator-key1 -w "<value>"
```

---

## Document Translation API issues

### "F0 tier doesn't support document translation"

You provisioned Translator with `TRANSLATOR_SKU="F0"`. F0 supports text
translation only.

```sh
# Upgrade to S1
az cognitiveservices account update \
  --name journal-translator \
  --resource-group rg-journal-ai \
  --sku S1
```

### Document translation returns 401 even with the right key

Document translation uses a **different endpoint** than text translation:

- Text endpoint: `https://api.cognitive.microsofttranslator.com/`
- Document endpoint: `https://<your-translator-name>.cognitiveservices.azure.com/`

Make sure the calling code reads
`azure-journal-translator-endpoint-document` (not `-endpoint-text`) for
document translation.

### Document translation can't read from blob storage

Translator authenticates to Blob Storage with a SAS token by default. If
you're using `--storage-container-name` directly, you may need to:

1. Generate a container-level SAS with read/list permissions for source,
   write/list for target.
2. Pass the SAS-tokenized URL, not the plain blob URL.

Long-term fix: enable managed identity on the Translator resource and grant
it `Storage Blob Data Contributor` on the storage account. Eliminates
SAS-token management. Not done yet — flagged in
[architecture.md § "Trust boundaries"](architecture.md).

---

## Cost / billing surprises

### Budget alert fired but I haven't done anything heavy

Likely causes:
1. Document Translation was tested on a large file (charges per character —
   a 100-page Arabic book is ~200K characters → ~$2).
2. Doc Intel S0 OCR'd more pages than expected (~$1.50 per 1K pages).
3. Egress charges if downloading large blobs from outside Azure.

Investigate:

```sh
az consumption usage list \
  --start-date "$(date -v-7d -u +%Y-%m-%d)" \
  --end-date "$(date -u +%Y-%m-%d)" \
  --query "[].{Date:usageStart, Service:meterCategory, Sub:meterSubCategory, Cost:pretaxCost}" \
  --output table | sort -k4 -r | head -20
```

### Forgot to set up the budget, racked up unexpected charges

Email Azure support — they're surprisingly forgiving on first-time accidents:
https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade

Set up the budget *now* so it can't happen again. See
[setup.md § Step 4](setup.md).

---

## Verification (`verify-azure.sh`) failures

### `FAIL subscription matches config`

You're logged in to a different subscription than the one in
`azure-config.env`.

```sh
az account set --subscription <SUBSCRIPTION_ID-from-config>
```

### `FAIL <resource-name> exists`

The named resource isn't in the resource group. Either:
- It was deleted manually (recreate: `./provision-azure.sh`)
- It's in a different resource group (check `azure-config.env`'s
  `RESOURCE_GROUP` value)
- Provisioning never completed (re-run `./provision-azure.sh`)

### `FAIL Keychain: <entry>`

Run `./store-keychain-keys.sh` — it's idempotent and will fill in any
missing entries.

### `FAIL container: <name>`

The container doesn't exist in the storage account. Either:
- The list in `STORAGE_CONTAINERS` changed and the new container hasn't
  been created — re-run `./provision-azure.sh`
- Someone deleted it manually — same fix
- Soft delete is hiding it (try restoring from the portal first)

---

## Nothing on this page helps

1. Read [architecture.md](architecture.md) to confirm you understand which
   layer is involved.
2. Check the Azure status page: https://azure.status.microsoft/en-us/status
   — East US outages do happen.
3. Open an Azure support ticket from the portal. Free-tier accounts get
   "basic" support which is fine for "this doesn't work" issues.
