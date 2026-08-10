# Pipeline runtime — every external thing the orchestrator touches

What the podcast-factory pipeline needs from outside this repo, phase by phase, so a
migration to a new machine has nothing left to infer. **Verified against the live
Azure subscription, the live Key Vault, and the running code on 2026-08-10.** Every
table below was read from the system, not copied from an earlier document.

The companion documents are narrower on purpose: [`azure/`](azure/) is the Azure
resources, [`llm-apis/`](llm-apis/) is the Anthropic + Google accounts,
[`cloudflare/`](cloudflare/) is what is deployed. This file is the one that says
which of them a given pipeline step actually reaches for.

---

## 1. The credential rule, and the thing most documents get wrong

**At runtime the pipeline resolves every secret as: environment variable → Azure Key
Vault. There is no keychain tier.** It was removed on 2026-06-04 so a drifted local
cache could never shadow the vault and make a run machine-dependent. The code is
[`scripts/podcast/_secrets.py`](../scripts/podcast/_secrets.py) `resolve_secret` and
[`scripts/podcast/_azure_creds.py`](../scripts/podcast/_azure_creds.py) `_resolve`;
both say so in their own docstrings.

The practical consequence for a migration is the whole point of this section:

> **`az login` is what makes a new Mac work. `pull-secrets.sh` is not.** A machine
> with `az login` and no keychain entries at all runs the full pipeline. A machine
> with a fully populated keychain and no `az login` cannot run phase 0a.

`_azure_creds._read_keychain` still exists and `_azure.py` still re-exports it, but
**nothing calls it.** It is dead code kept for the re-export's sake.

### Where each secret actually lives

| Secret | Home | Reachable on a fresh Mac by | Consumer |
|---|---|---|---|
| The 20 `azure-podcast-factory-*` values | Key Vault `podcast-factory-vault` | `az login` | Phase 0a (OCR + translation) and `audio-ingest` (Speech). The Language, Storage and OpenAI credentials resolve but no phase currently calls them |
| `llm-anthropic-api-key` | Key Vault | `az login` | Anthropic **SDK** path only — never `claude -p` |
| `llm-gemini-api-key` | Key Vault | `az login` | Gemini auditors, literary pass, Composer buttons |
| Claude Max OAuth token | macOS keychain, service `Claude Code-credentials` | `claude login` | Every `claude -p` call — the bulk of pipeline reasoning |
| `cloudflare_api_token` | macOS keychain **only** | ⚠ nothing — re-issue in the Cloudflare dashboard | `deploy_listener.sh`, `publish_to_production.py` |
| `listener_better_auth_secret` | macOS keychain **only** | ⚠ nothing — regenerate, `openssl rand -base64 32` | Podcast Factory Library local dev |
| `safina_google_client_secret` | macOS keychain **only** | ⚠ nothing — re-copy from the Google Cloud console | Podcast Factory Library local dev |

**The known gap, stated plainly.** The three keychain-only rows are *not* in the
vault and are *not* recoverable from anything in this repo. All three are cheap to
replace — re-issue, regenerate, or re-copy from a console — and all three belong to
the Podcast Factory Library rather than to the book pipeline, so a machine that only
processes books never needs them.

**No audio credential appears in this table, deliberately.** Audio is produced by
hand in NotebookLM. The ElevenLabs engine was evaluated and abandoned; a stale
`elevenlabs_api_key` may still sit in the keychain on this Mac and nothing reads it.

### Vault inventory — 22 secrets, read from the vault on 2026-08-10

```
azure-podcast-factory-docintel-{endpoint,key1,region}
azure-podcast-factory-language-{endpoint,key1,region}
azure-podcast-factory-openai-{endpoint,key1,region,dalle-deployment}
azure-podcast-factory-speech-{endpoint,key1,region}
azure-podcast-factory-storage-{account,endpoint,key1}
azure-podcast-factory-translator-{endpoint-text,endpoint-document,key1,region}
llm-anthropic-api-key
llm-gemini-api-key
```

Read the names yourself at any time — this reveals no values:

```bash
az keyvault secret list --vault-name podcast-factory-vault --query "[].name" -o tsv | sort
```

### Three different identities, and none of them is interchangeable

This trips people up because they are all "Asif":

| Surface | Account | How you'd notice the wrong one |
|---|---|---|
| **Azure** (subscription, Key Vault, OCR, Speech) | `asifhussain60@msn.com` | `az account show` names someone else; every credential resolves to `None` |
| **Anthropic + Google + Cloudflare (correct)** | `asifhussain60@gmail.com` | — |
| **Cloudflare (wrong, and `wrangler` is logged into it)** | `asifhussain60@hotmail.com` | A deploy succeeds and the site does not change; see [cloudflare/README.md §7](cloudflare/README.md) |

### The Azure coordinates in full

Read from the live subscription on 2026-08-10. Everything needed to reach it from a
machine that has never seen it:

| | |
|---|---|
| **Sign-in** | `asifhussain60@msn.com` |
| **Tenant / directory** | `55e453ce-cca7-4cf9-a1e1-c2a2f98a202b` — "Default Directory", a personal-Microsoft-account tenant with no custom domain |
| **Subscription** | `Journal AI — primary`, `3440564d-c056-4173-bec6-7af92dbece77`, Enabled |
| **Resource group** | `rg-journal-ai`, region `eastus` |
| **Portal** | <https://portal.azure.com> |

This identity sees **exactly one subscription in one tenant**, so `az login` needs no
`--tenant` and there is no wrong subscription to land in by accident. Record the
tenant id anyway: an account that later joins a work or school directory starts
seeing several, and `az login --tenant 55e453ce-…` is then the disambiguator.

The seven resources in the group are inventoried in
[docs/setup/azure-stack.md](../docs/setup/azure-stack.md); three of them are idle
(see §3). They are all still named `journal-*` from before the 2026-05-22 repo
rename — deliberate and permanent. Only the *app namespace* that drives secret naming
became `podcast-factory`.

---

## 2. What must be installed on the machine

| Requirement | Why the pipeline breaks without it | Install |
|---|---|---|
| macOS | `security`, and the keychain rows above | — |
| Python **≥ 3.11** | The cost ledger fails silently below it | `brew install python@3.11` |
| A repo venv at `.venv` | Sub-scripts inherit `sys.executable`; a system Python loses every dependency mid-run | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| `az` (Azure CLI) | The **only** path to every Azure and LLM credential | `brew install azure-cli` |
| Claude Code + `claude login` | `claude -p` is the pipeline's main reasoning engine | `brew install --cask claude-code` |
| `ffmpeg` + `ffprobe` | Audio normalize, chunking, duration probing (12 + 7 call sites) | `brew install ffmpeg` |
| `pdftoppm` (poppler) | Rasterising imported slide-deck PDFs | `brew install poppler` |
| Node + `npm`/`npx` | The Astro Site, the Podcast Factory Library, `wrangler`, the TS↔Python bridges | `brew install node` |
| `jq` | Provisioning and verification scripts | `brew install jq` |
| `gh` | Clone, and three pipeline call sites | `brew install gh` |
| Playwright chromium | `0book-render` (the PDF) and both site QA harnesses | Already vendored; `npx playwright install chromium` if absent |
| Docker/OrbStack | **Optional** — only the local SQL Server wisdom corpus | `brew install orbstack` |

Python dependencies are pinned in [`requirements.txt`](../requirements.txt). Pillow,
FastAPI/uvicorn and Whisper are listed there as commented-out optional extras — the
video layer, the source-library server and local transcription respectively.

**The pre-flight stage checks a subset of this for you.** `preflight_doctor.py` runs
at the top of every orchestrator launch and hard-fails with the exact fix command on
missing Python deps, an expired Claude token, an unreachable `api.anthropic.com`, or
unreachable Azure — but only when an ingest phase still has to run. It does not
check `ffmpeg`, `pdftoppm`, or Node.

---

## 3. The 29 phases, and what each one reaches outside the repo

The canonical list is `PHASES` in
[`scripts/podcast/_progress.py`](../scripts/podcast/_progress.py) — never re-declare
it anywhere. Plain-English names come from `book_status_card._PHASE_NAMES`. "Claude"
below means `claude -p` on the flat-rate Max subscription, which costs no money;
only the Azure and Gemini rows are real dollars.

| # | Phase id | What it is called on screen | Reaches out to |
|---|---|---|---|
| 1 | `pre-flight` | Pre-flight checks | Claude auth ping, `api.anthropic.com`, Azure reachability |
| 2 | `branch` | Branch created | git / `origin` |
| 3 | `scaffold` | Folders prepared | — |
| 4 | `0a` | Scanning and translating | **Azure Document Intelligence** (OCR) + **Azure Translator** — the largest metered cost |
| 5 | `0b` | English refinement | Claude |
| 6 | `0c` | Arabic pronunciation | Claude; the canonical mushaf in `mirror.db` |
| 7 | `0ci` | Source gap analysis | Claude; the knowledge base. Halts for review on Islamic content |
| 8 | `0d` | Chapter design | Claude |
| 9 | `0e` | Enrichment | Claude |
| 10 | `0literary` | Literary pass | **Gemini** |
| 11 | `06a` | Source review | **Human gate** |
| 12 | `0f` | Series plan review | **Human gate** |
| 13 | `0g` | Series registered | — |
| 14 | `per-chapter` | Writing each chapter | Claude; Gemini (second-opinion audit) |
| 15 | `per-chapter-optimize` | Chapter polish | Claude |
| 16 | `per-chapter-slides` | Slide decks | Claude. Skipped unless `enable_slide_decks` |
| 17 | `audio-script` | Dialogue scripts | **Always skipped** — see below |
| 18 | `audio-render` | Audio render | **Always skipped** — see below |
| 19 | `finalize` | Quality review | **Human gate** — this is the `phase_status=halted` you look for |
| 20 | `audio-ingest` | Audio ingest | **NotebookLM (manual)** then **Azure Speech** — the real audio path for every book |
| 21 | `0book-design` | Book structure | Claude |
| 22 | `0book-compose` | Writing the book | Claude; the mushaf; Gemini |
| 23 | `0book-illustrate` | Diagrams | Claude (proposes ≤3 diagrams); Playwright, to render Mermaid to SVG. No image model |
| 24 | `0book-slide-import` | Slide import | **NotebookLM deck PDFs (manual drop)**; `pdftoppm` |
| 25 | `0book-render` | Rendering the PDF | Playwright chromium |
| 26 | `publish` | Publishing | Flips `status` in place; then `deploy_listener.sh` unless `--skip-listener` |
| 27 | `trainer` | Learning pass | Claude |
| 28 | `merge` | Merging to develop | git / `origin` |
| 29 | `done` | Done | — |

### Phases 17 and 18 never run, and that is settled

`audio-script` and `audio-render` belong to the API audio path, which means
ElevenLabs — the only non-manual engine there has ever been. **No book uses it.**
Verified 2026-08-10: nothing in `content/` sets `audio_engine: elevenlabs`, two books
set `notebooklm` explicitly, and every other book takes the `notebooklm` default from
`_rules.audio_engine_default_for_profile`. Both phases skip via `is_autonomous()` and
record `status="skipped"`.

The registry entry in `_audio_engines.py` has been marked dormant since 2026-06-14
and is kept on purpose: it is what stops the audio engine from being a hardcoded
assumption rather than a choice. **It is a seam, not a dependency** — a migration
provisions no audio credential and installs nothing for it.

### Three Azure resources that are provisioned and idle

Worth knowing before a migration budgets for them or a cleanup deletes them:

- **`journal-language-market`** (Language / TextAnalytics, F0 free) — credentials
  resolve, `test_azure_connectivity.py` checks it, and `_engine.py` routes a
  `key_phrases` task to it. **Nothing dispatches that task.** Wired but unreached.
- **`journal-openai`** — provisioned for DALL-E 3, which was deprecated in March
  2026 before it was used. Image generation stayed on Gemini. Whisper is deployable
  there if local transcription is ever wanted.
- **`journalpodcaststorage`** — three containers, no active caller.

None of them costs anything meaningful today. Deleting them would break
`verify-azure.sh` and `test_azure_connectivity.py`, which both still probe them.

### The three places a human, not a machine, is the dependency

These have no API and cannot be automated away. A migration that reproduces every
credential and still cannot finish a book is almost always missing one of them.

1. **NotebookLM** — `notebooklm.google.com`, signed in as the gmail account. The
   pipeline writes the upload bundle and the framing text; a person uploads each
   chapter, pastes the framing into Customize, and drops the resulting `.m4a` into
   `content/<Bucket>/<slug>/m4a/`. Nothing in the repo can do this step.
2. **Slide-deck PDFs** — exported from NotebookLM by hand into
   `slide-decks/chNN-*.pdf`; `0book-slide-import` halts until they are there.
3. **Google Drive delivery** — `My Drive/Podcast Library/{Series}/{Edition}.pdf`,
   written with a plain `shutil.copy2` to the local CloudStorage mount. Requires
   Google Drive for Desktop installed and signed in. `ls` on that mount errors even
   when the copy worked; verify by opening Drive, never by listing.

---

## 4. Data stores, and which survive a fresh clone

| Store | Travels in git | Restore on a new machine |
|---|---|---|
| `content/knowledge-base/mirror.db` (~29 MB, all 6,236 vowelled ayat) | ✅ | Clone |
| `content/knowledge-base/*.jsonl` corpus atoms | ✅ | Clone; union-merged via `.gitattributes` |
| `content/knowledge-base/knowledge.db` | ✗ | `intelligence/corpus_sync.py rebuild` — **never `export`**, which clobbers the committed JSONL |
| `content/knowledge-base/morphology.db` | ✅ | Clone |
| `content/_shared/source-library/{KQur,KSessions,Kashkole}.sql` (~768 MB) | ✗ | External backup only. Feeds `wisdom-db/setup-wisdom-db.sh` |
| `content/_shared/source-library/wisdom-corpus.db` | ✗ | Rebuild from `KSessions.sql`; kept deliberately |
| Per-book audio (`m4a/`) | ✗ | Never tracked. Re-generate, or restore from Drive |
| Cloudflare D1 `podcast-listener` | ✗ | Schema from `listener/migrations/` (10 files); content re-pushed by `publish_to_listener.py` |
| R2 `podcast-listener-media` | ✗ | Re-uploaded by `upload_listener_media.py` |
| Local D1 (`listener/.wrangler/state/v3/d1`) | ✗ | `npm run db:migrate`. **Deleting it signs Asif out of localhost** — rebuild only when no migration path exists |

---

## 5. Bringing a new machine up

The order matters — steps 5 and 6 are what actually make the pipeline able to run,
and everything before them is inert without them.

```bash
xcode-select --install
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.11 jq azure-cli gh node ffmpeg poppler
brew install --cask claude-code

gh repo clone asifhussain60/podcast-factory && cd podcast-factory
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

bash scripts/install-git-hooks.sh       # all five hooks — see git-hooks/README.md
bash scripts/install-claude-skills.sh   # 22 agent specs into .claude/agents/

claude login                            # sign in as asifhussain60@gmail.com (Max)
az login                                # sign in as asifhussain60@msn.com
az account set --subscription "Journal AI — primary"

python3 scripts/podcast/preflight_doctor.py   # the real proof it works
bash scripts/start-session.sh
```

Then, by hand, because nothing can restore them for you: store
`cloudflare_api_token`, `listener_better_auth_secret` and
`safina_google_client_secret` in the keychain (§1), each with

```bash
security add-generic-password -U -a "$USER" -s <service> -w
```

which prompts, so the value never reaches shell history.

**Optional, and only if you need them:** `bash infra/wisdom-db/setup-wisdom-db.sh`
for the local SQL Server corpus (needs Docker and the 768 MB of dumps), and
`cd listener && node scripts/dev-vars.mjs` to rebuild `.dev.vars` from the keychain.

### Two verification scripts that will lie to you

- **`infra/azure/verify-azure.sh` checks the macOS keychain**, which the pipeline no
  longer reads. On a correct vault-only machine it reports missing keys for a stack
  that works perfectly. Trust `preflight_doctor.py` and
  `test_azure_connectivity.py` instead — both resolve the way the pipeline does.
- **`pull-secrets.sh` and `store-keychain-keys.sh` populate that same unread cache.**
  They are harmless and still correct for what they claim to do; they are simply no
  longer part of making a machine work.

---

## 6. Spend, and what is actually metered

Claude is flat-rate on the Max subscription and costs nothing per call — that is why
the pipeline routes its reasoning through `claude -p` and never through the Anthropic
API key, and why `_secrets.py` deliberately refuses to pre-load `ANTHROPIC_API_KEY`
into the environment. Real money is only ever these:

| Service | Where the cap is | Cap |
|---|---|---|
| Azure (all resources) | Azure portal budget `journal-ai-monthly-cap` | $50/month, alerts at 50/80/100% |
| Google Gemini | Cloud billing budget on `generativelanguage.googleapis.com` | $10/month tripwire |
| Anthropic API (separate org, unused by the pipeline) | Anthropic console | $25/month |
| Cloudflare | Free tier; R2 has no egress charge | ~1.4% of the 10 GB allowance |

Standing authorization: Azure and Gemini spend needs no per-run ask. Report real
dollars only — never token-equivalents for Claude work.
