# Podcast Skill — Roadmap (Consolidated State)

**Role.** This file is the **state-of-the-skill ledger**, loaded as cold-start item 18 by `.github/agents/podcast-challenger.agent.md` and as item 19 by `skills-staging/podcast/SKILL.md`. Producer and challenger consult it on every chapter and every episode authoring run so authoring decisions stay aware of: what was recently shipped (Section A), what is in flight (Section B), what is portable / out-of-tree (Section C), what was rejected from external proposals (Section D), and what awaits an explicit decision (Section E).

**Maintenance.** Update this file whenever an item moves between sections (e.g., a Section B item lands in code → migrate to Section A with the commit hash). Treat it as living state, not historical record.

**Last reconciled:** 2026-05-18
**Sources reconciled:**
- `_workspace/chatgpt-podcast-skill-prompt.md` (portable ChatGPT system prompt — out-of-tree personal derivative)
- `content/podcast/.skill/handbook/arabic-tts-protocol.md` (Track A protocol; was `_workspace/podcast-arabic-tts-protocol-plan.md` before promotion on 2026-05-18)
- ChatGPT "Recommendations and Architectural Guidance" doc (pasted 2026-05-18; assessment in Section D below)
- Repo commits 2026-05-17 → 2026-05-18

---

## A. Already implemented (May 17–18 commits — visible in repo)

| # | Item | Where it lives | Commit |
|---|---|---|---|
| A1 | Conversation choreography (Driver/Color roles; one cross-introduction beat per episode; no mid-sentence interjections) | `content/podcast/.skill/handbook/two-host-framing.md` | 6a2dec1 |
| A2 | R-NOMODERNIZE **softening**: explicit "DO use modern-life practical analogies" paragraph alongside the platform/anachronism DENY list | `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md` | 6a2dec1 |
| A3 | `scaffold_book.py` — deterministic one-shot creation of the canonical BOOK_DIR layout | `scripts/podcast/scaffold_book.py` | 906b46c |
| A4 | `chapter-contracts/<slug>.yml` as the I/O contract surface (title, content-type, enrichment scope) | per-book `chapter-contracts/` | 906b46c |
| A5 | Category Q challenger checks — cross-book bleed + chapter-set design quality | `.github/agents/podcast-challenger.agent.md` | 906b46c |
| A6 | Debate format alongside `deep_dive` (schema, render, challenger paths) | `content/podcast/.skill/handbook/` + scripts | 40d5163 |
| A7 | Canonical BOOK_DIR layout: `content/podcast/library/<category>/<book-slug>/` with `chapters/`, `chapter-contracts/`, `episodes/`, `transcripts/`, `_system/` | per-book trees | a9e8933 |
| A8 | Per-book overrides separated from skill internals (`.skill/` vs `library/`) | repo-wide | ad1cc37, 02bb140 |
| A9 | `audit_transcript.py` empirical-feedback loop (sensor → analyser → per-episode regression report) | `scripts/podcast/audit_transcript.py` | pre-May 18 |
| A10 | **Post-publication audit cadence** — 7-day SLA, 3-command sequence (transcript drop → `audit_transcript.py` → `podcast-challenger`), Loop M declared a standing invariant. Closes the rule-evolution feedback loop on actual NotebookLM output. | `skills-staging/podcast/SKILL.md` §post-publication; `scripts/podcast/audit_transcript.py` (next-step print) | 2026-05-18 |
| A11 | **Azure Speech-to-Text helper** — `transcribe_episode.py` (audio → `transcripts/EP##-<slug>.transcript.txt`); Speech client in `_azure.py` (Fast Transcription API 2024-11-15, synchronous, multipart); provisioning + keychain + connectivity-probe extensions across `infra/azure/*` + `test_azure_connectivity.py`. Manual transcript drops (any external service) continue to work unchanged. Activation gated on `ENABLE_SPEECH=true` in `azure-config.env` + re-run of `provision-azure.sh` and `store-keychain-keys.sh`. | `scripts/podcast/_azure.py`, `scripts/podcast/transcribe_episode.py`, `infra/azure/{provision-azure,store-keychain-keys}.sh`, `infra/azure/azure-config.{template.env,env}`, `scripts/podcast/test_azure_connectivity.py`, `skills-staging/podcast/SKILL.md` §post-publication step 1a | 2026-05-18 |
| A12 | **Closed-loop learning substrate** — `_learning/` directory + `findings.jsonl` append-only ledger (schema in `_learning/README.md`); `learn_aggregate.py` → `patterns.md`; `learn_propose.py` → markdown proposals; `test_challenger.py` regression harness with 5 bootstrap fixtures (B5, O1, N1, M3, R4); `write_health.py` per-book health score + trend log; single-source `CHALLENGER_VERSION` constant in `_rules.py`. Closes the empirical-feedback loop with a Goodhart-resistant promote stage (human approval required between propose and merge). Generic mangle map externalized from `audit_transcript.py` to `_mangle-map.md`. | `content/podcast/.skill/_learning/`, `scripts/podcast/{learn_aggregate,learn_propose,test_challenger,write_health}.py`, `scripts/podcast/_rules.py` (`CHALLENGER_VERSION`, `LEARNING_DIR`, `emit_finding`), `.github/agents/podcast-challenger.agent.md` v2.0, `content/podcast/.skill/handbook/_mangle-map.md` | 2026-05-18 |
| A13 | **First rule promotions from the learning loop** — two proposals matured + merged in one cycle. (a) **J2 bold-header surface form** — extended `R-NAMES` auto-fix scope to cover `**Long Name**` emphasis and `#+ **Long Name**` section headers; added 4 ceremonial-form entries to `05-name-alias-policy.md` (al-Razi, al-Sijistani, al-Kirmani, al-Nasafi ceremonial expansions); applied to kitab-al-riyad ch01 (4 occurrences rewritten to alias-led `**Alias** — long-form, the author of *work*.` bio anchors). (b) **R-NOSURPRISE positive companion** — added "name what is new in ONE short clause" positive directive alongside the DENY list; applied to kitab-al-riyad EP01 framing (~140-word add, still ~380 words under the 3,500-word hard cap). Two new regression fixtures (`j2_bold_header`, `surprise_positive_companion`); harness now 7/7 green. | `content/_shared/arabic/05-name-alias-policy.md`, `content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md` (R-NAMES), `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md` (R-NOSURPRISE), `scripts/podcast/test_challenger.py` (+2 detectors), `content/podcast/.skill/_learning/fixtures/{j2_bold_header,surprise_positive_companion}/`, kitab-al-riyad ch01 + EP01 framing | 2026-05-18 |

---

## B. In-flight proposal (approved, awaiting explicit `implement`)

Source: `content/podcast/.skill/handbook/arabic-tts-protocol.md` (Track A only; Track B-DirectTTS deferred).

| # | Step | Files touched |
|---|---|---|
| B1 | TTS engineering rules rewritten as **numbered imperatives** (Q→K, Dh→TH, Kh→KH guttural, stress-cap, hyphen-glottal) | `content/_shared/arabic/01-tts-pronunciation-key.md` |
| B2 | `R-PRONUNCIATION-IMPERATIVE` splits into **Conversational** (smooth Anglicized for casual integration) and **Classical** (Tajweed-approximating hard syllables for scripture and named figures) | `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md` |
| B3 | `## Pronunciation` → `## Phonetic Key (TTS Pronunciation)`; build script and challenger accept both for one cycle; auto-fix renames legacy headers | same as B2 + `scripts/podcast/build_episode_txt.py` |
| B4 | Per-book `pronunciation.md` gains a `Mode` column (Conversational/Classical) — optional on parse, defaults to Classical | `scripts/podcast/scaffold_book.py` template |
| B5 | Backfill `ayyuhal-walad/_system/pronunciation.md` with Mode classifications | per-book file |
| B6 | `worked-examples.md` §4 gains one Conversational + one Classical example | `content/podcast/.skill/handbook/worked-examples.md` |
| B7 | Challenger Loop C5 sub-check: scripture-citation term marked Conversational → flag (authoring decision; flag-only, not auto-fixed) | `.github/agents/podcast-challenger.agent.md` |
| B8 | Re-render `EP02-hatim-eight-benefits` with auto-fixed section name | per-book draft |

**R-PHONETICS-OUT remains intact** — no inline phonetic parens in chapters. Reverting it would regress the 5-episode audit.

**Note (2026-05-18):** the previously-listed B9–B12 (Azure Speech-to-Text helper) shipped as **A11** above. Activation requires `ENABLE_SPEECH=true` in `infra/azure/azure-config.env` + a re-run of `provision-azure.sh` and `store-keychain-keys.sh`. Smoke test (B11 equivalent): once provisioned, run `transcribe_episode.py` against an audio export of the existing `EP02-hatim-eight-benefits` and diff against the transcript already at `ayyuhal-walad/transcripts/`.

---

## C. Portable derivative (lives only in `_workspace/`)

`_workspace/chatgpt-podcast-skill-prompt.md` — a single ChatGPT system prompt that captures Phase 0a–0e for users who want to drive the pipeline through ChatGPT instead of running the repo skill.

**Deliberately omits** (the repo owns these):
- The `audit_transcript.py` empirical-feedback loop (post-NotebookLM, can't be self-driven by ChatGPT).
- Per-book `chapter-contracts/*.yml` (deterministic re-render is a repo-skill concern).
- `podcast-challenger` Category Q cross-book checks.
- `scaffold_book.py` workspace layout (user manages folders).

**Sync trigger:** if the underlying handbook files (`notebooklm-source-chapter-rules.md`, `notebooklm-customize-prompt-rules.md`, `two-host-framing.md`, `episode-architecture.md`, `enrichment-sources.md`, `01-tts-pronunciation-key.md`, `SKILL.md`) change, regenerate this prompt.

---

## D. From the GPT "Recommendations" doc — accepted / rejected

### Accepted (deferred, low-cost)

| Item | Disposition | Notes |
|---|---|---|
| YAML metadata discipline on quotes & translations | Defer | Extend `content/babu-memoir/_system/quotes-library.txt` schema (`source`, `translator`, `authenticity`, `tags`) **only if/when** external corpora arrive. Today the quote bank is memoir-internal. |

### Rejected (with reasons)

| Item | Why rejected |
|---|---|
| "Phase 9 uses SQLite" | No such phase exists. SQLite was removed in commit bee0480 (2026-05-17). The doc inverts the direction of travel. |
| ArcadeDB / PostgreSQL / Neo4j / pgvector | Solving a retrieval problem the repo does not have. The library currently holds one podcasted book (`ayyuhal-walad`). Re-evaluate at 3+ books. |
| Hadith / Ismaili quotation **corpus** | The corpus does not exist. Hadith fragments are embedded in memoir chapters and catalogued narrowly in `quotes-library.txt`. Building an index for an imaginary corpus is premature. |
| Arabic OCR pipeline (PaddleOCR-VL-1.5, RapidOCR v3.6.0) | The cited 2026 release dates and "State of Open Source report" claims are unverified. If/when an Arabic source PDF actually needs ingestion, pick OCR tooling against that real document, not against speculative release notes. |
| RGR (Red-Green-Refactor) framing as a process change | The repo just completed a v3.0/v3.5 cleanup cycle. No legacy debt of the kind the doc describes. |
| Interactive search UI / VS Code extension for cross-reference index | Scope inflation. NotebookLM is the UI for podcast output; VS Code is already the UI for memoir authoring. |
| "src-YYYY-NNN" identifier convention / `reference/` for primary sources / `scratch/` for working notes | These naming conventions do not exist in the repo. `reference/` holds skill governance, not primary sources. |

### Already true (the doc claimed these as recommendations but they're already the architecture)

- File-first model with markdown + YAML front matter — already how `chapter-contracts/` and memoir `_system/` files work.
- Challenger duplication detection — already enforced by LOOP 5 in `journal-workflow-v2.md` and inline in both challenger agents.
- Unique identifiers and tradition-coherence over breadth in citations — already the enrichment tier policy.

---

## E. Open items (user decision needed)

| # | Item | Status |
|---|---|---|
| E1 | `_workspace/folder-cleanup-prompt.md` (May 17) — proposed `skills-staging/` → `skills/`, fold `reference/` → `skills/`, flatten `_contracts/`. Partial: step 3 (`podcast/babu-memoir` → severed) executed via the v3.5 restructure (commit 02bb140); steps 2, 4, 5 still pending | Awaits decision |
| E2 | When to execute the Arabic TTS protocol (Section B above; details in `handbook/arabic-tts-protocol.md`) | Awaits `implement` |
| E3 | Whether to formalize the portable ChatGPT prompt as a tracked artifact (move from `_workspace/` into `content/podcast/.skill/exports/` or similar) | Awaits decision |

---

## Acceptance signals

- After B1–B8 land: zero `## Pronunciation` headers in non-archival files; all entries in per-book `pronunciation.md` have a Mode column; EP02 re-renders clean. Migrate the protocol entry from Section B to Section A with the commit hash; mark `handbook/arabic-tts-protocol.md` `IMPLEMENTED`.
- After E3 decision: `chatgpt-podcast-skill-prompt.md` either moves to a tracked location (likely `content/podcast/.skill/exports/`) or stays as a personal derivative in `_workspace/`.
- After E1 decision: workspace folder cleanup completes (the protocol + this ROADMAP no longer live in `_workspace/`; only `chatgpt-podcast-skill-prompt.md` and `folder-cleanup-prompt.md` remain).
