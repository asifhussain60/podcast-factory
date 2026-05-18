# Architecture — How the Azure Pipeline Works

This doc explains what each Azure resource does, what data crosses it, and
where the trust boundaries are. If something is misbehaving, this is the doc
that tells you *which layer* to investigate.

## The big picture

```
┌──────────────────────────┐
│  Scanned Arabic PDF      │  (from Asif's local archive)
└─────────────┬────────────┘
              │
              ▼
   ┌────────────────────┐      ┌────────────────────┐
   │ Blob: source-arabic│ ───▶ │ Document Intelligence │
   └────────────────────┘      │   (OCR — Arabic)      │
                               └──────────┬─────────────┘
                                          │  page-anchored text
                                          ▼
                               ┌────────────────────┐
                               │ Translator         │
                               │ (Arabic → English) │
                               └──────────┬─────────┘
                                          ▼
                               ┌────────────────────────┐
                               │ Blob: translated-english│
                               └──────────┬─────────────┘
                                          ▼
                                  /podcast skill in
                                  the journal app
```

Five components, five reasons they exist.

## Resource group: `rg-journal-ai`

Logical container. Lets you see total cost for "Journal AI stuff" on one
billing line, delete the entire stack with one command, and apply policies
or budgets at the group scope.

Region: **East US**. Picked because Translator's document-translation
feature has the broadest support there, including scanned-PDF Arabic→English
which several other regions lack.

## Translator (`journal-translator`)

Azure AI Translator, **Standard S1** SKU.

- **Text translation** via the global endpoint `https://api.cognitive.microsofttranslator.com/`.
  Used for short snippets (glossary entries, title translation, term lookups).
- **Document translation** via the per-resource endpoint
  `https://journal-translator.cognitiveservices.azure.com/`. Used for full
  scanned-PDF → English-PDF workflows, reading source blobs and writing output
  blobs asynchronously.

**Why S1 not F0:** Free F0 supports text translation but **not** document
translation. Document translation is the primary use case here, so F0 doesn't
work for this pipeline.

**Auth:** API key (Key 1 / Key 2). Stored in macOS Keychain as
`azure-journal-translator-key1`.

## Document Intelligence (`journal-docintel`)

Azure AI Document Intelligence, **Free F0** SKU.

OCR engine specifically tuned for documents (preserves layout, table
structure, reading order). Used for the 7 sources in the archive that have
no usable embedded text layer.

**API kind:** `FormRecognizer`. Microsoft rebranded the product to
"Document Intelligence" but kept the underlying Azure resource type name
unchanged. The deep-link URL still uses `FormRecognizer`.

**Why F0:** 500 pages/month is enough for the initial 20-page benchmark and
small follow-on work. Upgrade to **S0** (pay-per-page, ~$1.50 per 1K pages
for prebuilt-read) once we commit to the full archive run — Rāḥat al-ʿAql
alone is 591 pages, which exceeds F0 in a single run.

**Auth:** API key, stored in Keychain as `azure-journal-docintel-key1`.

## Storage account (`journalpodcaststorage`)

StorageV2 general-purpose account, **Standard LRS** (locally-redundant).

Three blob containers:

| Container | Purpose | Lifecycle |
|-----------|---------|-----------|
| `source-arabic` | Input: Arabic source PDFs | Long-lived archive |
| `source-urdu` | Input: Urdu source PDFs | Long-lived archive |
| `translated-english` | Output: English translations (Translator writes here) | Regenerable |

Plus a system-generated `$logs` container created automatically by Azure
(ignore it).

**Why LRS not GRS:** geo-redundant storage costs ~60% more and provides
cross-region disaster recovery. The sources live on the user's Mac (the
canonical copy), so the blob copy is recovery-redundant, not the source of
truth — LRS is the right call.

**Security posture:**
- Public network access enabled (API keys are the security boundary)
- Anonymous blob access **disabled**
- TLS 1.2 minimum
- Soft delete enabled (7 days) for blobs, containers, file shares — safety
  net for accidental deletes during OCR scratch work

**Auth:** account key OR Azure AD (RBAC). The provisioning script uses AAD
(`--auth-mode login`) for container creation; runtime workloads use the key.

## Budget (`journal-ai-monthly-cap`)

Cost Management budget at billing-account scope.

- **Cap:** $50 / month
- **Reset:** monthly (billing cycle)
- **Alert thresholds:** 50%, 80%, 100% of cap
- **Notifications:** email to `asifhussain60@gmail.com`

**Why billing-account scope, not subscription:** with one subscription,
they're equivalent. If a second subscription gets added later, the
billing-account budget catches its spend too — a more conservative default.

**Note:** budgets cannot be created via Azure CLI for personal pay-as-you-go
subscriptions. Must be set up manually in the portal. The provisioning
script prints the deep-link URL after running.

## Where keys live

| Resource | Keychain entry |
|----------|----------------|
| Translator | `azure-journal-translator-key1` |
| Translator (region) | `azure-journal-translator-region` |
| Translator (text endpoint) | `azure-journal-translator-endpoint-text` |
| Translator (document endpoint) | `azure-journal-translator-endpoint-document` |
| Document Intelligence | `azure-journal-docintel-key1` |
| Document Intelligence (endpoint) | `azure-journal-docintel-endpoint` |
| Document Intelligence (region) | `azure-journal-docintel-region` |
| Storage account | `azure-journal-storage-key1` |
| Storage account (endpoint) | `azure-journal-storage-endpoint` |
| Storage account (name) | `azure-journal-storage-account` |

Read any of them back with:

```sh
security find-generic-password -s azure-journal-translator-region -w
```

## Trust boundaries

1. **Mac → Azure**: TLS 1.2+ with API key auth. The key is the secret; lose
   it and an attacker can spend money on the account until it's rotated.
2. **Azure ↔ Azure** (Translator reading from Blob, writing back):
   currently uses SAS tokens at request time. A future hardening step is to
   give Translator a managed identity and grant it RBAC roles on the
   storage account — kills the SAS-token sprawl. Not done yet because the
   pipeline isn't live yet.
3. **Mac filesystem → Keychain**: any process running as the Mac user can
   read all `security`-stored entries. macOS doesn't sandbox by service
   name. Keychain is appropriate for personal-machine secrets, not shared
   workstations.

## Multi-Mac portability — the planned shift to Key Vault

The current Keychain layout works only on this Mac. The migration plan is:

1. Provision an Azure Key Vault in `rg-journal-ai` (flip
   `ENABLE_KEYVAULT="true"` in `azure-config.env` and re-run
   `provision-azure.sh`).
2. Copy each Keychain entry into Key Vault as a secret with the same name.
3. On a new Mac, run `az login`, then a one-time fetch script that pulls
   secrets from Key Vault into local Keychain.
4. The journal app continues reading from Keychain (no app-code change) —
   Key Vault becomes the cross-machine source of truth, Keychain is a local
   cache.

That migration is **planned but not done** — first the 20-page benchmark
needs to pass.
