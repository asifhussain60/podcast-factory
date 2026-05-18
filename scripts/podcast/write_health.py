#!/usr/bin/env python3
"""write_health.py — Per-book health score writer for the podcast pipeline.

PURPOSE

  Stage 4-bis of the learning pipeline. Called by the `podcast-challenger`
  agent at the end of every run. Inputs: book-slug + (p0, p1, p2,
  chapters_in_scope, auto_fixes, verdict). Outputs:
    1. `_learning/health/<book-slug>.json` — overwritten each run
    2. one appended row to `<BOOK_DIR>/_system/health-trend.md`

  The health score is **advisory** — SHIP-READY remains the binary gate. The
  score gives the human a quick trend signal: is this book getting healthier
  over time?

FORMULA

  penalty = (P0 × 1.0 + P1 × 0.2 + P2 × 0.05) / chapters_in_scope
  score   = max(0.0, 1.0 - penalty)

BADGES (advisory)

  ≥ 0.95 for ≥ 2 consecutive runs → "Stable"
  ≥ 0.90                          → "Healthy"
  0.50–0.89                       → "Drifting"
  < 0.50                          → "Unstable"

USAGE

  python3 scripts/podcast/write_health.py \\
      --book <book-slug> --p0 N --p1 N --p2 N \\
      --chapters N --auto-fixes N --verdict SHIP-WITH-CAUTION

OUTPUTS

  - content/podcast/.skill/_learning/health/<book-slug>.json
  - content/podcast/library/<category>/<book-slug>/_system/health-trend.md
    (appended; created on first run)

The script discovers the BOOK_DIR by globbing for
`content/podcast/library/*/<book-slug>/`. If multiple matches exist, fails
with a clear error so the user can disambiguate.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HEALTH_DIR = REPO_ROOT / "content/podcast/.skill/_learning/health"
LIBRARY_ROOT = REPO_ROOT / "content/podcast/library"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _rules import CHALLENGER_VERSION  # noqa: E402


def compute_score(p0: int, p1: int, p2: int, chapters: int) -> float:
    if chapters <= 0:
        return 0.0
    penalty = (p0 * 1.0 + p1 * 0.2 + p2 * 0.05) / chapters
    return max(0.0, 1.0 - penalty)


def badge_for(score: float, prior_stable_runs: int) -> str:
    if score >= 0.95 and prior_stable_runs >= 1:
        return "Stable"
    if score >= 0.90:
        return "Healthy"
    if score >= 0.50:
        return "Drifting"
    return "Unstable"


def find_book_dir(book_slug: str) -> Path:
    if not LIBRARY_ROOT.is_dir():
        raise SystemExit(f"ERROR: library root not found: {LIBRARY_ROOT}")
    matches = list(LIBRARY_ROOT.glob(f"*/{book_slug}"))
    matches = [m for m in matches if m.is_dir()]
    if not matches:
        raise SystemExit(f"ERROR: no library directory matches book-slug '{book_slug}' under {LIBRARY_ROOT}")
    if len(matches) > 1:
        raise SystemExit(f"ERROR: multiple matches for '{book_slug}': {matches}")
    return matches[0]


def prior_stable_count(history_path: Path) -> int:
    """Count consecutive trailing rows with score >= 0.95."""
    if not history_path.exists():
        return 0
    count = 0
    for raw in reversed(history_path.read_text(encoding="utf-8").splitlines()):
        if not raw.startswith("| "):
            continue
        if "| score:" not in raw:
            continue
        try:
            s = raw.split("| score:", 1)[1]
            s = s.split("|", 1)[0].strip()
            score = float(s)
        except (IndexError, ValueError):
            break
        if score >= 0.95:
            count += 1
        else:
            break
    return count


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--book", required=True)
    p.add_argument("--p0", type=int, required=True)
    p.add_argument("--p1", type=int, required=True)
    p.add_argument("--p2", type=int, required=True)
    p.add_argument("--chapters", type=int, required=True,
                   help="Chapters in scope for this run.")
    p.add_argument("--auto-fixes", type=int, default=0)
    p.add_argument("--verdict", required=True,
                   choices=["SHIP-READY", "SHIP-WITH-CAUTION", "BLOCKED"])
    p.add_argument("--challenger-version", default=CHALLENGER_VERSION)
    args = p.parse_args()

    book_dir = find_book_dir(args.book)
    history_path = book_dir / "_system" / "health-trend.md"
    prior_stable = prior_stable_count(history_path)

    score = compute_score(args.p0, args.p1, args.p2, args.chapters)
    badge = badge_for(score, prior_stable)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    health_path = HEALTH_DIR / f"{args.book}.json"
    health = {
        "ts": ts,
        "book": args.book,
        "chapters_in_scope": args.chapters,
        "p0": args.p0,
        "p1": args.p1,
        "p2": args.p2,
        "auto_fixes": args.auto_fixes,
        "score": round(score, 4),
        "badge": badge,
        "verdict": args.verdict,
        "challenger_version": args.challenger_version,
    }
    health_path.write_text(
        json.dumps(health, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Append trend row
    history_path.parent.mkdir(parents=True, exist_ok=True)
    new_row = (
        f"| {ts} | {args.challenger_version} | {args.chapters} chs | "
        f"P0:{args.p0} P1:{args.p1} P2:{args.p2} | auto:{args.auto_fixes} | "
        f"score:{score:.2f} | {badge} | {args.verdict} |\n"
    )
    if not history_path.exists():
        header = (
            f"# Health Trend — {args.book}\n\n"
            f"Append-only trend log. One row per `podcast-challenger` run.\n\n"
            f"| Timestamp | Version | Chapters | Findings | Auto-fixes | Score | Badge | Verdict |\n"
            f"|---|---|---|---|---|---|---|---|\n"
        )
        history_path.write_text(header + new_row, encoding="utf-8")
    else:
        with history_path.open("a", encoding="utf-8") as f:
            f.write(new_row)

    print(f"health: score={score:.2f} badge={badge} verdict={args.verdict}")
    print(f"  wrote: {health_path.relative_to(REPO_ROOT)}")
    print(f"  appended: {history_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
