# Setup — Bringing the Azure Pipeline Up from Zero

Use this when you're on a fresh Mac, recovering from a wipe, or helping a
future-you who has forgotten everything. Estimated time end-to-end:
**~25 minutes**, most of it waiting for resource deployments.

The provisioning is **automated** via three scripts in [`infra/azure/`](../../infra/azure/):

- [`provision-azure.sh`](../../infra/azure/provision-azure.sh) — creates all resources
- [`store-keychain-keys.sh`](../../infra/azure/store-keychain-keys.sh) — fetches keys and stores them in macOS Keychain
- [`verify-azure.sh`](../../infra/azure/verify-azure.sh) — health check that everything is wired up

If you want to understand what the scripts do, read
[architecture.md](architecture.md) first. If you just want a working stack,
follow the numbered steps below.

---

## Pre-requisites (one-time per Mac)

```sh
# 1. Install the Azure CLI
brew install azure-cli

# 2. Log in (opens browser)
az login

# 3. Confirm the right subscription is active
az account show --query name -o tsv
# Expect: "Azure subscription 1" (or whatever you renamed it to)
```

If `az account show` returns the wrong subscription:

```sh
az account set --subscription <SUBSCRIPTION_ID>
```

Find your subscription ID with `az account list --output table`.

---

## Provisioning (first time for this app)

### Step 1 — copy the config template and edit it

```sh
cd ~/PROJECTS/journal/infra/azure
cp azure-config.template.env azure-config.env
$EDITOR azure-config.env
```

Every variable is documented inline in the template. The defaults match the
journal app's existing stack. Most fields are safe to leave alone; the ones
you'll touch most often:

- `APP_NAME` — used as a prefix everywhere
- `STORAGE_ACCOUNT_NAME` — must be globally unique; if it's taken, pick another
- `ALERT_EMAIL` — where budget alerts go

### Step 2 — run the provisioning script

```sh
./provision-azure.sh
```

Takes 3–4 minutes. Idempotent — safe to re-run if it errors out partway
through. It prints a per-resource status line as it goes:

```
==> App:           journal (Memoir podcast pipeline — Arabic OCR + English translation)
==> Subscription:  Azure subscription 1 (3440564d-...)
==> Region:        eastus
==> Resource group: rg-journal-ai

==> [1/5] Resource group: rg-journal-ai
    OK
==> [2/5] Translator: journal-translator (SKU S1)
    OK
...
```

If a step errors, fix the underlying issue (see
[troubleshooting.md](troubleshooting.md)) and re-run. Existing resources are
left alone; only missing ones are created.

### Step 3 — store API keys in Keychain

```sh
./store-keychain-keys.sh
```

Fetches Key 1 + endpoints for each resource from Azure and writes them
into the macOS login keychain. Takes ~10 seconds. Output looks like:

```
==> Translator keys → keychain
    OK   azure-journal-translator-key1
    OK   azure-journal-translator-endpoint-text
    OK   azure-journal-translator-endpoint-document
    OK   azure-journal-translator-region
==> Document Intelligence keys → keychain
    OK   azure-journal-docintel-key1
    OK   azure-journal-docintel-endpoint
    OK   azure-journal-docintel-region
==> Storage account key → keychain
    OK   azure-journal-storage-key1
    OK   azure-journal-storage-endpoint
    OK   azure-journal-storage-account
```

### Step 4 — set up the budget (manual — only step that can't be scripted)

Azure CLI cannot create budgets on personal pay-as-you-go subscriptions.
Open the portal and create it manually:

1. Open https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/budgets
2. Click **+ Add**.
3. **Basics**:
   - Name: `journal-ai-monthly-cap` (or whatever `BUDGET_NAME` is in your config)
   - Reset period: **Billing month**
   - Expiration date: pick something ~24 months out
   - Amount: `50` (or `BUDGET_AMOUNT_USD` from your config)
4. **Set alerts**: three rows, all Type = "Actual cost":
   - 50% / 80% / 100% of budget
   - Email: `asifhussain60@gmail.com` (or whatever `ALERT_EMAIL` is)
5. Click **Create**.

### Step 5 — verify everything is wired up

```sh
./verify-azure.sh
```

Runs read-only checks across every resource + every Keychain entry. Exits
zero only if all checks pass. Example output:

```
==> Azure account
  PASS  az logged in
  PASS  subscription matches config
==> Resource group
  PASS  rg-journal-ai exists
==> Translator
  PASS  journal-translator exists
  PASS  Keychain: translator-key1
...
All checks passed (12 / 12).
```

If anything fails, see [troubleshooting.md](troubleshooting.md).

---

## Re-using an existing Azure stack (second Mac)

If `rg-journal-ai` already exists in Azure and you just want this Mac to
talk to it:

```sh
# 1. Install + log in
brew install azure-cli
az login

# 2. Copy the existing config (or recreate it — the resource names are
#    what matter; values must match what's already deployed)
cd ~/PROJECTS/journal/infra/azure
cp azure-config.template.env azure-config.env
$EDITOR azure-config.env    # match the existing deployment

# 3. Skip provision-azure.sh entirely. Just pull the keys:
./store-keychain-keys.sh

# 4. Verify
./verify-azure.sh
```

This works because `store-keychain-keys.sh` is read-only on Azure — it only
fetches keys, doesn't create anything.

**Better long-term**: once `ENABLE_KEYVAULT="true"` and secrets are
migrated to Key Vault, the per-Mac dance becomes one `az login` + one
fetch script.

---

## Adapting for a different app

The whole point of parameterizing via `azure-config.env` is that the same
scripts work for any app. To stand up a parallel stack for, say, a future
"Trip-log AI" project:

```sh
# 1. Make a new config
cd ~/PROJECTS/journal/infra/azure
cp azure-config.template.env triplog-config.env

# 2. Edit the values:
#    APP_NAME="triplog"
#    APP_DESCRIPTION="Trip-log AI helpers"
#    RESOURCE_GROUP="rg-triplog-ai"
#    TRANSLATOR_NAME="triplog-translator"
#    DOCINTEL_NAME="triplog-docintel"
#    STORAGE_ACCOUNT_NAME="triplogstorageNNN"  # globally unique
#    STORAGE_CONTAINERS="raw-images raw-audio processed"
#    ENABLE_TRANSLATOR="false"  # if you don't need it
#    etc.

# 3. Run with the new config (provision-azure.sh sources azure-config.env
#    by default, so either rename your file or temporarily symlink:
ln -sf triplog-config.env azure-config.env

./provision-azure.sh
./store-keychain-keys.sh
./verify-azure.sh
```

Each app gets its own resource group, its own Keychain prefix
(`azure-<APP_NAME>-...`), and an isolated cost surface. Nothing collides
with the journal app's stack.

---

## What gets created — summary

After a successful run:

```
rg-journal-ai (East US)
├── journal-translator        Translator        Standard S1
├── journal-docintel          FormRecognizer    Free F0
├── journalpodcaststorage     StorageV2         Standard LRS
│   ├── source-arabic
│   ├── source-urdu
│   └── translated-english
├── kv-journal-ai             Key Vault         (only if ENABLE_KEYVAULT=true)
└── journal-ai-monthly-cap    Budget            $50/mo (set up manually)
```

Plus 10 Keychain entries (12 if Key Vault enabled).

Total monthly cost when idle: **~$0**. Costs are entirely usage-based —
Translator charges per character translated, Doc Intel per page OCRed,
Storage per GB stored + per operation. The budget alert catches you well
before any real damage.
