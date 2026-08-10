# Azure stack — resources, keychain, recreate from scratch

Authoritative reference for the Azure side of the pipeline. The pipeline uses **6 Azure services** for OCR, translation, speech, storage, language NLP, and image generation, plus Azure Key Vault as the canonical secret store for multi-Mac portability.

## Live configuration

Source of truth: [infra/azure/azure-config.env](../../infra/azure/azure-config.env). Tracked — contains **non-secret** config only (subscription ID, region, resource names, feature flags). Secrets live in macOS Keychain (populated from Key Vault), never in tracked files.

| Field | Value |
|---|---|
| Sign-in account | `asifhussain60@msn.com` — **not** the gmail account the rest of the stack uses |
| Tenant / directory | `55e453ce-cca7-4cf9-a1e1-c2a2f98a202b` ("Default Directory"; no custom domain) |
| Subscription | `Journal AI — primary` (ID `3440564d-c056-4173-bec6-7af92dbece77`) |
| Resource group | `rg-journal-ai` |
| Region | `eastus` |
| App namespace | `podcast-factory` (drives keychain naming: `azure-podcast-factory-*`) |
| Key Vault | `podcast-factory-vault` — **ACTIVE since 2026-06-02** |

## Resource inventory

| Resource name | Type | SKU | Pipeline phase | Status |
|---|---|---|---|---|
| `journal-docintel` | Document Intelligence | S0 | 0a (OCR) | Live |
| `journal-translator` | Translator | S1 | 0a (bulk/utility translation) | Live |
| `journal-speech` | Speech | S0 | Audio transcription (post-pub) | Live |
| `journalpodcaststorage` | Storage account | Standard_LRS | Ancillary | Live |
| `podcast-factory-vault` | Key Vault | Standard | Secret store (all Macs) | **Active** |
| `journal-language-market` | Language (TextAnalytics) | **F0 free** | Augmentation — NER, key-phrase, sentiment | **Live — wired 2026-06-06** |
| `journal-openai` | Azure OpenAI | S0 | Image gen (future) / Whisper transcription | **Live** — DALL-E deprecated; deploy `whisper` for transcription or wait for `gpt-image-1` |

> **Note:** Azure resource names retain the `journal-*` prefix from before the 2026-05-22 repo rename. Only the app namespace (keychain prefix) changed to `podcast-factory`. Renaming the Azure resources themselves is unnecessary.

> **SKU note:** Document Intelligence was upgraded F0 → S0 on 2026-05-18 because F0 has a 4 MB binary cap that blocked Kitab-al-Riyad.pdf (4.4 MB). S0 cap is 500 MB.

## Secret names

Naming convention: `azure-podcast-factory-<resource>-<field>`. These are the **Key
Vault secret names** — the same strings were once keychain service names, which is
why the table below is titled for both.

Resolution priority in [scripts/podcast/_azure_creds.py](../../scripts/podcast/_azure_creds.py) `_resolve()`:
1. Environment variable (for CI) — `AZURE_DOCINTEL_KEY`, `AZURE_TRANSLATOR_KEY`, etc.
2. **Azure Key Vault** `podcast-factory-vault`, via the `az` CLI.

> **There is no keychain tier.** It was removed on 2026-06-04 so a drifted local
> cache could not shadow the vault. A machine needs `az login`, not
> `pull-secrets.sh`. Full detail, including which secrets are *not* in the vault:
> [infra/pipeline-runtime.md](../../infra/pipeline-runtime.md).

| Service name | Required for |
|---|---|
| `azure-podcast-factory-docintel-endpoint` | Phase 0a (OCR) |
| `azure-podcast-factory-docintel-key1` | Phase 0a (OCR) |
| `azure-podcast-factory-docintel-region` | Phase 0a (OCR) |
| `azure-podcast-factory-translator-endpoint-text` | Phase 0a (translation) |
| `azure-podcast-factory-translator-key1` | Phase 0a (translation) |
| `azure-podcast-factory-translator-region` | Phase 0a (translation) |
| `azure-podcast-factory-speech-endpoint` | Audio transcription |
| `azure-podcast-factory-speech-key1` | Audio transcription |
| `azure-podcast-factory-speech-region` | Audio transcription |
| `azure-podcast-factory-storage-key1` | Storage |
| `azure-podcast-factory-storage-endpoint` | Storage |
| `azure-podcast-factory-storage-account` | Storage |
| `azure-podcast-factory-language-key1` | Augmentation (NER, key-phrase, sentiment) |
| `azure-podcast-factory-language-endpoint` | Augmentation |
| `azure-podcast-factory-language-region` | Augmentation |
| `azure-podcast-factory-openai-key1` | Image generation (DALL-E 3) |
| `azure-podcast-factory-openai-endpoint` | Image generation |
| `azure-podcast-factory-openai-region` | Image generation |
| `azure-podcast-factory-openai-dalle-deployment` | Image generation (deployment name) |
| `llm-gemini-api-key` | Gemini tasks (literary pass, second-opinion audit, Composer buttons) |
| `llm-anthropic-api-key` | The Anthropic **SDK** refinement path only — `claude -p` uses the Max subscription and no key |

That is 22 secrets in the vault, verified 2026-08-10. The last two rows were
previously listed under their old keychain names (`gemini_api_key`,
`anthropic_api_key`); the vault names are the ones above, and the vault is what the
pipeline reads.

After provisioning a new resource, run `store-keychain-keys.sh` then
`migrate-to-keyvault.sh` on the primary Mac to get its secrets INTO the vault. New
Macs need only `az login` — `pull-secrets.sh` writes a keychain cache that nothing
reads any more.

## Multi-Mac secret workflow (ACTIVE since 2026-06-02)

Key Vault is the single source of truth. The workflow is:

```
Primary Mac (already set up)
  ├── azure-config.env  →  KEYVAULT_NAME + APP_NAME
  ├── migrate-to-keyvault.sh  →  Keychain → Key Vault  (run ONCE when first enabling KV)
  └── pull-secrets.sh  →  Key Vault → Keychain  (run to refresh after rotation)

New Mac
  └── pull-secrets.sh  →  Key Vault → Keychain  (that's it — fully bootstrapped)
```

### Setting up a new Mac

```bash
cd <repo>/infra/azure
az login
az account set --subscription "Journal AI — primary"
bash pull-secrets.sh
```

`pull-secrets.sh` pulls all 14+ secrets from Key Vault into the local Keychain, then runs `test_azure_connectivity.py` to verify. Idempotent — safe to re-run after rotation.

### Rotating a key

1. Rotate the key in Azure portal or with `az cognitiveservices account keys regenerate ...`
2. Run `store-keychain-keys.sh` on the primary Mac to fetch the new key into local Keychain
3. Run `migrate-to-keyvault.sh` to push the new value to Key Vault
4. On all other Macs: run `pull-secrets.sh` to refresh

## Recreate-from-scratch procedure

Use this if the Azure subscription is wiped, or for a brand-new project.

### Step 1 — Provision Azure resources (run ONCE per Azure account)

```bash
cd <repo>/infra/azure
az login
az account set --subscription "Journal AI — primary"
bash provision-azure.sh
```

Creates `rg-journal-ai` (if missing) and all enabled resources. Idempotent — safe to re-run.

### Step 2 — Populate Key Vault (primary Mac only, run ONCE)

```bash
bash store-keychain-keys.sh      # Pull keys from Azure → local Keychain
bash migrate-to-keyvault.sh      # Push local Keychain → Key Vault
```

After this, Key Vault is the source of truth for all other Macs.

### Step 3 — Verify end-to-end

```bash
cd <repo>
python3 scripts/podcast/test_azure_connectivity.py
```

Expect `pass 5  fail 0`.

## Adding a new Azure resource to the stack

1. Edit `infra/azure/azure-config.env` — add `<RESOURCE>_NAME="..."` and `ENABLE_<RESOURCE>="true"`.
2. Update `infra/azure/provision-azure.sh` with the `az` provisioning block.
3. Update `infra/azure/store-keychain-keys.sh` with the new keychain block (endpoint, key1, region).
4. Update `infra/azure/pull-secrets.sh` with matching `pull` calls.
5. Update `infra/azure/migrate-to-keyvault.sh` with matching `push_entry` calls.
6. Update `infra/azure/verify-azure.sh` with the new probe.
7. Add `<resource>Creds` dataclass + `load_<resource>_creds()` to `scripts/podcast/_azure.py`.
8. Run `provision-azure.sh` → `store-keychain-keys.sh` → `migrate-to-keyvault.sh` on primary Mac.
9. Update this doc's "Resource inventory" + "Keychain entries" tables.

## Known gotchas

| Symptom | Cause / Fix |
|---|---|
| `Translator credentials missing` | `_azure.py` APP_NAME mismatch — keychain uses `azure-podcast-factory-*`; if seeing this, check `APP_NAME` defaults to `"podcast-factory"` in `_azure.py:38` |
| macOS prompts "Always Allow" on first key access | Choose Always Allow; subsequent reads are silent |
| `verify-azure.sh` returns `Unauthorized` | Key rotated in Azure portal; re-run `store-keychain-keys.sh` then `migrate-to-keyvault.sh` |
| `pull-secrets.sh` shows `MISS` for a secret | Secret not yet in Key Vault; run `migrate-to-keyvault.sh` on primary Mac |
| Phase 0a `ConnectionRefused` on Translator | Known transient Azure Translator hiccup; retry once via `python3 scripts/podcast/orchestrate_book.py --resume <slug> --retry-phase 0a` |
| New Mac doesn't see Keychain entries | Run `bash infra/azure/pull-secrets.sh` — pulls from Key Vault |
| `python3 test_azure_connectivity.py` shows `app: journal` | `_azure.py` APP_NAME was reverted; set `APP_NAME = os.environ.get("AZURE_APP_NAME", "podcast-factory")` at line 38 |
