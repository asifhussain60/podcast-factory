<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-08 (session 19 — bundle numbering fix)

**BRANCH: `Islamic/asaas-al-taveel` — 10 commits. Push pending.**

**Session work completed (session 19 — 1 commit e891724):**

Fixed bundle generator sequential numbering + clarified English generalization workflow.

  - build_probe_bundle.py: reorder terms in segment-presentation order (names ->
    places -> terms) BEFORE assigning 1-N numbers. Previously places got mid-range
    global ranks (n=59, 108) while Part 3 restarted at n=1, breaking the checklist.
    Now Part 2 = items 1,2; Part 3 = items 3,4,5...115 sequentially.
  - Bundle regenerated: pronunciation-probe.md, 00-framing.md, listen-checklist.md
    all updated with correct sequential numbers.

**English generalization workflow (complete):**
  1. Click "English for N x1 terms" on each page -> marks in UI
  2. Click "Save" -> writes to library as unfixable with English gloss
  3. Click "Generate source and framing" again -> bundle now shows "Do NOT say X - say Y instead"

**Session work completed (session 18 — 1 commit 64c2114):**

LLM-filled English meanings for all probe terms + toggle-pill UI replacing checkbox.

  - fill_probe_meanings.py: new Gemini Flash batch script fills concise 1-4 word
    English meanings for terms missing one or with meanings >6 words. Biblical names
    for prophets. One API call per run; writes probe-terms.json in place.
  - probe-terms.json: all 128 terms now have concise English meanings. Examples:
    walaya -> Spiritual Guardianship, hujja -> Divine Proof, al-Qa'im -> The Awaited One.
  - PronunciationReview.tsx: checkbox replaced with pill toggle showing English text
    inline at all times. Inactive: grey pill with ⇄ + English preview. Active:
    accent-colored pill with checkmark; gloss input pre-fills with the meaning.
  - pronunciation.css: .pron-lang-toggle pill styles; old checkbox CSS removed.
  - TypeScript clean; html-view-lint: errors=0 warns=0.

**Session work completed (session 17 — 5 commits):**

Pronunciation probe overhaul — frequency counting, meaning pre-fill, count badge.

  - score_pronunciation_risk.py: fixed the core bug (freq=0 for all terms because
    the script was counting Arabic script in English text). Fix: normalise translit
    and count in normalised English text. Added concept-glossary.md parser for
    pre-built meanings; snippet-extraction fallback with honorific + circular guard;
    arabic_script now falls back to row["term"] (which IS Arabic script); segment
    re-sort removed so frequency order is preserved end-to-end.
  - pronunciation.ts: ProbeTerm gains meaning field; arabicScript = arabic_script ?? term.
  - PronunciationReview.tsx: count badge (xN) in accent color; meaning line below chips;
    "Use English translation" checkbox pre-fills gloss from t.meaning when available.
  - pronunciation.css: pron-chip-count + pron-term-meaning CSS classes (no inline styles).
  - probe-terms.json regenerated: top terms Allah x240, Adam x98, imam x72, Ali x54;
    13/40 have meanings. All have arabic_script populated.
  - TypeScript clean; html-view-lint: errors=0 warns=0.

**OPEN (next session):**
  - Teaching-relevance filter: new pipeline step to strip editor prefaces, publisher
    notes, author biographies from the source text before phonetics extraction.
    Currently no such step exists. Once built, re-run the probe on filtered text.
  - Asaas al-Taveel pipeline: resume from phase 0c after review.

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
