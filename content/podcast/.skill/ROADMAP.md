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
| A7 | Canonical BOOK_DIR layout: `content/podcast/library/<category>/<book-slug>/` with `chapters/`, `chapter-contracts/`, `episodes/`, `turboscribe/`, `_system/` | per-book trees | a9e8933 |
| A8 | Per-book overrides separated from skill internals (`.skill/` vs `library/`) | repo-wide | ad1cc37, 02bb140 |
| A9 | `audit_transcript.py` empirical-feedback loop (sensor → analyser → per-episode regression report) | `scripts/podcast/audit_transcript.py` | pre-May 18 |

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
