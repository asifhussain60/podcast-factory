# Surah Al-Fateha finish-line + Kashkole English rendering -- phased plan

**Written:** 2026-08-12. **Priority order:** Surah Al-Fateha (P1) before Kashkole (P2) --
Surah Al-Fateha is the book actively in flight and closer to a publishable state;
Kashkole is corpus infrastructure with no reader-facing deadline.

Checked against the live pipeline before writing this, not assumed from memory:
orchestrator-state.json, the articulation ledger, and translate_kashkole.py's own
source were all re-read on 2026-08-12. One real pipeline gap came out of that
check -- see Phase 3 below -- and is the reason this plan exists rather than a
one-line "resume the run" note.

Related snag-list items: `surah-al-fateha-articulation-incomplete`,
`spiritual-ethos-0book-compose-incomplete`, `kashkole-urdu-to-english` in
`_workspace/plan/pending-work.yaml`. Kashkole's own detailed state lives in
`_workspace/plan/kashkole-translation-status.md` -- this file does not duplicate
that data, only sequences the work around it.

---

## Stream A -- Surah Al-Fateha (P1)

State as of 2026-08-12: 2 of 23 chapters articulated (`Quranic Friendship`,
`Linguistic Meaning Of Allah`), 1 chapter failed on an exception rather than a
clean gate revert (`The Stages Of Love` -- will auto-retry on resume, not in
`KEPT_STATUSES` so the driver's resume logic does not skip it), 20 reverted.
`orchestrator-state.json` still reports the `sessions-articulate` step
`"status": "completed"` with only 2/23 kept -- that is the stale-flag bug fixed
earlier the same day; the flag self-corrects the moment the driver processes a
chapter, but nothing has run since the merge landed the fix.

1. **Resume articulation for the 21 remaining chapters.**
   Command: `python3 scripts/podcast/sessions/articulate.py surah-al-fateha`
   (resumable; skips the 2 already kept; the `_DEAD_STREAK_LIMIT = 2` circuit
   breaker halts the run and reports rather than mislabeling every remaining
   chapter if the model becomes unreachable mid-run).

2. **Verify the status flag self-corrects.**
   After the first few chapters land, re-read
   `content/Sessions/surah-al-fateha/_system/orchestrator-state.json` ->
   `.phases["sessions-articulate"]` and confirm it reports the real kept/total
   count instead of the merge-carried stale "completed". Verification only --
   the fix is already written and tested
   (`scripts/podcast/tests/test_book_status_card.py`).

3. **Run the (now built) `sessions-apparatus` driver once articulation finishes.**
   BUILT 2026-08-12: `scripts/podcast/sessions/apparatus.py` --
   `run_apparatus(slug)` calls `apply_book_apparatus` (the same compose tail
   every other book route runs) and `ingest._write_state` (the same state
   writer `ingest.py` already uses -- no second schema), and REFUSES to run
   while `sessions-articulate` is not `completed` rather than apparatus-ing
   half-rewritten prose. Covered by
   `scripts/podcast/tests/test_sessions_apparatus.py` (7 tests, all model
   calls mocked). Manually confirmed against the live book mid-run: it
   correctly refused with `sessions-articulate is 'running'`.
   Command once articulation is done:
   `python3 -m sessions.apparatus surah-al-fateha` (run from `scripts/podcast/`).

4. **Run book-challenger's convergence pass** (articulation conformance
   against REQ-BA-*, narrative-frame Pass 3 gate) over the composed book --
   the same gate every other reading edition clears before it is called done.

5. **Human review in the Book Composer** at `/studio/surah-al-fateha/compose`
   before anything moves toward publish. Per the standing rule: the Compose
   tab is the review gate, not a passing test suite. Nothing publishes without
   this regardless of how clean the gates read.

6. **Publish decision** -- Tier 2, always ask. Not part of this plan's
   auto-execution; flagged here only so the finish line is visible.

## Stream B -- Kashkole English rendering (P2)

State as of 2026-08-12: 76 of 1,347 topics translated (47.7% of the corpus by
character weight -- the pass takes the largest topics first), 1,271 remaining.
The first run stopped when every remaining topic failed within minutes,
consistent with the subscription's usage ceiling rather than a corpus or
prompt defect. Three real code gaps in `translate_kashkole.py` were found
while re-reading the source for this plan (not fixed since the status doc was
written) and should land before the next run, or a second outage reproduces
the same "everything fails in minutes" pattern.

1. **Fix the three engine gaps in `scripts/podcast/intelligence/translate_kashkole.py`:**
   - K1 -- no circuit breaker: add a stop-after-N-consecutive-failures check
     to the main loop (mirrors the pattern already proven in
     `scripts/podcast/sessions/articulate.py`'s `_DEAD_STREAK_LIMIT`).
   - K2 -- no retry: swap the `_run_claude_p` call (line ~397) for
     `_run_claude_p_with_retry`.
   - K3 -- per-topic rather than per-window storage: persist each window's
     rendering as it completes rather than only after every window in a topic
     finishes, so a crash mid-topic loses at most one window instead of the
     whole topic.

2. **Re-run the remaining 1,271 topics.**
   `python3 scripts/podcast/intelligence/translate_kashkole.py --workers 5`
   Idempotent on `source_sha`; roughly 2.5-3 hours of wall clock at the rate
   the first run held. `--status` to check progress without spending anything.

3. **Resolve the six `review`-flagged topics** (ids 5702, 5708, 5715, 5726,
   5740, 5766), each missing exactly one Qur'anic verse in its rendering --
   either a surgical repair per topic or a targeted re-render with the verse
   quoted back into the prompt.

4. **Decide the `mirror.db` commit cadence** before the remaining 1,271 land --
   each commit stores a full new ~30 MB+ blob of the tracked binary; committing
   after every run would grow the repo fast. Asif's call, not a default to
   assume.

5. **Wire `topic_translation` into the corpus index and the Companion lane.**
   Separate, smaller follow-on -- the renderings are inert until something
   queries them. Not blocking the corpus finishing.

---

## Execution note

Stream A phases 1-3 are the accepted next action as of 2026-08-12 (Asif chose
"proceed with A" on the chat plan this file mirrors). Stream B stays queued
behind it, tracked in `kashkole-urdu-to-english`.
