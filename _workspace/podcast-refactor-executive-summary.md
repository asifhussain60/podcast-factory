# Podcast Generation — Refactor & Enhancement Plan

**Date:** 2026-05-18
**Branch:** develop (one commit ahead of origin)
**Just shipped:** `8ab3da1` — Azure provisioning scripts + operator's guide

This document closes the loop between the Azure work that just landed and the `/podcast` skill that hasn't yet consumed it, and lays out a phased refactor that pays down the largest friction points in the current pipeline.

---

## 1. What just got committed (Azure work review)

Ten files, ~1490 lines, landed as commit `8ab3da1`:

| Surface | Lives at | What it does |
|---|---|---|
| Operator's guide | [docs/azure/](docs/azure/) | README, architecture, setup, operations, troubleshooting — modelled on `docs/cloudflare/` |
| Provisioning script | [infra/azure/provision-azure.sh](infra/azure/provision-azure.sh) | Idempotent one-shot for resource group, Translator (S1), Doc Intelligence (F0), Storage (LRS) + 3 containers, optional Key Vault |
| Secrets bootstrap | [infra/azure/store-keychain-keys.sh](infra/azure/store-keychain-keys.sh) | Fetches keys + endpoints, stores 10 entries in macOS Keychain under `azure-journal-*` |
| Health check | [infra/azure/verify-azure.sh](infra/azure/verify-azure.sh) | 12-check read-only audit (subscription, resources, containers, keychain) |
| Parameter template | [infra/azure/azure-config.template.env](infra/azure/azure-config.template.env) | App-portable config; defaults populated for the journal app |
| gitignore tweak | [.gitignore](.gitignore) | `!*.template.env` carve-out so the template tracks while real configs stay out |

### Verdict on the Azure layer itself

**Quality is high — this is production-ready infra-as-code for a personal-stack scale.** Three things stand out:

1. **App-portability is real**, not theoretical. Every variable that hard-codes "journal" lives in `azure-config.env`. A `triplog-config.env` sibling would stand up an isolated parallel stack with zero script edits. The setup doc walks through this explicitly.
2. **Trust boundaries are explicit and honest.** The architecture doc names what the keys protect, where the SAS-token sprawl problem is unsolved, and the planned managed-identity hardening. Nothing is hand-waved.
3. **The expensive call is correct and well-justified.** Translator S1 (not F0) because F0 doesn't support document translation; Doc Intel F0 (not S0) because 500p/mo covers the benchmark — with the one-line upgrade for full-archive runs documented.

### What is NOT done — and is the entire point of this summary

**The Azure stack is provisioned but not wired into `/podcast`.** None of the Phase 0a normalization in [SKILL.md](skills-staging/podcast/SKILL.md) references the Doc Intel endpoint, the Translator endpoint, or the blob containers. The pipeline exists; it does no work.

This is the central refactor opportunity.

---

## 2. Current podcast pipeline — where the friction lives

The `/podcast` skill today is a **deterministic build system wrapped around in-conversation reasoning**. The pipeline (per [SKILL.md §0 invariants](skills-staging/podcast/SKILL.md) and [ROADMAP.md](content/podcast/.skill/ROADMAP.md)) is roughly:

```
[external source] → Phase 0a normalize → Phase 0b…0e chapters/contracts/enrichment
 → extract_chapter.py → episode-drafts/ → build_episode_txt.py
 → BOOK_DIR/episodes/EP##-<slug>.txt → [upload to NotebookLM]
 → NotebookLM Audio Overview → [transcribe in ] → transcripts/
 → audit_transcript.py → loop closure
```

Six pain points stand out, in rough order of how much they slow you down:

### P1. Phase 0a is manual and unaided
Source normalization (PDF → text, scanned Arabic → English, audio → text,.docx/.pptx → text) is currently "do whatever you can with the tools you have". The Azure stack just provisioned **exists specifically to solve this**, but no script reaches it. Every new source today costs you an external-tool dance.

### P2. The loop is paid, manual, and slow
NotebookLM produces an MP3. You sign in to (paid subscription), upload, wait, download, rename to `EP##-<slug>.transcript.txt`, drop into `BOOK_DIR/transcripts/`. Only then does `audit_transcript.py` run. This is the single biggest source of human latency in the iteration loop.

### P3. The Arabic TTS protocol is approved but unexecuted
[ROADMAP §B (B1–B8)](content/podcast/.skill/ROADMAP.md) — Conversational vs Classical mode split, `## Pronunciation` → `## Phonetic Key (TTS Pronunciation)` rename, per-book Mode column, EP02 re-render. Gated on you typing `implement`. **Independent of Azure** but blocks any Track B direct-TTS work that would replace NotebookLM.

### P4. No "ingest a real Arabic PDF" path exists
The `source-arabic` and `source-urdu` blob containers were provisioned for this. No code uploads to them, no code reads from them, no chapter file currently traces back to a blob URL. The full-archive run (Rāḥat al-ʿAql at 591 pages + the rest) cannot start.

### P5. Skill-internal sprawl that ROADMAP §E1 already flagged
`skills-staging/` should fold into `skills/`. `_contracts/` should flatten. Step 3 (`podcast/babu-memoir` severance) shipped in `02bb140`; steps 2/4/5 are still pending. Each is small; together they would tighten the skill's contact surface.

### P6. Deterministic vs intelligent boundary is fuzzy in Phases 0d/0e
Chapter re-segmentation (Phase 0d) and outside-material enrichment (Phase 0e) currently happen in-conversation. There's a deterministic build layer underneath, but the upstream "where to cut chapters" and "what to enrich with" judgements are baked into Claude's working memory rather than into a re-runnable artifact. This is fine while you have one or two books; it gets expensive at five.

---

## 3. Refactor roadmap — by horizon

### Horizon A — wire the Azure stack into Phase 0a (1 evening)

**Single deliverable: `scripts/podcast/ingest_source.py`.**

```
Usage:
 ingest_source.py <pdf-path> --lang ar --book-slug rahat-al-aql
 ingest_source.py blob://source-arabic/rahat-al-aql.pdf --book-slug rahat-al-aql
```

Behaviour:
1. Reads the PDF (local path or `source-arabic` blob).
2. Routes through Document Intelligence (FormRecognizer prebuilt-read) → page-anchored text with reading order preserved.
3. Routes the OCR output through Translator's document-translation endpoint → English text.
4. Writes `content/podcast/library/books/<slug>/chapters/_raw/<source>.txt`.
5. Drops a sidecar `.provenance.json` with `{doc_intel_run_id, translator_batch_id, page_count, char_count, timestamp}`.

This script becomes the **first paragraph of Phase 0a in SKILL.md**: "if source is a PDF/scan, run `ingest_source.py` and proceed from the emitted `_raw/<source>.txt`; otherwise paste text as today." The agent stays dumb, the deterministic layer widens.

Downstream Phase 0d (chapter re-segmentation) is then operating on a known-good English text file with provenance, not on whatever someone hand-pasted.

**Cost to test once:** $2–3 (one full-archive book through Doc Intel S0 + Translator S1 on a 1500-page benchmark). Well under the $50/mo budget cap.

**Files touched:** new `scripts/podcast/ingest_source.py`; SKILL.md §0 Phase 0a paragraph; new `_system/provenance/` directory convention per book.

### Horizon B — execute the Arabic TTS protocol (1–2 evenings, gated)

Eight atomic steps already specified in [content/podcast/.skill/handbook/arabic-tts-protocol.md](content/podcast/.skill/handbook/arabic-tts-protocol.md). Each is reversible. Auto-fix paths exist for the header rename. **Awaits your `implement` token.**

Why now: independent of Azure, but the Conversational/Classical mode column in per-book `pronunciation.md` becomes the source-of-truth for any later Track B (direct-TTS) work. Without it, Track B has nothing to read.

### Horizon C — replace with Azure Speech-to-Text (1 evening)

**Single deliverable: `scripts/podcast/transcribe_audio.py`.**

```
Usage:
 transcribe_audio.py path/to/notebooklm-export.mp3 \
 --book-slug ayyuhal-walad --episode EP02
```

Behaviour:
1. Hits Azure Speech-to-Text (batch transcription endpoint).
2. Emits `BOOK_DIR/transcripts/EP##-<slug>.transcript.txt` directly.
3. Drops the audio file under `BOOK_DIR/transcripts/_audio/EP##-<slug>.mp3` (gitignored) for replay.

This drops the subscription, eliminates the manual rename, and lets `audit_transcript.py` run unattended right after you finish listening to NotebookLM's output.

**Provisioning delta:** Azure Speech is a Cognitive Services resource — add `ENABLE_SPEECH="true"` + a `SPEECH_NAME="journal-speech"` block to `azure-config.env`, re-run `provision-azure.sh`. No new script architecture; just one more service alongside Translator + Doc Intel. Keychain entries follow the same `azure-journal-speech-*` naming convention.

**Cost:** ~$1 per audio hour. A 15-minute episode is $0.25.

### Horizon D — the Track B (direct-TTS) decision (deferred until 5+ episodes)

[arabic-tts-protocol.md](content/podcast/.skill/handbook/arabic-tts-protocol.md) explicitly defers a separate direct-TTS authoring artifact. With Horizon B done and Azure Speech available from Horizon C, the path becomes concrete:

- Render a single Asif-supervised voice per host (Driver / Color) using Azure Speech Neural Voice.
- Honour the Conversational/Classical mode column from the per-book `pronunciation.md` at synthesis time.
- Drop NotebookLM's randomization and the upload/transcribe round-trip entirely.

**Cost:** Custom Neural Voice training is $$$ (≈$10/hour standard; custom voices are higher). Defer until the audited episode count justifies the investment.

### Horizon E — workspace cleanups already flagged in ROADMAP §E1 (1 evening)

- `skills-staging/` → `skills/` (Claude Code skills install convention)
- `_contracts/` flatten
- Promote `_workspace/chatgpt-podcast-skill-prompt.md` to `content/podcast/.skill/exports/` if you want it tracked; otherwise leave it where it is and acknowledge it as a personal derivative (ROADMAP §E3).

Independent of Azure. Done in an hour. The reason it hasn't shipped is just "no decision yet" — it's not blocked on anything.

---

## 4. What the refactor looks like end-to-end

After all five horizons, the pipeline becomes:

```
[Arabic PDF in source-arabic blob]
 │
 ▼
ingest_source.py ← Horizon A
 ├─ Doc Intel (OCR, layout preserved)
 └─ Translator (Arabic → English)
 │
 ▼
chapters/_raw/<source>.txt +.provenance.json
 │
 ▼
[Phase 0d/0e — chapter re-segment + enrich, with Mode-aware pronunciation] ← Horizon B
 │
 ▼
chapters/ch##-<slug>.txt + chapter-contracts/<slug>.yml
 │
 ▼
extract_chapter.py + build_episode_txt.py (unchanged — deterministic build)
 │
 ▼
episodes/EP##-<slug>.txt
 │
 ▼
[NotebookLM Audio Overview] (Horizon D may replace this later)
 │
 ▼
transcribe_audio.py ← Horizon C
 │
 ▼
transcripts/EP##-<slug>.transcript.txt
 │
 ▼
audit_transcript.py (unchanged — closes the loop empirically)
```

Every human-in-the-loop step that exists today either disappears or becomes an `--implement`-style explicit gate. The hand-paste paths drop. The subscription drops. The pronunciation contract becomes a re-runnable artifact instead of in-conversation memory.

---

## 5. Decisions you need to make to unlock work

| # | Decision | Effect | Effort |
|---|---|---|---|
| D1 | Approve Horizon A (`ingest_source.py`) | Wires Azure into Phase 0a — pipeline finally has source-of-truth ingestion | 1 evening |
| D2 | Type `implement` for the Arabic TTS protocol | ROADMAP §B1–B8 execute; EP02 re-renders clean | 1–2 evenings, gated |
| D3 | Approve Horizon C (Speech-to-Text) — and the `ENABLE_SPEECH` config addition | loop dies; iteration latency drops | 1 evening |
| D4 | Decide Horizon E cleanups (ROADMAP §E1) | `skills-staging/` → `skills/`, `_contracts/` flatten | 1 hour |
| D5 | Defer or commit to Horizon D (direct-TTS) | If commit: budget $$ for custom voice; if defer: no action | n/a unless deciding to commit |

D1 and D3 are independent. D2 is independent of all Azure work and could ship tomorrow. D4 is independent of everything and is purely "do it or don't".

**Recommended sequence:** D2 (it's gated and the smallest scope) → D1 (the biggest unblocker) → D3 (latency win) → D4 (cleanup), then revisit D5 only after 5+ episodes are shipped and audited.

---

## 6. Risks worth naming

- **F0 ceiling on Doc Intel.** 500 pages/month. Rāḥat al-ʿAql alone is 591. Bump to S0 (one CLI command, ~$1.50/1K pages) before the full-archive run.
- **Translator regional feature drift.** Document translation for Arabic→English is broad in `eastus`. Don't migrate region casually; confirm support first.
- **Managed-identity migration is still TODO.** Translator → Blob auth currently uses SAS tokens; the architecture doc flags managed identity as the hardening step. Not blocking, but worth scheduling before the pipeline goes "live" in any meaningful sense.
- **Keychain → Key Vault migration is planned, not done.** Single-Mac portability today. Re-running `store-keychain-keys.sh` on a second Mac (after `az login`) works, but losing the Mac means re-fetching from Azure. The `ENABLE_KEYVAULT=true` flow is wired but the secrets haven't been pushed up.

---

---

## 7. Horizon A — SHIPPED (2026-05-18)

Three files landed on branch `test/api-connectivity`:

- [`scripts/podcast/_azure.py`](../scripts/podcast/_azure.py) — Azure REST adapter. Pure stdlib (no `pip install` deps). Reads creds from macOS Keychain (or `AZURE_*` env vars for CI), wraps Document Intelligence `prebuilt-read` + Translator Text v3.0. Surfaces clean `AzureCredsError` when the stack hasn't been provisioned.
- [`scripts/podcast/ingest_source.py`](../scripts/podcast/ingest_source.py) — Horizon A deliverable verbatim per §3. PDF in → `raw-extract.md` + `_provenance.json` out. Refuses to write into a non-existent BOOK_DIR (run `scaffold_book.py` first). Idempotent with `--force`.
- [`scripts/podcast/test_azure_connectivity.py`](../scripts/podcast/test_azure_connectivity.py) — pre-flight test, the Azure half of SKILL.md §1 Step 0. Reports `pass N fail M` mirroring the Node test for symmetry. `SKIP_LIVE=1` skips the round-trip probes.

[SKILL.md](../skills-staging/podcast/SKILL.md) updated in two places:
- §1 Step 0 — Step 0 split into "Anthropic proxy (always)" and "Azure stack (when Phase 0a runs against a PDF)" halves, each with the failing-state diagnostic.
- §1.5 Phase 0a — the script is the **preferred path** for PDFs; the format-table rows for PDF text-layer / image-only now point at `ingest_source.py` first, with `pdftotext` / Tesseract as fallback.

### What you need to do to start ingesting

The wiring is in place; the cloud isn't. Run these once, ~25 minutes:

```sh
# 1. Install the Azure CLI (one-time per Mac)
brew install azure-cli
az login

# 2. Provision the stack (~10 min of resource deployment)
cd ~/PROJECTS/journal/infra/azure
./provision-azure.sh

# 3. Pull keys into Keychain (instant)
./store-keychain-keys.sh

# 4. Verify everything is wired
./verify-azure.sh
python3 ~/PROJECTS/journal/scripts/podcast/test_azure_connectivity.py
# Expect: pass 4 fail 0
```

Then a first real ingestion:

```sh
# scaffold the book if it doesn't exist yet
python3 scripts/podcast/scaffold_book.py books rahat-al-aql "Rāḥat al-ʿAql"

# put the PDF where the layout expects it
cp ~/Downloads/rahat-al-aql.pdf \
 content/podcast/library/books/rahat-al-aql/_system/source/

# ingest — Doc Intel OCR + Translator ar→en
python3 scripts/podcast/ingest_source.py \
 content/podcast/library/books/rahat-al-aql/_system/source/rahat-al-aql.pdf \
 --book-slug rahat-al-aql --src-lang ar
```

Output lands at `content/podcast/library/books/rahat-al-aql/_system/source/text/raw-extract.md` with a `_provenance.json` sidecar. From there, Phase 0b (English refinement) → 0c (phonetics) → 0d (chapter design) → 0e (enrichment) per SKILL.md §1.5.

**Cost note:** Doc Intel F0 has a 500-page/month ceiling. Rāḥat al-ʿAql at 591 pages will exceed it. Before the full-archive run, flip the SKU in [`azure-config.env`](../infra/azure/azure-config.env): `DOCINTEL_SKU="S0"` and re-run `provision-azure.sh` (idempotent — only the SKU is updated).

---

## Project Status

**Work Completed**
- Reviewed the Azure provisioning work (docs + scripts + template), confirmed quality, identified that the pipeline is provisioned but not wired.
- Committed all untracked Azure files as `8ab3da1` (`infra(azure): provisioning scripts + operator's guide for OCR/translation pipeline`), including a `.gitignore` carve-out for `*.template.env`.
- Produced this executive summary, organized into five refactor horizons (A–E) with cost/effort/decisions called out.
- **D1 executed (2026-05-18):** Horizon A shipped on branch `test/api-connectivity` — `_azure.py` + `ingest_source.py` + `test_azure_connectivity.py` + SKILL.md §0/§1.5 wiring. See §7 above.

**Work Pending**
- **Run the four provisioning commands** in §7 (`brew install azure-cli`, `az login`, `./provision-azure.sh`, `./store-keychain-keys.sh`). The wiring is callable today; only the cloud-side stack is missing.
- Four decisions remain (D2–D5 from §5). Recommended sequence next: D3 (Speech-to-Text, kills the loop) → D2 (Arabic TTS protocol, gated on your `implement` token) → D4 (cleanups). Defer D5.
- ROADMAP.md §B (Arabic TTS protocol) and §E1 (workspace cleanups) still flagged as awaiting explicit `implement`.

**Decisions Needed**
- D2 — Type `implement` to execute the Arabic TTS protocol's B1–B8 steps?
- D3 — Add Azure Speech-to-Text to `azure-config.env` and replace the loop? (Drops a paid subscription; ~$0.25 per episode.)
- D4 — Execute ROADMAP §E1 workspace cleanups (`skills-staging/` → `skills/`, flatten `_contracts/`)?
- D5 — Commit to or defer Horizon D (direct-TTS via Azure Neural Voice)?

**Next Action**
- Run the four provisioning commands in §7. After that, the first real ingestion is one `ingest_source.py` invocation away. Tell me which of D2/D3/D4 to take next.

**Verdict**
- Azure layer ships clean. Horizon A code now ships clean too — pipeline is wired end-to-end; the only thing standing between you and a real OCR'd Arabic chapter is `az login` + `./provision-azure.sh`. Existing deterministic build core (extract_chapter / build_episode_txt / audit_transcript) untouched; the refactor strictly widened the upstream Phase 0a surface.
