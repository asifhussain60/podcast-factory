# Walk-Away Mode — Podcast Pipeline W1

This document explains how to leave the podcast pipeline running unattended while it works through Wave 1 (Foundation & Guardrails).

The autonomous loop is **safe by default**: every phase is idempotent, every halt is at a well-defined human-review gate, and the only escape from the gate is an operator addressing the gap. The loop never silently advances past a failure.

---

## Install (one-time)

```bash
# 1. Copy the plist to LaunchAgents
cp infra/launchd/com.journal.podcast-w1.plist ~/Library/LaunchAgents/

# 2. Load it — launchd will start firing on the next tick
launchctl load ~/Library/LaunchAgents/com.journal.podcast-w1.plist

# 3. (Optional) Fire once immediately to see what happens
launchctl start com.journal.podcast-w1
```

The job fires `python3 scripts/podcast/run_wave.py 1` once per hour (`StartInterval: 3600`). Tune that in the plist if hourly is too aggressive or too slow.

---

## What happens on each tick

Each tick is fully deterministic. The harness:

1. Reads [`_workspace/plan/acceptance-criteria.md`](../../_workspace/plan/acceptance-criteria.md) — if every W1 row is `[x]`, exits 0 silently.
2. Iterates [`scripts/podcast/phases/__init__.py`](../../scripts/podcast/phases/__init__.py) `REGISTRY[1]` in declared order.
3. For each phase: calls `is_done()` first; if true, marks any unchecked acceptance rows and moves on.
4. For not-done phases: calls `execute()`. If the phase returns `status="done"`, marks its rows. If `status="halted"`, prints the gap + evidence path and stops the loop.
5. After all phases run, re-checks the wave's completion; emits exit code accordingly.

| Exit code | Meaning | Operator action |
|---:|---|---|
| 0 | Wave already DONE | None |
| 1 | Error (bad args / file missing / cost overrun) | Read `podcast-w1.err`, fix root cause |
| 2 | Wave executed and now DONE | Move to W2 (`launchctl unload` this plist, install W2 plist) |
| 3 | Halted at a human-review gate OR remaining phases need new runners | Read `podcast-w1.log`, address gap |
| 4 | Wave DONE but P-9 invariant violated (`test_challenger.py` red) | Inspect `_learning/` substrate immediately |

---

## Tail the logs

```bash
# Live tail (Ctrl-C to detach)
tail -F ~/Library/Logs/podcast-w1.log

# Recent errors
tail -50 ~/Library/Logs/podcast-w1.err

# Quick "where are we?" without spending compute
python3 scripts/podcast/run_wave.py --check 1
```

The `--check` flag is **read-only**: it reports the wave's completion percentage and lists which task IDs still have unchecked rows. Safe to run any time.

---

## Pause / resume

```bash
# Pause (stop firing; doesn't kill an in-flight tick)
launchctl unload ~/Library/LaunchAgents/com.journal.podcast-w1.plist

# Resume
launchctl load ~/Library/LaunchAgents/com.journal.podcast-w1.plist

# Check whether the agent is loaded
launchctl list | grep podcast-w1
```

The plist's `RunAtLoad: false` means `launchctl load` does NOT immediately fire — it just registers the agent and starts the hourly clock from that point.

---

## Adding new phase runners (developer hook)

The autonomous loop only knows about phases listed in `REGISTRY[wave_n]`. To add a new phase:

1. Ship its deliverable under `scripts/podcast/` with tests under `scripts/podcast/tests/`.
2. Author `scripts/podcast/phases/p<n>_<m>.py` exporting `PHASE_ID`, `DESCRIPTION`, `is_done()`, `execute()` per [`scripts/podcast/phases/_base.py`](../../scripts/podcast/phases/_base.py).
3. Import the new module in `scripts/podcast/phases/__init__.py` and append it to `REGISTRY[1]` (or its owning wave).
4. Re-run `python3 scripts/podcast/run_wave.py 1` to verify the loop picks it up. The next launchd tick will pick it up automatically.

Each phase runner is responsible for its own idempotency. The harness only orchestrates iteration + acceptance marking; it doesn't reason about phase semantics.

---

## What's currently wired (W1 phase registry)

| Phase | Module | Status |
|---|---|---|
| P5.4 phase-id constants | [`phases/p5_4.py`](../../scripts/podcast/phases/p5_4.py) | shipped |
| P1.1 boundary check | [`phases/p1_1.py`](../../scripts/podcast/phases/p1_1.py) | shipped |
| P1.2 proposal writer + handoff doc | — | not yet wired |
| P1.3 CI gate cross-reference | — | not yet wired (depends on P8.8) |
| P2.1 / P2.2 / P2.3 E2E test harness | — | not yet wired |
| P2.5 learning-loop E2E | — | not yet wired |
| P2.6 refinement determinism | — | not yet wired |
| P3.1 / P3.2 doc-cleanup | — | already shipped on develop (no runner needed) |
| P4.1 / P4.2 / P4.4b / P4.5 numeric protocol | — | not yet wired |
| P5.1 perm-mode flag | — | already shipped on develop (no runner needed) |
| P5.2 artifact validation harden | — | already shipped on this branch (no runner needed) |
| P5.3 kitab-al-riyad resume | — | not yet wired (needs Azure spend approval) |
| P6.1 / P6.2 / P6.3 / P6.4 cost ledger | — | not yet wired |

Until additional runners land, every tick will:
1. Mark P5.4 + P1.1 rows checked (no-ops after first tick).
2. Print "executed 2 phase(s); X/Y wave rows checked. Remaining rows belong to phases not yet in REGISTRY[1]."
3. Exit 3 (halted).

That's the intended state — the loop is parked, waiting for more runners.

---

## Safety properties

- **No silent advance.** Every halt prints a precise evidence path. Exit code 3 means "stop and ask the human."
- **Idempotent.** Running twice in a row never duplicates work. The first tick after a phase ships will mark its rows; subsequent ticks skip.
- **Append-only acceptance file.** Phase runners only flip `- [ ]` → `- [x]`. They never delete or rewrite content.
- **Boundary check enforced every tick** (via P1.1 runner) — `scripts/podcast/` cannot accidentally write to `content/babu-memoir/`, `content/_shared/`, `scripts/memoir/`, or `scripts/site/`.
- **W3 (corpus) and W5 (deferred) require explicit flags** — they will NOT auto-fire even if a launchd plist is misconfigured for them.

---

## Removing the agent (uninstall)

```bash
launchctl unload ~/Library/LaunchAgents/com.journal.podcast-w1.plist
rm ~/Library/LaunchAgents/com.journal.podcast-w1.plist
# Logs at ~/Library/Logs/podcast-w1.log* can stay or be archived.
```
