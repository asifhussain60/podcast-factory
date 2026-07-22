"""intake_preflight.py — pre-flight cost/time estimate for a new volume/book.

Phase 6 (Q10): the intake cockpit shows an estimate + the caps in effect BEFORE
the Tier-2 spend confirm. The estimate is intentionally simple and honest:
``chapter_count × historical per-chapter cost/time``, where the historical means
are derived from the chapter_timings ALREADY recorded across shipped volumes (via
the Phase-1 resolver), falling back to conservative constants for a fresh install.

Pure + testable: no LLM, no pipeline launch. The caller passes a chapter count
(or a book_dir to count contracts) and the caps; this returns a dict the UI
renders. NOTHING here authorises spend — the confirm button does.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths
from _progress import read_state

# Conservative fallbacks when no history exists yet (fresh install). Grounded in
# the cost-ledger analysis in pipeline-debt.md (clean chapter ≈ $3.5 / ≈ 2h20m).
DEFAULT_PER_CHAPTER_COST_USD = 3.5
DEFAULT_PER_CHAPTER_SEC = 8400  # 2h20m


def historical_means() -> tuple[float, float, int]:
    """Mean (cost_usd, duration_sec, sample_size) across all recorded chapters.

    Walks every book via the Phase-1 resolver and averages the per-chapter
    ``cost_usd`` / ``duration_sec`` already in state. Falls back to the module
    defaults when there is no history. Only counts chapters that actually shipped
    a verdict (so a half-run chapter doesn't skew the mean).
    """
    costs: list[float] = []
    durs: list[float] = []
    for _status, _bucket, book_dir in _paths.iter_content():
        state = read_state(book_dir) or {}
        timings = state.get("phases", {}).get("per-chapter", {}).get("chapter_timings", {})
        if not isinstance(timings, dict):
            continue
        for _slug, t in timings.items():
            if not isinstance(t, dict):
                continue
            c = t.get("cost_usd")
            d = t.get("duration_sec")
            if isinstance(c, (int, float)) and c > 0:
                costs.append(float(c))
            if isinstance(d, (int, float)) and d > 0:
                durs.append(float(d))
    n = max(len(costs), len(durs))
    mean_cost = sum(costs) / len(costs) if costs else DEFAULT_PER_CHAPTER_COST_USD
    mean_dur = sum(durs) / len(durs) if durs else DEFAULT_PER_CHAPTER_SEC
    return round(mean_cost, 4), round(mean_dur, 1), n


def count_chapters(book_dir: Path) -> int:
    """Count a book's chapter contracts (the unit the per-chapter loop runs over)."""
    cdir = book_dir / "chapter-contracts"
    if not cdir.is_dir():
        return 0
    return len(sorted(cdir.glob("*.yml")))


def estimate(
    *,
    chapter_count: int,
    per_chapter_cost_cap_usd: float = 5.0,
    book_cost_cap_usd: float = 0.0,
    mean_cost_usd: float | None = None,
    mean_sec: float | None = None,
) -> dict[str, Any]:
    """Return a pre-flight estimate dict for ``chapter_count`` chapters.

    The projected cost is capped per-chapter by ``per_chapter_cost_cap_usd`` (the
    rail Phase 3 enforces) so the estimate never promises spend the pipeline would
    refuse. Surfaces the caps in effect so the UI can show them next to the number.
    """
    if chapter_count < 0:
        raise ValueError("chapter_count must be >= 0")
    if mean_cost_usd is None or mean_sec is None:
        h_cost, h_sec, _n = historical_means()
        mean_cost_usd = mean_cost_usd if mean_cost_usd is not None else h_cost
        mean_sec = mean_sec if mean_sec is not None else h_sec

    # The per-chapter cost rail caps what any one chapter can spend.
    effective_per_chapter = mean_cost_usd
    if per_chapter_cost_cap_usd > 0:
        effective_per_chapter = min(mean_cost_usd, per_chapter_cost_cap_usd)

    projected_cost = round(effective_per_chapter * chapter_count, 2)
    projected_sec = int(round(mean_sec * chapter_count))

    return {
        "chapter_count": chapter_count,
        "mean_per_chapter_cost_usd": round(mean_cost_usd, 2),
        "mean_per_chapter_sec": int(round(mean_sec)),
        "projected_cost_usd": projected_cost,
        "projected_sec": projected_sec,
        "projected_human": _fmt_duration(projected_sec),
        "caps": {
            "per_chapter_cost_cap_usd": per_chapter_cost_cap_usd,
            "book_cost_cap_usd": book_cost_cap_usd,
            "book_cost_cap_active": book_cost_cap_usd > 0,
        },
    }


def _fmt_duration(sec: int) -> str:
    h, rem = divmod(int(sec), 3600)
    m = rem // 60
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


# ── CLI (JSON contract for the Astro preflight endpoint) ─────────────────────
def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="pre-flight cost/time estimate")
    p.add_argument("--chapters", type=int, help="chapter count (else --slug)")
    p.add_argument("--slug", help="resolve chapter count from a book's contracts")
    p.add_argument("--per-chapter-cap", type=float, default=5.0)
    p.add_argument("--book-cap", type=float, default=0.0)
    args = p.parse_args(argv)

    chapters = args.chapters
    if chapters is None and args.slug:
        found = _paths.find_content(args.slug)
        chapters = count_chapters(found[2]) if found else 0
    if chapters is None:
        print(json.dumps({"ok": False, "error": "need --chapters or --slug"}))
        return 2
    est = estimate(
        chapter_count=chapters,
        per_chapter_cost_cap_usd=args.per_chapter_cap,
        book_cost_cap_usd=args.book_cap,
    )
    print(json.dumps({"ok": True, "estimate": est}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
