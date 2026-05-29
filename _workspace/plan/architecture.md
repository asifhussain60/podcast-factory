# Architecture

This document describes the **shape** of the podcast-factory system: what each layer does, how layers compose, what contracts they expose, and where the extensibility seams sit. It is the timeless companion to the dashboard at `_workspace/plan/index.html` (live state, current metrics) and the execution roadmap at `_workspace/plan/refactor/plan.md` (what to build, in what order).

Read this once, then return to it whenever the question is *"where does X belong?"* The plan and the dashboard answer *"what's next?"* and *"what's the current state?"*.

---

## System at a Glance

The podcast-factory turns a scholarly Arabic book into a NotebookLM-driven podcast series, then ships it to a public catalog. The system is organized as a backbone of pipeline phases with modules plugging into each phase — like a track with stations along it, where each station's behavior depends on what KIND of book is on the track.

```mermaid
flowchart TB
    subgraph CLIENT["Inputs"]
        PDF[Book PDFs<br/>raw/]
        AUDIO[Audio recordings<br/>m4a/v1/]
        TXT[Lecture transcripts<br/>various]
    end

    subgraph BACKBONE["The Pipeline Backbone — phases as stations"]
        direction LR
        P0[Ingest] --> P1[Refine] --> P2[Design] --> P3[Enrich] --> P4[Augment] --> P5[Extract] --> P6[Author] --> P7[Slides] --> P8[Audit] --> P9[Ship]
    end

    subgraph MODULES["Modules plugging into each station"]
        ARCH[Archetypes<br/>play-novel · scholarly · encyclopedic · ...]
        DOCT[Doctrinal rules<br/>R-IMAM · R-PHONETICS · ...]
        ANTI[Anti-cliché registry]
        CTX[Context injection<br/>shared contract]
        DIAG[Rich-diagram classifier]
    end

    subgraph STORAGE["Storage layers"]
        BOOK[Per-book JSONL scratch<br/>content/drafts/]
        DB[(knowledge.db<br/>SQLite + JSON1)]
        CAT[Published catalog<br/>content/published/]
    end

    subgraph EXTERNAL["External integrations"]
        NLM[NotebookLM]
        AZ[Azure Speech /<br/>Translator / DocIntel]
        CLAUDE[Claude API]
        GEMINI[Gemini API]
    end

    CLIENT --> BACKBONE
    BACKBONE -.->|reads| MODULES
    BACKBONE -->|writes| STORAGE
    BACKBONE <-->|API calls| EXTERNAL
    BACKBONE --> CAT
```

Three things to notice:
- **The backbone is fixed** — every book follows phases in order, no special-case branches.
- **Modules are pluggable** — what each phase actually does depends on which archetype is resolved for the book.
- **Storage is layered** — the per-book scratch (JSONL, in git for diffability), the shared knowledge database (SQLite, the cross-book brain), and the published catalog (audience-facing, separate from drafts).

---

## The Six Module Layers

Code is organized into six layers. A layer can only depend on layers below it. This is the *acyclic dependency* invariant that keeps the system testable and changeable.

```mermaid
flowchart BT
    DRIVER["6. Driver<br/>orchestrate_book.py<br/>(thin: walks PHASE_ORDER, dispatches)"]
    PHASES["5. Phases<br/>phases/&lt;phase_id&gt;.py<br/>(one file per Phase enum entry)"]
    AUTHORING["4. Authoring<br/>_authoring/{framing, source_bundle,<br/>capstone, preface, augmentation}.py"]
    INTEL["3. Intelligence<br/>intelligence/{extractor, librarian,<br/>augmenter, resolve_conflicts}.py"]
    DOMAIN["2. Domain<br/>_archetypes · _doctrinal ·<br/>_context_injection · _cost_ledger"]
    CORE["1. Core<br/>_paths · _db · _rules · _branching ·<br/>intelligence/_anti_cliche"]

    CORE --> DOMAIN
    DOMAIN --> INTEL
    DOMAIN --> AUTHORING
    INTEL --> PHASES
    AUTHORING --> PHASES
    PHASES --> DRIVER

    style CORE fill:#eef
    style DOMAIN fill:#efe
    style INTEL fill:#fee
    style AUTHORING fill:#ffe
    style PHASES fill:#fef
    style DRIVER fill:#eff
```

**Layer 1 — Core (zero pipeline knowledge).** Pure utilities. `_paths.py` is the *only* place that maps a slug + category to a filesystem path. `_db.py` is the *only* place that opens SQLite connections. `_rules.py` holds R-* constants (banned phrases, caps, thresholds). `_anti_cliche.py` is the single phrase registry.

**Layer 2 — Domain (pipeline concepts).** Knows *what* the pipeline does but not *how* a specific phase runs. `_archetypes.py` resolves a book's meta.yml to an Archetype object. `_doctrinal.py` enforces tradition-adjacency and Imam-numbering checks via `tradition_adjacency.yml`. `_context_injection.py` is the single shared contract for any phase that injects external context (used by both 08b augmentation and the Augmenter).

**Layer 3 — Intelligence (cross-book learning).** `extractor.py` pulls atoms (Quran verses, hadith) from enriched chapter text. `librarian.py` dedupes and merges atoms into `knowledge.db`. `augmenter.py` returns top-K prior atoms relevant to a chapter, used by future books' authoring and audit prompts.

**Layer 4 — Authoring (per-piece content generation).** Splits the current 2,025-line `_authoring.py` into focused modules. Each module knows how to produce one kind of artifact (a framing, a source bundle, a capstone, a preface, an augmentation file). Archetype-aware: the same module behaves differently for PLAY-NOVEL vs ENCYCLOPEDIC.

**Layer 5 — Phases (PhaseHandler protocol).** One file per `Phase` enum entry. Each implements `run(bd: Path, ctx: PhaseContext) -> PhaseReport`. Phases are *substitutable*: any handler honoring the protocol can stand in for another. This is the L (Liskov) in SOLID.

**Layer 6 — Driver.** `orchestrate_book.py` shrinks from 2,280 lines to ≤ 400. It walks `PHASE_ORDER`, dispatches to the right handler, manages state.json, and surfaces heartbeat cards. No business logic.

**Line caps as code:** no file in `scripts/podcast/` exceeds 600 lines after the refactor. Enforced via a pre-commit hook + CI grep.

---

## Data Architecture

Three storage tiers, each with one job. None can substitute for another.

```mermaid
flowchart LR
    subgraph TIER1["Tier 1 — Per-Book Scratch (JSONL, git-tracked)"]
        S1[content/drafts/books/&lt;slug&gt;/<br/>_system/<br/>knowledge-atoms-scratch.jsonl]
        S2[content/drafts/books/&lt;slug&gt;/<br/>_system/<br/>orchestrator-state.json]
        S3[content/drafts/books/&lt;slug&gt;/<br/>chapters/*.txt]
        S4[content/drafts/books/&lt;slug&gt;/<br/>meta.yml]
    end

    subgraph TIER2["Tier 2 — Shared Knowledge Brain (SQLite)"]
        DB[(knowledge.db<br/>WAL mode<br/>JSON1 enabled)]
        T1[atoms]
        T2[book_metadata]
        T3[archetype_registry]
        T4[run_telemetry]
        T5[manual_review_queue]
        DB --- T1 & T2 & T3 & T4 & T5
    end

    subgraph TIER3["Tier 3 — Published Catalog (immutable)"]
        C1[content/published/books/&lt;slug&gt;/]
        C2[Audience-facing<br/>read-only]
    end

    subgraph EXPORT["Export (per-release snapshot)"]
        E1[content/knowledge-base/<br/>quran.jsonl · hadith.jsonl]
    end

    S1 -->|Librarian| DB
    S3 -->|Extractor| S1
    DB -->|on release| E1
    S4 -->|migrate_meta_yml.py| T2
    S2 -.->|periodic snapshot| T4
    TIER1 -->|publish_to_library.py| TIER3
```

**Tier 1 — Per-Book Scratch (JSONL, git-tracked).** Lives inside each book's draft folder. Git-diffable so humans can review every change in PRs. Per-book isolation = parallel book branches never conflict on scratch state.

**Tier 2 — Shared Knowledge Brain (SQLite + JSON1).** Single file at `content/knowledge-base/knowledge.db`. WAL mode for concurrent readers. JSON1 extension for flexible-schema fields (atom bodies, meta.yml snapshots). Backed up by copying the file. **Zero infrastructure** — SQLite ships with Python on every Mac.

**Tier 3 — Published Catalog (immutable).** What the audience reads. Populated only by `publish_to_library.py`. Never written-to except by that one script after gates G1-G12 pass.

**Export layer.** On every release to `develop`, `knowledge.db` snapshots out as JSONL into `content/knowledge-base/quran.jsonl` etc. The JSONL is the grep-friendly audit trail and the disaster-recovery fallback.

### Knowledge.db schema (ER view)

```mermaid
erDiagram
    atoms ||--o{ atoms_sources : "1:N (cross-book provenance)"
    atoms ||--o{ atoms_variants : "1:N (translation variants)"
    atoms {
        text id PK "quran:2:255 · hadith:bukhari:1"
        text type "quran | hadith | term | citation"
        json body "type-specific schema (JSON1)"
        text first_seen_book FK
        text first_seen_chapter
        date first_seen_date
        real confidence "0.0 - 1.0"
        datetime created_at
        datetime updated_at
    }
    atoms_sources {
        text atom_id FK
        text book_slug FK
        text chapter_id
        text locator "heading or para#"
    }
    atoms_variants {
        text atom_id FK
        text book_slug FK
        text text_en
        text translator
    }
    book_metadata {
        text slug PK
        text category "books | lectures | ..."
        text archetype "scholarly-deep-dive | play-novel | ..."
        json meta_yml "full meta.yml snapshot"
        text current_phase
        text phase_status
        datetime last_updated
    }
    archetype_registry {
        text slug PK
        text spec_yml
        text exemplar_md
        text anti_patterns_md
        datetime updated_at
    }
    run_telemetry {
        text run_id PK
        text book_slug FK
        text phase
        datetime started_at
        datetime finished_at
        real cost_usd
        int atoms_extracted
        text status
    }
    manual_review_queue {
        int id PK
        text book_slug FK
        text chapter_id
        text reason
        json payload
        datetime created_at
        datetime resolved_at
        text resolution
    }
    atoms ||--o{ run_telemetry : "extracted in run"
    book_metadata ||--o{ run_telemetry : "tracks per-phase"
    book_metadata ||--o{ manual_review_queue : "items needing human"
```

### Why SQLite, not Postgres-via-Docker

SQLite ships built-in with Python on every Mac. Zero install. Single-file backup. The `_db.py` module hides SQLite behind a SQLAlchemy ORM so the Wave 2 migration to Postgres + pgvector (when semantic embeddings join) is a one-time script, not a rewrite. Docker stays out of the v1 dependency story. Run on any Mac means *clone, run, works*.

---

## The Backbone — Pipeline Phases as Stations

Every book follows the same backbone. What happens at each station depends on the book's archetype (resolved at `08a-archetype-resolve`).

```mermaid
flowchart LR
    subgraph INGEST["Wave 0 · Ingest & Refine"]
        P01[01<br/>preflight] --> P02[02<br/>branch] --> P03[03<br/>scaffold] --> P04[04<br/>ocr-translate] --> P05[05<br/>refine-english] --> P06[06<br/>phonetics]
    end

    subgraph DESIGN["Wave 1 · Design & Enrich"]
        P07[07<br/>chapter-design] --> P08[08<br/>enrichment] --> P08a{{08a<br/>archetype-resolve}}
        P08a --> P08b[08b<br/>augmentation<br/>archetype-gated]
        P08a --> P08c[08c<br/>knowledge-extract]
        P08b --> P08c
    end

    subgraph AUTHOR["Wave 2 · Author & Audit"]
        P09[09<br/>series-plan] --> P10[10<br/>register-series] --> P11[11<br/>per-chapter]
        P11 --> P11b[11b<br/>slide-decks]
        P11b --> P0g[0g<br/>dual-auditor]
    end

    subgraph SHIP["Wave 3 · Train & Ship"]
        P12[12<br/>trainer] --> P13[13<br/>merge] --> P14[14<br/>done]
    end

    P06 --> P07
    P08c --> P09
    P0g --> P12

    style P08a fill:#fef3e2
    style P08b fill:#e8f5e9
    style P08c fill:#fce4ec
```

**The three new phases.** `08a-archetype-resolve` is a decision-only step: it reads `meta.yml.archetype` and configures the downstream phases. `08b-augmentation` writes modern-research markdown files (archetype-gated — default-on for encyclopedic, opt-in for scholarly + lecture-series, never for play-novel + aphorism). `08c-knowledge-extract` is the Extractor+Librarian phase that captures Quran/hadith atoms from the enriched chapter source AND from any 08b augmentation output.

**Why letter suffixes (08a/08b/08c).** Preserves numeric phase ordering for resume/state.json compatibility. Mirrors the existing `11b-slide-decks` precedent. No phase renumbering required — existing books on disk continue to resume cleanly.

---

## The Intelligence Layer — Three-Piece Architecture

Cross-book learning. Each piece does one thing well.

```mermaid
flowchart LR
    SRC[Enriched chapter source<br/>+ 08b augmentation .md] --> EXT
    EXT[Extractor<br/>scripts/podcast/intelligence/extractor.py<br/>≤ 300 lines<br/>structured-output Claude Sonnet]
    EXT --> SCRATCH[knowledge-atoms-scratch.jsonl<br/>per-book, git-tracked]
    SCRATCH --> LIB[Librarian<br/>scripts/podcast/intelligence/librarian.py<br/>≤ 250 lines<br/>pure Python no LLM]
    LIB --> DB[(knowledge.db)]
    LIB -->|conflicts halt phase| MRQ[manual_review_queue]
    DB -.->|future books only| AUG[Augmenter<br/>scripts/podcast/intelligence/augmenter.py<br/>≤ 250 lines<br/>regex + top-K injection]
    AUG -->|08-enrichment 200t<br/>11-per-chapter 500t<br/>0g-audit 800t| AUTH[future-book prompts]
    AUG -.->|gated by series.enable_knowledge_augmenter<br/>default false until G12| AUTH
```

**Extractor.** Reads enriched chapter text + 08b augmentation output. Emits atoms with canonical IDs (`quran:2:255`, `hadith:bukhari:1234`). Cost cap: $0.10/chapter, $10/book ceiling. Confidence < 0.7 auto-flags for manual review.

**Librarian.** No LLM. Exact-match canonical ID dedup. Three outcomes per atom: *new* (insert), *variant* (different translation → append to variants[]), *conflict* (different `text_ar` or different hadith grade → halt phase, write to `manual_review_queue`). Resume requires `resolve_conflicts.py`.

**Augmenter.** Helper called from FUTURE books' prompts. Wave 1 implementation is regex citation-scan + exact-ID lookup; Wave 2 adds semantic ranking. Token-budgeted (200/500/800 per call site). **Always strips `text_ar`** before injection — prevents Arabic script leak into phonetic-only chapter files. Always uses `_context_injection.format_provenance` neutral phrasing — prevents reactionary-praise priming.

**Default disabled** until the G12 acceptance gate fires green: Book N+1 must surface at least one challenger finding referencing an augmented atom. Until then, the flag stays `false` even though the code is shipped.

---

## Multi-Tier Capstone — Architectural Recursion

For dense philosophical books and the encyclopedic archetype, capstones layer recursively. Each tier reads ONLY the layer immediately below it.

```mermaid
flowchart BT
    CH[Chapter sources · Tier 0] --> PART1[Part-1 capstone] & PART2[Part-2 capstone] & PARTN[Part-N capstone]
    PART1 & PART2 & PARTN --> T1[Tier-1 Jāmiʿa<br/>book-level synthesis<br/>≤ 25 min]
    T1 --> T2[Tier-2 Jāmiʿat al-Jāmiʿa<br/>kernel distillation<br/>≤ 12 min · ≤ 50% of T1]

    style CH fill:#f5f5f5
    style T1 fill:#fff3e0
    style T2 fill:#fce4ec
```

**The invariant (locked):** tier-2 reads tier-1 plus chapter abstracts (~200 words/ch). Tier-2 NEVER reads chapter sources directly. If postprod-review surfaces a chapter-scope doctrinal correction, tier-1 must absorb it into its own output BEFORE tier-2 sees anything. This prevents kernel principles from inheriting un-synthesized chapter content. Enforced by `_authoring/capstone.py` source_assembly module — raises `CrossTierRead` on violation.

**Five capstone modes** in `meta.yml.capstone_mode`:
| Mode | Used by | Structure |
|---|---|---|
| `none` | play-novel, aphorism-collection | No capstone (preface bookends close the arc; aphorisms self-distill) |
| `single` | scholarly-deep-dive medium, lecture-series | Tier-1 only |
| `single_plus_distillation` | scholarly-deep-dive deep (≥ 12 ch) | Tier-1 + Tier-2 |
| `per_part_and_single` | encyclopedic-epistolary medium | Per-part capstones + Tier-1 |
| `full_brethren` | encyclopedic-epistolary deep (Rasāʾil) | Per-part + Tier-1 + Tier-2 |

---

## Content Archetypes — Extensibility Seam #1

Seven archetypes registered on disk at `content/_shared/archetypes/<slug>/`. Each has `exemplar.md`, `spec.yml`, `anti-patterns.md`. The `_archetypes.py` registry module resolves `meta.yml.archetype` to an Archetype object.

```mermaid
flowchart LR
    subgraph CHOICES["Per-book choice at intake"]
        BOOK[meta.yml.archetype]
    end

    subgraph SEVEN["Seven archetypes (v1)"]
        SDD[scholarly-deep-dive<br/>KaR · Asaas · Rahat al-Aql]
        PN[play-novel<br/>Master & Disciple]
        LS[lecture-series<br/>Kunooz Al-Hikmah]
        AC[aphorism-collection<br/>Ayyuhal Walad]
        NP[narrative-prose<br/>future novels]
        EE[encyclopedic-epistolary<br/>Rasāʾil Ikhwān al-Ṣafāʾ]
        SD[socratic-dialogue<br/>alias of play-novel]
    end

    BOOK --> SDD & PN & LS & AC & NP & EE & SD

    subgraph BEHAVIOR["Drives phase behavior"]
        PRE[preface required?]
        CAP[capstone_mode]
        AUG[augmentation default?]
        DIA[diagram_density]
        PHA[phased_rollout?]
        PRS[pre-synthesis required?]
    end

    SEVEN --> BEHAVIOR
```

**How to add an 8th archetype** (extensibility recipe):
1. Create `content/_shared/archetypes/<new-slug>/{exemplar.md, spec.yml, anti-patterns.md}`.
2. Register in `_archetypes.py` `KNOWN_ARCHETYPES` tuple.
3. Add invariants to `spec.yml` (preface required, capstone mode, augmentation default, etc.).
4. If the archetype needs phase-level changes, add an `if archetype.slug == "..."` branch in the affected phase handler. Most archetypes don't need this — they configure existing phases via meta.yml fields.

The registry is **content-as-config**: a new archetype is three markdown/yaml files, not three Python files.

---

## Agent Ecosystem

Nine agents collaborate on different surface areas, organized into two strata: **tactical agents** (single-purpose, fire-and-finish — orchestrator, challenger, auditor, trainer, blueprint, extract, publisher, vacuum, postprod-review, slide-deck-challenger) and a **strategic coordinator** (`project-steward`) that composes the tactical agents under a fixed four-pass protocol and a cited source corpus. The steward never reimplements a tactical check; it invokes the right tactical agent for the scope and interprets findings against the corpus.

```mermaid
flowchart TB
    USER[Asif]
    USER -->|/steward scope| STEW[project-steward<br/>strategic coordinator<br/>composes + cites]
    USER -->|/podcast| ORCH[podcast-orchestrator<br/>drives the backbone]
    USER -->|/extract| EXT[podcast-extract<br/>single-chapter NotebookLM bundle]
    USER -->|/publish| PUB[podcast-publisher<br/>drafts/ → published/]

    ORCH -->|after authoring| CHAL[podcast-challenger<br/>per-chapter validator]
    CHAL -->|writes findings| LEDGER[_learning/findings.jsonl]
    LEDGER -->|after N books| TRAIN[podcast-trainer<br/>cross-book pattern learner]

    ORCH -->|on every merge to develop| AUDIT[podcast-auditor<br/>holistic regression sweep]
    ORCH -->|optional gate| BLUE[podcast-blueprint<br/>content-aware episode planner]

    USER -->|post-NotebookLM| POST[postprod-review<br/>identify-only after recording]
    POST -->|surfaces vacuum plan| VAC[vacuum<br/>file-naming + folder mutation]

    ORCH -->|deck convergence| SCHA[slide-deck-challenger<br/>visual integrity loop]

    STEW -.->|composes| AUDIT
    STEW -.->|composes| RS[repo-surgeon<br/>skill]
    STEW -.->|composes| REC[reconcile<br/>skill]
    STEW -.->|reads| CORPUS[reference/steward-source-corpus.md<br/>cited bibliography]
```

**Read/write contracts:**
- `podcast-orchestrator` — reads everything; writes orchestrator-state.json, ledgers, branches.
- `podcast-challenger` — reads chapter + framing + handbook; writes findings.jsonl + per-chapter report. Never edits content.
- `podcast-auditor` — reads everything; writes audit report. Never edits.
- `podcast-trainer` — reads findings.jsonl across books; proposes spec edits + commits them only if regression suite passes.
- `vacuum` — reads file tree; mutates filenames + folder structure (Tier 1).
- `postprod-review` — identify-only audit after audio + transcripts arrive.
- `project-steward` — reads git state + active plan + composed-agent reports; writes structured prioritized findings (P0–P3 + low-hanging fruit + pushback) cited to entries in `reference/steward-source-corpus.md`. Never edits source files; the corpus itself is the only writable surface and only as Tier 2.

---

## External Integrations

```mermaid
flowchart LR
    subgraph PIPELINE["podcast-factory"]
        INGEST[Phase 04 OCR/Translate]
        REFINE[Phase 05 Refine]
        ENRICH[Phase 08 Enrich + 08b Augment]
        EXTRACT[Phase 08c Knowledge Extract]
        AUTHOR[Phase 11 Authoring]
        AUDIT[Phase 0g Audit + Challenger]
        SLIDES[Slide-deck classifier]
    end

    subgraph CLAUDE_API["Claude API (max-subscription, no Anthropic key)"]
        SONNET[Sonnet 4.6]
        OPUS[Opus 4.7]
        HAIKU[Haiku 4.5]
        VISION[Claude Vision]
    end

    subgraph AZURE["Azure"]
        DOCINTEL[Document Intelligence<br/>PDF → text]
        TRANS[Translator<br/>ar/ur → en]
        SPEECH[Speech-to-Text<br/>ur-PK locale]
    end

    subgraph GEMINI["Gemini (paid AI Studio key)"]
        GEM[Gemini 1.5 / 2.0]
        GVISION[Gemini Vision]
    end

    subgraph NLM["NotebookLM (browser-driven)"]
        DEEP[Deep Dive]
        DEBATE[Debate]
        SLIDEGEN[Slide deck generation]
    end

    INGEST --> DOCINTEL
    INGEST --> TRANS
    REFINE --> SONNET
    ENRICH --> SONNET
    EXTRACT --> SONNET
    AUTHOR --> SONNET & OPUS
    AUDIT --> SONNET & GEM
    SLIDES --> VISION
    SLIDES --> GVISION
    AUTHOR -->|framing.txt + source bundle| NLM
    NLM -->|audio + transcript + slides| AUTHOR
```

**Anthropic API key** — NOT in keychain. Pipeline calls Claude through Asif's max-subscription via `claude login` (zero per-token cost beyond subscription).

**Gemini** — paid AI Studio key in keychain (`gemini_api_key`). Used by `audit_bundle_gemini.py` (cheap second-opinion auditor) and by the rich-diagram classifier fallback.

**Azure** — `journal-speech` (S0, $1/audio-hour), `journal-translator`, `journal-docintel`. All provisioned via `infra/azure/`.

---

## Branch + Content Lifecycle

```mermaid
flowchart LR
    INTAKE[intake_book.py<br/>creates branch] --> BRANCH[book/&lt;slug&gt;]
    BRANCH --> ORCH[orchestrate_book.py<br/>runs backbone]
    ORCH --> FINALIZE[Phase 13 finalize<br/>halt-and-surface]
    FINALIZE --> REVIEW{Asif review<br/>+ NotebookLM<br/>+ postprod}
    REVIEW -->|approve| PUB[publish_to_library.py<br/>drafts → published]
    PUB --> MERGE[orchestrator merges<br/>book/slug → develop]
    MERGE --> DEV[develop]
    DEV -->|Asif explicit approval| MAIN[main]
    MERGE -.->|hook re-invokes<br/>Librarian if knowledge.db<br/>touched on both branches| KB[(knowledge.db on develop)]
```

**Branch policy.** Every content unit gets a typed branch off `develop`: `book/<slug>`, `doc/<slug>`, `lecture/<slug>`, `article/<slug>`, etc. The prefix-map lives in `scripts/podcast/_branching.py`. After publish, the orchestrator merges the typed branch to `develop` with `--no-ff`. `develop → main` requires Asif's explicit approval.

**Concurrent book branches + the knowledge brain.** Two books in flight on parallel branches may both write to `knowledge.db`. On the second branch's merge, a `post-merge` git hook re-invokes Librarian if both branches touched `knowledge.db`. Manual conflict resolution if the same atom was added independently on both sides.

---

## The SPA & Design System

The plan folder gains a Single Page Application at `_workspace/plan/index.html`. One shell; multiple sub-apps; shared CSS theme tokens. Built in **Astro** to match the existing Podcast Factory Astro Site (`plan-dashboard/`) stack — shared design tokens, shared component primitives, single source of truth for typography and color.

```mermaid
flowchart TB
    SHELL[_workspace/plan/index.html<br/>SPA shell · routing · theme provider]

    subgraph SUBAPPS["Sub-apps (v1 + roadmap)"]
        PLAN[/plan<br/>v1: roadmap viewer<br/>renders refactor/plan.md/]
        ARCH[/architecture<br/>v1: this document<br/>with live Mermaid + decision records/]
        DASH[/dashboard<br/>v1: live progress<br/>reads refactor/progress.json<br/>+ run_telemetry from knowledge.db/]
        BACKBONE[/backbone<br/>v1: pipeline visualization<br/>interactive backbone with<br/>module-plug-in animation/]
        DEBT[/debt<br/>future: pipeline-debt browser<br/>F-item status by phase/]
        BOOKS[/books<br/>future: per-book progress<br/>current phase · cost · gates/]
    end

    subgraph THEME["Shared design system (_workspace/plan/spa/)"]
        TOK[design-system/tokens.css<br/>color · type · spacing]
        COMP[components/<br/>card · table · diagram-frame · metric-tile]
        ROUTE[routing.md<br/>add a sub-app recipe]
    end

    SHELL --> SUBAPPS
    SUBAPPS -.->|imports tokens + components| THEME
    DASH -.->|fetches| LIVE[knowledge.db<br/>via lightweight read API<br/>or static JSON snapshot]
    BACKBONE -.->|reads| YAML[refactor/plan.yaml]
```

**Design system tokens** (CSS custom properties): `--c-bg`, `--c-text`, `--c-accent`, `--c-warn`, `--c-success`; `--type-serif`, `--type-sans`, `--type-mono`; `--space-xs..xl`; `--radius-sm..lg`. Shared across the plan SPA AND the reader section AND any future sub-app of the Podcast Factory Astro Site (catalog browser, transcript editor, knowledge-base explorer, etc.).

**Adding a new sub-app** (extensibility recipe): drop a route under `_workspace/plan/src/pages/<sub-app>/index.astro`, import design tokens, register in `routing.md`. Theme inherits automatically.

**Live data for the dashboard.** Two options the plan picks between:
1. **Static snapshot** — `refactor/progress.json` + `run_telemetry_snapshot.json` regenerated on every push by a tiny script. Zero runtime infra. Recommended for v1.
2. **Read-only API** — a small Astro server endpoint reading `knowledge.db` live. Requires Astro server mode + filesystem access. Reserved for v2 if real-time becomes a need.

---

## Annotation Intelligence Handoff

The chapter reader now includes a right-rail annotation workspace as a first-class operational lane. Paragraph hover selects context; all edits happen in the rail. This avoids floating overlays on text while preserving rapid classification flow.

The lane has two persistence levels:

- **Fast lane (session speed):** local queue in browser storage, capturing marker and action intent in order.
- **Durable lane (cross-session + automation):** chapter-scoped JSON handoff at `content/drafts/<category>/<slug>/_system/annotation-intelligence/<chapter>.json` containing markers, notes, queue items, and one combined instruction block ready for assistant execution.

This contract makes annotation output reusable by Copilot, Claude Code, Cowork sessions, and future pipeline automation without needing UI state reconstruction.

---

## Decision Records (ADRs)

Compact list of architectural decisions and why. Future Claude sessions and reviewers consult this list first when something feels arbitrary.

| ID | Decision | Why | Date |
|---|---|---|---|
| DR-001 | **SQLite + JSON1 for v1; Postgres + pgvector at Wave 2** | Mac portability beats infrastructure power for v1. Migration path via SQLAlchemy. | 2026-05-26 |
| DR-002 | **Tier-2 capstone NEVER reads chapter-scope material** | Recursion invariant. Tier-1 absorbs chapter corrections; tier-2 sees only tier-1. | 2026-05-26 |
| DR-003 | **Per-content-type typed branch policy** | `book/`, `doc/`, `lecture/`, `article/`. Single prefix-map in `_branching.py`. | 2026-05-24 |
| DR-004 | **Letter-suffix phase IDs (08a/08b/08c)** | Preserves numeric ordering for resume. Mirrors existing `11b-slide-decks`. | 2026-05-26 |
| DR-005 | **Every `scripts/podcast/` file ≤ 600 lines** | Forces modularization. Enforced by pre-commit + CI. | 2026-05-26 |
| DR-006 | **architecture.md is independent of `docs/architecture/index.html`** | This doc is timeless design; the HTML is a generated dashboard. Different lifecycles. | 2026-05-26 |
| DR-007 | **Augmenter default-disabled until G12 fires green** | A/B acceptance gate prevents shipping a flywheel that doesn't actually change outputs. | 2026-05-26 |
| DR-008 | **Per-book scratch stays JSONL, not SQLite** | Git-diffability for human PR review. SQLite holds merged canonical state. | 2026-05-26 |
| DR-009 | **No version stamps in tracked files** | The git history IS the version log. Pre-commit hook rejects `Version: \d` and `*v[0-9]*.md`. | 2026-05-26 |
| DR-010 | **Astro for the plan SPA + design tokens shared across the Podcast Factory Astro Site** | One stack, one theme, no duplicate UI primitives. | 2026-05-26 |
| DR-011 | **Cross-tradition guard via `tradition_adjacency.yml`** | Brethren-of-Purity vs orthodox-Ismaili requires structural prevention, not authoring judgment. | 2026-05-26 |
| DR-012 | **Augmenter strips `text_ar` before injection** | Prevents Arabic script leak into phonetic-only chapter files (violates R-PHONETICS-OUT). | 2026-05-26 |
| DR-013 | **Retroactive enhancements for shipped books = addendum-only** | Never re-run the pipeline against KaR, M&D, Ayyuhal Walad, etc. New episodes ship as addenda. | 2026-05-26 |
| DR-014 | **Strategic-tactical agent split: steward composes, doesn't reimplement** | `project-steward` sits above the tactical agents (orchestrator, auditor, challenger, vacuum, etc.). It composes them by scope rather than duplicating their checks. Every recommendation is bound to a `reference/steward-source-corpus.md` entry; unsourced claims are flagged `[unsourced]`. Prevents agent-sprawl and keeps strategic prioritization out of pipeline scripts. | 2026-05-26 |
| DR-016 | **Annotation output must persist as both queue and chapter handoff file** | Local queue keeps interaction fast; chapter JSON makes intent durable and machine-readable for assistant sessions and automation. | 2026-05-27 |

---

## What's NOT in This Document

- **Execution sequence + timelines** — see `refactor/plan.md`.
- **Live system state, metrics, in-flight books** — see `_workspace/plan/index.html` dashboard.
- **F-item operational backlog** — see `_workspace/plan/debt/pipeline-debt.md`.
- **Per-book ship checklists** — see `_workspace/plan/operations/per-book-ship-checklist.md`.
- **Day-to-day standing rules + response conventions** — see `_workspace/plan/conventions/`.
- **The 12-task postprod-vacuum sub-plan currently in flight** — see `_workspace/plan/postprod-vacuum-tasks.md` (folds into refactor Step C2 retroactive M&D work).
