#!/usr/bin/env python3
"""supervise_run.py — single active supervisor for a long-running book run (Phase E, C5+C6).

ONE component holds kill/relaunch authority (single-actor discipline). This is
it. It generalizes the hand-rolled probe + in-session heartbeat that supervised
the asaas Vol 1 run, and adds the hang-kill teeth the shell watchdog cannot have
(the shell watchdog blocks on the orchestrator subprocess and so cannot poll
mid-run).

Recovery policy (locked 2026-06-09):
  - TRANSIENT breaks (process crashed, or alive-but-hung with no progress and no
    LLM child) -> kill (if needed) + relaunch, BOUNDED retries with backoff.
  - SYSTEMIC breaks (circuit-breaker tripped, cost ceiling hit, pre-flight smoke
    failure, per-chapter iter-cap) -> HALT, raise an ALERT marker, do NOT relaunch.
  - TERMINAL (finalize/halted or done) -> exit cleanly.

Subcommands:
  status <slug>   read-only: print a structured card (used by the in-session
                  heartbeat, now demoted to read-only, and by humans). No mutation.
  watch  <slug>   the active loop: poll every POLL_SEC, apply the policy above,
                  maintain the run registry at _workspace/runs/<slug>.json.
  ensure <slug>   start a run (and a backgrounded watcher) if none is alive; exit.

When this supervisor launches the orchestrator it sets PODCAST_WATCHDOG=1 so the
orchestrator does NOT also spawn the shell watchdog — exactly one actor at a time.
It strips ANTHROPIC_API_KEY from the child env (cost policy: never divert
`claude -p` off the flat-rate Max subscription).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import REPO_ROOT, find_content
from _progress import read_state
from cost_guard import cost_ceiling_check

RUNS_DIR = REPO_ROOT / "_workspace" / "runs"
LOGS_DIR = REPO_ROOT / "_workspace" / "logs"
ORCH = REPO_ROOT / "scripts" / "podcast" / "orchestrate_book.py"

POLL_SEC = 60
MAX_RELAUNCHES = 5
HANG_SECS = 900  # alive + no progress + no LLM child this long -> hung
BACKOFF_BASE_SEC = 30


# ── helpers ──────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _book_dir(slug: str) -> Path | None:
    found = find_content(slug)
    return found[2] if found else None


def _pgrep_count(pattern: str) -> int:
    """macOS-safe process count (BSD pgrep has no -c)."""
    r = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    return len([tok for tok in r.stdout.split() if tok.strip()])


def _run_alive(slug: str) -> int:
    return _pgrep_count(f"orchestrate_book.py --resume {slug}")


def _llm_child_running() -> int:
    return _pgrep_count("claude -p")


def _progress_mtime(book_dir: Path) -> float:
    """Newest mtime across the files a healthy run keeps touching."""
    mtimes: list[float] = []
    sysd = book_dir / "_system"
    for p in (sysd / "cost-ledger.jsonl", sysd / "challenger-report.md", sysd / "orchestrator-state.json"):
        if p.is_file():
            mtimes.append(p.stat().st_mtime)
    for d in (book_dir / "chapters", sysd / "episode-drafts"):
        if d.is_dir():
            for f in d.rglob("*"):
                if f.is_file():
                    try:
                        mtimes.append(f.stat().st_mtime)
                    except OSError:
                        pass
    return max(mtimes) if mtimes else 0.0


def _terminal(state: dict) -> bool:
    ph, st = state.get("phase"), state.get("phase_status")
    return ph == "done" or (ph == "finalize" and st == "halted")


def _systemic_reason(state: dict, book_dir: Path) -> str | None:
    """Non-None when the break is SYSTEMIC (halt, do not relaunch)."""
    le = state.get("last_error")
    msg = le.get("message", "") if isinstance(le, dict) else ""
    for marker in ("CIRCUIT-BREAKER", "COST-CEILING", "pre-flight smoke gate"):
        if marker in msg:
            return msg
    cc = cost_ceiling_check(book_dir)
    if cc["action"] == "halt":
        return f"cost ceiling: real spend ${cc['real_spend_usd']:.2f} >= hard ${cc['hard']:.2f}"
    if state.get("phase") == "per-chapter" and state.get("phase_status") == "failed":
        return msg or "per-chapter failed (iter-cap / triage)"
    return None


def _registry_path(slug: str) -> Path:
    return RUNS_DIR / f"{slug}.json"


def _alert_path(slug: str) -> Path:
    return RUNS_DIR / f"{slug}.ALERT"


def _write_registry(slug: str, **fields) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"slug": slug, "updated": _now(), **fields}
    _registry_path(slug).write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")


def _raise_alert(slug: str, reason: str) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    _alert_path(slug).write_text(f"{_now()} {reason}\n", encoding="utf-8")


def _relaunch(slug: str) -> int:
    """Start the orchestrator detached, single-actor (no shell watchdog), off Max-safe env."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log = LOGS_DIR / f"supervise-{slug}-relaunch.log"
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["PODCAST_WATCHDOG"] = "1"
    with open(log, "a", encoding="utf-8") as fh:
        p = subprocess.Popen(
            [sys.executable, str(ORCH), "--resume", slug, "--skip-doctor"],
            stdout=fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
            cwd=str(REPO_ROOT),
        )
    return p.pid


# ── rendering (read-only) ────────────────────────────────────────────────────


def render_card(slug: str) -> str:
    book_dir = _book_dir(slug)
    if book_dir is None:
        return f"supervise_run: unknown slug {slug!r}"
    state = read_state(book_dir) or {}
    pc = state.get("phases", {}).get("per-chapter", {})
    cc = cost_ceiling_check(book_dir)
    alive = _run_alive(slug)
    children = _llm_child_running()
    lines = [
        f"── run: {slug} " + "─" * max(0, 46 - len(slug)),
        f"  phase:        {state.get('phase')}/{state.get('phase_status')}",
        f"  chapters:     done={len(pc.get('completed_slugs', []))} "
        f"failed={len(pc.get('failed_slugs', []))} "
        f"current={pc.get('current_chapter', '-')}",
        f"  real spend:   ${cc['real_spend_usd']:.2f}  "
        f"(soft ${cc['soft']:.0f} / hard ${cc['hard']:.0f}) [{cc['action']}]",
        f"  process:      orchestrator x{alive}  ·  claude -p x{children}",
        f"  last_error:   {(state.get('last_error') or {}).get('message', '-') if isinstance(state.get('last_error'), dict) else '-'}",
        "─" * 52,
    ]
    return "\n".join(lines)


# ── subcommands ──────────────────────────────────────────────────────────────


def cmd_status(slug: str) -> int:
    print(render_card(slug))
    return 0


def cmd_ensure(slug: str) -> int:
    book_dir = _book_dir(slug)
    if book_dir is None:
        print(f"supervise_run: unknown slug {slug!r}", file=sys.stderr)
        return 2
    state = read_state(book_dir) or {}
    if _terminal(state):
        print(f"{slug}: already terminal ({state.get('phase')}/{state.get('phase_status')}).")
        return 0
    if _run_alive(slug):
        print(f"{slug}: a run is already alive — nothing to do.")
        return 0
    if _systemic_reason(state, book_dir):
        print(f"{slug}: halted on a systemic failure — not auto-starting. Fix root cause first.")
        return 2
    pid = _relaunch(slug)
    _write_registry(slug, status="relaunched", parent_pid=pid, retries=0)
    print(f"{slug}: started orchestrator pid={pid}.")
    return 0


def cmd_watch(slug: str, poll_sec: int = POLL_SEC, max_ticks: int = 480) -> int:
    book_dir = _book_dir(slug)
    if book_dir is None:
        print(f"supervise_run: unknown slug {slug!r}", file=sys.stderr)
        return 2

    retries = 0
    last_progress = _progress_mtime(book_dir)
    last_progress_at = time.time()

    for _ in range(max_ticks):
        state = read_state(book_dir) or {}
        alive = _run_alive(slug)
        children = _llm_child_running()
        prog = _progress_mtime(book_dir)
        if prog > last_progress:
            last_progress, last_progress_at = prog, time.time()

        # TERMINAL — clean exit.
        if _terminal(state):
            _write_registry(
                slug, status="terminal", phase=f"{state.get('phase')}/{state.get('phase_status')}", retries=retries
            )
            print(f"{slug}: terminal ({state.get('phase')}/{state.get('phase_status')}).")
            return 0

        # SYSTEMIC — halt, alert, never relaunch.
        sysreason = _systemic_reason(state, book_dir)
        if sysreason:
            _write_registry(slug, status="halted-systemic", reason=sysreason, retries=retries)
            _raise_alert(slug, f"SYSTEMIC: {sysreason}")
            print(f"{slug}: SYSTEMIC halt — {sysreason}", file=sys.stderr)
            return 2

        # TRANSIENT — crashed.
        if not alive:
            if retries >= MAX_RELAUNCHES:
                _write_registry(slug, status="halted-retries-exhausted", retries=retries)
                _raise_alert(slug, f"retries exhausted after {retries} relaunches")
                print(f"{slug}: retries exhausted ({retries}).", file=sys.stderr)
                return 2
            time.sleep(min(BACKOFF_BASE_SEC * (retries + 1), 300))
            pid = _relaunch(slug)
            retries += 1
            last_progress_at = time.time()
            _write_registry(slug, status="relaunched-crash", parent_pid=pid, retries=retries)
            print(f"{slug}: process gone — relaunched pid={pid} (retry {retries}).")
            time.sleep(poll_sec)
            continue

        # TRANSIENT — alive but hung (no progress + no LLM child for HANG_SECS).
        stalled = (time.time() - last_progress_at) > HANG_SECS
        if stalled and children == 0:
            if retries >= MAX_RELAUNCHES:
                _write_registry(slug, status="halted-retries-exhausted", retries=retries)
                _raise_alert(slug, "hung, retries exhausted")
                return 2
            subprocess.run(["pkill", "-f", f"orchestrate_book.py --resume {slug}"])
            time.sleep(2)
            pid = _relaunch(slug)
            retries += 1
            last_progress, last_progress_at = _progress_mtime(book_dir), time.time()
            _write_registry(slug, status="relaunched-hang", parent_pid=pid, retries=retries)
            _raise_alert(slug, f"hung >{HANG_SECS}s — killed + relaunched (retry {retries})")
            print(f"{slug}: hung — killed + relaunched pid={pid} (retry {retries}).")
            time.sleep(poll_sec)
            continue

        # HEALTHY.
        pc = state.get("phases", {}).get("per-chapter", {})
        _write_registry(
            slug,
            status="running",
            phase=f"{state.get('phase')}/{state.get('phase_status')}",
            current_chapter=pc.get("current_chapter"),
            completed=len(pc.get("completed_slugs", [])),
            failed=len(pc.get("failed_slugs", [])),
            llm_child=children,
            retries=retries,
            real_spend_usd=cost_ceiling_check(book_dir)["real_spend_usd"],
        )
        time.sleep(poll_sec)

    _write_registry(slug, status="watch-timeout", retries=retries)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("status", "ensure", "watch"):
        sp = sub.add_parser(name)
        sp.add_argument("slug")
        if name == "watch":
            sp.add_argument("--poll-sec", type=int, default=POLL_SEC)
    args = p.parse_args(argv)
    if args.cmd == "status":
        return cmd_status(args.slug)
    if args.cmd == "ensure":
        return cmd_ensure(args.slug)
    if args.cmd == "watch":
        return cmd_watch(args.slug, poll_sec=args.poll_sec)
    return 1


if __name__ == "__main__":
    sys.exit(main())
