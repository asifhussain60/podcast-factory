#!/usr/bin/env python3
"""Batch challenger driver for all KAHSKOLE chapters (Phase 3).

Runs challenge for every chapter at stage 'adapted'.
Idempotent: skips chapters already 'challenged'.
Commits per binder. Logs P0/P1 findings.

Usage:
    python scripts/kashkole/kashkole_challenge_all.py
    python scripts/kashkole/kashkole_challenge_all.py --dry-run
    python scripts/kashkole/kashkole_challenge_all.py --binder 35
    python scripts/kashkole/kashkole_challenge_all.py --warn-only
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
VENV = REPO / "_workspace/kashkole-corpus/.venv/bin/python"
LEDGER = REPO / "_workspace/plan/kashkole-challenge-cost-ledger.jsonl"
FAILURE_LOG = REPO / "_workspace/plan/kashkole-challenge-failures.log"
FAIL_REPORT = REPO / "_workspace/plan/kashkole-challenge-fail-report.md"
EXTRACT_ROOT = REPO / "_workspace/kashkole-corpus/extracted/kashkole"

SESSION_COST_CAP = 10.0  # USD — challenger calls are short, cheap

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


def _ledger_total() -> float:
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
            if f"  id: {binder_id}" not in text:
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
            if f"  id: {binder_id}" in text and has_chapter:
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


def _challenge_chapter(binder_id: int, chapter_id: int, dry_run: bool) -> tuple[float, str]:
    """Run challenge on one chapter. Returns (cost_usd, verdict)."""
    cmd = [str(VENV), "-m", "tools.content_translator", "challenge"]
    if dry_run:
        cmd.append("--dry-run")
    cmd += ["kashkole", "--binder", str(binder_id), "--chapter", str(chapter_id)]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=120)
    output = result.stdout + result.stderr

    if result.returncode != 0:
        _log_failure(binder_id, chapter_id, f"challenge failed: {output[-400:]}")
        return 0.0, "ERROR"

    if "SKIPPED" in output:
        return 0.0, "SKIP"

    # Parse cost and verdict
    cost = 0.0
    verdict = "UNKNOWN"
    for line in output.splitlines():
        if line.strip().startswith("cost:"):
            try:
                cost = float(line.split("$")[1].strip())
            except (IndexError, ValueError):
                pass
        if "CHALLENGED [" in line:
            m = line.split("[")[1].split("]")[0] if "[" in line else ""
            if m in ("PASS", "WARN", "FAIL"):
                verdict = m
    return cost, verdict


def _log_failure(binder_id: int, chapter_id: int, reason: str) -> None:
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with FAILURE_LOG.open("a") as f:
        f.write(f"[{ts}] challenge failed binder={binder_id} chapter={chapter_id}: {reason}\n")


def _commit_binder(binder_id: int, name: str, chapters: int, cost: float, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] would commit binder {binder_id}")
        return
    msg = (
        f"feat(kashkole-challenge): binder {binder_id} — {name} "
        f"({chapters} chapters challenged, ${cost:.2f} Anthropic)"
    )
    subprocess.run(
        ["git", "add",
         "_workspace/kashkole-corpus/extracted/kashkole/",
         "_workspace/plan/kashkole-challenge-cost-ledger.jsonl"],
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
    ap.add_argument("--warn-only", action="store_true",
                    help="Continue even on WARN; only halt on FAIL")
    args = ap.parse_args()

    session_start = _ledger_total()
    session_cost = 0.0
    all_warns: list[str] = []
    all_fails: list[str] = []

    binders = BINDER_ORDER
    if args.binder:
        binders = [(b, n) for b, n in BINDER_ORDER if b == args.binder]
        if not binders:
            print(f"Binder {args.binder} not in order list")
            sys.exit(1)

    for binder_id, binder_name in binders:
        chapters = _get_chapters(binder_id)
        if not chapters:
            print(f"\nBinder {binder_id} ({binder_name}): 0 chapters — skip")
            continue

        done = skipped = failed = 0
        binder_cost = 0.0

        print(f"\n{'='*60}")
        print(f"Binder {binder_id} — {binder_name} ({len(chapters)} chapters)")
        print(f"{'='*60}")

        for ch_id in chapters:
            cumulative = session_start + session_cost
            if cumulative >= SESSION_COST_CAP:
                print(f"\n⚠ Cost cap ${SESSION_COST_CAP:.0f} reached. Halting.")
                _commit_binder(binder_id, binder_name, done, binder_cost, args.dry_run)
                sys.exit(0)

            stage = _get_stage(binder_id, ch_id)
            if stage == "challenged":
                print(f"  ch {ch_id}: already challenged — skip")
                skipped += 1
                continue
            if stage != "adapted":
                print(f"  ch {ch_id}: stage={stage} — skip (not adapted yet)")
                skipped += 1
                continue

            print(f"  ch {ch_id}: challenging...", end=" ", flush=True)
            t0 = time.time()
            cost, verdict = _challenge_chapter(binder_id, ch_id, args.dry_run)
            elapsed = time.time() - t0

            icon = {"PASS": "✅", "WARN": "⚠", "FAIL": "❌", "ERROR": "❌"}.get(verdict, "?")
            print(f"{icon} {verdict} ${cost:.4f} ({elapsed:.1f}s)")

            if verdict in ("PASS", "WARN", "SKIP") or args.dry_run:
                done += 1
                binder_cost += cost
                session_cost += cost
                if verdict == "WARN":
                    all_warns.append(f"b{binder_id}/c{ch_id}")
            elif verdict == "FAIL" and not args.warn_only:
                all_fails.append(f"b{binder_id}/c{ch_id}")
                print(f"    FAIL recorded — continuing (review {FAIL_REPORT})")
                done += 1
                binder_cost += cost
                session_cost += cost
            else:
                failed += 1

        print(f"\n  Binder {binder_id}: {done} challenged, {skipped} skipped, {failed} failed")
        print(f"  Binder cost: ${binder_cost:.4f}")
        _commit_binder(binder_id, binder_name, done, binder_cost, args.dry_run)

    total = session_start + session_cost
    print(f"\n{'='*60}")
    print(f"Challenge complete.")
    print(f"WARNs: {len(all_warns)}  FAILs: {len(all_fails)}")
    print(f"Session spend: ${session_cost:.4f}  |  Total: ${total:.4f}")
    print(f"{'='*60}")

    if all_warns or all_fails:
        FAIL_REPORT.parent.mkdir(parents=True, exist_ok=True)
        with FAIL_REPORT.open("w") as f:
            f.write(f"# KAHSKOLE Challenge Results\n\n")
            f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")
            if all_warns:
                f.write(f"## WARNs ({len(all_warns)})\n")
                f.write("\n".join(f"- {w}" for w in all_warns) + "\n\n")
            if all_fails:
                f.write(f"## FAILs ({len(all_fails)}) — require re-adaptation\n")
                f.write("\n".join(f"- {x}" for x in all_fails) + "\n\n")
        print(f"\nResults written to: {FAIL_REPORT}")


if __name__ == "__main__":
    main()
