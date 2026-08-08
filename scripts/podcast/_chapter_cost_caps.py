"""_chapter_cost_caps.py — the two spend limits that govern the per-chapter loop.

Split out of `phases/chapter_driver` on 2026-08-08. Two limits, deliberately different
in KIND, and keeping them together is the point — reading one without the other is how
you conclude the wrong thing about a halt:

  per-CHAPTER cap   fails just that chapter and degrades to the next. One expensive
                    chapter is a content problem, not a book problem.
  per-BOOK ceiling  halts the whole book. Enforced in two places that are NOT
                    redundant:
                      * `_convergence` checks it at every iteration boundary against
                        ACTUAL spend, which stops work already running;
                      * `admit()` below refuses to START a chapter once spend has
                        reached the cap, which is what the live check cannot do.

WHY ADMISSION AND NOT A RESERVATION

  A reservation would have to estimate what a chapter will cost, and that depends on how
  many convergence iterations it needs — unknowable before it runs. Too low blocks work
  that would have fit; too high wastes the ceiling. The live check already self-corrects
  because it reads real spend; the only gap was a NEW chapter starting after the ceiling
  was gone, which is exactly what admission closes, and it needs no estimate at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: `0` means disabled for both caps, matching how series-plan.md already spells it.
DISABLED = 0.0

#: Default per-chapter cap. The per-book ceiling defaults to disabled so existing books
#: are unaffected unless they opt in (F35).
DEFAULT_PER_CHAPTER_USD = 5.0
DEFAULT_PER_BOOK_USD = DISABLED


def read_caps(book_dir: Path, *, log=None) -> tuple[float, float]:
    """(per_chapter_cap, per_book_ceiling) from series-plan, logging whichever is live."""
    from phases.series_plan import _series_numeric

    per_chapter = _series_numeric(book_dir, "per_chapter_cost_cap_usd", default=DEFAULT_PER_CHAPTER_USD)
    per_book = _series_numeric(book_dir, "book_cost_cap_usd", default=DEFAULT_PER_BOOK_USD)
    if log:
        if per_chapter > DISABLED:
            log(f"per-chapter cost cap: ${per_chapter:.2f} (per series-plan)")
        if per_book > DISABLED:
            log(f"per-book cost ceiling: ${per_book:.2f} (per series-plan)")
    return per_chapter, per_book


def admit(book_dir: Path, per_book_ceiling: float, breaker) -> str | None:
    """Trip `breaker` when the book has no ceiling left. Returns the halt reason, or None.

    Called BEFORE a chapter starts. Serially that is the next loop iteration;
    concurrently it is every worker that has not begun yet — which is the whole reason
    this check exists rather than relying on the mid-convergence one alone.

    Reads live spend from the cost ledger, so it costs a file read and no estimate.
    """
    if per_book_ceiling <= DISABLED:
        return None
    from phases.series_plan import _book_cost_so_far

    spent = _book_cost_so_far(book_dir)
    if spent < per_book_ceiling:
        return None
    # The COST-CEILING marker is load-bearing: supervise_run.py reads it to decide NOT to
    # relaunch, because a relaunch would burn straight through the same ceiling again.
    return breaker.trip(
        f"COST-CEILING: book has spent ${spent:.2f} against a cap of "
        f"${per_book_ceiling:.2f} — not starting further chapters"
    )
