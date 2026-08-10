# LLM API stack — canonical reference

The accounts, billing settings, spend guardrails and rotation paths for the two model
providers the pipeline talks to: Anthropic (Claude) and Google (Gemini).

**Source of truth for accounts and billing.** For *where a credential is resolved
from at runtime*, the source of truth is
[infra/pipeline-runtime.md §1](../pipeline-runtime.md) — that changed on 2026-06-04
and this file described the old behaviour until 2026-08-10.

**Last reconciled:** 2026-08-10.

---

## TL;DR (skip to here if you're bringing a new Mac up)

1. Install Claude Code, run `claude login`, authenticate as **asifhussain60@gmail.com** with the **Claude Max** subscription.
2. Run `az login` as **asifhussain60@msn.com** (a different account — the Azure one). That is what gives this machine the Gemini and Anthropic API keys: both live in Key Vault as `llm-gemini-api-key` and `llm-anthropic-api-key`, and the pipeline reads them from there.
3. Run [`infra/llm-apis/verify-llm-apis.sh`](verify-llm-apis.sh) — confirms Claude and Gemini are reachable.

That is the whole provider setup. Audio is produced in NotebookLM, by hand, and needs
no key.

> **Correction, 2026-08-10.** This file used to say the pipeline reads the keychain
> for the Gemini key, and that `bootstrap-llm-apis.sh` is how a new Mac gets it. The
> keychain tier was removed from `_secrets.resolve_secret` on 2026-06-04; resolution
> is now environment variable → Azure Key Vault, full stop. `bootstrap-llm-apis.sh`
> still works and still writes a valid keychain entry — but nothing in the pipeline
> reads it, so it is no longer a bootstrap step.

---

## Provider 1 — Anthropic (Claude)

### Account

- **Email:** asifhussain60@gmail.com
- **Subscription tier:** **Claude Max** (the $200/month plan).
- **Organization (for API):** "Asif's Individual Org" — a separate Anthropic API account with its own $25 cap. **`claude -p` never touches it.** One pipeline path does: the SDK refinement route, via `_secrets.get_anthropic_key()`, which resolves the vault secret `llm-anthropic-api-key`. That key is pulled on demand at the call site and is deliberately never loaded into the process environment, because doing so would divert every `claude -p` call off the flat-rate subscription and onto metered billing — a P0 cost violation the code comments in `_secrets.py` call out by name.

### Auth model on operator Macs

The pipeline shells out to `claude -p` (Claude Code's headless mode) from `scripts/podcast/_authoring.py`, `scripts/podcast/audit_bundle.py`, and the orchestrator. Claude Code authenticates against the **Max subscription** via the `claude login` OAuth flow — no API key is configured on the Mac, no `ANTHROPIC_API_KEY` env var, nothing in keychain.

**Empirically verified 2026-05-25** by running `audit_bundle.py` against EP07 while the separate "Asif's Individual Org" API account was paused at its $25 monthly cap: the call succeeded (exit 0, 15 findings), confirming the pipeline never touched the API account.

### Why the API key is kept out of the environment

Three reasons:
1. **Cost.** The Max subscription covers Claude Code calls at a flat rate. Routing the same work through the API would be billed per token — double-paying for it.
2. **Isolation.** The API org's $25/month cap can never block podcast-factory work if the pipeline's main path cannot reach it.
3. **Simplicity.** `claude login` once per Mac; no per-machine secret to rotate for the reasoning path.

`_secrets.py` enforces this structurally: there is no `hydrate_env()`, and it actively
scrubs the *empty* `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_CUSTOM_HEADERS` that the
Claude-desktop runtime injects, which otherwise make the SDK raise
`APIConnectionError` even with a valid key.

### Bootstrap on a new Mac

```bash
brew install --cask claude-code      # Or use Anthropic's installer
claude login                          # OAuth flow in browser; sign in as asifhussain60@gmail.com
claude --version                      # Sanity check
```

### Verify

```bash
echo "say hi" | claude -p             # Should print a one-line greeting
```

---

## Provider 2 — Google (Gemini)

### Account

- **Google identity:** asifhussain60@gmail.com (same Google account that owns the YouTube/Drive/Cloud surface).
- **Billing account:** `AHHOME Google Cloud` — billing ID **`013693-D9BFBA-DBF063`**, Paid tier, card on file: AMAZON ••••1531.
- **Cloud project that owns the active key:** `gen-lang-client-0688822319` (display name "Gemini API"). Imported into AI Studio 2026-05-25.

### Why we need it (when the Anthropic stack covers Claude)

The pipeline uses Gemini as a **second-opinion auditor** running alongside the Claude auditor — see [audit_bundle_gemini.py](../../scripts/podcast/audit_bundle_gemini.py) and [audit_bundle.py](../../scripts/podcast/audit_bundle.py). Cross-vendor triangulation: when both models flag the same defect, confidence is high enough to auto-apply; when they disagree, a human reviews. The Max subscription doesn't cover Gemini because Gemini is a Google product.

### Active key

- **Key name (in AI Studio):** `podcast-factory`
- **Key format:** newer AI Studio format (53 chars, prefix `AQ.Ab8…`). Created 2026-05-25.
- **Project:** `gen-lang-client-0688822319` (Paid tier, linked to AHHOME billing 2026-05-25).
- **Where the pipeline reads it:** Key Vault secret **`llm-gemini-api-key`**, via `_secrets.get_gemini_key()`. Env override: `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
- **Keychain entry `gemini_api_key`:** still present on this Mac, still written by the bootstrap script — and **not read by anything**. Harmless; not a bootstrap step.

### Bootstrap on a new Mac

`az login` is the whole step — the key comes from the vault. `bootstrap-llm-apis.sh`
remains available for the secure-paste flow if you want a local keychain copy for
ad-hoc use, but the pipeline does not need it.

To get the key value itself: open [aistudio.google.com/apikey](https://aistudio.google.com/apikey), find the `podcast-factory` row, click the copy icon.

### Verify

```bash
bash infra/llm-apis/verify-llm-apis.sh
```

Confirms Gemini lists 50+ models and `gemini-2.5-pro` is reachable on Paid tier (not blocked by Free-tier `limit: 0` quota).

### Rotation

If the key needs to be rotated:
1. AI Studio → API keys → `podcast-factory` → ⋮ → Revoke.
2. Create new key in the same `gen-lang-client-0688822319` project (so billing stays linked).
3. **Put it in the vault** — that is the step that actually changes what the pipeline uses:
   ```bash
   az keyvault secret set --vault-name podcast-factory-vault \
     --name llm-gemini-api-key --value "<new key>"
   ```
   `_secrets` caches per process, so any already-running orchestrator keeps the old value until it exits.

---

## Audio needs no provider — and ElevenLabs is not one

Every book's audio comes from **NotebookLM**, produced by hand: a person uploads the
chapter, pastes the framing, and drops the resulting `.m4a` into the book folder. No
API, no key, no metered spend.

**ElevenLabs was evaluated and is not used.** Verified 2026-08-10: no book sets
`audio_engine: elevenlabs`, two set `notebooklm` explicitly, and every other book
takes the `notebooklm` default. `_audio_engines.py` has carried the entry as
explicitly dormant since 2026-06-14, kept only so the registry keeps more than one
engine in it — the extensibility seam, not a live path.

Nothing here needs an ElevenLabs key, and this file no longer documents how to
provision one. If the engine is ever reactivated for a book, the resolution order
lives in `scripts/podcast/_elevenlabs.py` and that decision should re-add a section
here rather than rely on this note.

---

## Budgets and spend caps

| Provider | Cap | Where set | Triggers at | Why this cap |
|---|---|---|---|---|
| **Google Cloud** | $10 / month on Generative Language API | [Billing → Budgets & Alerts](https://console.cloud.google.com/billing/013693-D9BFBA-DBF063/budgets), scoped to `services/generativelanguage.googleapis.com` only | 50% ($5), 90% ($9), 100% ($10), email-only | Smoke-test workload is ~$0.55/book; $10 is the runaway-script tripwire, not the operating limit. |
| **Google Cloud (prepay)** | $50 prepay, auto-reload when balance < $50 | AHHOME Google Cloud billing account | n/a (auto-funded) | Cushion so a billing-card decline never pauses a multi-hour orchestrator run. |
| **Anthropic API** | $25 / month on "Asif's Individual Org" | Anthropic console → Alert Settings | At $25 — pauses ALL API access until next month, OR manual lift | Guards the SEPARATE API account from runaway spend. Does NOT affect Claude Code / Max subscription. |

### Resetting / removing caps

- **Google $10 monthly:** edit at the same Budgets URL. Increase to $25 once orchestrator F30 (Phase 0g audit) is wired and per-book spend stabilizes.
- **Anthropic $25 monthly:** Anthropic console → Alert Settings → remove or raise. Only relevant if you start using the API account directly (the pipeline never does).

---

## What must be in the keychain, and what merely may be

Check presence without reading any value:

```bash
security find-generic-password -s "Claude Code-credentials" >/dev/null 2>&1 \
  && echo "ok      Claude Code-credentials" || echo "MISSING Claude Code-credentials"
```

| Service | Status |
|---|---|
| `Claude Code-credentials` | **The only one required.** Written by `claude login`; carries the Max OAuth token every `claude -p` call uses. `preflight_doctor.py` reads its `expiresAt` as an advisory pre-check |
| `gemini_api_key` | Leftover. Nothing reads it — the vault supplies the key |
| `elevenlabs_api_key` | Leftover from the abandoned ElevenLabs evaluation. Nothing reads it; safe to delete |
| `azure-podcast-factory-*` | Leftovers. Nothing reads them — `verify-azure.sh` checks them anyway, which is why it reports failures on a working machine |

An earlier version of this table listed the Azure entries under the prefix
`azure-podcast-*`. That prefix has never been correct for this repo: the app
namespace is `podcast-factory`, so both the (unread) keychain names and the (live)
vault secret names are `azure-podcast-factory-*`.

---

## What is intentionally NOT here

- ❌ `ANTHROPIC_API_KEY` as an exported env var — see §"Why the API key is kept out of the environment". The key exists, in the vault, read on demand.
- ❌ `~/.anthropic/` config file with an API key
- ❌ Any `claude` config pointing to an API key instead of the OAuth subscription
- ❌ `OPENAI_API_KEY` — the pipeline does not use OpenAI. (Azure OpenAI is a separate resource and is currently used for nothing; DALL-E 3 was deprecated and image generation stayed on Gemini.)
- ❌ Vertex AI / Google Cloud service-account JSON — AI Studio API keys, not Vertex

The `.env` rule holds for every provider in use. The one exception in the codebase —
`_elevenlabs.py` reading `ELEVENLABS_API_KEY` from a repo-root `.env` — belongs to
the dormant audio engine above and is not a live path.

---

## Quick-reference URLs

| Surface | URL |
|---|---|
| Gemini API keys list | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Google Cloud billing overview | [console.cloud.google.com/billing/013693-D9BFBA-DBF063](https://console.cloud.google.com/billing/013693-D9BFBA-DBF063) |
| Google Cloud budgets | [console.cloud.google.com/billing/013693-D9BFBA-DBF063/budgets](https://console.cloud.google.com/billing/013693-D9BFBA-DBF063/budgets) |
| Google Cloud credits | [console.cloud.google.com/billing/013693-D9BFBA-DBF063/credits](https://console.cloud.google.com/billing/013693-D9BFBA-DBF063/credits) |
| Generative Language API metrics | [console.cloud.google.com/apis/api/generativelanguage.googleapis.com/metrics](https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/metrics?project=gen-lang-client-0688822319) |
| Gemini API pricing | [ai.google.dev/pricing](https://ai.google.dev/pricing) |
| Gemini API rate limits | [ai.google.dev/gemini-api/docs/rate-limits](https://ai.google.dev/gemini-api/docs/rate-limits) |
| Anthropic console (separate from Max) | [console.anthropic.com](https://console.anthropic.com) |
| Claude.ai subscription portal | [claude.ai/settings/billing](https://claude.ai/settings/billing) |

---

## See also

- [`infra/azure/`](../azure/) — Azure Cognitive Services (Document Intelligence, Translator, Speech) provisioning + keychain wiring. Independent stack; same pattern.
- [`docs/setup/bootstrap.md`](../../docs/setup/bootstrap.md) — full from-scratch Mac bootstrap; links to this file from Step 5.5.
- [`scripts/podcast/audit_bundle.py`](../../scripts/podcast/audit_bundle.py) — Claude-side auditor (uses `claude -p` / Max subscription).
- [`scripts/podcast/audit_bundle_gemini.py`](../../scripts/podcast/audit_bundle_gemini.py) — Gemini-side auditor (uses the keychain entry documented above).
