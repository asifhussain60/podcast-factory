# Watchdog architecture runbook

Three-layer self-healing keeps multi-hour orchestrator runs alive without operator babysitting. Each layer covers a different failure mode.

## Layer 1 — Shell watchdog (`watch_orchestrator.sh`)

Plain bash loop that wakes every 30s, checks `BOOK_DIR/_system/orchestrator.pid`, restarts the orchestrator if the PID is dead AND the book isn't at a terminal phase. Auto-spawned by `orchestrate_book.py` on every `--resume`.

```bash
# Manual spawn (rarely needed — orchestrate_book.py does this automatically):
bash scripts/podcast/watch_orchestrator.sh content/drafts/my-book-slug &
```

Logs at `content/drafts/<slug>/_system/watchdog.log`. Stops naturally when the book reaches `phase=publish, phase_status=completed` OR after 30 consecutive restart failures (safety cap).

## Layer 2 — Auto-spawn in `orchestrate_book.py`

[orchestrate_book.py:1388-1405](../../scripts/podcast/orchestrate_book.py) acquires a per-book fcntl lock and spawns the Layer 1 watchdog if not already running. Every `--resume` checks: is the watchdog alive? If no, spawn it. Idempotent — `pgrep` check prevents duplicate watchdogs.

## Layer 3 — In-session AI heartbeat (CLAUDE.md Tier 0)

After ANY orchestrator action (`--resume`, `--retry-phase`, restart), the AI MUST `ScheduleWakeup` at 270s with the active-liveness heartbeat prompt. The 270s interval keeps the Anthropic cache warm (5-min TTL). Tier 0 — automatic, no user instruction needed. Per `feedback_loop_rearm_mandatory.md` and `feedback_watchdog_active_liveness.md`.

**Active-liveness checks per tick** (mandatory; passive status cards are worse than no watchdog):

1. `ps -p <parent_pid>` — parent task alive?
2. `ps aux | grep -E "audit_bundle|phase_0X"` — subprocesses making progress?
3. Per-PID `ps -o etime= -p <pid>` — any subprocess past its 900s budget? Kill -9 it.
4. Snapshot `ls -la --time-style=+%H:%M:%S` of audit/output dir vs prior tick. If no new files AND no size growth AND parent alive AND all subprocess CPU=0 → suspect stall; check on next tick; kill on two consecutive zero-progress ticks.

**Kill-early discipline**: don't ask for permission to kill stalled processes. Wasted minutes = wasted LLM spend. Log what you killed and why.

## Known orchestrator-resume bug class

Stale `phase_status="running"` after unclean shutdown blocks `--resume`. Recovery: `--retry-phase <phase>`. F30 / F33 / F35-second resume dispatchers (see `_resume_from_state` in orchestrate_book.py) handle `(phase, status)` combinations `(0g, completed/failed/running/pending)`, `(finalize, halted/failed/pending)`, `(publish/trainer/merge, failed/running/pending)` — re-entry is idempotent for all of these.

## Heartbeat card format

Every tick emits a structured card per `feedback_heartbeat_format.md` memory:

```
─────────────────────────────────────────────────────────────────
HEARTBEAT · <phase> · <book-slug>
2026-MM-DD · HH:MM EDT · TICK STATUS: <ACTIVE|TERMINAL>
─────────────────────────────────────────────────────────────────
| Metric          | Value                                      |
|---|---|
| Parent PID       | <pid> · etime=<HH:MM:SS>                   |
| Subprocesses     | <count> running                            |
| Cost (book)      | $<amount> / $<cap>                         |
| Last ledger entry| <ts> · <step>                              |
| Chapters         | ✅✅✅🔄⏳⏳ (<done>/<total>)                |
| Watchdog PID     | <pid> · etime=<HH:MM:SS>                   |
─────────────────────────────────────────────────────────────────
```

## Recovery cheatsheet

| Symptom | Action |
|---|---|
| `--resume` says "phase already running" but no PID | `--retry-phase <phase>` |
| Watchdog log shows 30+ restart cycles | Manual investigate; orchestrator has a real bug not transient |
| Heartbeat shows zero-progress two ticks running | Kill subprocesses, fix root cause, --retry-phase |
| Cost approaching `per_chapter_cost_cap_usd` | Either raise cap in series-plan.md + --resume, or accept FAILED-COST-CAPPED |
| `phase=finalize, phase_status=halted` | Normal — awaiting human review per F33-second graceful-degrade; run publish_to_library.py when satisfied |
