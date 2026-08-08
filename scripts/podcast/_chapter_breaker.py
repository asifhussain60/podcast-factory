"""_chapter_breaker.py — the C3 circuit breaker, in a shape that survives concurrency.

WHAT IT IS FOR

  The per-chapter loop halts the whole book on a SYSTEMIC failure rather than grinding
  through twenty chapters reproducing one root cause. Two signals:

    * the first chapter attempted died in under five seconds — that is a deterministic
      bug (a path, a contract, a template), not content;
    * the same normalized failure has now hit a second chapter — paying for the same
      lesson twice is waste (the archetype-over-rerun rule).

  Its value is ECONOMIC and it is entirely about TIMING: it exists to stop before the
  remaining chapters are paid for. A breaker that reports after everything has already
  run is a log line, not a control.

WHY IT MOVED HERE

  The logic lived inline in the loop over three local variables (`attempted`,
  `failure_signatures`, `_systemic`). That is correct while the loop is serial and
  unusable the moment it is not: two workers would race the counter and the signature
  map, and — worse — nothing would consult the verdict until a chapter had already
  finished, by which point every other chapter is in flight and the saving is gone.

  So the state is behind a lock and the verdict is asked for at a NEW point: `begin()`,
  which a worker calls BEFORE it starts. A worker that has not started can still
  decline, which is the only way the economics survive workers.

  Extracted while the loop is still serial and pinned by tests that assert the old
  behaviour, so parallelising later adds workers rather than changing decisions.
"""

from __future__ import annotations

import re
import threading

#: A first chapter that dies faster than this is a deterministic bug, not content.
FAST_FAILURE_SEC = 5.0

#: How many distinct chapters must share one failure signature before it is systemic.
SHARED_FAILURE_CHAPTERS = 2


def failure_signature(reason: str) -> str:
    """Normalize a failure reason so the same root cause across chapters matches.

    Collapses digits and slug-like tokens to a stable shape: "word count 2 outside band"
    and "word count 5000 outside band" share a signature, while two genuinely different
    findings stay distinct.

    Moved here from `phases/chapter_driver` on 2026-08-08 — the breaker was its only
    caller, and a decision's inputs belong with the decision.
    """
    s = reason.lower()
    s = re.sub(r"[0-9]+", "#", s)
    s = re.sub(r"[^a-z#\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:80]


class BreakerTripped(Exception):
    """Raised by `begin()` when the book has already been halted.

    A worker that has not begun must not begin. Raising (rather than returning a
    sentinel) means a caller cannot accidentally proceed by ignoring a return value —
    the whole point of this class is that the decision is not skippable.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ChapterBreaker:
    """Thread-safe systemic-failure detector for the per-chapter loop.

    Usage, per chapter::

        try:
            ordinal = breaker.begin(slug)
        except BreakerTripped as t:
            ...skip this chapter, the book is already halting...

        outcome = run_the_chapter()
        if failed:
            systemic = breaker.record_failure(slug, reason, duration_sec, ordinal)
            if systemic:
                ...halt the book...
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._attempted = 0
        self._signatures: dict[str, list[str]] = {}
        self._tripped: str | None = None

    # ── the pre-start gate ───────────────────────────────────────────────────

    def begin(self, slug: str) -> int:
        """Claim an attempt ordinal for `slug`, or refuse if the book is halting.

        The ordinal is assigned HERE rather than derived from loop position, so "the
        first chapter attempted" stays a single well-defined chapter under any number of
        workers. Under one worker it is identical to the old `attempted` counter.
        """
        with self._lock:
            if self._tripped is not None:
                raise BreakerTripped(self._tripped)
            self._attempted += 1
            return self._attempted

    def tripped(self) -> str | None:
        """The halt reason, or None. Safe to poll."""
        with self._lock:
            return self._tripped

    # ── recording ────────────────────────────────────────────────────────────

    def record_failure(self, slug: str, reason: str, duration_sec: float, ordinal: int) -> str | None:
        """Record a chapter failure. Returns a systemic-halt reason, or None.

        `ordinal` is what `begin()` returned for this chapter — passed back rather than
        re-read, because under workers the counter has moved on by now and "was this the
        first attempt" is a fact about when the chapter STARTED.

        Idempotent on the verdict: once tripped, the first reason is kept. A second
        worker failing a moment later must not overwrite the diagnosis the operator will
        read.
        """
        sig = failure_signature(reason)
        with self._lock:
            slugs = self._signatures.setdefault(sig, [])
            if slug not in slugs:
                slugs.append(slug)

            systemic: str | None = None
            if ordinal == 1 and duration_sec < FAST_FAILURE_SEC:
                systemic = (
                    f"first attempted chapter '{slug}' failed in {duration_sec:.1f}s — "
                    f"deterministic/systemic (not content): {reason}"
                )
            elif len(slugs) >= SHARED_FAILURE_CHAPTERS:
                systemic = (
                    f"same failure across {len(slugs)} chapters "
                    f"({', '.join(slugs)}) — systemic, not per-chapter: {reason}"
                )

            if systemic and self._tripped is None:
                self._tripped = systemic
            return self._tripped if systemic else None

    # ── introspection, for the status card and tests ─────────────────────────

    def attempted(self) -> int:
        with self._lock:
            return self._attempted

    def signature_groups(self) -> dict[str, list[str]]:
        """Copy of {signature: [slugs]} — for reporting, never mutated by callers."""
        with self._lock:
            return {k: list(v) for k, v in self._signatures.items()}
