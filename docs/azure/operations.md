# Operations — Day-2 Maintenance

How to keep the Azure pipeline running once it's set up. Rotations, scale
changes, cost monitoring, deletions. For breakage see
[troubleshooting.md](troubleshooting.md).

## Routine — every quarter

Three light-touch checks:

### 1. Confirm the budget is still firing

```sh
az consumption usage list --top 5 --output table  # actually billed usage
```

Open the portal and confirm the budget alerts are still configured:
https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/budgets

If the email recipient has changed (e.g., new email), update it in place —
no need to recreate the budget.

### 2. Run the health check

```sh
cd ~/PROJECTS/journal/infra/azure
./verify-azure.sh
```

Catches drift (someone deleted a container, a key rotated outside the
script, a region got migrated, etc.).

### 3. Look at last 30 days of spend

```sh
az consumption usage list \
  --start-date "$(date -v-30d -u +%Y-%m-%d)" \
  --end-date "$(date -u +%Y-%m-%d)" \
  --query "[].{Date:usageStart, Service:meterCategory, Cost:pretaxCost, Currency:currency}" \
  --output table | head -50
```

Spot anomalies: if Doc Intel suddenly shows $20 in a quiet month, something
is calling the API more than expected.

---

## Key rotation

Microsoft recommends rotating Cognitive Services keys every 90 days. The
two-key design is specifically to enable zero-downtime rotation.

### Translator + Document Intelligence

```sh
# Rotate Key 1 in Azure
az cognitiveservices account keys regenerate \
  --name journal-translator \
  --resource-group rg-journal-ai \
  --key-name Key1

# Pull the new value into Keychain (overwrites the old entry)
cd ~/PROJECTS/journal/infra/azure
./store-keychain-keys.sh
```

Same recipe for `journal-docintel` — just change the `--name`.

**Zero-downtime variant** (if the journal app is mid-translation and you
can't have any failed calls):

1. Temporarily edit the app to use `key2` instead of `key1`.
2. Rotate Key 1: `az cognitiveservices account keys regenerate ... --key-name Key1`.
3. Pull new Key 1: `./store-keychain-keys.sh`.
4. Switch app back to `key1`.
5. Rotate Key 2 too (different `--key-name Key2`) so neither key is "the
   one that's been around longest" anymore.

### Storage account keys

```sh
az storage account keys renew \
  --account-name journalpodcaststorage \
  --resource-group rg-journal-ai \
  --key key1

./store-keychain-keys.sh   # re-fetch
```

---

## Scaling Document Intelligence

The Free F0 SKU caps at **500 pages/month** and 20 calls/minute. Rāḥat
al-ʿAql alone is 591 pages, so we'll need S0 for the full archive run.

### Upgrade F0 → S0

```sh
az cognitiveservices account update \
  --name journal-docintel \
  --resource-group rg-journal-ai \
  --sku S0
```

**No downtime.** The endpoint and keys stay the same; only billing changes.
S0 is pay-per-page (no monthly minimum). Prebuilt-read OCR is ~$1.50 per
1K pages, so the full ~1500-page archive costs **~$2.25** to OCR.

To downgrade after a heavy batch:

```sh
az cognitiveservices account update \
  --name journal-docintel \
  --resource-group rg-journal-ai \
  --sku F0
```

Free tier is rate-limited but never charges, so this is a useful "park"
state between batches.

---

## Cost monitoring tips

### Per-resource cost breakdown

```sh
# Top services by spend, last billing cycle
az consumption usage list --output json | \
  python3 -c '
import json, sys, collections
data = json.load(sys.stdin)
by_service = collections.Counter()
for u in data:
    by_service[u.get("meterCategory","?")] += float(u.get("pretaxCost",0))
for s,c in by_service.most_common():
    print(f"  {s:30s}  ${c:.4f}")
'
```

### What to expect for this workload

| Activity | Approx cost |
|----------|-------------|
| Full archive OCR (~1500 pages, Doc Intel S0) | $2.25 once |
| Translate ~3M Arabic characters → English (Translator S1) | ~$30 once |
| Storage ~1 GB of PDFs + outputs (LRS) | ~$0.02/month |
| Idle stack (no API calls) | $0 |

The $50/month budget gives you ~2x headroom over the full archive run.

---

## Deleting things safely

### Delete a single container (preserve everything else)

```sh
az storage container delete \
  --name source-urdu \
  --account-name journalpodcaststorage \
  --auth-mode login
```

Soft delete is on (7 days), so undelete is possible within that window:

```sh
az storage container restore \
  --name source-urdu \
  --account-name journalpodcaststorage \
  --auth-mode login \
  --deleted-version <version-from-list-deleted>
```

### Tear down the entire stack

```sh
az group delete --name rg-journal-ai --yes --no-wait
```

Removes every resource in the group in one shot. Takes 5–10 minutes async.
Run `az group exists --name rg-journal-ai` to confirm; returns `false` once
fully gone.

Re-creating after a teardown: same `./provision-azure.sh` — the script is
fully idempotent.

---

## Moving the stack to a different region

Not recommended (it's a multi-step migration), but if you need to:

1. Stand up a parallel stack in the new region by editing `LOCATION` in
   `azure-config.env` and changing resource names (e.g., `journal-translator-west`).
2. Copy blob data between accounts:
   ```sh
   az storage blob copy start-batch \
     --source-account-name journalpodcaststorage \
     --source-container source-arabic \
     --destination-container source-arabic \
     --account-name <new-storage-account> \
     --auth-mode login
   ```
3. Cut the journal app over to the new endpoints (re-run `store-keychain-keys.sh`
   with the new config).
4. Tear down the old stack.

Document translation has region-specific feature availability — confirm
the new region supports Arabic→English document translation *before*
migrating.

---

## Migrating to Key Vault (planned)

When ready to move from Keychain-only to Key-Vault-backed-with-Keychain-cache:

```sh
# 1. Flip the flag in azure-config.env
sed -i '' 's/ENABLE_KEYVAULT="false"/ENABLE_KEYVAULT="true"/' azure-config.env

# 2. Re-run provisioning (creates the Key Vault, grants you access)
./provision-azure.sh

# 3. Push existing Keychain entries up to Key Vault
# (a migration script will go here once written — for now, do it manually
# via `az keyvault secret set --vault-name kv-journal-ai --name <name> --value <val>`)
```

After that, a second Mac runs `az login` + a one-time pull script and is
fully configured.
