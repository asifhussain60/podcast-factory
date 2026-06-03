<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-03 (session 3, continued ×2)

**BRANCH: `develop` — clean.**
- Wave K complete (commits `af2f8f9`, `2f7f6fa`, `9f16e9d`, 2026-06-03):
  - B4 wired: augment_episode_text() in per-chapter pipeline (step 3.5)
  - Ayyuhal Walad meta.yml: enable_knowledge_augmenter=true, tradition=fatimid-ismaili
  - augmenter.py: 600-char atom truncation to avoid flooding NotebookLM prompt
  - quote atom type added to schema, extractor prompt, and DB (migration 023)
  - term atoms expanded 58→622 via regex scan of doctrine text (zero Gemini cost)
  - 55 existing KQUR terms fixed: text_en populated from definition field
  - Total DB atoms: 7,600

**PIPELINE HEALTH:**
- 351 tests passing (1 skip)
- `astro check`: 0 errors (from prior session)
- `lint:views`: errors=0 warns=0 (from prior session)

**OPEN DEBT:**
- None.

**NEXT WORK:**
- Wave K + quality pass complete. Ayyuhal Walad episodes are augmented and
  comparison-report saved. Next: discuss Wave L scope with Asif.

**PARKED:**
- Site redesign (IA complete; WC8.5 TipTap Studio rebuild deferred)
- Ayyuhal Walad pipeline: 5 chapters fully staged; waiting on hadith DB from Asif
- Video visual layer (WC8.9, authorized, ~$2 cost)
