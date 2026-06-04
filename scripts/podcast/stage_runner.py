#!/usr/bin/env python3
"""stage_runner.py — WC8 Phase-6 stage runner (pipeline productionisation).

Checks the per-chapter stage-gate and runs the next WC8 stage producer script.
Designed to be called by the Astro "Run next stage" API endpoint (via subprocess)
OR used from the CLI during development.

USAGE
    # Run the next eligible stage for a chapter:
    python3 scripts/podcast/stage_runner.py \\
        --slug ayyuhal-walad --chapter ch02-hatim-eight-benefits

    # Check state without running anything:
    python3 scripts/podcast/stage_runner.py \\
        --slug ayyuhal-walad --chapter ch02-hatim-eight-benefits --dry-run

    # Run all chapters in sequence:
    python3 scripts/podcast/stage_runner.py --slug ayyuhal-walad --all

OUTPUT (stdout JSON when --json, prose otherwise):
    {
      "status":    "ran" | "awaiting_approval" | "no_script" | "all_done" | "error",
      "stage":     "denoised",           // stage that ran (or was targeted)
      "chapter":   "ch02-...",
      "message":   "...",
      "cost_usd":  0.00686               // parsed from script stdout, 0 if unavailable
    }

STAGE PIPELINE (per chapter):
    source       → intake_stage.py (Azure OCR — expensive; skipped if cached)
    core         → inline agent (no standalone script yet — requires manual production)
    denoised     → gemini_refine.py --mode denoise
    normalized   → gemini_refine.py --mode normalize
    augmented    → inline agent (no standalone script yet — requires manual production)
    narrator     → narrator_additions.py (reads lecture-chapter-map.json)

    Stages without a standalone script return status="no_script" — the artifact
    must be produced by the Claude Code agent, then approved in Studio.

EXIT CODES
    0  success (ran or all_done)
    1  error / exception
    2  awaiting_approval (next stage blocked on human sign-off)
    3  no_script (next stage has no standalone producer)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _paths import REPO_ROOT, resolve_content  # noqa: E402
from _stage_gate import (  # noqa: E402
    STAGE_ORDER,
    awaiting_approval_stage,
    chapter_stage_summary,
    next_runnable_stage,
)

SCRIPT_DIR = _HERE


# ---------------------------------------------------------------------------
# Stage → producer command factory
# ---------------------------------------------------------------------------

def _lecture_slugs_for(slug: str, chapter: str) -> list[str]:
    """Read lecture-chapter-map.json and return the lecture slugs for this chapter."""
    map_path = (
        resolve_content(slug)
        / "_system" / "lecture-chapter-map.json"
    )
    if not map_path.exists():
        return []
    data = json.loads(map_path.read_text(encoding="utf-8"))
    return data.get("map", {}).get(chapter, [])


def _build_command(slug: str, chapter: str, stage: str) -> list[str] | None:
    """Return the subprocess command list for a stage, or None if no script."""
    py = sys.executable

    if stage == "source":
        # Expensive Azure OCR — we run --role english as the canonical spine.
        # intake_stage.py only OCRs; core alignment is done by the agent.
        # Re-run is a no-op if cached (no re-spend).
        return [py, str(SCRIPT_DIR / "intake_stage.py"),
                "--slug", slug, "--role", "english"]

    if stage == "denoised":
        return [py, str(SCRIPT_DIR / "gemini_refine.py"),
                "--slug", slug, "--chapter", chapter, "--mode", "denoise"]

    if stage == "normalized":
        return [py, str(SCRIPT_DIR / "gemini_refine.py"),
                "--slug", slug, "--chapter", chapter, "--mode", "normalize"]

    if stage == "narrator":
        lectures = _lecture_slugs_for(slug, chapter)
        if not lectures:
            # No lectures mapped — produce an empty narrator stub so the
            # pipeline can continue without blocking on this stage.
            return None
        return [py, str(SCRIPT_DIR / "narrator_additions.py"),
                "--slug", slug, "--chapter", chapter,
                "--lectures", ",".join(lectures)]

    # core, augmented — no standalone script yet
    return None


# ---------------------------------------------------------------------------
# Cost extraction
# ---------------------------------------------------------------------------

_COST_RE = re.compile(r"~?\$(\d+\.\d+)", re.MULTILINE)


def _parse_cost(stdout: str) -> float:
    """Extract the first cost figure from script stdout."""
    m = _COST_RE.search(stdout)
    return float(m.group(1)) if m else 0.0


# ---------------------------------------------------------------------------
# Single-chapter runner
# ---------------------------------------------------------------------------

def run_chapter(slug: str, chapter: str, *, dry_run: bool = False, as_json: bool = False) -> int:
    """Run the next eligible stage for one chapter.

    Returns an exit code: 0=success, 1=error, 2=awaiting_approval, 3=no_script.
    """

    def _emit(status: str, stage: str, msg: str, cost: float = 0.0) -> None:
        if as_json:
            print(json.dumps({
                "status": status, "stage": stage, "chapter": chapter,
                "message": msg, "cost_usd": cost,
            }))
        else:
            print(f"[{status.upper()}] chapter={chapter} stage={stage}: {msg}")

    # Determine next stage.
    target = next_runnable_stage(slug, chapter)

    if target is None:
        # Either all stages done, or predecessor not yet approved.
        blocking = awaiting_approval_stage(slug, chapter)
        if blocking:
            _emit("awaiting_approval", blocking,
                  f"Stage '{blocking}' is complete — approve it in Studio before continuing.")
            return 2

        # Check if truly all done.
        summary = chapter_stage_summary(slug, chapter)
        if all(e["status"] == "done_approved" for e in summary):
            _emit("all_done", "", "All stages complete and approved.")
            return 0

        # A preceding done_pending stage is blocking but wasn't caught above.
        for e in summary:
            if e["status"] == "done_pending":
                _emit("awaiting_approval", e["stage"],
                      f"Stage '{e['stage']}' is complete — approve it in Studio before continuing.")
                return 2

        _emit("all_done", "", "All available stages complete.")
        return 0

    # Build the command for the target stage.
    cmd = _build_command(slug, chapter, target)
    if cmd is None:
        _emit("no_script", target,
              f"Stage '{target}' has no standalone producer — produce the artifact manually "
              f"then approve it in Studio.")
        return 3

    if dry_run:
        _emit("ran", target, f"(dry-run) would run: {' '.join(cmd)}")
        return 0

    # Run the producer.
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as exc:  # noqa: BLE001
        _emit("error", target, f"subprocess error: {exc}")
        return 1

    stdout = result.stdout + result.stderr
    cost = _parse_cost(stdout)

    if result.returncode != 0:
        _emit("error", target,
              f"producer exited {result.returncode}: {stdout.strip()[-200:]}", cost)
        return 1

    _emit("ran", target,
          f"Stage '{target}' produced successfully. {stdout.strip().splitlines()[-1] if stdout.strip() else ''}",
          cost)
    return 0


# ---------------------------------------------------------------------------
# All-chapters runner
# ---------------------------------------------------------------------------

def run_all(slug: str, *, dry_run: bool = False, as_json: bool = False) -> int:
    """Run the next stage for every chapter in the book, in order."""
    book_dir = resolve_content(slug)
    stages_root = book_dir / "_stages"
    if not stages_root.exists():
        print(f"No _stages directory found for {slug}", file=sys.stderr)
        return 1

    chapters = sorted(d.name for d in stages_root.iterdir() if d.is_dir())
    if not chapters:
        print("No chapter stage directories found.", file=sys.stderr)
        return 1

    overall = 0
    for ch in chapters:
        rc = run_chapter(slug, ch, dry_run=dry_run, as_json=as_json)
        if rc == 1:
            overall = 1  # escalate errors
    return overall


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def show_status(slug: str, chapters: list[str]) -> None:
    """Print a table of per-chapter stage state."""
    hdr = f"{'CHAPTER':<45} " + " ".join(f"{s[:6]:>7}" for s in STAGE_ORDER)
    print(hdr)
    print("-" * len(hdr))
    icons = {"done_approved": "  ✅", "done_pending": "  🔄", "missing": "  ⬜"}
    for ch in chapters:
        summary = chapter_stage_summary(slug, ch)
        row = f"{ch:<45} " + " ".join(icons.get(e["status"], "   ?  ") for e in summary)
        print(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="WC8 stage runner — check gate + run next stage producer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--slug", required=True, help="Book slug (e.g. ayyuhal-walad)")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--chapter", help="Chapter slug to advance (e.g. ch02-hatim-eight-benefits)")
    group.add_argument("--all", action="store_true", help="Advance all chapters one stage each")
    group.add_argument("--status", action="store_true", help="Print stage-state table and exit")
    ap.add_argument("--dry-run", action="store_true", help="Show what would run; do nothing")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="Emit result as JSON (for API callers)")
    args = ap.parse_args()

    book_dir = resolve_content(args.slug)
    if not book_dir.exists():
        print(f"Book directory not found: {book_dir}", file=sys.stderr)
        sys.exit(1)

    stages_root = book_dir / "_stages"
    all_chapters = sorted(d.name for d in stages_root.iterdir() if d.is_dir()) if stages_root.exists() else []

    if args.status:
        show_status(args.slug, all_chapters)
        sys.exit(0)

    if args.all:
        sys.exit(run_all(args.slug, dry_run=args.dry_run, as_json=args.as_json))

    if args.chapter:
        sys.exit(run_chapter(args.slug, args.chapter, dry_run=args.dry_run, as_json=args.as_json))

    # Default: show status
    show_status(args.slug, all_chapters)


if __name__ == "__main__":
    main()
