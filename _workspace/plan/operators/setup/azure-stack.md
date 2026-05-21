# Azure stack — resources, keychain, recreate from scratch

Authoritative reference for the Azure side of the pipeline. The pipeline currently uses **4 Azure resources** for OCR, translation, and NER pre-seed, plus optional storage and speech.

## Live configuration

Source of truth: [../../../../infra/azure/azure-config.env](../../../../infra/azure/azure-config.env). That file is intentionally tracked — it contains **non-secret** config (subscription ID, region, resource names, feature flags). Secrets live in macOS Keychain, never in tracked files.

| Field | Value | Used by |
|---|---|---|
| Subscription | `Journal AI — primary` (ID `3440564d-c056-4173-bec6-7af92dbece77`) | All resources |
| Resource group | `rg-journal-ai` | All resources |
| Region | `eastus` | All resources |
| App namespace | `journal` (drives keychain naming) | All Mac machines |

## Resource inventory

| Resource name | Type / Kind | SKU/Tier | Pipeline phase | Endpoint |
|---|---|---|---|---|
| [journal-docintel](https://portal.azure.com/#@/resource/subscriptions/3440564d-c056-4173-bec6-7af92dbece77/resourceGroups/rg-journal-ai/providers/Microsoft.CognitiveServices/accounts/journal-docintel/overview) | Document Intelligence | (see azure-config.env) | 0a (OCR) | (in keychain) |
| [journal-translator](https://portal.azure.com/#@/resource/subscriptions/3440564d-c056-4173-bec6-7af92dbece77/resourceGroups/rg-journal-ai/providers/Microsoft.CognitiveServices/accounts/journal-translator/overview) | Translator | S1 | 0a (AR→EN translation) | (in keychain) |
| [journal-language-market](https://portal.azure.com/#@/resource/subscriptions/3440564d-c056-4173-bec6-7af92dbece77/resourceGroups/rg-journal-ai/providers/Microsoft.CognitiveServices/accounts/journal-language-market/overview) | Cognitive Services Language (Kind: `TextAnalytics`) | Free F0 | 0a.5 NER pre-seed (pending framework wiring) | `https://journal-language-market.cognitiveservices.azure.com/` |
| journalpodcaststorage | Storage account | (see azure-config.env) | ancillary, not pipeline-critical | (storage URL) |

Optional / feature-flagged:
- `journal-speech` (Speech) — `ENABLE_SPEECH=true` in azure-config.env; enabled 2026-05-18 for Urdu lecture transcription on `kunooz-al-hikmah`
- Key Vault (`ENABLE_KEYVAULT=false` until multi-Mac migration kicks off — see [../../../../infra/azure/migrate-to-keyvault.sh](../../../../infra/azure/migrate-to-keyvault.sh))

## Keychain entries (per machine)

Naming convention: `azure-<APP_NAME>-<resource>-<field>` where `APP_NAME=journal`. Each machine populates its own keychain — separate stores per machine, populated by [../../../../infra/azure/store-keychain-keys.sh](../../../../infra/azure/store-keychain-keys.sh).

Resolution priority in [../../../../scripts/podcast/_azure.py](../../../../scripts/podcast/_azure.py) `_resolve()`:
1. Environment variable (for CI) — `AZURE_DOCINTEL_KEY`, `AZURE_TRANSLATOR_KEY`, etc.
2. macOS Keychain (local-Mac fallback) — the names below

| Service name | Type | Required for |
|---|---|---|
| `azure-journal-docintel-endpoint` | public | Phase 0a (OCR) |
| `azure-journal-docintel-key1` | secret | Phase 0a (OCR) |
| `azure-journal-docintel-region` | public | Phase 0a (OCR) |
| `azure-journal-translator-endpoint-text` | public | Phase 0a (translation) |
| `azure-journal-translator-key1` | secret | Phase 0a (translation) |
| `azure-journal-translator-region` | public | Phase 0a (translation) |
| `azure-journal-language-endpoint` | public | Phase 0a.5 (NER) |
| `azure-journal-language-key1` | secret | Phase 0a.5 (NER) — 84-char Base64 on the Language SKU |
| `azure-journal-language-region` | public | Phase 0a.5 (NER) |
| `azure-journal-speech-endpoint` | public | (optional) Speech phase |
| `azure-journal-speech-key1` | secret | (optional) Speech phase |
| `azure-journal-speech-region` | public | (optional) Speech phase |

## Recreate-from-scratch procedure

Use this if Azure account is wiped, or for a brand-new project. Each step is idempotent.

### Step 1 — Provision Azure resources (run ONCE per Azure account)

```bash
cd <repo>/infra/azure
# Log in as the owning Azure account:
az login
az account set --subscription "Journal AI — primary"
bash provision-azure.sh
```

This creates `rg-journal-ai` (if missing) and all enabled resources from [../../../../infra/azure/azure-config.env](../../../../infra/azure/azure-config.env). Idempotent — re-running just updates anything that drifted.

### Step 2 — Populate the local Mac's keychain (run ONCE per Mac)

```bash
cd <repo>/infra/azure
bash store-keychain-keys.sh
```

What it does:
- Sources `azure-config.env`
- Calls `az cognitiveservices account keys list` per enabled resource
- Stores each key + endpoint + region in macOS Keychain under the names above
- Uses `security add-generic-password -U` (the `-U` flag updates if entry exists)

First time you run it, macOS may pop up a Keychain Access dialog asking "Always Allow" — choose Always Allow.

### Step 3 — Verify end-to-end

```bash
cd <repo>/infra/azure
bash verify-azure.sh
```

Probes credential resolution + an authenticated call against each enabled resource. Should print all green.

### Manual verification of one resource (no script needed)

```bash
ENDPOINT=$(security find-generic-password -s azure-journal-language-endpoint -w)
KEY=$(security find-generic-password -s azure-journal-language-key1 -w)
curl -sS -o /dev/null -w "HTTP %{http_code}\n" \
    -X POST "${ENDPOINT}language/:analyze-text?api-version=2023-04-01" \
    -H "Ocp-Apim-Subscription-Key: ${KEY}" \
    -H "Content-Type: application/json" \
    -d '{"kind":"EntityRecognition","analysisInput":{"documents":[{"id":"1","language":"en","text":"Cairo."}]}}'
unset KEY
# Expect: HTTP 200
```

Substitute `docintel`, `translator`, etc. for `language` to test each resource individually.

## Adding a new Azure resource to the stack

1. Edit [../../../../infra/azure/azure-config.env](../../../../infra/azure/azure-config.env) to add `<RESOURCE>_NAME="..."` and `ENABLE_<RESOURCE>="true"`.
2. Update [../../../../infra/azure/provision-azure.sh](../../../../infra/azure/provision-azure.sh) with the new resource's `az` provisioning block.
3. Update [../../../../infra/azure/store-keychain-keys.sh](../../../../infra/azure/store-keychain-keys.sh) with the new keychain block (3 entries: endpoint, key1, region).
4. Update [../../../../infra/azure/verify-azure.sh](../../../../infra/azure/verify-azure.sh) with the new probe.
5. Add `<resource>Creds` dataclass + `get_<resource>()` resolver to [../../../../scripts/podcast/_azure.py](../../../../scripts/podcast/_azure.py).
6. Run `provision-azure.sh` (creates resource in Azure), then `store-keychain-keys.sh` on each Mac.
7. Update this doc's "Resource inventory" + "Keychain entries" tables.
8. Commit on `develop` so both machines see the change.

## Known gotchas

| Symptom | Cause / Fix |
|---|---|
| Newer Azure resources have 84-char Base64 keys instead of 32-char hex | Both formats work transparently in `_azure.py`; nothing to fix |
| macOS prompts "Always Allow" on first key access | Choose Always Allow; subsequent reads are silent |
| `verify-azure.sh` returns `Unauthorized` | Key rotated in Azure portal; re-run `store-keychain-keys.sh` |
| Phase 0a `ConnectionRefused` on Translator | Known transient (see [../coordination-protocol.md §12](../coordination-protocol.md)); retry once via `--retry-phase 0a` |
| Cost-ledger silently fails to append | Python < 3.11 `datetime.UTC` bug (P6.5); phases run anyway |
| New Mac doesn't see Keychain entries | Each Mac's keychain is separate; run `store-keychain-keys.sh` on the new Mac too |
| `ENABLE_KEYVAULT=true` but pipeline still hits Azure direct | Key Vault either unreachable or empty; check `az keyvault secret list --vault-name <name>` |

## Multi-Mac key sharing (future, not yet active)

The current model is "each Mac has its own keychain populated from the same Azure source". When `ENABLE_KEYVAULT=true`:
- Secrets get written to Azure Key Vault (single source of truth across all Macs)
- Each Mac's `store-keychain-keys.sh` reads from Key Vault first, falls back to direct Azure
- Single rotation point (rotate in Key Vault → every Mac picks up on next `store-keychain-keys.sh`)

See [../../../../infra/azure/migrate-to-keyvault.sh](../../../../infra/azure/migrate-to-keyvault.sh) for the migration script. Not active today — flip when multi-Mac portability becomes a pain point.
