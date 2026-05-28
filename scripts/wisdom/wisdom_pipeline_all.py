#!/usr/bin/env python3
"""Full KAHSKOLE translation pipeline orchestrator.

Runs Phase 2 (adapt) then Phase 3 (challenge) in sequence.
Both drivers are idempotent — safe to re-run at any point.

Usage:
    python scripts/wisdom/wisdom_pipeline_all.py
    python scripts/wisdom/wisdom_pipeline_all.py --phase adapt
    python scripts/wisdom/wisdom_pipeline_all.py --phase challenge
    python scripts/wisdom/wisdom_pipeline_all.py --binder 35
    python scripts/wisdom/wisdom_pipeline_all.py --status
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VENV = REPO / "CONTENT/_shared/source-library/.venv/bin/python"
EXTRACT_ROOT = REPO / "CONTENT/_shared/source-library/extracted/wisdom"


def _count_stages() -> dict[str, int]:
    counts: dict[str, int] = {}
    for shelf in EXTRACT_ROOT.iterdir():
        if not shelf.is_dir():
            continue
        for book in shelf.iterdir():
            yml = book / "bundle.yml"
            if not yml.exists():
                continue
            for line in yml.read_text().splitlines():
                if line.startswith("stage:"):
                    stage = line.split(":", 1)[1].strip()
                    counts[stage] = counts.get(stage, 0) + 1
    return counts


def _print_status() -> None:
    counts = _count_stages()
    total = sum(counts.values())
    print(f"\nKAHSKOLE Pipeline Status ({total} chapters)")
    print(f"{'='*40}")
    for stage in ("reviewed", "translated", "adapted", "challenged"):
        n = counts.get(stage, 0)
        bar = "█" * (n // 3) if n else ""
        print(f"  {stage:>12}: {n:>3}  {bar}")
    other = {k: v for k, v in counts.items() if k not in ("reviewed", "translated", "adapted", "challenged")}
    for stage, n in other.items():
        print(f"  {stage:>12}: {n:>3}")
    print()


def _run_phase(phase: str, binder: int | None, dry_run: bool) -> int:
    driver = {
        "adapt": REPO / "scripts/wisdom/wisdom_adapt_all.py",
        "challenge": REPO / "scripts/wisdom/wisdom_challenge_all.py",
    }[phase]
    cmd = [str(VENV), str(driver)]
    if dry_run:
        cmd.append("--dry-run")
    if binder:
        cmd += ["--binder", str(binder)]
    print(f"\n{'='*60}")
    print(f"Starting Phase: {phase.upper()}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=REPO)
    return result.returncode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["adapt", "challenge", "both"], default="both")
    ap.add_argument("--binder", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.status:
        _print_status()
        return

    phases = ["adapt", "challenge"] if args.phase == "both" else [args.phase]

    for phase in phases:
        rc = _run_phase(phase, args.binder, args.dry_run)
        if rc != 0:
            print(f"\n❌ Phase '{phase}' exited with code {rc}. Stopping.")
            sys.exit(rc)

    print("\n✅ Pipeline complete.")
    _print_status()


if __name__ == "__main__":
    main()
