#!/usr/bin/env python3
"""Wave kickoff harness for the podcast pipeline.

Single entry point invoked at the start of each wave (W1..W5). Reads the
canonical acceptance checklist (_workspace/plan/operations/per-book-ship-checklist.md) to
determine done-status, then dispatches to per-wave runners — or just reports
status with --check.

Per `_workspace/plan/refactor/plan.yaml` P1.4 spec. The dispatchers in this
file are minimal stubs that get filled in as the underlying phases ship.

USAGE
    python3 scripts/podcast/run_wave.py {1,2,3,4,5}
    python3 scripts/podcast/run_wave.py --check {1,2,3,4,5}
    python3 scripts/podcast/run_wave.py 3 --book <slug>
    python3 scripts/podcast/run_wave.py 5 --phase <phase-id>

EXIT CODES
    0 — wave already DONE (all acceptance rows checked); zero work performed
    1 — error (bad args, system_check failure, file missing, cost overrun)
    2 — wave executed and now DONE
    3 — wave halted at human-review gate (dispatcher returned without finishing)
    4 — wave DONE but P-9 invariant violated (test_challenger.py red on develop)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

# Repo root is two levels up from this file (scripts/podcast/run_wave.py).
REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DIR = REPO_ROOT / "_workspace" / "plan"
ACCEPTANCE_FILE = PLAN_DIR / "operations" / "wave-acceptance-checklist.md"
DEFAULT_ACCEPTANCE_FILE = ACCEPTANCE_FILE
LEGACY_ACCEPTANCE_FILE = PLAN_DIR / "operations" / "per-book-ship-checklist.md"
REFACTOR_DIR = PLAN_DIR / "refactor"
WAVE_EVENTS_FILE = REFACTOR_DIR / "wave-execution-events.jsonl"
BOOKS_DIR = REPO_ROOT / "content" / "drafts"
CHALLENGER_TEST = REPO_ROOT / "scripts" / "podcast" / "test_challenger.py"

# Exit codes — see module docstring + yaml P1.4 acceptance.
EXIT_DONE = 0
EXIT_ERROR = 1
EXIT_EXECUTED_DONE = 2
EXIT_HALTED_REVIEW = 3
EXIT_P9_VIOLATED = 4

# Wave 1..5 metadata; mirrors podcast-plan.yaml waves[].
WAVE_NAMES: dict[int, str] = {
    1: "Foundation & Guardrails",
    2: "Observability + Polish",
    3: "Corpus Validation",
    4: "Control Plane",
    5: "Deferred + Self-Learning",
}

WAVE_LETTERS: dict[int, str] = {
    1: "A",
    2: "B",
    3: "C",
    4: "D",
    5: "E",
}

COST_CAP_HARD_DEFAULT = 50.0  # P6.3 default; override via --cost-cap-hard
WAVE_BRANCH_PREFIX = "refactor/wave-"
DEVELOP_BRANCH = "develop"


def _git(args: Sequence[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a git command at repo root with optional output capture."""
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=check,
        text=True,
        capture_output=capture,
    )


def _wave_branch_name(wave_n: int) -> str:
    return f"{WAVE_BRANCH_PREFIX}{wave_n}"


def _current_branch() -> str:
    proc = _git(["branch", "--show-current"])
    return proc.stdout.strip()


def _working_tree_dirty() -> bool:
    proc = _git(["status", "--porcelain"])
    return bool(proc.stdout.strip())


def _ensure_wave_branch(wave_n: int) -> str:
    """Ensure execution happens on refactor/wave-<n>, creating from develop if needed."""
    expected = _wave_branch_name(wave_n)
    current = _current_branch()
    if current == expected:
        return expected

    if _working_tree_dirty():
        raise RuntimeError(
            "working tree is dirty; commit or stash changes before switching wave branches"
        )

    _git(["fetch", "origin", DEVELOP_BRANCH, "--prune"], check=False)

    exists_local = _git(["rev-parse", "--verify", expected], check=False)
    if exists_local.returncode == 0:
        _git(["checkout", expected])
        print(f"[run_wave] switched to existing wave branch: {expected}")
        return expected

    _git(["checkout", DEVELOP_BRANCH])
    _git(["pull", "--ff-only", "origin", DEVELOP_BRANCH], check=False)
    _git(["checkout", "-b", expected])
    _git(["push", "-u", "origin", expected], check=False)
    print(f"[run_wave] created and switched to wave branch: {expected}")
    return expected


def _run_wave_cleanup_gates(wave_n: int) -> int:
    """Run mandatory cleanup checks at wave completion."""
    print(f"[run_wave] running wave-end cleanup gates for W{wave_n}…")

    if os.environ.get("RUN_WAVE_ENABLE_PLANNER_UI") != "1":
        print("[run_wave] planner UI cleanup gates skipped (chat-only mode).")
        return EXIT_DONE

    plan_dashboard = REPO_ROOT / "plan-dashboard"
    if plan_dashboard.exists():
        proc = subprocess.run(
            ["npm", "run", "check"],
            cwd=plan_dashboard,
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            print("[run_wave] cleanup gate failed: plan-dashboard check is red.", file=sys.stderr)
            return EXIT_ERROR

        snap = subprocess.run(
            ["npm", "run", "snapshot"],
            cwd=plan_dashboard,
            text=True,
            capture_output=True,
        )
        if snap.returncode != 0:
            print(snap.stdout)
            print(snap.stderr, file=sys.stderr)
            print("[run_wave] cleanup gate failed: snapshot refresh failed.", file=sys.stderr)
            return EXIT_ERROR

    return EXIT_DONE


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _planner_updates_enabled() -> bool:
    # Chat-first mode: planner telemetry is OFF by default.
    # Set RUN_WAVE_ENABLE_PLANNER_UI=1 to opt back in.
    if os.environ.get("RUN_WAVE_ENABLE_PLANNER_UI") != "1":
        return False
    if ACCEPTANCE_FILE != DEFAULT_ACCEPTANCE_FILE:
        return False
    return True


def _refresh_planner_snapshot() -> None:
    if not _planner_updates_enabled():
        return
    plan_dashboard = REPO_ROOT / "plan-dashboard"
    if not plan_dashboard.exists():
        return
    subprocess.run(
        ["npm", "run", "snapshot", "--", "--trace-steps"],
        cwd=plan_dashboard,
        text=True,
        capture_output=True,
        check=False,
    )


def _append_wave_event(*, event_type: str, wave_n: int, status: str, message: str, details: dict | None = None) -> None:
    if not _planner_updates_enabled():
        return
    WAVE_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": _now_iso(),
        "wave": wave_n,
        "wave_letter": WAVE_LETTERS.get(wave_n, str(wave_n)),
        "event_type": event_type,
        "status": status,
        "message": message,
        "details": details or {},
    }
    with WAVE_EVENTS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    _refresh_planner_snapshot()


def _missing_task_ids(text: str, wave_n: int) -> list[str]:
    rows = parse_wave_rows(text).get(wave_n, [])
    ids = [task_id for status, task_id in rows if status != "x"]
    out: list[str] = []
    seen: set[str] = set()
    for tid in ids:
        if tid in seen:
            continue
        seen.add(tid)
        out.append(tid)
    return out


def _align_prior_waves(args: argparse.Namespace) -> int:
    text = ACCEPTANCE_FILE.read_text()
    gaps = [w for w in range(1, args.wave) if not is_wave_done(text, w)]

    if not gaps:
        _append_wave_event(
            event_type="collective_quality",
            wave_n=args.wave,
            status="passed",
            message="Collective quality check passed for all prior waves.",
        )
        return EXIT_DONE

    _append_wave_event(
        event_type="mandatory_alignment",
        wave_n=args.wave,
        status="started",
        message="Prior-wave gaps detected. Strict wave-order gate enforced.",
        details={"gap_waves": gaps},
    )
    print(f"[run_wave] strict wave-order gate blocked W{args.wave}; incomplete prior waves: {gaps}")

    gap_details = {
        str(gap_wave): _missing_task_ids(ACCEPTANCE_FILE.read_text(), gap_wave)
        for gap_wave in gaps
    }
    _append_wave_event(
        event_type="mandatory_alignment",
        wave_n=args.wave,
        status="blocked",
        message="Earlier wave(s) must complete before this wave can start.",
        details={"gap_waves": gaps, "missing_task_ids_by_wave": gap_details},
    )
    return EXIT_HALTED_REVIEW


def _merge_wave_to_develop_and_return(wave_n: int) -> int:
    """Merge completed wave branch to develop, then return to wave branch."""
    wave_branch = _wave_branch_name(wave_n)
    current = _current_branch()
    if current != wave_branch:
        _git(["checkout", wave_branch])

    if _working_tree_dirty():
        _git(["add", "-A"])
        _git(["commit", "-m", f"chore(wave-{wave_n}): wave completion cleanup checkpoint"], check=False)

    _git(["fetch", "origin", DEVELOP_BRANCH, "--prune"], check=False)
    _git(["checkout", DEVELOP_BRANCH])
    _git(["pull", "--ff-only", "origin", DEVELOP_BRANCH], check=False)
    _git(["merge", "--no-ff", wave_branch, "-m", f"merge: wave {wave_n} completion"])
    _git(["push", "origin", DEVELOP_BRANCH], check=False)

    _git(["checkout", wave_branch])
    _git(["merge", "--ff-only", DEVELOP_BRANCH], check=False)
    _git(["push", "origin", wave_branch], check=False)
    print(f"[run_wave] wave completion merged to {DEVELOP_BRANCH} and returned to {wave_branch}")
    return EXIT_DONE

# ───────────────────────────────────────────────────────────────────────────────
# Acceptance-file parsing
# ───────────────────────────────────────────────────────────────────────────────

# Wave anchors look like:    ## Wave 1 — Foundation & Guardrails ...
WAVE_HEADING_RE = re.compile(r"^##\s+Wave\s+(\d+)\b", re.MULTILINE)
# Rows look like:             - [ ] **P1.4** ✅ ...   OR   - [x] **P1.4** ✅ ...
ROW_RE = re.compile(r"^- \[([ x])\] \*\*(P\d+(?:\.\d+\w?)?)\*\*", re.MULTILINE)


def parse_wave_rows(text: str) -> dict[int, list[tuple[str, str]]]:
    """Parse acceptance-criteria.md text. Return {wave_n: [(status, id), ...]}.

    `status` is "x" (checked) or " " (unchecked). `id` is the bold task id
    (e.g., "P1.4", "P17.1"). One id may appear multiple times per wave
    (e.g., several acceptance bullets under P1.4); that's expected.
    """
    boundaries: list[tuple[int | None, int]] = [
        (int(m.group(1)), m.start()) for m in WAVE_HEADING_RE.finditer(text)
    ]
    if not boundaries:
        return {}
    boundaries.append((None, len(text)))

    result: dict[int, list[tuple[str, str]]] = {}
    for i in range(len(boundaries) - 1):
        wave_n, start = boundaries[i]
        _, end = boundaries[i + 1]
        if wave_n is None:
            continue
        slice_text = text[start:end]
        result[wave_n] = [(m.group(1), m.group(2)) for m in ROW_RE.finditer(slice_text)]
    return result


def wave_status(text: str, wave_n: int) -> tuple[int, int]:
    """Return (checked_count, total_count) for the wave."""
    wave_rows = parse_wave_rows(text)
    rows = wave_rows.get(wave_n, [])
    checked = sum(1 for status, _ in rows if status == "x")
    return checked, len(rows)


def is_wave_done(text: str, wave_n: int) -> bool:
    """A wave is DONE iff it has at least one row AND every row is checked."""
    checked, total = wave_status(text, wave_n)
    return total > 0 and checked == total


# ───────────────────────────────────────────────────────────────────────────────
# Cost-ledger inspection (W3 pre-flight guard)
# ───────────────────────────────────────────────────────────────────────────────


def book_cost_usd(book_slug: str) -> float:
    """Sum the `cost_usd` field across cost-ledger.jsonl rows for a book.

    Returns 0.0 if the ledger file doesn't exist yet (no spend has happened).
    Tolerates malformed lines (skips them) rather than crashing the harness.
    """
    ledger = BOOKS_DIR / book_slug / "_system" / "cost-ledger.jsonl"
    if not ledger.exists():
        return 0.0
    total = 0.0
    for line in ledger.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            total += float(row.get("cost_usd", 0))
        except (TypeError, ValueError):
            continue
    return total


# ───────────────────────────────────────────────────────────────────────────────
# P-9 invariant check
# ───────────────────────────────────────────────────────────────────────────────


def p9_invariant_green() -> bool:
    """Run test_challenger.py once; return True iff it exits 0.

    Tolerates the script's absence (returns True) — the P-9 invariant is
    only enforceable once the challenger regression harness exists.
    """
    if not CHALLENGER_TEST.exists():
        return True
    proc = subprocess.run(
        [sys.executable, str(CHALLENGER_TEST)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.returncode == 0


# ───────────────────────────────────────────────────────────────────────────────
# Per-wave dispatchers
#
# Each dispatcher is intentionally a thin stub that prints the per-phase work
# its wave will require, then halts. Per-phase work lands in the corresponding
# phase commits (P1.1 / P1.2 / P2.x / etc); when a phase ships, its dispatcher
# stub here is replaced with the real callable.
# ───────────────────────────────────────────────────────────────────────────────


def _print_phase_status(label: str, status: str) -> None:
    pad = 36
    print(f"[run_wave]   {label.ljust(pad)} — {status}")


def _run_phase_registry(args: argparse.Namespace, wave_n: int) -> int:
    """Iterate the wave's phase registry autonomously until convergence.

    Runs a red-green convergence loop: each pass visits every phase in
    registry order. Phases already done are skipped. Phases that complete
    mark their acceptance rows. Halted/blocked phases are noted but the
    loop CONTINUES to the next phase — a single blocked phase never aborts
    the wave.

    The loop terminates when a full pass produces no new completions
    (convergence). At that point all remaining halted phases are reported
    together as a consolidated blocker summary.

    Phases that raise an error (not just halt) abort immediately — an error
    indicates a code defect, not a missing deliverable.
    """
    try:
        from scripts.podcast import phases as _phases_pkg  # type: ignore
        from scripts.podcast import _acceptance  # type: ignore
    except ImportError:
        sys.path.insert(0, str(REPO_ROOT))
        from scripts.podcast import phases as _phases_pkg  # type: ignore
        from scripts.podcast import _acceptance  # type: ignore

    phase_list = _phases_pkg.wave_phases(wave_n)
    if not phase_list:
        print(f"[run_wave] W{wave_n} phase registry is empty — no autonomous work to drive.")
        print(f"[run_wave]   Land per-phase runners under scripts/podcast/phases/ and append")
        print(f"[run_wave]   them to phases/__init__.py REGISTRY[{wave_n}].")
        return EXIT_HALTED_REVIEW

    print(f"[run_wave] W{wave_n} ({WAVE_NAMES[wave_n]}) — {len(phase_list)} phase(s) registered")
    print(f"[run_wave] Starting red-green convergence loop…")
    print()

    pass_number = 0
    completed_ever: set[str] = set()

    while True:
        pass_number += 1
        new_completions = 0
        halted_this_pass: list[tuple[str, object]] = []  # (pid, result)

        print(f"[run_wave] ── Pass {pass_number} ──────────────────────────────────────────")

        for mod in phase_list:
            pid = getattr(mod, "PHASE_ID", "?")
            desc = getattr(mod, "DESCRIPTION", "")

            if pid in completed_ever:
                _print_phase_status(f"{pid}", "✓ done (skip)")
                continue

            _print_phase_status(f"{pid} {desc[:50]}", "checking…")

            if mod.is_done(REPO_ROOT):
                _print_phase_status(f"{pid}", "✓ already done (idempotent skip)")
                n = _acceptance.mark_task_rows_in_file(pid, acceptance_file=ACCEPTANCE_FILE)
                if n > 0:
                    _print_phase_status(f"  └─ marked", f"{n} acceptance row(s) → [x]")
                completed_ever.add(pid)
                new_completions += 1
                continue

            try:
                result = mod.execute(REPO_ROOT)
            except Exception as e:  # noqa: BLE001
                _print_phase_status(f"{pid}", f"✗ ERROR: {e!r}")
                return EXIT_ERROR

            if result.status == "done":
                _print_phase_status(f"{pid}", f"✓ done — {result.message}")
                for rid in result.rows_marked:
                    n = _acceptance.mark_task_rows_in_file(rid, acceptance_file=ACCEPTANCE_FILE)
                    if n > 0:
                        _print_phase_status(f"  └─ marked", f"{n} row(s) for {rid} → [x]")
                completed_ever.add(pid)
                new_completions += 1
            elif result.status == "halted":
                _print_phase_status(f"{pid}", f"⏸ blocked — continuing to next phase")
                halted_this_pass.append((pid, result))
                # ← CONTINUE — do NOT break; evaluate every remaining phase
            else:
                _print_phase_status(f"{pid}", f"✗ ERROR — {result.message}")
                return EXIT_ERROR

        print()
        print(
            f"[run_wave] Pass {pass_number} complete — "
            f"{new_completions} new completion(s), "
            f"{len(halted_this_pass)} blocked phase(s)."
        )
        print()

        # Convergence: no new completions in this pass → loop cannot make further progress.
        if new_completions == 0:
            break

        # If no blockers remain, also stop — everything done.
        if not halted_this_pass:
            break

    # ── Convergence reached ──────────────────────────────────────────────────
    text = ACCEPTANCE_FILE.read_text()
    if is_wave_done(text, wave_n):
        print(f"[run_wave] ✅ W{wave_n} DONE — every acceptance row is checked.")
        return EXIT_EXECUTED_DONE

    # Report all remaining blockers together.
    checked, total = wave_status(text, wave_n)
    still_blocked = [pid for pid, _ in halted_this_pass]

    print(f"[run_wave] W{wave_n} converged at {checked}/{total} acceptance rows checked.")
    print(f"[run_wave] {len(still_blocked)} phase(s) still blocked (operator action required):")
    print()
    for pid, result in halted_this_pass:
        print(f"  ┌── {pid} ─────────────────────────────────────────────")
        for line in str(result.message).splitlines():
            print(f"  │  {line}")
        for ep in getattr(result, "evidence_paths", []):
            print(f"  │  → {ep}")
        print(f"  └────────────────────────────────────────────────────")
        print()

    return EXIT_HALTED_REVIEW


def run_wave_1(args: argparse.Namespace) -> int:
    """W1 — Foundation & Guardrails. Iterates the phase registry."""
    return _run_phase_registry(args, 1)


def run_wave_2(args: argparse.Namespace) -> int:
    """W2 — Observability + Polish. Iterates the W2 phase registry."""
    return _run_phase_registry(args, 2)


def run_wave_3(args: argparse.Namespace) -> int:
    """W3 — Corpus Validation. Iterates the W3 phase registry."""
    return _run_phase_registry(args, 3)


def run_wave_4(args: argparse.Namespace) -> int:
    """W4 — Control Plane. Iterates the W4 phase registry."""
    return _run_phase_registry(args, 4)


def run_wave_5(args: argparse.Namespace) -> int:
    """W5 — Deferred + Self-Learning. Iterates the W5 phase registry."""
    return _run_phase_registry(args, 5)


DISPATCHERS = {
    1: run_wave_1,
    2: run_wave_2,
    3: run_wave_3,
    4: run_wave_4,
    5: run_wave_5,
}

# ───────────────────────────────────────────────────────────────────────────────
# --check command (report-only; no execution)
# ───────────────────────────────────────────────────────────────────────────────


def cmd_check(text: str, wave_n: int) -> int:
    """Report wave done-status without dispatching. Always exit 0 (reporting only)."""
    name = WAVE_NAMES.get(wave_n, f"W{wave_n}")
    rows = parse_wave_rows(text).get(wave_n, [])
    checked = sum(1 for s, _ in rows if s == "x")
    total = len(rows)
    pct = (100.0 * checked / total) if total else 0.0
    is_done = total > 0 and checked == total
    verdict = "DONE" if is_done else "PENDING"
    print(
        f"[run_wave --check] Wave {wave_n} ({name}): "
        f"{checked}/{total} acceptance rows checked ({pct:.1f}%) — {verdict}"
    )
    if not is_done:
        unchecked = [task_id for status, task_id in rows if status != "x"]
        seen: set[str] = set()
        unique: list[str] = []
        for tid in unchecked:
            if tid not in seen:
                seen.add(tid)
                unique.append(tid)
        if unique:
            print("[run_wave --check] Unchecked task ids in this wave:")
            for tid in unique:
                _, sample_total = wave_status(text, wave_n)  # noqa: F841 (kept for symmetry)
                n_unchecked = sum(1 for s, t in rows if t == tid and s != "x")
                n_total = sum(1 for _, t in rows if t == tid)
                print(f"  {tid}: {n_unchecked}/{n_total} bullets unchecked")
    return EXIT_DONE


def _resolve_acceptance_file() -> None:
    global ACCEPTANCE_FILE
    if (
        ACCEPTANCE_FILE == DEFAULT_ACCEPTANCE_FILE
        and not ACCEPTANCE_FILE.exists()
        and LEGACY_ACCEPTANCE_FILE.exists()
    ):
        ACCEPTANCE_FILE = LEGACY_ACCEPTANCE_FILE


# ───────────────────────────────────────────────────────────────────────────────
# Argument parser + main
# ───────────────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_wave.py",
        description=(
            "Wave kickoff harness for the podcast pipeline. "
            "See _workspace/plan/podcast-plan.yaml P1.4."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0 — wave already DONE (no work)\n"
            "  1 — error\n"
            "  2 — wave executed and now DONE\n"
            "  3 — wave halted at human-review gate\n"
            "  4 — wave DONE but P-9 invariant violated"
        ),
    )
    parser.add_argument(
        "wave",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Wave number to invoke (W1..W5).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report wave done-status from per-book-ship-checklist.md without executing.",
    )
    parser.add_argument(
        "--book",
        type=str,
        default=None,
        help="(W3) Book slug; required for W3 corpus invocation.",
    )
    parser.add_argument(
        "--phase",
        type=str,
        default=None,
        help="(W5) Phase id to promote (e.g., P17, P17.1, P18). Required for W5.",
    )
    parser.add_argument(
        "--cost-cap-hard",
        type=float,
        default=COST_CAP_HARD_DEFAULT,
        metavar="USD",
        help=(
            f"Hard cap on per-book cost in USD (default ${COST_CAP_HARD_DEFAULT:.2f}). "
            "W3 invocation refuses if cost-ledger sums exceed this."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # --check is report-only and must remain read-only; avoid branch switching.
    if args.check:
        _resolve_acceptance_file()
        if not ACCEPTANCE_FILE.exists():
            print(
                f"error: acceptance file missing at {ACCEPTANCE_FILE}",
                file=sys.stderr,
            )
            return EXIT_ERROR
        text = ACCEPTANCE_FILE.read_text()
        return cmd_check(text, args.wave)

    # Always operate from the canonical wave branch for this invocation.
    try:
        _ensure_wave_branch(args.wave)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except subprocess.CalledProcessError as exc:
        print(f"error: failed to switch to wave branch: {exc}", file=sys.stderr)
        return EXIT_ERROR

    # Resolve acceptance path after checkout, because the active branch may use
    # a different checklist surface.
    _resolve_acceptance_file()
    if not ACCEPTANCE_FILE.exists():
        print(
            f"error: acceptance file missing at {ACCEPTANCE_FILE}",
            file=sys.stderr,
        )
        return EXIT_ERROR

    text = ACCEPTANCE_FILE.read_text()

    # W3 pre-flight: cost-cap guard only when --book is explicitly supplied.
    if args.wave == 3 and args.book:
        cost = book_cost_usd(args.book)
        if cost > args.cost_cap_hard:
            print(
                f"error: Wave 3 refused — book {args.book!r} cost-ledger sums "
                f"${cost:.2f}, exceeding hard cap ${args.cost_cap_hard:.2f}.",
                file=sys.stderr,
            )
            return EXIT_ERROR

    # W5 pre-flight: if no registry phases exist yet, require --phase to avoid
    # a confusing empty-loop run.  Once phases are wired, the loop drives them all.
    if args.wave == 5 and not args.phase:
        try:
            from scripts.podcast import phases as _phases_pre  # type: ignore
        except ImportError:
            sys.path.insert(0, str(REPO_ROOT))
            from scripts.podcast import phases as _phases_pre  # type: ignore
        if not _phases_pre.wave_phases(5):
            print(
                "error: Wave 5 registry is empty — add pw5_*.py runners first.",
                file=sys.stderr,
            )
            return EXIT_ERROR

    # Idempotency: if the wave is already DONE, exit 0 without dispatching.
    if is_wave_done(text, args.wave):
        checked, total = wave_status(text, args.wave)
        print(
            f"[run_wave] Wave {args.wave} already DONE "
            f"({checked}/{total} acceptance rows checked). No work."
        )
        return EXIT_DONE

    align_rc = _align_prior_waves(args)
    if align_rc != EXIT_DONE:
        return align_rc

    _append_wave_event(
        event_type="wave_start",
        wave_n=args.wave,
        status="started",
        message=f"Wave {args.wave} started in autonomous mode.",
    )

    # Dispatch.
    rc = DISPATCHERS[args.wave](args)

    # Halted at review gate → return that code directly.
    if rc == EXIT_HALTED_REVIEW:
        _append_wave_event(
            event_type="wave_progress",
            wave_n=args.wave,
            status="halted",
            message="Wave halted at review gate.",
        )
        return rc

    # Did the dispatcher leave the wave fully DONE?
    text_after = ACCEPTANCE_FILE.read_text()
    if is_wave_done(text_after, args.wave):
        # Wave just transitioned to DONE → render the plain-language summary
        # into the HTML views (per yaml.waves[id=WN].on_completion).
        try:
            from scripts.podcast import _view_updater  # type: ignore
            result = _view_updater.update_view_for_wave(args.wave)
            if result["updated"]:
                print(
                    f"[run_wave] HTML views updated for W{args.wave}: "
                    f"{', '.join(result['updated'])}"
                )
            elif result["missing_summary"]:
                print(
                    f"[run_wave] W{args.wave} done — no on_completion.html_summary "
                    f"declared in YAML; skipping view update."
                )
        except Exception as e:  # noqa: BLE001 — view update is non-fatal
            print(
                f"[run_wave] WARNING: view update for W{args.wave} failed: {e!r}",
                file=sys.stderr,
            )

        if not p9_invariant_green():
            print(
                "[run_wave] Wave DONE but P-9 invariant violated "
                "(test_challenger.py exit != 0). Inspect _learning/ before proceeding.",
                file=sys.stderr,
            )
            return EXIT_P9_VIOLATED

        cleanup_rc = _run_wave_cleanup_gates(args.wave)
        if cleanup_rc != EXIT_DONE:
            return cleanup_rc

        merge_rc = _merge_wave_to_develop_and_return(args.wave)
        if merge_rc != EXIT_DONE:
            return merge_rc

        _append_wave_event(
            event_type="wave_complete",
            wave_n=args.wave,
            status="completed",
            message=f"Wave {args.wave} completed and merged.",
        )

        return EXIT_EXECUTED_DONE

    # Dispatcher returned a non-halt code but the wave isn't DONE — treat as halt.
    return EXIT_HALTED_REVIEW


if __name__ == "__main__":
    sys.exit(main())
