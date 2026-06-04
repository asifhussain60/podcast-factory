<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-04 (session 9 — production-readiness sweep, pipeline + site)

**BRANCH: `develop` — active. Committed (8773be7).**

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
