# Review Request: podcast-factory Wave 1 Architecture

You are acting as a senior software architect and technical reviewer. I am building a podcast-authoring pipeline called **podcast-factory** that converts scholarly Arabic books into NotebookLM Audio Overview podcast series. I have designed a multi-wave refactor plan and need a comprehensive review of the **Wave 1 scope** (Waves A + B), with full context for the subsequent waves so your review is informed by what comes after.

Please read this entire document before responding. At the end I list specific review questions. Do not skim — the design decisions interact in non-obvious ways.

---

## What the System Does

The pipeline takes a scholarly Arabic (or Urdu) book PDF and produces a series of NotebookLM "Audio Overview" podcast episodes. The workflow in brief:

1. **Ingest**: Azure Document Intelligence extracts text from the PDF
2. **Translate / Refine**: Azure Translator + Claude refine the English chapter text
3. **Phonetics**: Transliteration and pronunciation markup for Arabic terms
4. **Chapter Design**: Claude designs the episode-by-episode structure
5. **Enrichment (08)**: Claude enriches each chapter with scholarly context
6. **Per-Chapter Authoring (11)**: Claude authors `framing.txt` + `episode.txt` per chapter, fed to NotebookLM
7. **Slide Decks**: Claude authors slide bundles as a companion visual layer
8. **Challenger**: An AI reviewer checks quality gates (P0/P1/P2 findings)
9. **Publish**: Validated content ships to a published catalog

The whole process is orchestrated by `scripts/podcast/orchestrate_book.py`. The pipeline can cost $50–700 per book depending on length.

**Shipped books so far** (production, live in the catalog):
- *Kitāb al-Riyāḍ* (KaR) — Ismaili theological text, 13 chapters
- *The Master and the Disciple* (M&D) — play-novel format, 6 chapters
- *Ayyuhā al-Walad* — Ghazālī aphorism collection, 2 chapters
- *ISLR Mas-I* — lecture series, 3 chapters
- *Asāsāt al-Taʾwīl* — scholarly deep-dive, in progress

**Next books in the queue**:
- *Kunooz al-Ḥikma* — lecture series
- *Rasāʾil Ikhwān al-Ṣafāʾ* — 52-epistle encyclopedic work (~$350–700)

---

## The Kashkole Corpus (Key Context for Wave B)

**Kashkole** is a separate corpus of 122 chapters of Ismaili scholarly text (theology, taʾwīl, jurisprudence, ethics, cosmology) that has been translated and adapted into polished scholarly English. **It is NOT being produced as a podcast series**. Instead, it serves as a **doctrinal knowledge substrate** — a queryable knowledge base that enriches future book productions.

Kashkole is organized into 17 binders (thematic collections). Each chapter has gone through a three-stage pipeline:
- **Phase 1**: Translation (Urdu → English via Azure + Claude)
- **Phase 2**: Adaptation (scholarly refinement via Claude)
- **Phase 3**: Challenge (AI quality review — verdict: PASS / WARN / FAIL)

**Current state**:
| Verdict | Count | Notes |
|---|---|---|
| PASS | 9 | Ready to ingest immediately |
| WARN | 66 | Ingest with `needs_review=1` flag |
| FAIL | 18 | Need re-adaptation before ingest |
| Unchallenged (adapted only) | 26 | Need Phase 3 run first |
| Stuck at translated | 3 | Need Phase 2 + Phase 3 |
| **Total** | **122** | |

The 75 PASS+WARN chapters are ready to become knowledge atoms the moment Wave B ships.

---

## Architecture Overview

### Six-Layer Module Structure

The codebase follows a strict dependency chain — no cycles allowed:

```
Layer 1: Core        — _paths, _db, _archetypes, _anti_cliche, _atom_schemas
Layer 2: Domain      — _doctrinal, _context_injection, _cost_ledger
Layer 3a: Intelligence — extractor, librarian, augmenter
Layer 3b: Authoring  — _authoring/{framing, source_bundle, capstone, preface, augmentation}
Layer 4: Phases      — phases/{preflight, scaffold, ocr_translate, ..., knowledge_extract}
Layer 5: Driver      — orchestrate_book.py (thin dispatcher)
Layer 6: Agents      — podcast-challenger, podcast-auditor, podcast-trainer (AI agents)
```

### 16-Table SQLite Database Schema

The knowledge base lives at `content/knowledge-base/knowledge.db`. The 16 tables:

**Core group** (pipeline metadata):
- `books` — one row per book, slug + category + archetype
- `chapters` — one row per chapter, with phase status
- `episodes` — one row per episode, linked to chapters
- `phonetics` — pronunciation mappings
- `pipeline_runs` — per-book-per-phase run records
- `cost_ledger` — LLM cost per call, queryable by phase/book

**Knowledge group** (the intelligence library):
- `knowledge_atoms` — the core atom table: `id, type, canonical_id, body_json, confidence, needs_review, first_seen_book, first_seen_chapter`
- `atom_sources` — provenance: every path by which an atom entered the library (one atom can have multiple sources from different books)
- `atom_topic_tags` — many-to-many: atom → topic type tag (integers from `topic_type_taxonomy`)
- `external_corpora` — registry of external corpus sources (one row for Kashkole)
- `topic_type_taxonomy` — 18-row lookup table of Ismaili doctrinal topic types (seeded from the Kashkole database)
- `corpus_chapters` — per-chapter ingestion state machine for Kashkole chapters (tracks: `pending → ingested → needs_correction → correction_draft → re_ingested`)

**Quality group**:
- `challenger_findings` — per-finding records from the AI challenger, queryable across books

**Etymology group** (Wave 3):
- `arabic_roots` — Arabic root → English meaning + derivation tree
- `word_etymologies` — per-word etymology records
- `letter_profiles` — per-Arabic-letter symbolic profiles

### Three Atom Types (Wave 1 implements all three)

```
quran   — Quran verse atoms: surah, ayah, text_ar, text_en, tafsir_note
           canonical_id: "quran:<surah>:<ayah>"

hadith  — Hadith atoms: collection, number, grade, text_ar, text_en, chain
           canonical_id: "hadith:<collection>:<number>"

doctrine — Kashkole doctrine chunks: tradition, genre, binder/chapter metadata,
           topic_tags, text_en, quran_refs
           canonical_id: "doctrine:kashkole:<binder_id>:<chapter_id>:<chunk_index>"
```

### Seven Content Archetypes

Each book is tagged with one archetype that configures how the pipeline behaves:

| Archetype | Examples | Capstone | Notes |
|---|---|---|---|
| `scholarly-deep-dive` | KaR, Asāsāt | single_plus_distillation | Standard long-form |
| `play-novel` | M&D | none | Mandatory EP00 preface |
| `aphorism-collection` | Ayyuhā al-Walad | none | Short, no enrichment |
| `lecture-series` | Kunooz | single | Pre-synthesis step required |
| `encyclopedic-epistolary` | Rasāʾil | full_brethren | Phased rollout, augmentation ON by default |
| `narrative-prose` | (future) | single | |
| `socratic-dialogue` | (future, alias of play-novel) | none | |

### Key Design Decisions (ADRs)

These are locked and not open for review — include them in your thinking when reviewing other aspects:

- **DR-001**: SQLite + JSON1 for v1. Postgres + pgvector pathway kept open for Wave 2 (just swap `_db.py`'s connection factory).
- **DR-002**: The tier-2 capstone (distillation) NEVER reads chapter-scope source material — only tier-1 capstone output + per-chapter abstracts (~200 words). Raises `CrossTierRead` on violation.
- **DR-005**: Every file in `scripts/podcast/` is hard-capped at 600 lines. Pre-commit hook enforces.
- **DR-007**: Augmenter is default-disabled (`R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED = False`) until Gate G12 fires green on at least one A/B pair. The code ships in Wave B; the switch flips in Wave E.
- **DR-008**: Per-book scratch atoms stay in JSONL (`BOOK_DIR/_system/knowledge-atoms-scratch.jsonl`), not SQLite. Only the Librarian writes to the DB.
- **DR-009**: No version stamps (`Version: X.Y`) anywhere in tracked files. No `*v[0-9]*.md` filenames. Git history is the version log. Pre-commit hook enforces.
- **DR-012**: The Augmenter strips all Arabic script (U+0600–06FF, U+0750–077F) before injecting atoms into prompts. NotebookLM cannot parse Arabic text.
- **DR-013**: Shipped books (KaR, M&D, etc.) receive ONLY addendum episodes + metadata stamps + extraction-only passes. They are NEVER re-run through the pipeline from scratch.

---

## Wave 1 — Foundation + Intelligence (Current Scope)

Wave A is the gate — everything else follows. Wave B begins immediately after A5 completes.

### Wave A · Foundation (5 steps)

**A1 — Clean the legacy plan folder**

The `_workspace/plan/` folder has accumulated 37 files including 14 operational logs, 3 large legacy files (263K YAML, 84K acceptance-criteria, an old disambiguation plan), and various event reports. A1 surveys each file, folds any live content into the new nested structure, and deletes the rest. The git history preserves everything.

New layout after A1:
```
_workspace/plan/
  conventions/    (response template, authoring conventions)
  debt/           (live operational backlog — pipeline-debt.md)
  operations/     (per-book ship checklist)
  reader/         (podcast-reader polish notes)
  refactor/       (this plan + YAML + recommendation docs)
  research/       (existing)
  _drivers/       (existing batch scripts)
```

Three files need a scan before delete: `numeric-symbolic-disambiguation-plan.md` (may have live items), `acceptance-criteria.md` (84K — scan for untracked P-items), `podcast-plan.yaml` (263K — scan for live items not yet in debt.md).

**A2 — Build the Core layer**

Four stable modules that every later layer imports:

1. `scripts/podcast/_paths.py` — single path API: `book_dir(slug, category)`, `category_dir(category)`, `knowledge_base_dir()`, `knowledge_atoms_scratch(slug, category)`, `all_books()`. No hardcoded paths anywhere else.

2. `scripts/podcast/_db.py` — SQLite gateway: `get_connection()` (WAL mode singleton), `run_migrations()` (idempotent, applies 16 SQL files in order), seven repository functions (one per entity group). No other module touches `sqlite3` directly.

3. `scripts/podcast/_archetypes.py` — archetype registry: `load_archetype(slug)`, `resolve_archetype_for_book(meta_yml)`, `list_archetypes()`.

4. `scripts/podcast/intelligence/_anti_cliche.py` — four banned-phrase lists: `CAPSTONE_DENY`, `SELF_HELP_DENY`, `TIER_2_DENY`, `AUGMENTER_PRIOR_TREATMENT_DENY`.

5. `scripts/podcast/knowledge/_atom_schemas.py` (**EXTEND existing scaffold**) — currently has `QuranBody`, `HadithBody`, `AtomType = Literal["quran", "hadith"]`. A2 adds:
   - `DoctrineGenre = Literal["tawil", "theology", "jurisprudence", "ethics", "cosmology", "narrative", "scholarly"]`
   - `DoctrineBody(TypedDict)` with fields: `tradition, genre, binder_id, binder_slug, chapter_id, chapter_slug, section_ids, chunk_index, topic_tags, text_en, quran_refs`
   - Updates `AtomType = Literal["quran", "hadith", "doctrine"]`
   - Adds `doctrine_canonical_id(binder_id, chapter_id, chunk_index) -> str`

A2 also creates `content/knowledge-base/knowledge.db` via `_db.py:run_migrations()` and seeds the archetype registry on disk (`content/_shared/archetypes/<slug>/{exemplar.md, spec.yml, anti-patterns.md}` for the seven archetypes).

**A3 — Build the Domain layer**

1. `scripts/podcast/_doctrinal.py` gains:
   - `tradition_adjacency.yml` loader — defines `ismaili-orthodox` vs `ismaili-adjacent` author sets
   - `assert_no_cross_tradition_collision(text, window=150)` — flags any paragraph that cites both an ismaili-orthodox and ismaili-adjacent author within 150 words without an explicit adjacency acknowledgment
   - Inherits the existing `R-IMAM-NUMBERING` check (Imam Hasan = first Imam; "Imam Ali" is forbidden — substitute "Commander of the Faithful" / "Father of Imams")

2. `scripts/podcast/_context_injection.py` — shared injection contract:
   - `format_provenance(source) -> str` — neutral phrasing template for atom provenance
   - `build_injection(atoms, max_tokens, types) -> str` — token-budgeted injection block builder
   - `strip_arabic_script(text) -> str` — removes U+0600–06FF and U+0750–077F (DR-012)

Both the 08b augmentation phase (Wave C) and the Wave B Augmenter use this same contract, so they never diverge on phrasing or token budgeting.

**A4 — Modularize the two giant files**

`orchestrate_book.py` is currently 2,280 lines. `_authoring.py` is 2,025 lines. Both violate DR-005 (600-line cap).

- `orchestrate_book.py` → thin driver (≤ 400 lines) + per-phase handlers in `scripts/podcast/phases/` (one file per Phase enum entry, each ≤ 300 lines, each implementing `PhaseHandler.run(bd, ctx) -> PhaseReport`). 16 handler files total.
- `_authoring.py` → `_authoring/` package: `framing.py`, `source_bundle.py`, `capstone.py`, `preface.py`, `augmentation.py`. `__init__.py` re-exports the public API so existing call sites keep working with zero changes.

**A5 — Strip version stamps + install pre-commit guard**

- Remove `Version: X.Y` headers from 4 tracked files
- Rename 2 files with version numbers in their names
- Remove version comments from 5 specific locations in code files
- Install `infra/git-hooks/pre-commit` that rejects any commit with `^Version:\s*\d` in tracked files OR any new file matching `*v[0-9]*.md`
- Investigate: `CONTENT/` vs `content/` case mismatch (Mac case-insensitive FS may hide a duplicate-tree bug)

---

### Wave B · Intelligence Layer (5 steps)

Wave B builds the knowledge brain. All Wave B steps depend on A5 completing first.

**B0 — Kashkole corpus ingestion driver**

A standalone batch driver at `_workspace/plan/_drivers/kashkole_ingest_knowledge.py` (≤ 400 lines) that seeds the intelligence library from the 75 PASS+WARN Kashkole chapters. Does NOT go through `orchestrate_book.py` — Kashkole is a substrate, not a book being produced.

**Key behaviors:**

*Idempotent per chapter*: re-running on a corrected chapter deletes that chapter's old atoms (cascades through `atom_sources`, `atom_topic_tags`, orphaned `knowledge_atoms`), then re-ingests clean.

*Refinement state machine* on `corpus_chapters.ingestion_status`:
```
pending → ingested → needs_correction → correction_draft → re_ingested
```
Asif can mark a chapter for correction, edit its `adapted-extract.en.md`, and re-ingest without affecting any other chapter's atoms.

*Verdict handling*: PASS chapters ingest with `needs_review=0`. WARN chapters ingest with `needs_review=1` (atoms are in the library but the Augmenter blocks them until re-ingested clean).

**Atom extraction logic**:

Three atom types extracted per chapter:
1. **Quran atoms**: Find all `⟪quran S:A⟫` markers in `adapted-extract.en.md`. For each, extract the surrounding paragraph (~150 words) as `tafsir_note`. Emit `quran:<S>:<A>` atom.
2. **Hadith atoms**: Read `adaptation-citations.jsonl`. Entries matching known hadith collection names (Bukhārī, Muslim, Tirmidhī, etc.) become hadith atoms.
3. **Doctrine chunks**: Split `adapted-extract.en.md` on `<!-- section N -->` markers. Group consecutive sections into ≤600-word chunks without splitting mid-section. `chunk_index` is 0-based within the chapter. Each chunk becomes a `doctrine:kashkole:<binder_id>:<chapter_id>:<chunk_index>` atom.

**Topic tag assignment**: Sourced from `_workspace/kashkole-ksessions/topic-type-map.json` — a pre-extracted JSON file containing the 18-row `Lookup_TopicTypes` taxonomy and 223 per-topic assignments. No database access needed during ingestion. The 18 types map to doctrinal tag lists:

| TopicTypeID | English Name | Tags Applied |
|---|---|---|
| 0 | Unknown | *(use binder fallback)* |
| 15 | Proof and Evidence | `kalam, argumentation, theology` |
| 17 | Prophetic Hadith | `hadith, sunnah` |
| 18 | Moral Advice and Ethics | `ethics, adab, nasihah` |
| 19 | Meaning of Quranic Verse | `tawil, quran-exegesis, haqaiq` |
| 20 | Golden Sayings / Aphorisms | `aphorisms, wisdom, hikma` |
| 22 | Meaning of Daʿāʾim al-Ṭahāra | `tawil, zahir-batin, jurisprudence, daaim` |
| 23 | Hadith Commentary | `hadith, tawil, commentary` |
| 24 | Knowledge of ʿAlī | `wilaya, ali, imamate` |
| 25 | Meaning of a Story | `tawil, narrative, haqaiq` |
| 26 | Meaning of Sharīʿa Command | `tawil, zahir-batin, jurisprudence` |
| 27 | Knowledge of the Esoteric (Bāṭin) | `batin, haqaiq, tawil, esoteric` |
| 29 | Rulings of Sharīʿa | `jurisprudence, sharia, fiqh, daaim` |
| 30 | Knowledge of the Ḥadd | `hudud, dawat, hierarchy` |
| 31 | Manqabat (Praise poem) | `poetry, manqabat, wilaya` |
| 32 | Virtues / Faḍāʾil | `fadail, praise, wilaya` |
| 33 | Religious Terminology | `terminology, definitions, glossary` |
| 34 | History | `history, biography, tarikh` |

**CLI**:
```bash
python kashkole_ingest_knowledge.py                     # all chapters
python kashkole_ingest_knowledge.py --chapter <slug>    # single chapter
python kashkole_ingest_knowledge.py --re-ingest <slug>  # correction cycle
python kashkole_ingest_knowledge.py --dry-run           # preview only
python kashkole_ingest_knowledge.py --status            # 122-row table
python kashkole_ingest_knowledge.py --force <slug>      # override FAIL after manual clearance
```

Seeds `external_corpora` (one Kashkole row) and `topic_type_taxonomy` (18 rows) on first run; idempotent on repeat.

---

**B1 — Extractor**

`scripts/podcast/intelligence/extractor.py` (≤ 300 lines)

API:
- `extract_atoms_for_book(bd: Path) -> Path`
- `extract_atoms_for_chapter(text, slug, ch) -> list[Atom]`

One Claude Sonnet structured-output call per chapter (strict JSON schema, not free-text). Reads enriched chapter source at `BOOK_DIR/chapters/<ch-slug>.txt` — **NOT** audio scripts (which carry NotebookLM drift). Writes atoms to `BOOK_DIR/_system/knowledge-atoms-scratch.jsonl`.

Cost caps (new R-* constants):
- `R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_CHAPTER = 0.10`
- `R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_BOOK = 10.00`
- `R_KNOWLEDGE_EXTRACTOR_CONFIDENCE_REVIEW_THRESHOLD = 0.7`

Atoms with confidence < 0.7 are auto-appended to `manual_review_queue`.

---

**B2 — Librarian**

`scripts/podcast/intelligence/librarian.py` (≤ 250 lines) — pure Python, no LLM.

API: `merge_into_library(bd, scratch_path) -> MergeReport`

**Four outcomes on canonical-ID match**:
1. **new** — INSERT into `knowledge_atoms` + INSERT into `atom_sources` with `source_type='pipeline'`
2. **duplicate** — atom already exists; INSERT a new `atom_sources` row for this pipeline provenance; `knowledge_atoms` row unchanged
3. **variant** — same canonical ID, different `text_en`; INSERT new `knowledge_atoms` row with variant marker in `body_json` + new `atom_sources` row
4. **conflict** — same canonical ID, different `text_ar` or hadith grade; write to `manual_review_queue`, halt phase

Conflict-resolution helper at `intelligence/resolve_conflicts.py`:
```bash
python resolve_conflicts.py <slug> --accept-incoming
python resolve_conflicts.py <slug> --keep-existing
python resolve_conflicts.py <slug> --both-as-variants
```

Also emits `content/knowledge-base/_index/doctrine-by-tag.json` — flat JSON mapping each topic tag to a sorted list of atom IDs. Rebuilt incrementally on each Librarian run. Enables O(1) Augmenter lookup without a DB scan.

Post-merge git hook at `infra/git-hooks/post-merge-knowledge.sh` re-invokes Librarian when both merged branches touched `knowledge.db`.

---

**B3 — Augmenter**

`scripts/podcast/intelligence/augmenter.py` (≤ 250 lines)

API:
```python
augment_for_chapter(
    book_slug: str,
    chapter_id: int,
    chapter_text: str,
    *,
    max_atoms: int = 5,
    max_tokens: int = 800,
    doctrine_topic_ids: list[int] | None = None
) -> str
```

**Two independent lookup paths**:

Path 1 — Quran + hadith:
- Regex-scan `chapter_text` for canonical citation patterns (`Q\d+:\d+`, hadith chain patterns)
- Exact-ID lookup: `knowledge_atoms WHERE type IN ('quran','hadith') AND needs_review=0`

Path 2 — Doctrine (Kashkole):
- Only executes when `doctrine_topic_ids` is a non-empty list (from `meta.yml`)
- Topic signals extracted from `⟪ar:…⟫` markers + key theological terms in `chapter_text`: `tawhid, wilaya, tawil, mabda, maad, aql, nafs, hudud, dawat`
- Query: `atom_topic_tags JOIN knowledge_atoms WHERE type='doctrine' AND needs_review=0 AND topic_type_id IN (doctrine_topic_ids)`
- Scoring: `score = len(intersection(chapter_signals, atom.topic_tags))`; sort desc; cap at 3 doctrine atoms (~300 tokens each)
- **Self-exclusion**: atoms whose `binder_slug` matches `book_slug` are excluded (a book cannot be its own prior doctrinal source)
- **Silent skip** when `doctrine_topic_ids` is absent — Kashkole doctrine never bleeds into non-Ismaili books

**`needs_review=0` gate applies to BOTH paths.** WARN-verdict Kashkole atoms are blocked from augmentation output until Asif re-ingests them clean.

**Injected prompt block format**:
```
[PRIOR DOCTRINAL CONTEXT — Kashkole corpus]
Topic: {comma-joined topic_tags}
Source: Kashkole — {binder_slug}, ch. {chapter_slug}
---
{text_en truncated at sentence boundary to fit token budget}
---
```

**`doctrine_topic_ids` meta.yml field**:
- Type: `list[int] optional`
- Values: integers matching `topic_type_taxonomy.type_id` (the 18-row seed from B0)
- Example: `doctrine_topic_ids: [19, 27, 26]` for a book on Quranic exegesis + esoteric knowledge + sharīʿa taʾwīl
- Absent = doctrine injection silently skipped

**Default disabled** (`R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED = False`): returns empty string when `series.enable_knowledge_augmenter: false`.

Three call sites with documented token budgets:
- `08-enrichment` phase: 200 tokens (hint-level, always present)
- `11-per-chapter` authoring: 500 tokens (full prior treatment)
- `0g-audit` / podcast-challenger: 800 tokens (complete cross-book context)

New R-* constants:
```python
R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED = False
R_KNOWLEDGE_AUGMENT_MAX_ATOMS = 5
R_KNOWLEDGE_AUGMENT_MAX_TOKENS = 800
```

---

**B4 — Wire 08a/08b/08c into PHASE_ORDER**

Adds three new Phase enum entries to `scripts/podcast/_phases.py`:
```python
ARCHETYPE_RESOLVE  = "08a-archetype-resolve"
AUGMENTATION       = "08b-augmentation"
KNOWLEDGE_EXTRACT  = "08c-knowledge-extract"
```

Phase order: `08-enrichment → 08a → 08b → 08c → 09-series-plan`

Three new handler files in `scripts/podcast/phases/`:
- `archetype_resolve.py` — reads `meta.yml.archetype`, configures downstream phase behavior, writes to `orchestrator-state.json`
- `augmentation.py` — **stub for now** (full implementation in Wave C step C3)
- `knowledge_extract.py` — dispatches to Extractor + Librarian; handles conflict-halt + phased-rollout interaction

When `phased_rollout: true` (Rasāʾil), `08c-knowledge-extract` runs per-phase-boundary rather than per-book; conflicts halt only that phase, not the whole book.

As part of this step: update `framework.md` phase table + `skills-staging/podcast/SKILL.md` + `podcast-challenger.md` Category catalog in the same PR (standing docs-sweep rule).

---

## Waves C, D, E — Summary (Future Context)

### Wave C · Archetype Expansion

**C1** — Land archetype specs on disk for PLAY-NOVEL, LECTURE-SERIES, and ENCYCLOPEDIC-EPISTOLARY.
- PLAY-NOVEL: mandatory EP00 preface (≤20 min), character roster as prose (not bulleted list), per-chapter `presumed_context` field
- LECTURE-SERIES: `08-pre-synthesis` step synthesizes thematic clusters before enrichment; Azure Urdu gap-fill workflow (~$3/book)
- ENCYCLOPEDIC-EPISTOLARY: `phased_rollout: true`, `augmentation_enabled: true` (default ON for this archetype only), `capstone_mode: full_brethren`
- Also adds an Arabic-source translation workflow (for Rasāʾil — Arabic original PDF)

**C2** — Multi-tier capstone authoring (`_authoring/capstone.py`). Five capstone modes. Strict recursion invariant (DR-002). Six new challenger quality gates for distillation quality.

**C3** — 08b modern-research augmentation phase. For each source unit, Claude generates 5–15 contemporary scientific/scholarly findings that confirm/extend/contest/contextualize the source's claims. Live citation verification (HTTP HEAD + Crossref DOI lookup, cached 30 days). Anti-cliché guard blocks "quantum spirituality"-style buzzword hijacking. Augmentation output feeds back into the Extractor (B1) — verified citations become atoms.

**C4.0** — NotebookLM diagram-capability pilot (2–3 Rasāʾil epistles, ~$30). **Findings decide whether C4's diagram gate is hard (P1) or advisory (P2).**

**C4** — MANUAL-REVIEW marker syntax + canonical-form pre-filter + rich-diagram classifier.

**C5** — Phased rollout for large books (> 20 episodes). Rasāʾil: 5 phases (Parts 1–4 + capstone tier). Each boundary = Tier-2 always-ask gate.

### Wave D · SPA + Dashboard

**D1** — Design system tokens (CSS custom properties) shared across the plan SPA and `podcast-reader/`.

**D2** — Astro SPA shell at `_workspace/plan/index.html`. Top nav: Plan · Architecture · Dashboard · Backbone · Debt · Books.

**D3** — Backbone visualization: interactive pipeline diagram, click-to-explore phases and archetypes.

**D4** — Live dashboard: real-time plan execution progress, knowledge-base atom counts, cost-to-date, open manual-review queue, phase failure rates. Reads static snapshots regenerated on every push.

### Wave E · Retroactive Enhancements + Extended Publish Gate

**E1** — Migrate every existing book's `meta.yml` to the unified archetype-aware schema.

**E2** — KaR addendum: tier-2 distillation episode (no re-run). Also: Imam-doctrine sweep on KaR chapter sources; extraction-only knowledge pass.

**E3** — M&D addendum: EP00 preface episode + archetype-aware postprod review + extraction-only pass.

**E4** — Extend publish gate with G8–G12:
- G8: capstone-mode-honored
- G9: rich-diagram-coverage ≥ 60%
- G10: manual-review-resolved (zero open markers)
- G11: knowledge-base-merge-clean (zero conflicts in merge report)
- G12: augmenter A/B acceptance — at least one challenger finding references an augmented atom. **G12 is the gate that flips `R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED` from False to True.**

---

## Open Questions (Unresolved)

These are open for discussion and your input may inform the final decision:

5. **Branch strategy**: Direct commits on `develop` vs feature branches per step. My preference is direct on `develop` for small mechanical steps; feature branches only for Wave C+ content.

6. **Three large legacy files** in `_workspace/plan/` need a scan before A1 deletes them. Risk: live items may be buried in a 263K YAML file. Mitigation: grep for known F-item IDs and P-item patterns before delete.

7. **Rich-diagram classifier engine** — Claude vision (better quality) vs Gemini vision (lower cost). Decision deferred to after the C4.0 pilot.

8. **Augmenter A/B pair for G12**: Kunooz (augmenter disabled, baseline) + first Rasāʾil phase (augmenter enabled). Confirm after Kunooz completes.

9. **Rasāʾil intake layout**: Single book + `part_map` in `meta.yml` (my recommendation) vs 4 sub-books per part vs 52 epistle-level books.

10. **Dashboard data source**: Static JSON snapshots regenerated per push (my recommendation) vs Astro server-mode read-only API.

11. **Default `capstone_mode` per existing book**: KaR/Asāsāt → `single_plus_distillation`; ISLR → `single`; Ayyuhā → `none`; M&D → `none`; Kunooz → `single`; Rasāʾil → `full_brethren`.

---

## What Is NOT in Scope

- The operational F-item backlog (F4, F7, F11–F13, F22, F23, F25/F26, F29) — tracked separately
- `podcast-reader` polish and Gemini AI integration — tracked separately
- The 12-task postprod-vacuum sub-plan currently in flight on M&D — folds into E3
- Live system metrics beyond push-triggered snapshots (Wave D v1 is static)

---

## Review Questions

Please review the Wave 1 design (Waves A + B) against the full context above, and address each of the following. Be specific — "looks good" is not useful. Flag concrete risks, gaps, or better alternatives with reasoning.

### Architecture & Design

**Q1 — Database schema adequacy**: The 16-table schema is designed to support Wave 1 (quran/hadith/doctrine atoms) and Wave 3 (etymology). Do you see any missing tables or columns for the planned use cases? Specifically: Is the `atom_topic_tags` design (integers from `topic_type_taxonomy`) sufficient for the intersection-scoring Augmenter (B3), or would a different indexing strategy perform meaningfully better at the expected atom count (500–800 atoms at Wave 1)?

**Q2 — Kashkole ingestion driver placement**: The B0 driver lives in `_workspace/plan/_drivers/` not in `scripts/podcast/`. This is intentional — it's a one-time batch migration tool, not a pipeline phase. Do you see any issues with this separation? Specifically: should the topic-type expansion logic (shared between B0 and B1) live in `scripts/podcast/knowledge/` as a shared utility rather than being extracted inline?

**Q3 — `needs_review` gate completeness**: The `needs_review=0` gate at B3 blocks WARN-verdict atoms from augmentation output. But WARN-verdict atoms DO enter the library (they just have `needs_review=1`). Is there a scenario where a WARN atom in the library causes problems before it's ever queried by the Augmenter? For example: does the Librarian's variant/conflict detection work correctly when comparing a `needs_review=1` atom against an incoming `needs_review=0` atom from B1?

**Q4 — Modularization approach (A4)**: Splitting `_authoring.py` (2,025 lines) into a package with `__init__.py` re-exporting the public API is described as "zero changes to existing call sites." Is that guaranteed to be true? What Python edge cases could break this?

**Q5 — doctrine_topic_ids integer list**: The `doctrine_topic_ids` meta.yml field uses integers matching `topic_type_taxonomy.type_id`. The 18-row seed is only inserted by the B0 driver. What happens at B3 query time if B0 hasn't run yet (empty `topic_type_taxonomy` table)? Is a silent-empty-result the right behavior, or should B3 log a warning?

### Wave B Sequencing

**Q6 — B0 before B1 dependency**: B0 (Kashkole ingest) is listed as a Wave B step but has no formal `depends_on` relationship with B1–B4 (it's parallel, standalone). Should B0 be treated as a prerequisite for B3 (the Augmenter), or is the "default-disabled until G12" guard (DR-007) sufficient protection against running B3 on an empty doctrine library?

**Q7 — Pre-B0 data prep**: 18 FAIL + 26 unchallenged Kashkole chapters must complete their pipeline phase before they can be ingested. This is tracked operationally (gate report), but is not a Wave B plan step. Does this omission create a gap? Should it be a named step (e.g., B0-pre: fix FAIL chapters)?

### Forward Compatibility

**Q8 — Wave 2 Postgres migration**: DR-001 says "swap `_db.py`'s connection factory." Is swapping just the connection factory realistically sufficient for a SQLite → Postgres migration, or are there JSON1 functions, SQLite-specific pragmas, or ATTACH DATABASE patterns in the planned schema that would require query changes?

**Q9 — Wave C augmentation (C3) vs Wave B Augmenter (B3)**: B3 is the knowledge-library Augmenter (queries `knowledge_atoms`). C3 is the modern-research augmentation phase (generates new citations via Claude). They are different things but both write to similar output locations. Is the naming clear enough to prevent implementation confusion? Is the relationship between C3's output and B1's input (C3's verified citations feed B1's Extractor) architecturally sound, or does it create a circular dependency?

**Q10 — doctrine_by_tag.json index ownership**: The `_index/doctrine-by-tag.json` file is built by the Librarian (B2). But B0 is what inserts the doctrine atoms. B0 runs first. Does B0 also need to emit/update this index, or is it acceptable that the index doesn't exist until B2 first runs after B0?

### General

**Q11 — What is the highest-risk step in Wave A?** Rank A1–A5 by execution risk and explain your top pick.

**Q12 — What is missing?** Looking at the complete Wave 1 scope, what important design element, failure mode, or operational concern is absent from this plan that you would add before execution begins?

**Q13 — Open questions 5–11**: Of the 7 unresolved open questions listed above, which two have the most downstream design impact and should be resolved before Wave A execution begins?

---

*Please structure your response with one section per question. Prioritize depth over breadth — where you are uncertain, say so explicitly. Flag any place where you think the plan makes an assumption that is not stated.*
