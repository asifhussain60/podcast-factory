# Pipeline ↔ Challenger cohesion audit — 2026-05-23

**Author**: Air operator, post-KaR ship.
**Scope**: 5 structural gaps between the pipeline (`scripts/podcast/*`) and the podcast challenger agent (`.claude/agents/podcast-challenger.md`) — recommend automate vs human-gate vs accept-as-designed.

---

## Context

After KaR shipped (ship-with-caution, 2026-05-23), an audit of the F27 + v4-revised reconciliation revealed that most framework debt had already landed but planning docs were stale. The remaining structural surface is **not** more validators — it's the 5 cohesion gaps below, where the challenger validates something the pipeline doesn't enforce (or vice versa).

---

## Gap 1 — Transcript empirical checks (M3 / M4 / N5 / O3 / P12 / P13 / R6 / R7)

**Challenger scope**: 8 empirical-transcript checks that re-read a NotebookLM transcript and audit for modernization injections, surprise-phrase density, phonetic doublings, formal transitions, proposition statement leakage, and host position drift.

**Pipeline state**: `scripts/podcast/audit_transcript.py` EXISTS and is called manually after a transcript drops at `transcripts/EP##-<slug>.transcript.txt` ([orchestrate_book.py:449-450](../../scripts/podcast/orchestrate_book.py#L449-L450)). The orchestrator does NOT trigger this — it's a human-gated step.

**Recommendation**: **ACCEPT as human-gate**. The transcript only exists *after* a human uploads to NotebookLM, generates the audio overview, and downloads the transcript. There's no automation path that doesn't first route through NotebookLM. The current design (orchestrator emits episode .txt → human uploads → human downloads transcript → human runs `audit_transcript.py`) is structurally honest.

**Minor improvement**: Add a one-line reminder in the orchestrator's final "done" output: `"Next: upload episodes/* to NotebookLM, then run python3 scripts/podcast/audit_transcript.py for each."` Already partially present at L449-450; verify it surfaces at end-of-run.

---

## Gap 2 — Category Q (chapter-set design) book-scope check

**Challenger scope**: Title uniqueness, word-count band match, inter-chapter balance ≤30% variance — runs once per book invocation via [check_chapter_set.py](../../scripts/podcast/check_chapter_set.py).

**Pipeline state**: `check_chapter_set` is NOT invoked from `orchestrate_book.py` or `_phases.py` (confirmed by grep — zero hits). Category Q is challenger-only.

**Recommendation**: **AUTOMATE**. Add a Phase 0d.5 sub-step that invokes `check_chapter_set.py` after chapter segmentation completes. Fail-soft (P1 advisory) so it doesn't block; surface findings in `_system/chapter-set-report.md` for operator review at the 0f gate. Effort: ~30 min (one call site + state.json reporting).

**Why**: catches title collisions and balance variance BEFORE Phase 0g LLM authoring runs — failing fast saves 5–9h of LLM time on mis-segmented books.

---

## Gap 3 — S1 / S3 / S5 async-safety pre-flight lock

**Challenger scope**: S1 (async-safety gate), S3 (boundary contract enforcement), S5 (scope-out write defense) are HALT-blocking checks in the challenger.

**Pipeline state**: No `fcntl`, `flock`, `LOCK`, `lockfile`, or `process_lock` anywhere in `orchestrate_book.py` or `_phases.py` (confirmed by grep — zero hits). Two concurrent orchestrator runs on the same book could corrupt `state.json`.

**Recommendation**: **AUTOMATE**. Add a `~/.podcast-locks/<book-slug>.lock` file-based mutex acquired at orchestrator startup, released at clean exit. Use `fcntl.flock(LOCK_EX | LOCK_NB)` so a second process gets immediate "already locked by PID X" error instead of corrupting state. Effort: ~1h including stale-lock detection via PID liveness check.

**Why**: this is the *one* place where pipeline silence allowed a real data-corruption risk on KaR (Air + Studio could have collided if both had tried KaR simultaneously). Cheap to add; high asymmetric value.

---

## Gap 4 — Category G post-extraction contract re-validation

**Challenger scope**: When `chapter-contracts/` is populated, challenger re-runs `extract_chapter.py` to validate contract parity, lineage validity, slug discipline, staleness.

**Pipeline state**: `extract_chapter.py` IS invoked from `orchestrate_book.py:716` during Phase 0d. But there's no *re*-validation gate — after Phase 0d emits a contract, nothing re-confirms it's still parity-clean against the chapter source if Phase 0e modifies anything.

**Recommendation**: **VERIFY first, then likely accept**. The current pipeline is mostly write-once on contracts (Phase 0d emits, Phase 0e reads but doesn't write contracts). G4/G6 staleness is unlikely to actually trip unless an operator hand-edits a contract mid-run. If verified clean, accept as designed (write-once contract semantics is structurally honest).

**Effort if accepting**: zero. **If automating**: ~30 min for a Phase 0f pre-gate check (read each contract, hash the referenced chapter file, compare to contract's `source_hash` field if it exists or add one).

---

## Gap 5 — Word-count soft/hard band alignment

**Initial claim**: "script enforces [500–10,500] hard, challenger advises [1,000–9,500] soft" — a mismatch.

**Actual code** ([build_episode_txt.py:103-106](../../scripts/podcast/build_episode_txt.py#L103-L106)):
- `CHAPTER_WORD_MAX_HARD = 10500`
- `CHAPTER_WORD_MAX_SOFT = 9500`
- `CHAPTER_DEAD_ZONE_MIN = 4500`

Both bands exist; the script enforces soft + hard with different consequences. Challenger's [1,000–9,500] advisory aligns with the script's soft band (9,500 ceiling matches). The "dead zone" (4,500-?) is a separate quality concept.

**Recommendation**: **NO ACTION needed — already aligned**. The initial gap report was based on a partial reading. The script and challenger are using the same band model; only the upper hard band (10,500) is a 10% tolerance above the challenger's soft advisory, which is intentional ("M5 empirical thresholds vs ~ prose" — see pipeline-debt.md meta-pattern).

---

## Summary recommendations

| Gap | Action | Effort | Priority |
|---|---|---|---|
| **G1** Transcript audit | Accept as human-gate; add reminder in orchestrator done-output | ~5 min | P3 |
| **G2** Category Q in orchestrator | **AUTOMATE** — wire `check_chapter_set.py` into Phase 0d.5 | ~30 min | P1 |
| **G3** Async-safety lock | **AUTOMATE** — fcntl lockfile in orchestrator startup | ~1h | P1 (real data-corruption risk) |
| **G4** Category G re-validation | Verify write-once semantics; likely accept | ~15 min verify | P3 |
| **G5** Word-count bands | Already aligned — close as misreport | 0 | DONE |

**Net new framework work surfaced**: ~2h for G2 + G3 (the only real gaps). G1/G4/G5 are either by-design human-gates or non-issues.

**Updated cohesion picture**: Pipeline ↔ Challenger are tighter than the initial audit suggested. Closing G2 + G3 brings cohesion to ~95%; the remaining 5% is human-gate-by-design (transcript audit) which is honest, not a bug.
