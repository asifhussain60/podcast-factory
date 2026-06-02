<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-02

**BRANCH: `develop` — clean.**
- `refactor/wave-1` merged to `develop` (commit `5cbba2e`, 2026-06-02).
- Post-merge sweep passed: 348 tests, 0 TS errors, lint clean.
- Wave J complete (J0–J5 all shipped): local-first verse + term lookups, FTS5 mirror,
  live verse fallback in augmenter, live session style fetch, TopicPopover. Quality-over-cost:
  ~90% of popover hovers resolve from the local KQUR/KASHKOLE mirror — Gemini/quran.com
  only on misses or server down.

**PIPELINE HEALTH:**
- 348 tests passing (1 skip, no failures)
- `astro check`: 0 errors across 150 files
- `lint:views`: errors=0 warns=0
- Consumer category gates: `CONSUMER_CATEGORIES = {"sites", "explainers"}` in `_rules.py`;
  `initial_driver.py` skips phonetics (0c) and enrichment (0e) for consumer content.

**OPEN DEBT (tracked, not blocking):**
- **F38** (HIGH) — `_chunking.py:304` + `tighten_source.py:366` use `subprocess.run(["claude","-p"])` in
  the live pipeline. Migration target: direct Anthropic SDK calls. Both files are also DR-005
  violators (1,051 lines each approximately).
- **DR-005** (MAJOR) — 8 files exceed 600-line cap; worst: `build_episode_txt.py` (1,563) and
  `extract_chapter.py` (1,307). Wave H splits scheduled.

**NEXT WORK (authorized, in order):**
1. F38 fix — migrate `_chunking.py` + `tighten_source.py` from `claude -p` to SDK
2. Wave H DR-005 splits — `build_episode_txt.py` and `extract_chapter.py` first

**PARKED:**
- Site redesign (IA complete; WC8.5 TipTap Studio rebuild deferred)
- Ayyuhal Walad pipeline: 5 chapters fully staged; waiting on hadith DB from Asif
- Video visual layer (WC8.9, authorized, ~$2 cost)
