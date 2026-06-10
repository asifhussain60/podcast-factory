<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-10 (session 26 — /library/[slug] full tabbed-workspace redesign)

**Session 26 (book-detail redesign, Asif-approved option A):** /library/[slug]
rebuilt from a 4,000px seven-section scroll into a tabbed workspace:
compact hero (title + status chips: quality avg, pipeline phase, archetype),
sticky hash-routed tab bar (Overview/Binders/Episodes/Media/Audits/Source,
counts in pills; legacy anchors #meta/#audio/#slide-decks remapped in JS;
panels render server-side, JS collapses to active tab — no-JS still shows all).
Overview = fact grid (dl, not fake inputs) + Quality/Pipeline side cards +
compact red-tinted Archive row (Danger zone section removed). Binders = card
grid (chapter-number chip, humanized title, gauge score pill, icon'd meta,
session trays). Episodes/Audio/Audits/Source = .lib-asset-row (tinted icon
circle, humanizeFile() labels, right-aligned size·date). Pruned dead CSS:
lib-toolbar/lib-tab-link/lib-detail-head/lib-file-*/lib-meta-form/lib-field*/
lib-new-form/lib-peq-summary (verified unused repo-wide; index.astro keeps
lib-slug/lib-section-head/lib-card etc.). Visual-QA'd 1440+390, all six tabs,
empty states, legacy-hash deep link; lint:views clean, astro check 0 errors,
console clean. Follow-up same session: (a) meta fact values now pass through
simplifyTransliteration (lib/translit.ts — display-only ASCII, per the locked
ASCII rule); (b) source_pdf/source_audio render as icon'd basename links via
NEW endpoint src/pages/api/library/source.ts (client sends FIELD NAME only,
server re-reads the path from meta.yml, realpath-guarded to repo root;
file→link, dir→FOLDER badge, absent→MISSING badge). NOTE: all three books'
meta source paths point at repo-root raw/ which does NOT exist on this
machine (pre-restructure pointers) — UI honestly shows MISSING; verified the
live-link branch with a temp fixture (200 audio/mpeg), fixture deleted.
UNCOMMITTED on branch Islamic/the-master-and-the-disciple (in-flight book
branch — commit with care).
Preview-screenshot quirk found: scrolled captures paint blank in the occluded
preview window; workaround = temporarily display:none the sections above the
target, capture at scrollY=0, then reload.

**Session 25 (audit; committed to develop):** (see below)

**Session 25 (audit):** repo-wide audit found zero functional bugs. Site work was
dead-code-only: 31 unused imports/vars removed across 21 files (astro check
35 hints -> 4; the 4 survivors are intentional @deprecated category/stage
back-compat shims in library.ts / annotation-export.ts / archive.ts — leave them).
React.FormEvent -> React.SubmitEvent in NewContentForm. No rendering/CSS changes;
preview-smoked /, /studio, /intelligence, /library, /library/[slug], /architecture,
/db-schema, /corpus — all clean. Pipeline side: deleted orphaned knowledge/
{extractor,librarian}.py (augmenter.py kept — p2_3 conformance + JSONL fallback);
runbooks/skill-registry/CI triggers/agent specs de-drifted. NOT yet swept by
visual-QA: /library, /corpus, /about, /intelligence (carried over from session 24).

**Session 24 (later half):** single-select filter buttons (In Pipeline/Published/Up Next),
per-category --shelf-accent design system, volume badge, card blurbs, New-content
primary button, intake column balance (Editorial Defaults left, intake-card--grow),
mobile topnav spacer fix, NarrativeScroll hero plays on mount (trigger race fixed;
frozen anims in automation = occluded-window rAF throttling, not a bug), intake
dropdowns humanized via humanizeOption() (values stay raw pipeline tokens).
Visual-QA loop iteration 1 covered /studio (3 states, 2 viewports), /studio/new
(2 viewports), step page, home. NOT yet swept: /library, /corpus, /about,
/intelligence.

**BRANCH: `Islamic/asaas-al-taveel` — session 24 adds lifecycle filter chips to the Studio picker.**

**Session 24 work (Astro site only — no pipeline changes):**
  - Studio picker (`/studio`) now has three icon filter chips above the shelves:
    In the Works (default ON) / Up Next / Published. Default view shows only
    actively-worked books; batch-scaffolded Asas volumes 02-06 are hidden until
    the Up Next chip is toggled.
  - Classifier `classifyStatusBucket()` + `loadStatusBucket()` exported from
    `studio-pipeline.ts`: published status wins; no completed phase or only
    automated ingest/refine (<= 0b) = up-next; unknown-but-real phases
    (e.g. 0book-render) = in-the-works.
  - Cards carry `data-status` and are hidden server-side for non-default
    statuses (no flash); shelves with zero visible cards hide; shelf counts
    track visible cards. Chip toggle script guards against zero active filters.
  - lint:views clean; verified in preview (default 5 books, Up Next reveals 7,
    Published reveals 2, Fiction shelf hides/shows correctly).

**IN FLIGHT:** Vol 1 orchestrator is HALTED at `finalize` (last_completed_phase=per-chapter,
no orchestrator/watchdog PIDs alive) — waiting for Asif's publish review. No heartbeat needed.

**Session 23 work (Astro site only — no pipeline changes):**
  - System subnav consolidated 13 -> 8 (Overview, Architecture, Intelligence, Infrastructure,
    Security, Quality, Roadmap, About & Help). System map / Pipeline paths / Annotations fold
    under Architecture (deep-dive links in its hero); Pronunciation + Pre-Upload Review moved
    to the Studio domain (linked from the Studio picker header). site-nav.ts is the single edit point.
  - Roadmap page was rendering NO steps: dashboard-snapshot `waves` was emptied long ago and
    the regenerator never rebuilt it. regenerate-snapshots.py now rebuilds wave metadata from
    plan.yaml (dedup by id, steps-bearing entry wins, empty bands dropped). plan.astro lede
    is dynamic (59 steps / 12 waves).
  - Architecture page "0 LAYERS" stat: layers/modules/archetypes restored into
    architecture-snapshot.json from commit 98efddf (archived islr-mas-i entry dropped).
  - Quality page showed all zeros: baselines path fixed (_workspace/test-strategy/ ->
    _workspace/tests/); added a note that baselines are four-axis, live formula is K6 five-axis.
  - Stale docs fixed: about.astro (4-section IA, status-field publish semantics, Corpus labels),
    pipeline-paths.astro (_phonetics.md -> glossary.yml/inline exonyms; bucket branch naming).
  - Studio-language pass (Asif approved "B"): about.astro quick-start + FAQ rewritten from
    Workbench-first to Studio-first wording; one definitional Workbench mention kept
    (it survives as ?view=workbench inside Studio).
  - Gates: lint:views 0/0; html-view-challenger PASS (final run: 1 MUST fixed — quality.css
    reading-floor font size; advisories noted, no restyles). Full-sweep visual QA converged:
    13 System routes x 2 viewports, 0 overflow, 0 console errors.

**Session 22 work (commit cc73909):**
  - PHONETICS SURGERY COMPLETE (option A, Asif-approved): retired _phonetics.md windowed
    extraction, EP00 probe, listen-checklist, and the _bake_probe halt from phase 0c.
    Phase 0c slot kept (ordering test unchanged); now just runs glossary scaffold.
  - Phase 0d: removed _phonetics.md prerequisite gate + _phonetics.md authority reference
    from the worker prompt; replaced with exonym resolution rules inline.
  - Framing: _phonetics.md lookup replaced with English-exonym-first + plain-translit
    guidance in both the initial framing prompt and the compress-rewrite prompt.
  - _tts_sanitize.py: new sanitize_text_with_terms() wraps sanitize_text and
    auto-applies knowledge-base exonyms (Qabil->Cain, Israfil->Raphael, etc.) +
    inline book glosses per chapter — no manual pass per volume.
  - sanitize_chapter_for_tts.py: updated to use sanitize_text_with_terms; accepts
    --book-dir to mine inline glosses from refined-english.md.
  - Tests: 561 passed (2 deleted: the respelling-format validator tests). Green.
  - Branch: fast-forward merged wip/phonetics-removal -> Islamic/asaas-al-taveel;
    both pushed to origin. Worktree at ~/PROJECTS/pf-phonetics-wt can be cleaned up.

**OPEN (next session):**
  - Vol 1 is at finalize/halted: surface the NotebookLM upload table (4-column locked format)
    and proceed with manual review + episode uploads, then publish authorization.
  - Then: Vol 2..6 sequentially on same branch.
  - Worktree cleanup: `git worktree remove ~/PROJECTS/pf-phonetics-wt` (safe now that
    wip/phonetics-removal is on origin and merged into the content branch).
  - Post-merge repo-surgeon --scope podcast audit (required after pipeline changes).

**Pronunciation reality:** still imperfect in NotebookLM output. Fix at MANUAL REVIEW step
by replacing Arabic with English substitutions in the CHAPTER source. The chapter is the
dominant pronunciation control, not the framing block. term_render auto-applies known
exonyms/loanwords at sanitize time; residual terms need hand-editing at review.

---
_(prior status below)_

**Last updated:** 2026-06-08 (session 20 — teaching filter + phonetics cleanup + pipeline resume)

**BRANCH: `Islamic/asaas-al-taveel` — 14 commits. Push pending.**

**Session work completed (session 20 — 4 commits 8c70778 -> 18affff):**

Teaching-relevance filter, complete IPA cleanup, probe regenerated, pipeline resumed.

  - score_pronunciation_risk.py: reads body_starts_at_page from content-range.md and
    slices refined-english.md to that page before frequency counting. Strips 54,665 chars
    (39%) of front matter (editor intro + author preface pp. 1-32). Probe counts
    only body text (pp. 33-75). 28 terms remain unconfirmed.
  - _phonetics.md: all 73 remaining IPA rows converted to plain hyphenated stress guides
    (NAA-tiq, al-ZAA-hir, KAY-n, etc.). File is now fully IPA-free.
  - Probe + bundle regenerated: all 28 terms show clean phonetics.
  - Pipeline resumed past phase 0c halted into 0ci/0d/0e/0f.

**OPEN (next session):**
  - Pronunciation review: 28 terms remain unconfirmed. Upload EP00-pronunciation-probe
    bundle to NotebookLM, listen, use /pronunciation UI to confirm/correct.
    Then run apply_pronunciation_corrections.py to commit to library.
  - Pipeline status: check orchestrator state after 0ci/0d/0e complete.

**Last updated:** 2026-06-06 (session 16 — full repo hygiene + pipeline audit)

**BRANCH: `develop` — CLEAN. 6 commits ahead of origin. Push pending.**

**Session work completed (session 16 — 6 commits 0ee218f → 2632391):**

Full repo hygiene pass + LEARNING_DIR migration + production audit.

  - Hygiene commit: 29 tracked orchestrator log files removed from _workspace/reviews/;
    TurboScribe zip untracked (kunooz-al-hikmah); gitignore additions for
    content/**/*.zip + _workspace/reviews/archive/**/*.log.
  - LEARNING_DIR migration: `content/podcast/.skill/_learning` → `_learning/` in
    _rules.py + 9 other scripts; 112-entry old findings.jsonl merged into canonical
    _learning/findings.jsonl (129 total); health file git mv'd; 321 tests green.
  - knowledge.db untracked (31MB binary slipped into tracking; now correctly gitignored).
  - _learning/.gitignore added: fences patterns.md / proposals/ / promoted/ / archive/
    (runtime outputs); findings.jsonl + health/ remain tracked (persistent ledger).
  - Ayyuhal Walad pipeline state committed: all 4 framings, EP04 episode txt,
    challenger report, health-trend, orchestrator-state, cost-ledger, augment-ledger.
  - Production audit (repo-surgeon): phase registry COMPLETE, no tracked binaries, no
    stale path references, 321 tests green.

**BRANCH: `ayyuhal-walad` — PUBLISHED. Final commit (18c60c2). Ready to merge → develop.**

**Session work completed (session 15 — 4 commits 0288816 → 18c60c2):**

Complete Ayyuhal Walad podcast production and publish cycle.

  - 4 chapter/framing edits: pronunciation format (R-PRONUNCIATION-DOUBLE) fixed
    for all 4 episodes, meta-prose headers renamed in ch01 and ch02, ch02 opening
    paragraph made standalone.
  - Chapter renames: ch01a→ch01, ch02b→ch02 (letter suffixes blocked G2 gate).
  - Full v1 vs v2 vs v3 audio comparison via Whisper transcription (4×87M Whisper
    medium transcriptions). Found EP01 and EP02 had wrong content/framing in v2;
    EP01 re-run as v3, EP02 confirmed correct on second run.
  - All 4 m4a files renamed to canonical ch01–ch04-ayyuhal-walad.m4a.
  - Published: status=published in orchestrator-state.json + meta.yml; catalog
    appended; 9 files (PDF + 4 audio + 4 video) synced to Google Drive
    Podcast Library/Ayyuha al-Walad.
  - G7 regex fix: verdict_re now matches **Verdict (book-level):** shape from
    whole-book challenger reports (was silently returning verdict='unknown').
  - Tests: 321 passed, 1 skipped (unchanged).

**Session work completed (session 14 — 1 commit f1e64cc):**

Full five-pass repo-surgeon audit + P1 fixes + test suite green (21→0 failures).

  - `_book_illustrate.py`: per-section try/except around the LLM call so a
    single Gemini timeout/crash skips that section instead of aborting the phase.
  - `build_book_pdf.py`: committed the uncommitted session-13 Google Drive copy
    feature (was in working tree, never committed).
  - Test suite: 21 pre-existing failures resolved to 0:
    - `test_waves_chain.py`: _paths stub leaked into full suite via `sys.modules`
      — fixed with save/restore around `exec_module`.
    - `test_systemic_fixes.py`: phase pin updated (PHASES moved to `_progress.py`),
      HOST_A_ROLES_SCHOLAR checked in `_validators.py`, `_is_rule_example_line`
      import corrected to `_validator_constants`.
    - `test_intelligence_extractor.py`: `claude_caller` → `llm_caller` param rename.
    - `test_source_library_mirror.py`: mock `open_mirror` for no-mirror path tests.
  - Tests: 321 passed, 1 skipped.

Audit confirmed the following were ALREADY fixed (auditor false positives):
  - `build_book_pdf.py` preference for `book-illustrated.md` — present since session 13.
  - `publish_to_library.py --dry-run` mutation — fixed in session 9 (Wave 1, b435df3).

**Session work completed (session 13 — 1 commit 29faf2f):**

New `0book-illustrate` pipeline phase: LLM-generated teaching diagrams (flowchart/
mindmap/graph) embedded in the PDF reading edition. Claude analyses each chapter,
identifies philosophical concepts that benefit from visual structure, writes Mermaid
DSL, renders SVG via the existing Playwright renderer (already themed to editorial-
modern palette), and injects `<figure class="book-diagram">` blocks into
`book-illustrated.md`. The PDF renderer picks them up automatically.

  - `_progress.py`: added "0book-illustrate" to PHASES
  - `_book_illustrate.py`: new module (section split, LLM call, render, inject)
  - `render-mermaid.mjs`: `--book-dir=<path>` mode for book diagram rendering
  - `render-book-pdf.mjs`: HTML block pass-through + figure/figcaption CSS
  - `build_book_pdf.py`: prefers `book-illustrated.md` over `book.md` when present
  - `phases/book_driver.py`: wires illustrate between compose and render (non-blocking)
  - Ayyuhal Walad: 14 diagrams across 8 chapters; book.pdf 544KB / 70 pages.
  - Tests: 460 passed, 1 skipped.

**Session work completed (session 11 — 1 commit 0bcd27e):**

Holistic review (read-only survey via 3 parallel Explore agents), then critical
review of pipeline + site strategy. Two genuine gaps found and closed:

  - F25 apparatus table: `render_show_notes()` in `_extract_helpers.py` now reads
    `name-aliases.yml` and emits `## Name and Title Preservation Table` with one
    row per figure/book_title/concept_word. Category derived from YAML section
    (Person/Book Title/Concept Term) with optional `category` override field.
    KaR name-aliases.yml: added `category` override for three Imam figures (F26 minimal).
  - PEQ voice-axis: added `voice_available: bool` to `PEQScore`; `markdown_table()`
    now shows "N/A (→Fidelity)" / "50% (incl. Voice)" when voice scorer not ready,
    instead of a misleading 0.0 row. Fixed 2 pre-existing test failures (stale
    weight comment + voice scorer predating `_VOICE_SCORER_READY = False`).
  - pipeline-debt.md: open-items table reconciled — F25/F27/F24/F17/F29/v4-revised
    all marked CLOSED; F26 downgraded to P1 followup.

**Session work completed (session 10 — 2 commits 711088c → 4200b64):**

Studio "Edit & Enrich" now shows the full content-transformation journey + an
in-context metrics dashboard (Asif request: "see the entire pipeline flow and
the modifications at each step"). NO site redesign — built additively on the
in-flight three-pane rebuild after self-review caught that a restructure would
fight the existing author's design + that the real symptom was a data-filter.

  - 711088c (checkpoint): committed the uncommitted in-flight three-pane Studio
    rebuild as a restore point (verified green first: check/lint/build + 512 py
    tests). Removed superseded reader components.
  - 4200b64 (feature): left rail now renders the whole stage chain up to the
    editable Review (uncaptured stages = muted non-interactive "not captured"
    rungs) + plain-English role badges; collapsible "Transformation" dashboard
    band (words-per-stage SVG bar chart + 3 headline chips: % noise removed,
    words augmented, wisdom integrated — all from stage-metrics +
    augmentation-ledger; honest "not captured" when absent) + a what-each-stage
    -did <dl> legend; per-stage header card (name+role+tool+metric) replacing
    the plain read-only note.
  - New: stage-roles.ts, enrichment-ledger.ts, TransformationDashboard.tsx,
    StageBarChart.tsx, transformation-dashboard.css. No theme/colour change, no
    Python change, no new deps.
  - html-view-challenger: PASS / Level 1 Conformant. Auto-fixed one real bug it
    caught (chart text inherited global .svg-host 19.2px → qualified .sbc-*).
  - Plan file: ~/.claude/plans/adding-to-my-previous-distributed-glacier.md.

**Earlier — session 9 (production-readiness sweep). BRANCH: `develop`, 8773be7.**

**Session work completed (session 9 — 6 commits a723620 → 8773be7):**

Full production-readiness audit (4 parallel auditors) + risk-ordered fix sweep.
Every finding re-verified against real code first — several sub-agent findings
were false positives and were excluded.

  - Wave 0 (a723620): resolved a committed git merge conflict in
    infrastructure-snapshot.json that was breaking `astro build` (vite:json parse
    fail); gitignored stray plan-dashboard/knowledge.db.
  - Wave 1 (b435df3): fixed the real --dry-run mutation bug (G4 build-clean now
    runs build_episode_txt.py with a new --check mode under dry-run, so it never
    rewrites source episodes/*.txt); subprocess timeouts on _run (git) +
    keychain fetches; stale-resume auto-recovery (is_phase_stale downgrade);
    PDF/slug input validation; write_state() no longer mutates caller's dict.
  - Wave 2 (c763605): PHASE REGISTRY UNIFIED to one source (_progress.PHASES).
    Fixed a LATENT P0 CRASH — "0literary" + "publish" were emitted by drivers
    but missing from PHASES, so update_phase() raised ValueError when they ran
    (this is why literary had to be run manually). The full test suite was RED
    on develop; now GREEN.
  - Wave 3 (4809f8d): Cortex MUSTs — architecture.astro sections 06/07 numbered;
    scroll-margin-top on anchored sections; SVG a11y triple moved onto <svg>.
  - Wave 4 (40511e9): render-mermaid.mjs degrades gracefully without chromium;
    retired _workspace/Books/ path drift corrected across agent specs + SKILL.md;
    REQ-027 documented decorative exception for the home-logo ornament.
  - Wave 5 (8773be7): new test_publish_gates.py (14 tests) covering G1-G3/G4/G6 +
    the dry-run no-mutation invariant (the regression guard for the Wave 1 bug).

**PIPELINE HEALTH:**
- Tests: full unittest suite GREEN — 426 passed, 1 skipped (was 2 failures +
  2 errors at session start; the red suite is fixed).
- `astro check`: 0 errors, 0 warnings.
- `lint:views`: errors=0 warns=0.
- `npm run build`: completes end-to-end (P0 build-blocker resolved).
- html-view-challenger re-gate: PASS / Conformant on all changed views.

**OPEN DEBT:**
- Ayyuhal Walad: literary chapters written for 3 chapters manually (the
  automated literary path now works after the Wave 2 crash fix — re-runnable).
- knowledge.db 030 migration: applied live.
- _phases.py is now a thin re-export of _progress.PHASES (was a dead aspirational
  enum). It is a candidate for outright deletion (only its test imports it) —
  deferred as a Tier-2 deletion pending Asif's confirmation.
- regenerate-snapshots.py side-effect: running it dirties the committed
  knowledge.db + stage-metrics.json (opens the SQLite DB read-write). Cosmetic;
  worth making read-only later.

**NEXT WORK:**
- Validate Ayyuhal Walad literary chapters in Studio before uploading to NotebookLM.
- Video visual layer (WC8.9, authorized, ~$2 cost).
- section_depths: pipeline-side auto-assignment in phase 0d (future Wave O).
- Ayyuhal Walad: waiting on hadith DB from Asif (pipeline blocked on this).

**PARKED:**
- Same as before.
