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

**OPEN DEBT (tracked, not blocking):**
- **F38 tail** (LOW) — `_chunking.py` legacy `claude -p` fallback kept for test back-compat
  (5 tests mock `subprocess.run`). Dead in production — all callers pass `_invoke_fn`.
  Cleanup requires updating the 5 affected tests; deferred to a dedicated session.
- **DR-005** — FULLY RETIRED. All files now under 600-line cap.

**NEXT WORK (authorized, in order):**
1. Wave K — authorize scope (discuss with Asif: Intelligence Pipeline Wave 2,
   video visual layer, or Ayyuhal Walad run)

**PARKED:**
- Site redesign (IA complete; WC8.5 TipTap Studio rebuild deferred)
- Ayyuhal Walad pipeline: 5 chapters fully staged; waiting on hadith DB from Asif
- Video visual layer (WC8.9, authorized, ~$2 cost)
