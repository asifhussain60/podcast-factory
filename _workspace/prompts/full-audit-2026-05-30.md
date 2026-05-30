# Full Repo Audit — 2026-05-30
*Architect + Senior Engineer review. Four parallel audit streams. Synthesized here as single source of truth.*
*Status: AWAITING APPROVAL before execution*

---

## SECTION A — Critical / Security (fix before any build)

### A1. Plaintext database password in source control
**File**: `tools/source_extractor/db.py` lines 10–11
```python
CONTAINER = "wisdom-mssql"
PASSWORD = "Kashkole_Local_2026!"
```
**Impact**: Credential in git history; rotation breaks all three remote DB queries.
**Fix**: Move to Mac Keychain (`security find-generic-password -s wisdom-mssql -w`). Same pattern as `gemini_api_key`. Update `db.py` to call `keychain_get("wisdom-mssql")`.

### A2. mirror.db missing — pipeline crashes on Docker unavailability
**Issue**: `source_library_mirror.py` builds a local SQLite FTS5 mirror of KQUR + KASHKOLE + KSESSIONS. The mirror file (`content/knowledge-base/mirror.db`) does not exist. All searches currently hit SQL Server via `docker exec` subprocess calls. If Docker is unavailable → immediate `CalledProcessError` crash, no graceful degradation.
**Fix**: Auto-build mirror on first `source_library_queries` import if absent, OR document as a one-time setup step in `docs/setup/` with a health check gate.

### A3. No Gemini API retry on rate-limit
**File**: `scripts/podcast/gemini_refine.py` lines 50–60
**Issue**: Bare `urllib.request.urlopen` — no retry on HTTP 429 / 500. Mid-book rate-limit → phase crash → requires manual `--retry-phase`. Azure OCR path has proper backoff; Gemini path does not.
**Fix**: Add exponential backoff helper (max 3 retries, 2×/4×/8× seconds) around the `urlopen` call. Mirror the pattern in `scripts/podcast/_azure.py`.

---

## SECTION B — Content Folder Restructure

### B1. Current confusion
`content/drafts/` and `content/published/` are folder names that imply status-as-path. `content/published/` is empty (never populated; `publish_to_library.py` was designed to write there but nothing does). Three books still live in a legacy nested `content/drafts/BOOKS/<slug>/` tree rather than the canonical flat `content/drafts/books/<slug>/` tree.

### B2. Proposed flat structure (status as metadata, not folder name)
```
content/
  books/
    <slug>/
      meta.yml       ← status: draft | published (NEW field)
      _system/
      _stages/       (where applicable)
      chapters/
      episodes/
      slide-decks/
      ...
  lectures/
    <slug>/
      meta.yml
  asbaaq/
    <slug>/
  _shared/
    archetypes/
  knowledge-base/
```
All scripts iterate `content/books/*/` once. No more dual-tree fallback. `publish_to_library.py` writes `meta.yml status: published` instead of moving files.

### B3. Migration steps
| Step | Action | Risk |
|---|---|---|
| B3a | Move `content/drafts/BOOKS/kitab-al-riyad/` → `content/books/kitab-al-riyad/` | Low — _paths.py handles both |
| B3b | Move `content/drafts/BOOKS/the-master-and-the-disciple/` → `content/books/the-master-and-the-disciple/` | Low |
| B3c | Move `content/drafts/BOOKS/asaas-al-taveel/` → `content/books/asaas-al-taveel/` | Low |
| B3d | Move all `content/drafts/books/<slug>/` → `content/books/<slug>/` | Low |
| B3e | Move `content/drafts/lectures/`, `content/drafts/asbaaq/` → `content/` root | Low |
| B3f | Update `_paths.py`: replace DRAFTS_ROOT/PUBLISHED_ROOT with single BOOKS_ROOT | Medium — touch 1 file, all downstream auto-resolves |
| B3g | Update `publish_to_library.py`: write `meta.yml status: published` instead of file move | Medium |
| B3h | Update `cross_book_dashboard.py`: walk `content/books/*/` | Low — 1 line |
| B3i | Update plan-dashboard pages that read content paths | Medium — 3–4 pages |
| B3j | Remove `content/published/` stub directory | Low (after migration) |
| B3k | Remove legacy BOOKS/ fallback from `_paths.py` after migration confirmed | Low |

### B4. Additional content questions to resolve
- Should `_shared/archetypes/` stay under `content/` or move to a top-level `archetypes/` dir? (Recommend: stay in `content/_shared/` — it's content, not code)
- Should `content/knowledge-base/` move to `data/knowledge-base/` since it's a DB, not content? (Recommend: keep under `content/` for now; Wave 2 migration to Postgres removes this ambiguity)

---

## SECTION C — _Workspace Cleanup

### C1. Files to DELETE (stale / folded into plan)
| File | Reason |
|---|---|
| `_workspace/prompts/improvements/01-reader-into-site.md` | Folded into spec 07 (site redesign) |
| `_workspace/prompts/improvements/02-ynab-and-memory-flush.md` | Executed; no further reference |
| `_workspace/prompts/improvements/09-source-intake-decisions.md` | Summary; full decisions in plan.yaml |
| `_workspace/plan/research/2026-05-19-redesign-audit-from-air.md` | Superseded by architecture.md |
| `_workspace/plan/research/2026-05-19-redesign-proposal-from-air.md` | Merged into plan.yaml |
| `_workspace/plan/research/findings.md` | Folded into architecture.md + plan.md |
| `_workspace/plan/research/podcast-best-practices.md` | Reference only; git history preserves |
| `_workspace/wisdom-brief.md` | Folded into architecture.md §Intelligence Layer |
| `_workspace/architecture/podcast-factory-architecture.html` | Superseded by plan-dashboard/ |

### C2. Files to ARCHIVE (history, not active)
| File | Action |
|---|---|
| `_workspace/prompts/improvements/08-source-intake-discussion.md` (1,667 lines) | Move to `_workspace/audit/_archive/2026-05-30/` — locked decisions already in plan.yaml (D1–D18) |

### C3. Files to KEEP (live specs, ledgers, pilots)
`00-audit-findings.md`, `03-wisdom-corpus-merge.md`, `04-mcp-blackbox-annotation-engine.md`, `05-intelligence-podcast-integration.md`, `06-ayyuhal-walad-annotation-prompt.md`, `07-site-redesign-spec.md`, `10-reader-redesign-decisions.md`, `_tasklist.md`, `master-disciple-recommendations.md`, `notebooklm-diagram-pilot-findings.md`, `postprod-vacuum-review.md`, `postprod-vacuum-tasks.md`

---

## SECTION D — Agent / Skill Sprawl

### D1. Broken agent references (fix)
| File | Issue | Fix |
|---|---|---|
| `infra/claude-agents/docs-updater.md` | Target `docs/architecture/index.html` deleted 2026-05-28 | Archive spec to `_workspace/audit/_archive/2026-05-30/`; delete `infra/` entry; update `.github/agents/docs-updater.agent.md` stub to point to archived path |
| `.github/agents/reconcile.agent.md` | Target `infra/claude-agents/reconcile.md` never created | Delete stub — reconcile work tracked in plan.yaml Wave I; no standalone agent needed |

### D2. Cosmetic fixes (low risk)
| File | Fix |
|---|---|
| `skills-staging/repo-surgeon/skill.md` | Rename → `SKILL.md` |
| `skills-staging/usage-auditor/skill.md` | Rename → `SKILL.md` |
| `_workspace/prompts/luum-onboarding-bootstrap.md` | Archive or document "luum" context; appears vestigial |

### D3. Stale remote branches
| Branch | Age | Action |
|---|---|---|
| `origin/archive/full-stack-pre-strip` | 23 days | Delete — explicitly labeled archive |
| `origin/backup/pre-restructure-2026-05-23-1849` | 7 days | Confirm then delete — documented backup, no outstanding checkouts |

---

## SECTION E — Intelligence Corpus Gaps

### E1. Corpus population: only 1 of 3 sources wired
**File**: `scripts/podcast/intelligence/populate_corpus.py` SOURCES list
**Current**: Only wisdom (Kashkole doctrine) ingested. Quran (6,236 verses from KQUR) and KSESSIONS (teaching session transcripts) slots are comments.
**Fix**: Wire ingest callables as part of B5 (already planned). Add `ingest_quran_kqur()` and `ingest_ksessions()` to SOURCES in the same B5 build pass.

### E2. Topic tag assignment near-zero (0.076 avg per atom)
**Issue**: 92% of doctrine atoms have zero topic tags. `wisdom_ingest_knowledge.py` assigns tags per-section only when that section has a `TopicTypeID` assignment. Most sections have `TypeID=0` (Unknown) → zero tags → atoms are undiscoverable by the augmenter.
**Fix**: Implement fallback tag assignment: when `TypeID=0`, apply binder-level doctrinal tags from the `BINDER_TAGS` map in `wisdom-intelligence-spec.md`. This lifts avg tags from 0.076 to ~3–5 per atom.

### E3. No FTS5 on knowledge.db atoms
**Issue**: Doctrine atoms in `knowledge.db` have no full-text search. The augmenter finds atoms only by topic tag match — cannot find by keyword.
**Fix**: Add FTS5 virtual table `fts_atoms(body_text, atom_id, type, tradition)` to `knowledge.db`. Schema migration 020. Populate on ingest. Query in augmenter as fallback when tag match returns zero results.

### E4. No unified cross-source search
**Issue**: Each source (Quran, topics, sessions) has isolated endpoints. Cannot search "tawil" across all atom types simultaneously.
**Fix**: Add `GET /search-multi?q=keyword&types=quran,hadith,doctrine&limit=20` to `source_library_server.py`. Fan out to FTS5 tables, merge results, rank by tradition affinity + relevance score.

### E5. Cross-type dedup not implemented
**Issue**: Same Quran verse can appear as a `type=quran` atom AND embedded in a `type=doctrine` atom body. No dedup strategy handles this.
**Fix**: Add cross-type dedup pass in `dedup_corpus.py`: after per-type dedup, scan doctrine atom bodies for Quran verse citations; mark them as `source_also: quran:<s>:<a>` rather than creating separate quran atoms.

---

## SECTION F — Astro Site Code Quality

### F1. Component size violations (DR-005: 300-line cap)
8 components violate the cap. Proposed splits:

| Component | Lines | Split into |
|---|---|---|
| `NarrativeScroll.tsx` | 1,126 | `NarrativeBlock.tsx` + `ScrollProgress.tsx` + `NarrativeScroll.tsx` (shell) |
| `ChapterEditor.tsx` | 787 | `EditorCore.tsx` + `EditorToolbar.tsx` + `ChapterEditor.tsx` (shell) |
| `DbArchitecture.tsx` | 710 | `EntityTable.tsx` + `RelationshipDiagram.tsx` + `DbArchitecture.tsx` (shell) |
| `AnnotationWorkbench.tsx` | 685 | `TagPalette.tsx` + `AnnotationInspector.tsx` + `AnnotationWorkbench.tsx` (shell) |
| `ParagraphAnnotationBar.tsx` | 524 | `AnnotationBar.tsx` + `TagButton.tsx` |
| `PipelineOverviewRail.tsx` | 438 | `PhaseCard.tsx` + `PipelineOverviewRail.tsx` (shell) |
| `PhaseSwimlaneDiagram.tsx` | 474 | `SwimlaneRow.tsx` + `PhaseSwimlaneDiagram.tsx` (shell) |
| `PipelineSpine.tsx` | 405 | `SpineNode.tsx` + `PipelineSpine.tsx` (shell) |

### F2. Inline styles (49 instances)
All `style="..."` attributes must move to external CSS or Tailwind `@apply` classes. Priority files: `AnnotationWorkbench.tsx`, `ContractView.astro`, `wisdom/index.astro`, `book-review/[slug].astro`.

### F3. DRY violations
| Duplication | Files | Fix |
|---|---|---|
| Quran verse ref parsing (SURAH_MAP + regex) | `StudioPoc.tsx` + `QuranPopover.tsx` | Extract to `lib/reader/quran-refs.ts` |
| Chapter path resolution | Multiple pages + API routes | Centralize in `lib/content-paths.ts` using `_paths.py` logic mirrored for frontend |

### F4. Hardcoded values
| File | Issue | Fix |
|---|---|---|
| `StudioPoc.tsx:15` | `const SLUG = 'ayyuhal-walad'` | Load from URL query param |
| `StudioPoc.tsx:19–25` | `CHAPTERS` array hardcoded | Load from `/api/studio/chapters?book=<slug>` |

### F5. Unused dependency
`@tanstack/react-query` v5 installed but not imported in any src/ file. Remove from `package.json`. (~580KB saved from bundle).

### F6. Pipeline scripts > 600 lines (DR-005)
| Script | Lines | Approach |
|---|---|---|
| `build_episode_txt.py` | 1,563 | Extract `_framing.py` (framing logic), `_validation.py` (output gate), `_assembly.py` (text assembly) |
| `extract_chapter.py` | 1,301 | Extract `_extract_phases.py` (per-phase handlers), `_extract_output.py` (bundle writer) |
| `tighten_source.py` | 1,051 | Extract `_source_passes.py` (individual tighten passes) |
| `run_wave.py` | 824 | Extract `_wave_runner.py` (execution loop), `_wave_reporter.py` (output) |
| `_slide_convergence.py` | 764 | Extract `_slide_checker.py` (per-slide validators) |
| `_slide_authoring.py` | 652 | Extract `_slide_templates.py` (slide type templates) |
| `publish_to_library.py` | 627 | Extract `_publish_gates.py` (G1–G7 gate implementations) |

### F7. Structured logging
516 `print()` calls in non-test production scripts. Add `logging` module with per-module loggers. Output to both stdout (INFO+) and `_system/logs/<phase>.log` (DEBUG+). Enables post-hoc diagnosis without re-running.

---

## SECTION G — Additional Questions Surfaced

These require answers before or during execution:

| # | Question | Recommended Default |
|---|---|---|
| G1 | CI/CD: Is there a GitHub Actions workflow? Audit found none. | Add `.github/workflows/test.yml` — run `pytest` + `npm run lint:views` on push to develop |
| G2 | Test coverage: Current count = unknown. What's the coverage % for critical paths (extractor, librarian, augmenter, _quality)? | Target: ≥ 80% for `scripts/podcast/intelligence/`; run `pytest --cov` to establish baseline |
| G3 | Concurrent books: Can two books be processed simultaneously? `knowledge.db` is shared. Is there write locking? | `_db.py` uses WAL mode (safe for concurrent reads), but write contention on `librarian.py` merges needs explicit transaction locking |
| G4 | Backup for `knowledge.db`: Single SQLite file, no backup strategy visible. | Add daily `cp knowledge.db knowledge.db.bak` in a cron hook or `SessionStart` hook |
| G5 | Rollback policy for failed book branches: If a book fails partway, what's the cleanup plan? | Document in `docs/runbooks/failed-book-cleanup.md` |
| G6 | Per-book cost cap: Existing cap is per-chapter ($0.10) and per-book ($10). Does this cover Azure transcription costs ($4.31 per book)? | Raise per-book cap to $25 or make it configurable per archetype |
| G7 | NotebookLM audio feedback loop: Can quality scores be updated after the audio is generated? | Not in scope for Wave 8; flag for Wave 9 |
| G8 | Mobile support for Studio editor: Is the editorial cockpit desktop-only by design? | Yes, per `10-reader-redesign-decisions.md` R-10 — document explicitly |

---

## MASTER TO-DO LIST (execution order)

### Phase 0 — Safety + Plan repair (no spend, ~2 hrs)
| # | Task | Tier | Risk |
|---|---|---|---|
| 0a | Move DB password to keychain in `tools/source_extractor/db.py` | T0 | Low |
| 0b | Fix `.github/agents/reconcile.agent.md` — delete broken stub | T0 | None |
| 0c | Archive `infra/claude-agents/docs-updater.md` → `_workspace/audit/_archive/` | T0 | None |
| 0d | Rename `skill.md` → `SKILL.md` for repo-surgeon + usage-auditor | T0 | None |
| 0e | Delete stale branch `origin/archive/full-stack-pre-strip` | T1 | Low |
| 0f | Confirm + delete `origin/backup/pre-restructure-2026-05-23-1849` | T2 (confirm first) | Low |

### Phase 0.5 — Workspace cleanup (~30 min)
| # | Task |
|---|---|
| 0.5a | Archive `08-source-intake-discussion.md` to `_workspace/audit/_archive/2026-05-30/` |
| 0.5b | Delete 8 stale workspace files (01, 02, 09 from improvements/; 3 from research/; wisdom-brief.md; architecture HTML) |
| 0.5c | Archive `_workspace/prompts/luum-onboarding-bootstrap.md` (clarify first) |
| 0.5d | Write this document as `11-full-audit-2026-05-30.md` (done: this file) |

### Phase 0.6 — Content folder restructure (~1 hr code, ~30 min migration)
| # | Task | Risk |
|---|---|---|
| 0.6a | Move 3 legacy-nested books from `content/drafts/BOOKS/` → `content/books/` | Low |
| 0.6b | Move all `content/drafts/books/<slug>/` → `content/books/<slug>/` | Low |
| 0.6c | Move lectures + asbaaq to `content/` root | Low |
| 0.6d | Update `_paths.py` — single BOOKS_ROOT, remove DRAFTS_ROOT/PUBLISHED_ROOT | Medium |
| 0.6e | Update `publish_to_library.py` — write `meta.yml status: published` | Medium |
| 0.6f | Update `cross_book_dashboard.py` + plan-dashboard pages | Low |
| 0.6g | Remove `content/published/` stub + legacy `content/drafts/BOOKS/` after migration | Low |
| 0.6h | Add migration entry to plan.yaml + regenerate snapshots | T0 |

*Then the existing 9 phases proceed (unchanged in substance):*

### Phases 1–9 (existing authorized plan)
*(See site-work-status.md for current phase table)*

### Phase 10 — Intelligence corpus hardening
| # | Task |
|---|---|
| 10a | Add FTS5 `fts_atoms` table to `knowledge.db` (schema migration 020) |
| 10b | Fix topic tag assignment in `wisdom_ingest_knowledge.py` — apply binder-level fallback tags when TypeID=0 |
| 10c | Add unified `/search-multi` endpoint to `source_library_server.py` |
| 10d | Add cross-type dedup pass in `dedup_corpus.py` |
| 10e | Build `mirror.db` OR add auto-build on first query |

### Phase 11 — Astro site + scripts code quality refactor
| # | Task |
|---|---|
| 11a | Remove `@tanstack/react-query` from `package.json` |
| 11b | Extract `lib/reader/quran-refs.ts` (DRY: Quran ref parsing) |
| 11c | Fix StudioPoc hardcoded slug + CHAPTERS array |
| 11d | Remove 49 inline styles → external CSS/Tailwind |
| 11e | Split 8 oversized components (NarrativeScroll, ChapterEditor, DbArchitecture, AnnotationWorkbench, ParagraphAnnotationBar, PipelineOverviewRail, PhaseSwimlaneDiagram, PipelineSpine) |
| 11f | Split 7 oversized pipeline scripts (build_episode_txt.py is the priority — 1,563 lines) |
| 11g | Add `logging` module to pipeline scripts (replace print() calls for structured output) |
| 11h | Add relevance sorting to `augmenter._fetch_doctrine_atoms` |
| 11i | Add file locking to `gemini_refine.py` cost ledger |
| 11j | Run red-green refactor loop: lint → fix → verify no regressions → repeat until clean |

### Phase 12 — CI/CD + test infrastructure
| # | Task |
|---|---|
| 12a | Add `.github/workflows/test.yml` (pytest + npm run lint:views on push to develop) |
| 12b | Establish test coverage baseline: `pytest --cov scripts/podcast/intelligence/` |
| 12c | Document rollback runbook: `docs/runbooks/failed-book-cleanup.md` |
| 12d | Add `knowledge.db` backup hook to SessionStart |

---

## Summary metrics

| Category | Files affected | Estimated effort | Spend |
|---|---|---|---|
| Security (0a, A3) | 2 | 30 min | $0 |
| Workspace cleanup | 10 deletions, 2 archives | 20 min | $0 |
| Content restructure | ~12 files + 5 books moved | 2 hrs | $0 |
| Agent sprawl | 5 files | 15 min | $0 |
| Intelligence corpus | 4 new features | 3 hrs | $0 |
| Astro code quality | 15+ components/pages | 6–8 hrs | $0 |
| Pipeline scripts refactor | 7 scripts | 4–6 hrs | $0 |
| CI/CD + tests | 3 new files | 2 hrs | $0 |
| **Total** | | **~20–22 hrs** | **~$0** |
