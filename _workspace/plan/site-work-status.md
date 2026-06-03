<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-03 (session 4)

**BRANCH: `feature/wave-m-inspector-corpus` — active (off develop `b791c00`).**
- Wave L + Wave M prep committed to develop (`b791c00`):
  - CONTENT_LEVEL_LADDER expanded to 6 rungs (general→advanced→taveel→mamsool→mabda_maad→haqaiq)
  - Terminology locked: `mabda_maad` code ID; "Origin & Return" display label
  - ContentLevelSelector.tsx, _rules.py, categorize_atoms.py, tests updated

**PIPELINE HEALTH:**
- 351 tests passing (1 skip) — from prior session; re-verify after Wave M M-1
- `astro check`: 0 errors (from prior session)
- `lint:views`: errors=0 warns=0 (from prior session)

**OPEN DEBT:**
- None.

**NEXT WORK (Wave M — in active design/implementation):**
- Plan at `~/.claude/plans/how-do-i-edit-robust-wigderson.md`
- M-1: Floating paragraph toolbar (AI-only) + section-level depth markers + inspector
  declutter + scroll fix (StudioPoc.tsx, studio-poc.css — no new dependencies)
- M-2: Wire CorpusExplorer to real DB data via new knowledge.ts + /api/corpus/atoms
- M-3: Edit + create inline within CorpusExplorer
- Open decisions: (1) Kashkole SQLite import + Lookup_levels verification
  (2) Full 6→7-rung ladder from Lookup_levels (3) Section stable IDs

**PARKED:**
- Ayyuhal Walad pipeline: 5 chapters fully staged; waiting on hadith DB from Asif
- Video visual layer (WC8.9, authorized, ~$2 cost)
