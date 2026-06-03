<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-03 (session 5 — autonomous execution of P1 + Wave CP + Wave N)

**BRANCH: `develop` — active. Committed and pushed (3c5f3ea).**

**Session work completed:**

P1 (type cleanup):
  - MockAtom/AtomType/Tradition/CorpusId/Concept moved from corpus-mock-sample.ts
    to lib/db/knowledge.ts; re-exported from mock file for backward compat.

Wave CP (Content-Profile Branching) — all 5 steps:
  - _rules.py: CONTENT_PROFILES tuple + ISLAMIC_SCHOLARLY_PROFILE constant
  - _content_profile.py: resolve_content_profile() + is_islamic_scholarly()
  - build_episode_txt.py: Arabic assertions gated on is_islamic_scholarly()
  - _authoring/_refine.py: 0c also gated on content_profile (future-proof)
  - healthequity series-config.yaml: content_profile: consumer_explainer
  - content/_shared/consumer_explainer/: 3 enrichment stub files
  - podcast-challenger.md: SECTION 0B content-profile gating table
  - 9 new tests in test_content_profile.py

Wave N (Kashkole + Stable Section IDs + Studio Depth Markers) — all 3 steps:
  - 027_lookup_levels.sql: imports 6 base rungs + 3 combos into knowledge.db
  - 028_section_depths.sql: section_depths table (ordinal-keyed)
  - knowledge.ts: getSectionDepths() + upsertSectionDepth() + getLookupLevels()
  - /api/studio/section-depth: GET + PATCH
  - StudioPoc.tsx: depth marker PM widget next to every h2 (click to cycle rungs)
  - studio-poc.css: 6 depth-level colour classes

**PIPELINE HEALTH:**
- 401 tests passing (1 skip) — 9 new from Wave CP
- `astro check`: 0 errors
- `lint:views`: errors=0 warns=0

**OPEN DEBT:**
- None. All waves complete.

**NEXT WORK:**
- No immediate plan items. Next wave would require new design (Wave O).
- Ayyuhal Walad pipeline: 5 chapters staged; waiting on hadith DB from Asif.
- Video visual layer (WC8.9, authorized, ~$2 cost).
- section_depths: pipeline-side tooling to auto-assign depth levels in phase 0d
  (currently only human override via Studio is supported; pipeline-guess source
  requires phase 0d to emit section_id assignments — future Wave O item).

**PARKED:**
- Same as before.
