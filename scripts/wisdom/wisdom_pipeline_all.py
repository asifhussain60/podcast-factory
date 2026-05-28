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

    # K5: emit PEQ summary report after challenge phase completes.
    if "challenge" in phases:
        _emit_peq_summary(args.binder)


# ─── K5: PEQ summary report ────────────────────────────────────────────────────

def _emit_peq_summary(binder_filter: int | None = None) -> None:
    """Scan all challenged reports; emit a per-binder PEQ summary to stdout."""
    import re as _re
    from datetime import datetime

    print(f"\n{'='*60}")
    print("PEQ Quality Summary (Wave K)")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    binder_dirs = sorted(EXTRACT_ROOT.glob("**/bundle.yml"))
    binder_reports: dict[str, list[tuple[str, float]]] = {}

    for yml in binder_dirs:
        binder_name = yml.parents[1].name  # shelf directory
        text_dir = yml.parent / "_system" / "source" / "text"
        report = text_dir / "wisdom-challenger-report.md"
        if not report.exists():
            continue
        if binder_filter and str(binder_filter) not in binder_name:
            continue
        rtext = report.read_text(encoding="utf-8", errors="replace")
        m = _re.search(
            r'\|\s*\*\*Total\*\*\s*\|\s*100%\s*\|\s*—\s*\|\s*\*\*(\d+(?:\.\d+)?)\*\*',
            rtext,
        )
        if m:
            chapter = yml.parent.name
            total = float(m.group(1))
            binder_reports.setdefault(binder_name, []).append((chapter, total))

    if not binder_reports:
        print("  No challenger reports found yet.")
        return

    all_scores: list[float] = []
    for binder, chapters in sorted(binder_reports.items()):
        scores = [s for _, s in chapters]
        all_scores.extend(scores)
        avg = sum(scores) / len(scores)
        fail_n = sum(1 for s in scores if s < 70)
        warn_n = sum(1 for s in scores if 70 <= s < 85)
        pass_n = sum(1 for s in scores if s >= 85)
        flag = " ⚠" if fail_n > 0 else ""
        print(f"\n  Binder: {binder}{flag}")
        print(f"    Chapters: {len(scores)}  |  Avg PEQ: {avg:.1f}  |  PASS={pass_n} WARN={warn_n} FAIL={fail_n}")
        for ch, score in sorted(chapters, key=lambda x: x[1]):
            tag = "PASS" if score >= 85 else "WARN" if score >= 70 else "FAIL ⚠"
            print(f"      {tag}  {score:>5.1f}  {ch}")

    if all_scores:
        grand = sum(all_scores) / len(all_scores)
        print(f"\n  Grand total: {len(all_scores)} chapters  |  Grand avg PEQ: {grand:.1f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
