# Holistic Audit — 48-hour work review (Waves A–K + dashboard + MCP + reader)

**Author:** Claude (Opus 4.8)  ·  **Date:** 2026-05-29  ·  **Mode:** research + documentation only, NO code changes
**Scope:** repo, podcast pipeline, intelligence pipeline, MCP blackbox (KQUR/KASHKOLE/KSESSIONS), wisdom corpus, DB schema, Astro site/reader.

> This is the evidence-based system-of-record for the audit. Every claim below is sourced to a file path I read or a command I ran. Documentation in the repo was NOT trusted; this reflects actual code state on `develop` as of 2026-05-29.

---

## 1. What actually got built (verified)

| Area | State | Evidence |
|---|---|---|
| Core layer (Wave A) | Real, in use | `scripts/podcast/_db.py`, `_archetypes.py`, `_paths.py`, `intelligence/_anti_cliche.py`, `_quality.py` |
| Intelligence chain (Wave B) | Built, **orphaned** | `scripts/podcast/intelligence/{extractor,librarian,augmenter,wisdom_ingest_knowledge}.py` |
| Source-library MCP (Wave J) | Real, **not consumed by reader** | `scripts/podcast/source_library_server.py` (6 tools, stdio+HTTP), `source_library_queries.py`, `source_library_mirror.py` |
| PEQ quality scoring (Wave K) | Real, surfaced in reader | `scripts/podcast/_quality.py`, `intelligence/challenger_scoring.py`, schema `019_quality_scores.sql`, `plan-dashboard/src/lib/peq-scores.ts` |
| Phase 06a source-review gate (Wave I) | **Wired + runs** | `scripts/podcast/phases/source_review_gate.py`, called in `phases/initial_driver.py` |
| Phase per-chapter-optimize (Wave I) | **Wired + runs** | `scripts/podcast/phases/per_chapter_optimize.py`, called in `phases/chapter_driver.py` |
| Astro reader + annotation workspace | Real, production-grade | `plan-dashboard/src/pages/library/[slug]/chapter/[chapter].astro`, `components/reader/AnnotationWorkbench.tsx` |
| Reader AI features | Real, **Gemini-backed (not MCP)** | `plan-dashboard/src/pages/api/ai/*`, `lib/reader/gemini-server.ts` |
| DB schema | 20 migrations, applied | `scripts/podcast/schema/001..020*.sql`; live DB `CONTENT/knowledge-base/knowledge.db` (356 KB) |

Books in `CONTENT/drafts/books/`: `asaas-al-taveel`, `ayyuhal-walad`, `islr-mas-i`, `kitab-al-riyad`, `the-master-and-the-disciple`. **No `anwar` book exists** — the screenshot is `ayyuhal-walad` (al-Ghazali, *O Beloved Son*).

---

## 2. The three load-bearing disconnects (the real story)

These are the gaps that matter. Everything the user wants ("intelligence + podcast hand-in-hand", "MCP drives annotations", "wisdom corpus") sits on top of fixing them.

### 2a. The intelligence pipeline is operationally orphaned
`orchestrate_book.py` `CANONICAL_PHASES` (lines ~152-161) is:
`pre-flight, branch, scaffold, 0a, 0b, 0c, 0d, 0e, 06a, 0f, 0g, per-chapter, per-chapter-optimize, per-chapter-slides, finalize, publish, trainer, merge, done`.
There is **no `0h` / extractor / librarian / augmenter phase** in the execution path. The three intelligence scripts only run when invoked manually. The augmenter is gated by `enable_knowledge_augmenter` (default `False` in `_rules.py`, not enabled on any book). Atoms in `knowledge.db` are **write-only** — nothing in a book run reads them back. → topic doc `05`.

### 2b. The MCP blackbox does not feed the reader
The reader's Quran popover calls **quran.com** (`plan-dashboard/src/pages/api/quran/verse.ts`), and term definitions call **Gemini** (`api/ai/define-term`). Neither calls `source_library_server` (port 4390). The 6-tool MCP blackbox exists but **no consumer is wired to it**. The reader's reference-highlighting machinery (`lib/reader/highlight-renderer.ts` + pluggable `ref-categories/`) is regex-based, not corpus-driven. → topic docs `04` + `06`.

### 2c. The "wisdom corpus" is still three separate application databases
`CONTENT/_shared/source-library/` holds three raw SQL Server dumps (KQur 15M, KSessions 29M, Kashkole 724M). They are restored into a Docker container by `infra/setup-wisdom-db.sh`. There is **no unified corpus** — and there is real duplication (two complete Quran representations; see doc `03`). The MCP queries route to these raw DBs. The FTS5 mirror (`mirror.db`) referenced in Wave J **does not exist on disk yet** (`CONTENT/knowledge-base/` has no `mirror.db`). → topic doc `03`.

---

## 3. Smaller findings (straightforward)

- **YNAB MCP is unrelated to this project and leaks a key.** `.vscode/mcp.json` registers `ynab` with a plaintext `YNAB_API_KEY`. Remove. → doc `02`.
- **`loop-intelligence.md` ledger is corrupted with ~100 duplicate log lines** (`_workspace/prompts/loop-intelligence.md` lines 42-131 are the same 7-line block repeated). The H3 autonomous chain driver was looping and appending identical entries. Worth truncating. → doc `02`.
- **Stale memory:** `project_podcast_reader.md` says the reader lives at `podcast-factory/podcast-reader/` — that directory does not exist; the reader is in `plan-dashboard/`. → doc `02`.
- **Plan drift:** the dashboard/SPA and reader are fully built but the refactor plan still lists "Wave D (SPA)" as PLANNED. Plan needs reconciliation. → doc `01`.

---

## 4. What is genuinely healthy (don't touch)

- Phase 06a + per-chapter-optimize are correctly wired (Wave I delivered).
- PEQ scoring is coherent end-to-end: contract in `_quality.py`, computed in `challenger_scoring.py`, stored in `quality_scores`, rendered in the reader header.
- The reader is well-architected: pluggable `ref-categories` registry (matches the "extensibility first" principle), clean `lib/reader/` separation, SQLite-backed annotations (`annotation_tags`, `paragraph_annotations`, `paragraph_notes` in the shared `knowledge.db`).
- Schema migrations are ordered and idempotent (`016_schema_migrations.sql` tracks applied files).

---

## 5. Document index for this review

| Doc | Topic | Disposition |
|---|---|---|
| `01-reader-into-site.md` | Reader folded into main site + advanced features | STRAIGHTFORWARD → plan delta proposed |
| `02-ynab-and-memory-flush.md` | Remove YNAB MCP; flush stale memory; fix loop ledger | STRAIGHTFORWARD → ready to apply |
| `03-wisdom-corpus-merge.md` | Merge KQUR/KASHKOLE/KSESSIONS without duplication | **DISCUSS SEPARATELY** |
| `04-mcp-blackbox-annotation-engine.md` | MCP drives annotations + silent markers | **DISCUSS SEPARATELY** |
| `05-intelligence-podcast-integration.md` | Intelligence + podcast pipeline hand-in-hand | **DISCUSS SEPARATELY** |
| `06-ayyuhal-walad-annotation-prompt.md` | Annotation/visual-differentiation prompt for the book | PROMPT documented |


---

# Preserved from intelligence-pipepine-discussion.md (transcript deleted 2026-05-29)

> The 125KB Copilot-era discussion transcript was deleted to reduce sprawl after its binding decisions were absorbed into plan.yaml `wisdom_corpus_program` (WC5 audio-intake) + the ledger. The two decision tables and the Plan Audit punchlist below are preserved verbatim because they contain actionable items not captured elsewhere.


## Binding decisions table (conversational pass)

| Decision | Answer |
|---|---|
| Ayyuhal Walad authority layer | Arabic text primary, English aid |
| Historical/biographical content | Strip universally (noise) |
| YouTube commentary (Misra) | Enrichment only, not structural |
| Noise-strip cost gate | Rule-based pre-pass first, Sonnet for ambiguous only |
| Episode slicing | Blueprint agent, content-first, ~30 min, learning arc |
| YouTube transcription | Azure Speech-to-Text (~$6) |
| Companion PDF trust | Auto-detect translator, metadata-tag fidelity, dynamic calibration |
| Turboscribe for Ismaili Urdu lectures | Urdu mode only → Azure Translator + terminology glossary |
| Urdu lecture on absent Arabic text | Urdu is working authority; Arabic terms preserved verbatim; phonetics mandatory |
| Incomplete books | Slice from what exists; intelligence pipeline supplements depth, not content |
| Review gate position | After clean/refine, before blueprint |
| Review gate unit | Book-level approval; warnings must clear before approve unlocks |
| Gemini role | Format + enrich + host-role consistency; does not change meaning |

## Requirements Definition (final, phase-numbered)

| # | Decision | Answer |
|---|---|---|
| 1 | Gate position | After Phase 06 phonetics, before Phase 07 |
| 2 | Gate scope | Per-book; other books unaffected |
| 3 | Approval mechanism | `review-gate.json`; astro site button; CLI fallback |
| 4 | Astro site | Always-on at port 4322; read/edit in podcast-reader, approve in astro site |
| 5 | Phase 11g model | Claude Sonnet (preserves Gemini independence in 0g) |
| 6 | Pre-gate analysis | Phase 06a, Claude Haiku, ~$0.50–1.00/book, `warnings[]` in `review-gate.json` |
| 7 | Noise detection | Model-driven routing layer; intelligent service selection by input_type + tradition + complexity; no fixed regex patterns |
| 8 | Tradition firewall | `tradition` field on all atoms; `tradition_affinity` in `meta.yml`; Augmenter filters; `universal` atoms freely injectable |
| 9 | Two gates | "Source Review Gate" (06a) + "Publish Review Gate" (13); both in single unified astro site view |
| 10 | Audio intake | `input_type` branch in Phase 04; mixed sources merge before Phase 05 |
| 11 | Turboscribe | Urdu mode → Azure Translator + `ismaili-glossary.yml` |
| 12 | Source authority | Urdu-on-absent-Arabic: Urdu is working authority; Arabic terms preserved verbatim |
| 13 | Incomplete books | Slice from what exists; intelligence pipeline supplements depth |
| 14 | Original source search | Auto-search at intake; missing = logged, never blocks |

No contradictions with existing architecture. Backward-compatible phase numbering. Ready to write the plan.

## Plan Audit — May 2026 (R/G/P punchlist)

> **Verdict: Structurally sound but with 6 regression risks, 5 structural gaps, and 7 modern pattern gaps.** The plan is ambitious and coherent. The risks below are specific and fixable before execution resumes.

---

### 🔴 Regression Risks — would break something currently working

**R1 — Wave B has a contradictory execution state.**
The `execution_notes` say B0/B1/B2/B3 are "complete" with test counts. Then a `CORRECTION (2026-05-28)` immediately below says "all Wave B files are scaffold stubs — real B0 starting now." The plan ends in a contradictory state. Any Claude session reading the YAML will draw opposite conclusions depending on which line it reads last. The current true state needs one authoritative stamp.

**R2 — H2 is marked "PENDING APPROVAL" but has been partially executed.**
The session log in `copilot-handoff.md` shows REPO_ROOT unification (step 1) and state machine tests (step 2) were committed as part of `refactor/pipeline-quality`. The plan still says H2 is pending. This isn't cosmetic — the next session may re-execute H2 step 1 and create duplicate or conflicting changes.

**R3 — Wave I's tradition schema change (I3) is a Wave B regression.**
Adding a `tradition` field to all atom types requires a new DB migration (019+) and updates to the Librarian's merge logic. Wave B's B2 was built without this field. If I3 is executed after B2 ships, the Librarian will either silently ignore tradition on all existing atoms or fail on schema validation. This needs to be a B2.1 patch before any new book runs extraction.

**R4 — The Source Review Gate (06a) isn't in `PHASE_ORDER` and the hourly launchd tick will re-enter halted books.**
The orchestrator runs hourly. `phase_status: awaiting_human_review` is a new state the resume_dispatcher has no documented handler for. Without an explicit `if phase_status == 'awaiting_human_review': skip_book()` guard, the launchd tick will repeatedly attempt to advance a halted book, potentially overwriting the review state. This is a data-loss risk.

**R5 — README.md now contradicts reality.**
After today's refactor, published still contains a README saying content goes there. The next Claude session reading that file will think the layout is `drafts/` + `published/` and may recreate the duplication pattern.

**R6 — `publish_to_library.py` still physically copies files.**
The UI now reads `publication.status` from `meta.yml`. The pipeline still copies files to published. When the pipeline finishes a book and calls `publish_to_library.py`, it will create files that the UI won't scan (because we removed the `published` stage scan). The book will show "Draft" in the UI forever, even after the pipeline marks it published. The publish script needs to write `publication.status: published` to `meta.yml` instead of copying files.

---

### 🟡 Structural Gaps — missing pieces that block forward work

**G1 — Wave I has zero plan entries.**
Six locked decisions (audio intake, noise routing, tradition firewall, Source Review Gate, Book Review view, Phase 11g) exist only in the conversation summary. They are not in plan.md or plan.yaml. They have no wave assignment, no acceptance criteria, no dependency wiring. They are invisible to any tool or agent that reads the plan.

**G2 — Phase 11g references a "Phase 11" that doesn't exist in `PHASE_ORDER`.**
The existing pipeline goes Phase 01–0g with letter suffixes for 08a/08b/08c. There is no Phase 11. Either the Wave I authoring phases need a phase-numbering scheme or "Phase 11g" needs to be renamed to fit the existing convention (e.g. `per-chapter-optimize`).

**G3 — The Batches API optimization was applied only to KASHKOLE, not the podcast orchestrator.**
A7 migrated KASHKOLE adapt/challenge to the Batches API (50% cost reduction). The podcast orchestrator makes per-chapter sequential API calls for enrichment, authoring, and framing. For Rasāʾil (52 epistles × ~4 phases each = ~200 calls), sequential calls cost roughly 2× what batching would cost. This is a meaningful gap given the $350-700 estimated cost for Rasāʾil.

**G4 — No Gemini API fallback in Phase 0g.**
`audit_bundle_gemini.py` is the second-opinion auditor. The plan has no documented degradation path if the Gemini API is unavailable or rate-limited. A flaky Gemini response would fail the phase and halt the book with no recovery option other than manual intervention.

**G5 — No prompt-change tracking.**
DR-009 prevents file version stamps but doesn't address prompt versioning. When a system prompt in `_rules.py` changes, every chapter processed after that change produces different output with no record of which chapters used which prompt. For a book processed over multiple sessions, some chapters may be inconsistent with others and the pipeline has no way to detect this. A lightweight solution: hash each system prompt at runtime and store it in `orchestrator-state.json` per chapter. Zero cost, no new infrastructure.

---

### 🟢 Modern Pattern Gaps — cost-neutral improvements the field has converged on

**P1 — No cross-episode semantic similarity check.**
Modern podcast production pipelines at Spotify and BBC R&D run episode-to-episode similarity before publish to detect "we're saying the same thing 3 episodes in a row." The challenger catches rule violations per episode but has no cross-episode view. For a 52-episode Rasāʾil book, drift compounds invisibly. A cosine similarity pass on episode embeddings using the existing Azure infrastructure costs ~$0.01/book and would catch structural repetition before it reaches NotebookLM.

**P2 — Model version not tracked per chapter output.**
The pipeline uses Claude Sonnet/Haiku/Opus based on phase rules. When Anthropic releases Claude 4 or updates Sonnet, earlier chapters and later chapters of the same book will have been produced by different models with no record. Best practice (used by every serious LLMOps team): store `model_id` + `model_version` in the per-chapter ledger. Already writing `orchestrator-state.json` — add two fields.

**P3 — GSAP ScrollTrigger in Wave G requires a commercial licence for public sites.**
The narrative homepage uses GSAP ScrollTrigger, which is free for personal projects but requires a "Club GreenSock" membership (~$150/year) for commercial/public use. If this site is ever public-facing, the licence is non-compliant. CSS `@scroll-timeline` + `animation-timeline: scroll()` (now broadly supported) achieves the same pinned-scroll effect with zero cost and zero dependency.

**P4 — The manual-review queue has no SLA or aging.**
Items enter `manual_review_queue` (low-confidence atoms, unverified citations, doctrinal conflicts) but the plan has no policy for how old an item can get before it blocks publishing. In practice, a book will accumulate review items across a long pipeline run and nobody will notice until the G10 gate fires at publish time. Best practice: a weekly digest query (`--status` on the queue showing items > 7 days old) wired into the dashboard metric tiles.

**P5 — archetypes is not validated at intake.**
A new book's `meta.yml` can reference an archetype that doesn't exist in the registry, or misspell one. The pipeline will fail silently or at an arbitrary phase when `resolve_archetype_for_book()` returns None. A validation step at `phases/preflight.py` — before any LLM spend — that confirms the archetype exists in the registry would catch this at ~$0 cost and prevent an expensive pipeline run from failing mid-way.

**P6 — No structured rollback path for a book that fails mid-Rasāʾil.**
F33 (book halts on first per-chapter failure) is a known debt item. For a 52-episode book across 5 phases, the probability of at least one chapter failure somewhere is high. The current plan has no documented recovery story: can Asif skip a failing chapter and continue? Can he mark a chapter as manually-resolved and resume from that point? This needs a decision before Rasāʾil starts, not during it.

**P7 — `tradition: universal` atoms have no governance policy.**
The I3 tradition firewall allows `tradition: universal` atoms to be freely injected into any book. But who decides an atom is truly universal? A Quran verse with an Ismaili tafsir note could be tagged `universal` accidentally or intentionally and then inject that interpretation into a Sunni book. The plan needs an explicit rule: `universal` atoms contain only the raw text of the source (the verse itself, the hadith text) with no interpretive note, OR they require explicit human approval to carry that tag.

---

### Summary

| Category | Count | Most Urgent |
|---|---|---|
| 🔴 Regression risks | 6 | R6 (publish script breaks UI model), R4 (hourly tick re-enters halted books), R1 (Wave B state contradiction) |
| 🟡 Structural gaps | 5 | G1 (Wave I not in plan), G2 (Phase 11 doesn't exist), G3 (Batches API gap) |
| 🟢 Pattern gaps | 7 | P5 (archetype validation at intake), P2 (model version tracking), P7 (tradition:universal governance) |

