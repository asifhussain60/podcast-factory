#!/usr/bin/env python3
"""Batch adaptation driver for all KAHSKOLE chapters (Phase 2).

Runs adapt-auto for every chapter in binder order (smallest first).
Idempotent: skips chapters already at stage adapted/challenged.
Enforces per-session cost cap. Commits per binder. Logs failures.

Usage:
    python _workspace/plan/_drivers/kashkole_adapt_all.py
    python _workspace/plan/_drivers/kashkole_adapt_all.py --dry-run
    python _workspace/plan/_drivers/kashkole_adapt_all.py --binder 35
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VENV = REPO / "_workspace/kashkole-ksessions/.venv/bin/python"
LEDGER = REPO / "_workspace/plan/kashkole-adapt-cost-ledger.jsonl"
FAILURE_LOG = REPO / "_workspace/plan/kashkole-adapt-failures.log"
EXTRACT_ROOT = REPO / "_workspace/kashkole-ksessions/extracted/kashkole"

SESSION_COST_CAP = 30.0   # USD — adaptation is cheaper than translation

# Same binder order as translation driver
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


def _ledger_session_total() -> float:
    if not LEDGER.exists():
        return 0.0
    total = 0.0
    with LEDGER.open() as f:
        for line in f:
            line = line.strip()
            if line:
                total += json.loads(line).get("cost_usd", 0.0)
    return total


def _get_stage(binder_id: int, chapter_id: int) -> str:
    for shelf_dir in EXTRACT_ROOT.iterdir():
        if not shelf_dir.is_dir():
            continue
        for book_dir in shelf_dir.iterdir():
            yml = book_dir / "bundle.yml"
            if not yml.exists():
                continue
            text = yml.read_text(encoding="utf-8")
            has_binder = f"  id: {binder_id}" in text
            if not has_binder:
                continue
            in_book = False
            has_chapter = False
            for line in text.splitlines():
                if line.startswith("book:"):
                    in_book = True
                if in_book and line.strip() == f"id: {chapter_id}":
                    has_chapter = True
                    break
                if in_book and not line.startswith("  ") and line.strip() and not line.startswith("book:"):
                    in_book = False
            if has_binder and has_chapter:
                for line in text.splitlines():
                    if line.startswith("stage:"):
                        return line.split(":", 1)[1].strip()
    return "unknown"


def _get_chapters(binder_id: int) -> list[int]:
    result = subprocess.run(
        [str(VENV), "-c", f"""
from tools.source_extractor.db import query_json
rows = query_json('KASHKOLE', '''
SELECT bc.ChapterID AS id
FROM BinderChapters bc
WHERE bc.BinderID = {binder_id}
ORDER BY bc.BinderChapterOrder FOR JSON PATH;''')
for r in rows: print(r['id'])
"""],
        capture_output=True, text=True, cwd=REPO,
    )
    return [int(x) for x in result.stdout.strip().splitlines() if x.strip()]


def _adapt_chapter(binder_id: int, chapter_id: int, dry_run: bool) -> float:
    """Run adapt-auto on one chapter. Returns cost_usd (0 if skipped/failed)."""
    cmd = [str(VENV), "-m", "tools.content_translator", "adapt-auto"]
    if dry_run:
        cmd.append("--dry-run")
    cmd += ["kashkole", "--binder", str(binder_id), "--chapter", str(chapter_id)]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=7200)
    output = result.stdout + result.stderr

    if result.returncode != 0:
        _log_failure(binder_id, chapter_id, f"adapt-auto failed: {output[-400:]}")
        return 0.0

    if "SKIPPED" in output:
        return 0.0

    for line in output.splitlines():
        if line.strip().startswith("cost:"):
            try:
                return float(line.split("$")[1].strip())
            except (IndexError, ValueError):
                pass
    return 0.0


def _log_failure(binder_id: int, chapter_id: int, reason: str) -> None:
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with FAILURE_LOG.open("a") as f:
        f.write(f"[{ts}] adapt failed binder={binder_id} chapter={chapter_id}: {reason}\n")


def _commit_binder(binder_id: int, name: str, chapters: int, cost: float, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] would commit binder {binder_id}")
        return
    msg = (
        f"feat(kashkole-adapt): binder {binder_id} — {name} "
        f"({chapters} chapters adapted, ${cost:.2f} Anthropic)"
    )
    subprocess.run(
        ["git", "add",
         "_workspace/kashkole-ksessions/extracted/kashkole/",
         "_workspace/plan/kashkole-adapt-cost-ledger.jsonl"],
        cwd=REPO, check=False,
    )
    subprocess.run(
        ["git", "commit", "-m", msg,
         f"--trailer=Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"],
        cwd=REPO, check=False,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--binder", type=int, help="Run a single binder only")
    args = ap.parse_args()

    session_start = _ledger_session_total()
    session_cost = 0.0

    binders = BINDER_ORDER
    if args.binder:
        binders = [(b, n) for b, n in BINDER_ORDER if b == args.binder]
        if not binders:
            print(f"Binder {args.binder} not in order list")
            sys.exit(1)

    for binder_id, binder_name in binders:
        chapters = _get_chapters(binder_id)
        if not chapters:
            print(f"\nBinder {binder_id} ({binder_name}): 0 chapters in DB — skip")
            continue

        done = skipped = failed = 0
        binder_cost = 0.0

        print(f"\n{'='*60}")
        print(f"Binder {binder_id} — {binder_name} ({len(chapters)} chapters)")
        print(f"  Session cost so far: ${session_start + session_cost:.2f}")
        print(f"{'='*60}")

        for ch_id in chapters:
            cumulative = session_start + session_cost
            if cumulative >= SESSION_COST_CAP:
                print(f"\n⚠ Session cost cap ${SESSION_COST_CAP:.0f} reached (${cumulative:.2f}). Halting.")
                _commit_binder(binder_id, binder_name, done, binder_cost, args.dry_run)
                print("Re-run to continue (idempotent).")
                sys.exit(0)

            stage = _get_stage(binder_id, ch_id)
            if stage in ("adapted", "challenged"):
                print(f"  ch {ch_id}: already {stage} — skip")
                skipped += 1
                continue

            print(f"  ch {ch_id}: adapting...", end=" ", flush=True)
            t0 = time.time()
            cost = _adapt_chapter(binder_id, ch_id, args.dry_run)
            elapsed = time.time() - t0

            if args.dry_run:
                print(f"[dry-run] ({elapsed:.1f}s)")
                done += 1
            elif cost == 0.0:
                stage_after = _get_stage(binder_id, ch_id)
                if stage_after == "adapted":
                    print(f"✅ $0.00 ({elapsed:.1f}s)")
                    done += 1
                else:
                    print(f"❌ failed")
                    failed += 1
            else:
                print(f"✅ ${cost:.4f} ({elapsed:.1f}s)")
                done += 1
                binder_cost += cost
                session_cost += cost

        print(f"\n  Binder {binder_id} done: {done} adapted, {skipped} skipped, {failed} failed")
        print(f"  Binder cost: ${binder_cost:.4f}")
        _commit_binder(binder_id, binder_name, done, binder_cost, args.dry_run)

    total = session_start + session_cost
    print(f"\n{'='*60}")
    print(f"All binders processed.")
    print(f"Session spend: ${session_cost:.4f}  |  Corpus total: ${total:.4f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
