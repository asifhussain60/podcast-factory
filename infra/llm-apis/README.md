# LLM API stack — canonical reference

Everything Asif's `podcast-factory` Macs need to talk to Anthropic (Claude) and Google (Gemini), with the exact accounts, billing settings, keychain entries, and spend guardrails currently in effect.

**Source of truth.** Anything that contradicts this file is stale and should be deleted or updated to match.

**Last reconciled:** 2026-05-25.

---

## TL;DR (skip to here if you're bringing a new Mac up)

1. Install Claude Code, run `claude login`, authenticate as **asifhussain60@gmail.com** with the **Claude Max** subscription (no API key on this machine).
2. Run [`infra/llm-apis/bootstrap-llm-apis.sh`](bootstrap-llm-apis.sh) — it walks you through pasting the Gemini API key into the keychain (the key value is NOT stored in this repo).
3. Run [`infra/llm-apis/verify-llm-apis.sh`](verify-llm-apis.sh) — confirms both Claude and Gemini are reachable from this machine.

That's it. The Anthropic API key is intentionally NOT used on operator Macs; the pipeline runs entirely off the Max subscription. See §"Anthropic — auth model" below for why.

---

## Provider 1 — Anthropic (Claude)

### Account

- **Email:** asifhussain60@gmail.com
- **Subscription tier:** **Claude Max** (the $200/month plan that includes Opus 4.7 with 1M-context).
- **Organization (for API):** "Asif's Individual Org" — a separate Anthropic API account that exists for occasional standalone API use; **NOT used by the podcast pipeline.**

### Auth model on operator Macs

The pipeline shells out to `claude -p` (Claude Code's headless mode) from `scripts/podcast/_authoring.py`, `scripts/podcast/audit_bundle.py`, and the orchestrator. Claude Code authenticates against the **Max subscription** via the `claude login` OAuth flow — no API key is configured on the Mac, no `ANTHROPIC_API_KEY` env var, nothing in keychain.

**Empirically verified 2026-05-25** by running `audit_bundle.py` against EP07 while the separate "Asif's Individual Org" API account was paused at its $25 monthly cap: the call succeeded (exit 0, 15 findings), confirming the pipeline never touched the API account.

### Why no Anthropic API key in keychain

Three reasons:
1. **Cost.** The Max subscription covers unlimited Opus 4.7 / Sonnet 4.6 / Haiku 4.5 calls via Claude Code. Routing through the API would be billed per-token and would double-pay for the same work.
2. **Isolation.** The separate "Asif's Individual Org" API account is for ad-hoc programmatic use (one-off scripts, third-party tools). Keeping it OUT of the pipeline means its $25/month soft cap (see §Budgets) can never block podcast-factory work.
3. **Simplicity.** Zero per-machine secret rotation. `claude login` once per Mac.

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
- **Keychain entry:** service=`gemini_api_key`, account=`<your USER>`. Read with:

  ```bash
  security find-generic-password -s gemini_api_key -a "$USER" -w
  ```

### Bootstrap on a new Mac

Use the helper script — it walks you through the secure-paste flow that avoids writing the key to disk or shell history:

```bash
bash infra/llm-apis/bootstrap-llm-apis.sh
```

The script will prompt you to paste the key (silent — nothing echoes to terminal) and store it under the canonical keychain service name.

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
3. Re-run `bootstrap-llm-apis.sh` to re-paste into keychain.

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

## What's in keychain on a fully-set-up Mac

Run this audit (it reads only service names, no secrets):

```bash
security dump-keychain 2>/dev/null | grep '"svce"' | grep -E "gemini|azure-podcast" | sort -u
```

Expected entries (post-bootstrap):

```
"svce"<blob>="gemini_api_key"
"svce"<blob>="azure-podcast-docintel-endpoint"
"svce"<blob>="azure-podcast-docintel-key1"
"svce"<blob>="azure-podcast-docintel-region"
"svce"<blob>="azure-podcast-speech-endpoint"
"svce"<blob>="azure-podcast-speech-key1"
"svce"<blob>="azure-podcast-speech-region"
"svce"<blob>="azure-podcast-translator-endpoint-document"
"svce"<blob>="azure-podcast-translator-endpoint-text"
"svce"<blob>="azure-podcast-translator-key1"
"svce"<blob>="azure-podcast-translator-region"
```

If you see anything ELSE prefixed `gemini`, `anthropic`, or `claude` — it's stale and can be deleted. The pipeline only consumes the entries listed above.

---

## What is intentionally NOT here

The following are explicitly NOT documented, NOT scripted, and NOT in keychain — because the pipeline doesn't need them. If you find references elsewhere, treat them as legacy and remove:

- ❌ `ANTHROPIC_API_KEY` env var
- ❌ `~/.anthropic/` config file with an API key
- ❌ Any `claude` config pointing to an API key instead of the OAuth subscription
- ❌ `OPENAI_API_KEY` (the pipeline does not use OpenAI)
- ❌ `.env` / `.env.local` files with LLM credentials (the pipeline reads keychain only)
- ❌ Vertex AI / Google Cloud service-account JSON (we use AI Studio API keys, not Vertex)

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
