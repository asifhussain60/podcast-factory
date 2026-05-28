#!/usr/bin/env python3
"""Cross-wave autonomous execution chain driver.

Sequences multiple waves of the podcast pipeline refactor end-to-end.
Each wave is executed as a run_wave.py subprocess; acceptance gates are
validated between waves; a global spend cap is enforced throughout.

USAGE
    # Step 1 — authorize a chain (one-time, writes wave-chain-auth.json):
    python3 scripts/podcast/run_waves_chain.py authorize \\
        --waves 1 2 3 4 5 6 \\
        --spend-cap-total 50.0 \\
        --spend-cap-per-wave 15.0

    # Step 2 — walk away, let it run:
    python3 scripts/podcast/run_waves_chain.py run

    # Check current authorization and recent log:
    python3 scripts/podcast/run_waves_chain.py status

    # Revoke an authorization (deletes wave-chain-auth.json):
    python3 scripts/podcast/run_waves_chain.py revoke

EXIT CODES
    0 — chain complete (all authorized waves DONE)
    1 — error (missing auth, code defect, bad args)
    2 — chain halted at human-review gate (a wave requires operator action)
    3 — chain interrupted by spend cap
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from _paths import REPO_ROOT

AUTH_FILE = (
    REPO_ROOT / "_workspace" / "plan" / "operations" / "wave-chain-auth.json"
)
CHAIN_LOG_FILE = (
    REPO_ROOT / "_workspace" / "plan" / "refactor" / "wave-chain-log.jsonl"
)
RUN_WAVE = REPO_ROOT / "scripts" / "podcast" / "run_wave.py"
LOOP_INTEL = REPO_ROOT / "_workspace" / "prompts" / "loop-intelligence.md"

EXIT_DONE = 0
EXIT_ERROR = 1
EXIT_HALTED = 2
EXIT_SPEND_CAP = 3

WAVE_NAMES: dict[int, str] = {
    1: "Foundation & Guardrails",
    2: "Observability + Polish",
    3: "Corpus Validation",
    4: "Control Plane",
    5: "Deferred + Self-Learning",
    6: "Archetype Completion",
}

# Exit code meanings returned by run_wave.py subprocess.
_RW_ALREADY_DONE = 0
_RW_EXECUTED_DONE = 2
_RW_HALTED = 3
_RW_P9_VIOLATED = 4


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(event: str, status: str, message: str,
         wave: int | None = None, details: dict | None = None) -> None:
    CHAIN_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": _now_iso(),
        "event": event,
        "wave": wave,
        "status": status,
        "message": message,
        "details": details or {},
    }
    with CHAIN_LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _total_spend_usd() -> float:
    """Sum cost-ledger.jsonl across all books in content/drafts/."""
    books_dir = REPO_ROOT / "content" / "drafts"
    total = 0.0
    for ledger in books_dir.glob("**/_system/cost-ledger.jsonl"):
        for line in ledger.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                total += float(row.get("cost_usd", 0))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    return total


def _load_auth() -> dict | None:
    """Return parsed auth envelope, or None if missing/corrupt."""
    if not AUTH_FILE.exists():
        return None
    try:
        return json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _display_path(p: Path) -> str:
    """Return a repo-relative path string, or absolute if outside the repo."""
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def _append_loop_intel_iteration(waves: list[int], outcome: str) -> None:
    """Append one line to the loop-intelligence Iteration Log."""
    if not LOOP_INTEL.exists():
        return
    text = LOOP_INTEL.read_text(encoding="utf-8")
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    wave_label = f"Chain W{waves[0]}–W{waves[-1]}" if len(waves) > 1 else f"W{waves[0]}"
    line = (
        f"- {date} | {wave_label} | {outcome} "
        f"| SP-004 (chain driver) | None\n"
    )
    # Insert before the last blank line(s) / end of file
    if "## Iteration Log" in text:
        text = text.rstrip("\n") + "\n" + line
        LOOP_INTEL.write_text(text, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────────────


def cmd_authorize(args: argparse.Namespace) -> int:
    """Write the pre-authorization envelope."""
    waves: list[int] = sorted(set(args.waves))
    auth = {
        "authorized_at": _now_iso(),
        "authorized_by": "operator",
        "waves": waves,
        "spend_cap_total_usd": args.spend_cap_total,
        "spend_cap_per_wave_usd": args.spend_cap_per_wave,
        "note": args.note or f"Authorized waves {waves}",
    }
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps(auth, indent=2, ensure_ascii=False) + "\n")
    _log(
        "authorized", "ok",
        f"Chain authorized: waves={waves} "
        f"cap_total=${auth['spend_cap_total_usd']:.2f} "
        f"cap_per_wave=${auth['spend_cap_per_wave_usd']:.2f}",
        details=auth,
    )
    print(f"[chain] Authorization written to {_display_path(AUTH_FILE)}")
    print(f"[chain]   waves         : {waves}")
    print(f"[chain]   cap total     : ${auth['spend_cap_total_usd']:.2f}")
    print(f"[chain]   cap per-wave  : ${auth['spend_cap_per_wave_usd']:.2f}")
    print(f"[chain]   note          : {auth['note']}")
    print()
    print("[chain] Run:  python3 scripts/podcast/run_waves_chain.py run")
    return EXIT_DONE


def cmd_revoke(args: argparse.Namespace) -> int:  # noqa: ARG001
    """Delete the pre-authorization envelope."""
    if not AUTH_FILE.exists():
        print("[chain] No authorization file to revoke.")
        return EXIT_DONE
    AUTH_FILE.unlink()
    _log("revoked", "ok", "Authorization file deleted.")
    print("[chain] Authorization revoked.")
    return EXIT_DONE


def cmd_status(args: argparse.Namespace) -> int:  # noqa: ARG001
    """Show current authorization and recent chain log entries."""
    auth = _load_auth()
    if auth is None:
        print("[chain status] No valid authorization file found.")
        print(
            "[chain status] Create one: "
            "python3 scripts/podcast/run_waves_chain.py authorize --waves 1 2 ..."
        )
    else:
        print("[chain status] Authorization")
        print(f"  authorized_at  : {auth.get('authorized_at', '?')}")
        print(f"  authorized_by  : {auth.get('authorized_by', '?')}")
        print(f"  waves          : {auth.get('waves', [])}")
        print(f"  cap_total      : ${auth.get('spend_cap_total_usd', 0):.2f}")
        print(f"  cap_per_wave   : ${auth.get('spend_cap_per_wave_usd', 0):.2f}")
        print(f"  note           : {auth.get('note', '')}")

    if CHAIN_LOG_FILE.exists():
        lines = [
            l for l in CHAIN_LOG_FILE.read_text(encoding="utf-8").splitlines()
            if l.strip()
        ]
        rows = []
        for l in lines:
            try:
                rows.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        tail = rows[-10:]
        print(f"\n[chain status] Last {len(tail)} of {len(rows)} log entries:")
        for row in tail:
            wave = f"W{row['wave']}" if row.get("wave") else "chain"
            msg = row.get("message", "")[:80]
            print(f"  {row['ts']}  {wave:5s}  {row['status']:20s}  {msg}")
    else:
        print("\n[chain status] No chain log yet.")

    return EXIT_DONE


def cmd_run(args: argparse.Namespace) -> int:  # noqa: ARG001
    """Execute the authorized wave chain."""
    auth = _load_auth()
    if auth is None:
        print(
            f"[chain] ERROR: no valid authorization at "
            f"{_display_path(AUTH_FILE)}",
            file=sys.stderr,
        )
        print(
            "[chain] Run first:  "
            "python3 scripts/podcast/run_waves_chain.py authorize --waves 1 2 ...",
            file=sys.stderr,
        )
        return EXIT_ERROR

    waves: list[int] = auth.get("waves", [])
    cap_total: float = float(auth.get("spend_cap_total_usd", 50.0))
    cap_per_wave: float = float(auth.get("spend_cap_per_wave_usd", 15.0))

    if not waves:
        print("[chain] ERROR: authorization file has an empty 'waves' list.", file=sys.stderr)
        return EXIT_ERROR

    _log(
        "chain_start", "running",
        f"Chain started: waves={waves} cap_total=${cap_total:.2f}",
        details={"authorized_at": auth.get("authorized_at"), "waves": waves},
    )

    print("[chain] " + "━" * 55)
    print("[chain] Autonomous wave chain — starting")
    print(f"[chain]   waves        : {waves}")
    print(f"[chain]   cap total    : ${cap_total:.2f}")
    print(f"[chain]   cap per-wave : ${cap_per_wave:.2f}")
    print("[chain] " + "━" * 55)
    print()

    baseline_spend = _total_spend_usd()

    for wave_n in waves:
        wave_name = WAVE_NAMES.get(wave_n, f"W{wave_n}")
        print(f"[chain] ── Wave {wave_n} — {wave_name} " + "─" * 30)

        # Global spend cap pre-check
        chain_spend = _total_spend_usd() - baseline_spend
        if chain_spend >= cap_total:
            msg = (
                f"Global spend cap ${cap_total:.2f} reached "
                f"(${chain_spend:.2f} spent). Chain halted before W{wave_n}."
            )
            print(f"[chain] SPEND CAP: {msg}")
            _log("spend_cap_exceeded", "halted", msg, wave=wave_n)
            _append_loop_intel_iteration(waves, "SpendCapHalt")
            return EXIT_SPEND_CAP

        wave_spend_before = _total_spend_usd()

        proc = subprocess.run(
            [sys.executable, str(RUN_WAVE), str(wave_n)],
            cwd=str(REPO_ROOT / "scripts" / "podcast"),
        )

        wave_cost = _total_spend_usd() - wave_spend_before
        _log(
            "wave_spend", "recorded",
            f"W{wave_n} cost: ${wave_cost:.4f}",
            wave=wave_n, details={"cost_usd": wave_cost},
        )

        if proc.returncode == _RW_ALREADY_DONE:
            print(f"[chain] W{wave_n}: already DONE — continuing.")
            _log("wave_done", "skipped", "Wave was already DONE.", wave=wave_n)
            continue

        if proc.returncode == _RW_EXECUTED_DONE:
            print(f"[chain] W{wave_n}: ✅ DONE")
            _log("wave_done", "done", "Wave executed and completed.", wave=wave_n)
            if wave_cost > cap_per_wave:
                msg = (
                    f"W{wave_n} per-wave cap ${cap_per_wave:.2f} exceeded "
                    f"(${wave_cost:.4f} spent)."
                )
                print(f"[chain] ⚠  SPEND WARNING: {msg}")
                _log("wave_spend_warning", "over_cap", msg, wave=wave_n)
            continue

        if proc.returncode == _RW_HALTED:
            msg = f"W{wave_n} halted at human-review gate. Chain suspended."
            print(f"[chain] ⏸  HALTED: {msg}")
            print(
                "[chain] Resolve the blocker, then resume: "
                "python3 scripts/podcast/run_waves_chain.py run"
            )
            _log("wave_halted", "halted", msg, wave=wave_n)
            _append_loop_intel_iteration(waves, "Halted")
            return EXIT_HALTED

        if proc.returncode == _RW_P9_VIOLATED:
            msg = (
                f"W{wave_n} completed but P-9 invariant "
                "(test_challenger.py) is RED. Chain halted."
            )
            print(f"[chain] 🔴  P-9 VIOLATED: {msg}")
            _log("p9_violated", "error", msg, wave=wave_n)
            _append_loop_intel_iteration(waves, "P9Violated")
            return EXIT_ERROR

        # Any other non-zero returncode = code defect
        msg = f"W{wave_n} exited with code {proc.returncode}. Chain halted."
        print(f"[chain] ✗  ERROR: {msg}")
        _log(
            "wave_error", "error", msg, wave=wave_n,
            details={"exit_code": proc.returncode},
        )
        _append_loop_intel_iteration(waves, "Error")
        return EXIT_ERROR

    total_spent = _total_spend_usd() - baseline_spend
    print()
    print("[chain] " + "━" * 55)
    print(f"[chain] ✅ Chain complete — all {len(waves)} wave(s) DONE.")
    print(f"[chain]   Total spend this run : ${total_spent:.4f}")
    print("[chain] " + "━" * 55)
    _log(
        "chain_done", "done",
        f"Chain complete. waves={waves} total_spend=${total_spent:.4f}",
        details={"waves": waves, "total_spend_usd": total_spent},
    )
    _append_loop_intel_iteration(waves, "Completed")
    return EXIT_DONE


# ─────────────────────────────────────────────────────────────────────────────
# Argument parser + main
# ─────────────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_waves_chain.py",
        description=(
            "Autonomous cross-wave execution chain driver. "
            "Authorize a wave sequence once, then run end-to-end."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0 — chain complete (all waves DONE)\n"
            "  1 — error (missing auth, code defect)\n"
            "  2 — chain halted at human-review gate\n"
            "  3 — chain interrupted by spend cap"
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # authorize
    auth_p = sub.add_parser(
        "authorize",
        help="Write pre-authorization envelope (spend caps + wave sequence).",
    )
    auth_p.add_argument(
        "--waves",
        type=int,
        nargs="+",
        required=True,
        choices=[1, 2, 3, 4, 5, 6],
        metavar="N",
        help="Wave numbers to authorize, e.g. --waves 1 2 3.",
    )
    auth_p.add_argument(
        "--spend-cap-total",
        type=float,
        default=50.0,
        metavar="USD",
        help="Global spend cap for the entire chain run (default $50.00).",
    )
    auth_p.add_argument(
        "--spend-cap-per-wave",
        type=float,
        default=15.0,
        metavar="USD",
        help="Per-wave spend warning threshold (default $15.00).",
    )
    auth_p.add_argument(
        "--note",
        type=str,
        default="",
        help="Optional human note recorded in the authorization file.",
    )

    # run
    sub.add_parser("run", help="Execute the currently authorized wave chain.")

    # status
    sub.add_parser(
        "status",
        help="Show authorization and recent chain-log entries.",
    )

    # revoke
    sub.add_parser(
        "revoke",
        help="Delete the authorization file (stops any future run).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "authorize": cmd_authorize,
        "run": cmd_run,
        "status": cmd_status,
        "revoke": cmd_revoke,
    }
    handler = dispatch.get(args.cmd)
    if handler is None:
        print(f"[chain] Unknown command: {args.cmd}", file=sys.stderr)
        return EXIT_ERROR
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
