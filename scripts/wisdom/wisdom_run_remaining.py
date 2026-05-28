#!/usr/bin/env python3
"""Run adapt + challenge for all remaining KAHSKOLE chapters in one pass.

For each binder: adapt all chapters → challenge all chapters → commit.
Idempotent: skips already-adapted/challenged chapters.

Usage:
    # Stop the existing adapt batch first, then:
    python scripts/wisdom/wisdom_run_remaining.py
    python scripts/wisdom/wisdom_run_remaining.py --start-binder 12
    python scripts/wisdom/wisdom_run_remaining.py --dry-run
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VENV = REPO / "_workspace/wisdom-ksessions/.venv/bin/python"

BINDER_ORDER = [
    (35, "The Wise Reminder"),
    (32, "Al-Ghazali — Kimiya"),
    (36, "Islam Iman Ihsan"),
    (12, "Duʿāt Lives"),
    (5,  "Devotional Poetry"),
    (16, "Selected Duʿāʾs"),
    (18, "Prophet Stories"),
    (25, "Daʿāʾim: Ṭahāra"),
    (27, "Ādāb wa-Akhlāq"),
    (29, "Daʿāʾim: Ṣawm"),
    (1,  "Sciences of Origin/Return"),
    (24, "Tawḥīd"),
    (26, "Daʿāʾim: Ṣalāt"),
    (19, "Daʿāʾim: Wilāya"),
    (34, "Quranic Studies"),
    (28, "Drafts"),
    (6,  "Imam ʿAlī"),
    (8,  "Taʾwīl of Divine Words"),
    (23, "Selected Scholarly Treatises"),
]


def _run(driver: Path, binder: int, dry_run: bool, extra_timeout: int = 7200) -> int:
    cmd = [str(VENV), str(driver), "--binder", str(binder)]
    if dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(cmd, cwd=REPO, timeout=extra_timeout)
    return result.returncode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--start-binder", type=int, help="Skip to this binder")
    ap.add_argument("--adapt-only", action="store_true")
    ap.add_argument("--challenge-only", action="store_true")
    args = ap.parse_args()

    adapt_driver = REPO / "scripts/wisdom/wisdom_adapt_all.py"
    challenge_driver = REPO / "scripts/wisdom/wisdom_challenge_all.py"

    start_idx = 0
    if args.start_binder:
        for i, (b, _) in enumerate(BINDER_ORDER):
            if b == args.start_binder:
                start_idx = i
                break

    for binder_id, binder_name in BINDER_ORDER[start_idx:]:
        print(f"\n{'='*60}")
        print(f"Processing binder {binder_id} — {binder_name}")
        print(f"{'='*60}")

        if not args.challenge_only:
            print(f"\n[ADAPT] binder {binder_id}...")
            t0 = time.time()
            rc = _run(adapt_driver, binder_id, args.dry_run)
            print(f"[ADAPT] binder {binder_id} done in {time.time()-t0:.0f}s (rc={rc})")
            if rc != 0:
                print(f"❌ Adapt failed for binder {binder_id}. Stopping.")
                sys.exit(rc)

        if not args.adapt_only:
            print(f"\n[CHALLENGE] binder {binder_id}...")
            t0 = time.time()
            rc = _run(challenge_driver, binder_id, args.dry_run)
            print(f"[CHALLENGE] binder {binder_id} done in {time.time()-t0:.0f}s (rc={rc})")

            # K5: PEQ gate — flag chapters that fall below the WARN threshold
            # (fidelity < 70) so operators know they need re-adaptation.
            _check_peq_after_challenge(binder_id, binder_name)

    print("\n✅ All binders processed.")


# ─── K5: Post-challenge PEQ scan ─────────────────────────────────────────────

def _check_peq_after_challenge(binder_id: int, binder_name: str) -> None:
    """Scan challenger reports for PEQ totals; surface chapters below 70."""
    import re as _re
    binder_dir = REPO / "CONTENT" / "drafts" / "books" / f"wisdom-binder-{binder_id:02d}"
    if not binder_dir.exists():
        return

    low: list[str] = []
    for report in sorted(binder_dir.glob("**/wisdom-challenger-report.md")):
        text = report.read_text(encoding="utf-8", errors="replace")
        m = _re.search(
            r'\|\s*\*\*Total\*\*\s*\|\s*100%\s*\|\s*—\s*\|\s*\*\*(\d+(?:\.\d+)?)\*\*',
            text,
        )
        if m and float(m.group(1)) < 70.0:
            low.append(f"  ⚠  {report.parent.parent.name} — PEQ {m.group(1)} (below 70 WARN threshold; re-adapt recommended)")

    if low:
        print(f"\n[PEQ GATE] Binder {binder_id} ({binder_name}) — {len(low)} chapter(s) below WARN threshold:")
        for line in low:
            print(line)
        print("  → Run wisdom_adapt_all.py --binder-id <N> --chapter <slug> to re-adapt and re-challenge.")
    else:
        print(f"[PEQ GATE] Binder {binder_id}: all challenged chapters ≥ 70 PEQ. ✓")


if __name__ == "__main__":
    main()
