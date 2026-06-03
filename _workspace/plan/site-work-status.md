<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-03 (session 6 — depth taxonomy + literary pipeline + combined annotation picker)

**BRANCH: `develop` — active. Committed and pushed (001f497).**

**Session work completed:**

Depth level taxonomy (commit b4b8d79):
  - StudioPoc: DEPTH_LEVELS_BY_PROFILE — 4 content-profile sets (islamic_scholarly/
    consumer_explainer/technical/fiction); combo levels and Kashkole jargon removed.
  - knowledge.ts: ALLOWED_LEVELS split → ALLOWED_ATOM_LEVELS (Kashkole, for atoms)
    + ALLOWED_DEPTH_LEVELS (new Studio section codes). Fixes silent bug where removing
    old codes would have broken atom write validation.
  - [step].astro: reads content_profile from series-config.yaml, passes to StudioPoc.
  - theme.css + studio-poc.css: new token groups and badge classes for all 4 profiles.
  - ContractView.astro + chapter-viewer.css: DoD fix (inline styles → CSS classes).

Literary pipeline — Phase 1 pilot (commit 3101132):
  - 3 Ayyuhal Walad chapters rewritten as first-person Ghazali literary nonfiction.
  - _stages/ch0N-*/literary.md: Studio Literary tab source.
  - chapters/literary/ch0N-*.txt: NotebookLM upload source (literary version preferred).
  - book-workspace.ts: chapter IDs fixed to match actual files; Literary stage added.
  - _validators.py: find_chapter_by_slug gains required=False for literary fallback.
  - build_episode_txt.py: prefers chapters/literary/ when present.

Literary pipeline — Phase 2 + Option A (commit 001f497):
  - _literary.py: Gemini 2.5 Pro script; per-book voice config from series-config.yaml;
    idempotent via literary-log.md; writes both Studio + NotebookLM outputs.
  - _phases.py: LITERARY = "08b-literary" (between ENRICHMENT and SERIES_PLAN).
  - initial_driver.py: _run_literary() in phase_map after 0e enrichment.
  - ayyuhal-walad series-config.yaml: literary block (author_first_person, Ghazali).
  - Option A combined annotation picker: depth (single-select) + tags (multi-select)
    in one popover. Tags: Esoteric/Reality/Sharia/Narrative/Origins/Delete/Improve.
  - 030_section_tags.sql: section_tags column added to section_depths.
  - section-depth API: PATCH accepts tags[]; GET returns section_tags.
  - studio-poc.css: tag picker buttons + inline chip styles.

**PIPELINE HEALTH:**
- Tests: not re-run this session (no Python logic changes to existing pipeline).
- `astro check`: 0 errors
- `lint:views`: errors=0 warns=0

**OPEN DEBT:**
- Ayyuhal Walad: series-config.yaml literary block in place; literary chapters
  written manually for 3 existing chapters. Phase 2 auto-runs for ALL future books.
- knowledge.db 030 migration: applied live; schema/030_section_tags.sql tracks it.
- plan-dashboard/knowledge.db: empty stale file (not the real DB path); should be
  deleted or gitignored.

**NEXT WORK:**
- Validate Ayyuhal Walad literary chapters in Studio before uploading to NotebookLM.
- Video visual layer (WC8.9, authorized, ~$2 cost).
- section_depths: pipeline-side auto-assignment in phase 0d (future Wave O).
- Ayyuhal Walad: waiting on hadith DB from Asif (pipeline blocked on this).

**PARKED:**
- Same as before.
