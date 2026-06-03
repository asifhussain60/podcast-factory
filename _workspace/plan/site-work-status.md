<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-03 (session 3)

**BRANCH: `develop` — clean.**
- Wave K / B4 complete (commit `af2f8f9`, 2026-06-03): wired `augment_episode_text()`
  into per-chapter pipeline as step 3.5 (between build and converge). Gate is
  `meta.yml series.enable_knowledge_augmenter` (default False) — all existing books
  untouched. Tradition-match guard and error-recovery baked in. 3 new tests.
  351 tests pass, 1 skip (was 303 last session).

**PIPELINE HEALTH:**
- 351 tests passing (1 skip, zero pre-existing failures regressed)
- `astro check`: 0 errors (from prior session; not re-run this session)
- `lint:views`: errors=0 warns=0 (from prior session)

**OPEN DEBT:**
- None.

**NEXT WORK:**
- Wave K continued: Option B (quote type + expand term extraction to 500+ atoms) or
  enable augmenter on a live book (add `enable_knowledge_augmenter: true` +
  `knowledge_tags` + `tradition_affinity` to ayyuhal-walad meta.yml and smoke-test)

**PARKED:**
- Site redesign (IA complete; WC8.5 TipTap Studio rebuild deferred)
- Ayyuhal Walad pipeline: 5 chapters fully staged; waiting on hadith DB from Asif
- Video visual layer (WC8.9, authorized, ~$2 cost)
