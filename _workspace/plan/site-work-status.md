<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-02 (session 2)

**BRANCH: `develop` — clean.**
- DR-005 warmup complete (commit `5522d16`, 2026-06-02): split `_validators.py` (1,050 ln)
  and `_extract_helpers.py` (823 ln) into 6 files, all under the 600-line cap.
  `_validator_constants.py`, `_validators_framing.py`, `_validators.py`,
  `_extract_yaml.py`, `_extract_contract.py`, `_extract_helpers.py`.
  303 tests pass, 17 pre-existing failures unchanged.

**PIPELINE HEALTH:**
- 303 tests passing (1 skip, 17 pre-existing failures — unchanged from before this session)
- `astro check`: 0 errors (from prior session; not re-run this session)
- `lint:views`: errors=0 warns=0 (from prior session)

**OPEN DEBT:**
- None. F38 and DR-005 both fully retired as of 2026-06-02.

**NEXT WORK:**
- Wave K — scope TBD (discussing with Asif)

**PARKED:**
- Site redesign (IA complete; WC8.5 TipTap Studio rebuild deferred)
- Ayyuhal Walad pipeline: 5 chapters fully staged; waiting on hadith DB from Asif
- Video visual layer (WC8.9, authorized, ~$2 cost)
