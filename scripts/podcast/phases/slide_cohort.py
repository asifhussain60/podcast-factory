"""phases/slide_cohort.py — the per-chapter-slides phase (Phase 11b).

Split out of `chapter_driver.py` on 2026-07-31 along a genuine seam: this is a
whole phase with its own concurrency model, its own fail-loud status rule, and
its own outcome vocabulary, and none of it is referenced by the chapter or audio
work either side of it. The driver now calls `run_slide_cohort` and moves on.

Two shapes, chosen by `slide_deck_mode`:

  * "book"  — ONE deck pair for the whole book (one NotebookLM generation), the
              human reviewing the exported deck at the 0book-slide-import gate.
  * default — one deck pair per chapter, chapters run CONCURRENTLY.

The concurrency is safe only because `_slide_convergence._record_state` holds
the shared state lock from `_progress` across its read-modify-write. Every
worker writes the same orchestrator-state.json; unguarded, two chapters
finishing close together each write from a snapshot predating the other and one
verdict disappears with no error raised anywhere. Do not copy this fan-out into
a phase whose writers are unguarded.
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _progress import update_phase
from _subprocess import err as _err
from _subprocess import info as _info

# Chapters are independent, and the work is subprocess-bound (`claude -p`), so
# the GIL is not the constraint and threads are the right tool. Capped rather
# than unbounded: each worker holds a model call, and a wide fan-out on a large
# book would queue against the provider instead of going faster.
_MAX_SLIDE_WORKERS = 4


def is_bad_slide_outcome(v: str) -> bool:
    """A slide-deck verdict that means the deck did NOT succeed.

    Feeds the fail-loud net that decides whether the phase reports `completed`
    or `failed`. STALLED (challenger never reached SHIP-READY after max
    iterations) is a genuine non-success and MUST count — otherwise an
    all-STALLED cohort masquerades as `completed`. BLOCKED/ERROR and any FAILED:*
    are bad too. SHIP-READY / SHIP-WITH-CAUTION / SKIPPED / AUTHORED are good
    (SKIPPED is a legitimate content-grounded outcome).
    """
    return v in {"BLOCKED", "ERROR", "STALLED"} or v.startswith("FAILED")


def _publish(book_dir: Path, outcomes: dict[str, str], *, status: str) -> None:
    """Write the cohort summary to state.

    Called after EVERY chapter, not only at the end. A cohort takes the better
    part of an hour, and `extras` merges into the phase block rather than
    replacing it — so a phase re-entered after a retry used to keep serving the
    previous run's outcomes for its entire duration. On 2026-07-31 that meant a
    cohort converging 6/6 SHIP-READY read as 6/6 BLOCKED to anything inspecting
    state mid-phase, for three hours.
    """
    n_bad = sum(1 for v in outcomes.values() if is_bad_slide_outcome(v))
    update_phase(
        book_dir,
        phase="per-chapter-slides",
        status=status,
        extras={"outcomes": dict(outcomes), "bad_outcomes": n_bad, "total_outcomes": len(outcomes)},
    )


def _run_book_mode(book_dir: Path, outcomes: dict[str, str]) -> None:
    """Book mode (2026-06-10): one deck pair for the whole book."""
    _info("phase: per-chapter-slides · slide_deck_mode=book → single book-level pair")
    try:
        from _slide_authoring import author_book_deck_pair

        result = author_book_deck_pair(book_dir)
        outcomes["book"] = "AUTHORED" if result.success else f"FAILED: {'; '.join(result.validation_findings[:3])}"
    except Exception as e:
        _err(f"book-level slide-deck authoring failed (non-fatal): {e}")
        outcomes["book"] = "ERROR"


def _run_per_chapter(book_dir: Path, slugs: list[str], outcomes: dict[str, str]) -> None:
    """One deck pair per chapter, chapters converging concurrently."""
    from _slide_convergence import run_slide_convergence

    def converge_one(slug: str) -> tuple[str, str]:
        _info(f"phase: per-chapter-slides[{slug}] · density gauge → author → challenge")
        try:
            return slug, run_slide_convergence(book_dir, slug).verdict
        except Exception as e:
            _err(f"slide-deck convergence failed for {slug} (non-fatal): {e}")
            return slug, "ERROR"

    workers = min(_MAX_SLIDE_WORKERS, max(1, len(slugs)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed(pool.submit(converge_one, s) for s in slugs):
            slug, verdict = fut.result()
            outcomes[slug] = verdict
            _publish(book_dir, outcomes, status="running")


def run_slide_cohort(book_dir: Path, completed_chapter_slugs: list[str]) -> str:
    """Run Phase 11b end to end. Returns the phase status it recorded.

    Never raises: a slide deck is a companion deliverable and must not cost the
    podcast its run. Every failure lands as an outcome instead.
    """
    _info("phase: per-chapter-slides · slide-deck cohort authoring + slide-deck-challenger")
    # Clear the PRIOR cohort's summary before re-running — see `_publish`.
    _publish(book_dir, {}, status="running")

    try:
        import _slide_convergence  # noqa: F401  (presence check — optional module)
    except ImportError as e:
        _err(f"slide-deck integration missing: {e}; skipping phase")
        update_phase(book_dir, phase="per-chapter-slides", status="skipped", extras={"reason": "module-not-available"})
        return "skipped"

    from _content_profile import slide_deck_mode

    outcomes: dict[str, str] = {}
    if slide_deck_mode(book_dir) == "book":
        _run_book_mode(book_dir, outcomes)
    else:
        _run_per_chapter(book_dir, list(completed_chapter_slugs), outcomes)

    # Fail-loud safety net: if every — or a majority of — outcomes are bad, the
    # phase did NOT succeed, and must not be able to masquerade as `completed`.
    n_total = len(outcomes)
    n_bad = sum(1 for v in outcomes.values() if is_bad_slide_outcome(v))
    status = "failed" if n_total and n_bad * 2 >= n_total else "completed"
    _publish(book_dir, outcomes, status=status)
    if status == "failed":
        _err(f"per-chapter-slides: {n_bad}/{n_total} deck outcomes BLOCKED/ERROR/FAILED — phase marked failed")
    return status
