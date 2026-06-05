<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-05 (session 12 — pronunciation bug fix + video layer redesign + AW regeneration)

**BRANCH: `ayyuhal-walad` — active. Committed (0bcd27e).**

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
