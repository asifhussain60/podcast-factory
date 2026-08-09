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


class BookCeiling:
    """Admission control for the per-book ceiling, correct when chapters run at once.

    Called BEFORE a chapter starts. Serially that is the next loop iteration;
    concurrently it is every worker that has not begun yet — which is the whole reason
    this check exists rather than relying on the mid-convergence one alone.

    WHY THIS IS AN OBJECT AND NOT A FUNCTION (2026-08-09)

      The function it replaces read live spend and decided with no lock, so N workers
      could each read the same "spent" a moment apart and all admit. Four workers under
      a $50 ceiling with $49 spent started four chapters and took the book to ~$69. The
      decision and the record of having decided must happen under ONE lock or the check
      is advisory, and a lock needs something to own it.

      It also RETURNS its refusal instead of only tripping the breaker. The old function
      returned a reason the caller discarded, and the chapter was actually stopped by
      `breaker.begin()` re-reading the tripped flag a few lines later — so the ceiling
      was enforced by a side effect at a distance, one reordering away from silently
      doing nothing.

    WHY IN-FLIGHT CHAPTERS ARE COUNTED AGAINST THE CEILING, AND WHY THAT IS NOT AN
    ESTIMATE

      A chapter already running can still spend up to the per-chapter cap — that is not
      a guess about this chapter, it is the hard limit the loop already enforces on it.
      Counting `in_flight * per_chapter_cap` as committed is therefore a BOUND, not a
      forecast, which is what keeps the no-estimates rule this module was built on. The
      cost is conservatism: near the ceiling some work that would have fit is refused.
      That is the correct direction to be wrong about a spend limit.

      When a book sets a ceiling but NO per-chapter cap there is no bound to count, so
      concurrency cannot be made safe — `concurrency_limit` returns 1 and the book runs
      serially, where admission is exact.
    """

    def __init__(self, ceiling_usd: float, per_chapter_cap_usd: float, spend_fn) -> None:
        import threading

        self._ceiling = float(ceiling_usd or DISABLED)
        self._per_chapter_cap = float(per_chapter_cap_usd or DISABLED)
        #: `spend_fn(book_dir) -> float`. Injected rather than imported so this module
        #: does not depend on `phases.series_plan` (a cycle) and so the caller's own
        #: binding is the one used — which is also what makes it substitutable in tests.
        self._spend_fn = spend_fn
        self._lock = threading.Lock()
        self._in_flight = 0

    @property
    def enabled(self) -> bool:
        return self._ceiling > DISABLED

    def concurrency_limit(self, requested: int) -> int:
        """Workers this book may safely use, given its caps.

        A ceiling with no per-chapter cap has no bound on what an in-flight chapter may
        still spend, so the only safe width is one.
        """
        requested = max(1, int(requested))
        if not self.enabled:
            return requested
        if self._per_chapter_cap <= DISABLED:
            return 1
        return requested

    def admit(self, book_dir: Path) -> str | None:
        """None to start the chapter — which is then counted in flight — or the refusal.

        The caller MUST call `release()` when the chapter finishes, however it finishes.
        """
        with self._lock:
            if not self.enabled:
                self._in_flight += 1
                return None
            spent = float(self._spend_fn(book_dir))
            committed = spent + self._in_flight * self._per_chapter_cap
            if committed < self._ceiling:
                self._in_flight += 1
                return None
            # The COST-CEILING marker is load-bearing: supervise_run.py reads it to decide
            # NOT to relaunch, because a relaunch would burn straight through the same
            # ceiling again.
            in_flight_note = f" with {self._in_flight} chapter(s) still running against it" if self._in_flight else ""
            return (
                f"COST-CEILING: book has spent ${spent:.2f}{in_flight_note} against a cap of "
                f"${self._ceiling:.2f} — not starting further chapters"
            )

    def release(self) -> None:
        """This chapter is no longer in flight. Safe to call more than once."""
        with self._lock:
            if self._in_flight > 0:
                self._in_flight -= 1

    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight
