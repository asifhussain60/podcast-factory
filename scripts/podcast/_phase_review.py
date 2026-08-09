"""_phase_review.py — after each phase, check the evidence that it actually worked.

WHY THIS EXISTS

  A phase records `completed` when its code reached the end without raising. That
  is not the same as having done the work, and the gap has cost real books: the
  compose path wraps twenty-five steps in non-fatal `try` blocks, so a book could
  reach `completed` having silently discarded the human's own Composer edits, the
  Arabic overlay and the vowelling. `validate_book_ready` catches some of that —
  but it runs ONCE, at the very end, after every phase has already reported
  success.

  This module moves that idea to every phase boundary, and bases it on recorded
  evidence rather than exit codes. Two tiers:

    OWN gates      — did THIS phase do its own job
    RECHECK gates  — is the work of every EARLIER phase still intact

  The recheck tier is the specific request behind this: phase 0c should evaluate
  0a's and 0b's work too, not assume a pass that already succeeded is still
  correct. Recheck gates are therefore deliberately CHEAP and read-only — a stat,
  a word count, a JSON parse — so a phase twenty deep can re-verify everything
  before it for free.

BLOCKING POLICY (deliberate)

  Every gate is ADVISORY unless its id is in `BLOCKING_GATES`. A blocking gate
  REWRITES the phase as failed — `_progress.update_phase` runs this review at every
  phase completion and applies the verdict — so the run stops at the phase that did
  not do its job instead of advancing over it.

  The line is drawn at judgement. A gate blocks when its failure means the phase
  provably did not produce its own required output: a missing file, a chapter never
  shipped, a status never flipped. A gate stays advisory when it applies a HEURISTIC
  — a word-count ratio, a heading count, a re-run shape — because a threshold can be
  wrong about a healthy book, and the first false positive would be a finished book
  halted over a rule nobody can argue with at 2am.

  A blocking gate can delay a book but never strand one: the phase is recorded
  `failed` with the gate's own reason, and `--resume <slug> --retry-phase <phase>`
  resets it and everything downstream. `PODCAST_PHASE_GATES=off` withdraws blocking
  for a run without withdrawing the review.

  Until 2026-08-09 this layer could not block at all — it recorded its verdict beside
  a `completed` phase and the run carried on, which made it a report nobody was
  obliged to read. Promotion was gated on watching the gates report correctly on real
  books; that evidence was gathered at once instead, by sweeping every gate across all
  22 books on disk over each book that had actually completed the phase.

SHAPE

  Each gate returns `(passed, note)` — the exact shape `validate_book_ready`'s
  `gate_b1..b8` already use, so the two report identically and a reader learns one
  format. Results land in `_system/phase-reviews/<phase>.json` and a one-line
  summary is written into the phase's own state block.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA = "podcast.phase-review/v1"

#: A gate is (id, human name, fn(book_dir) -> (passed, note)).
Gate = tuple[str, str, Callable[[Path], tuple[bool, str]]]

VERDICT_SOUND = "PHASE-SOUND"
VERDICT_CONCERNS = "PHASE-CONCERNS"
VERDICT_BROKEN = "PHASE-BROKEN"

# The gates themselves live in `_phase_gates` (DR-005 split, 2026-08-09). Re-exported
# here because every caller and test reaches for them at this path, and because the
# registries below read as a table of contents only when the names are in scope.
from _phase_gates import (  # noqa: F401  - re-exported for callers and tests
    gate_apparatus_steps_all_ran,
    gate_audit_bundle_written,
    gate_book_md_covers_toc,
    gate_book_md_present,
    gate_book_toc_parses,
    gate_chapter_contracts_exist,
    gate_completed_slugs_cover_contracts,
    gate_contracts_have_chapter_files,
    gate_enrichment_recorded,
    gate_every_chapter_has_an_episode,
    gate_no_new_reading_edition_defects,
    gate_no_page_altering_step_failed,
    gate_no_step_failed,
    gate_publication_status_flipped,
    gate_refined_covers_source,
    gate_refined_text_present,
    gate_rendered_pdf_present,
    gate_slide_decks_present,
    gate_source_text_present,
    gate_window_cache_intact,
    gate_windows_not_repaid,
)


def _completed_phases(book_dir: Path) -> set[str] | None:
    """Phases this book has actually completed, or None when state is unreadable.

    None means "cannot tell", and every caller treats that as "check everything" —
    a standalone review over a book with no state file must still report something.
    """
    try:
        from _progress import read_state

        state = read_state(book_dir)
    except Exception:
        return None
    if not state:
        return None
    phases = state.get("phases")
    if not isinstance(phases, dict):
        return None
    return {p for p, blk in phases.items() if isinstance(blk, dict) and blk.get("status") == "completed"}


# ─── registries ──────────────────────────────────────────────────────────────

#: Gates about a phase's OWN work, run when that phase completes.
OWN_GATES: dict[str, list[Gate]] = {
    "0a": [("PA1", "source-text-present", gate_source_text_present)],
    "0b": [
        ("PB1", "refined-text-present", gate_refined_text_present),
        ("PB2", "refined-covers-source", gate_refined_covers_source),
        ("PB3", "windows-not-repaid", gate_windows_not_repaid),
    ],
    "0d": [("PD1", "chapter-contracts-exist", gate_chapter_contracts_exist)],
    "0book-design": [("PG1", "book-toc-parses", gate_book_toc_parses)],
    "0book-compose": [
        ("PC1", "book-md-present", gate_book_md_present),
        ("PC2", "apparatus-steps-all-ran", gate_apparatus_steps_all_ran),
        ("PC3", "no-page-altering-step-failed", gate_no_page_altering_step_failed),
        ("PC4", "book-md-covers-toc", gate_book_md_covers_toc),
        ("PC5", "no-new-reading-edition-defects", gate_no_new_reading_edition_defects),
    ],
    # Added 2026-08-09. Until then twenty-four of the twenty-nine phases checked
    # nothing about the work they had just done; the review layer only re-verified
    # that the five gated phases' outputs still existed.
    "0e": [("PE1", "enrichment-recorded", gate_enrichment_recorded)],
    "0g": [("PGG1", "audit-bundle-written", gate_audit_bundle_written)],
    "per-chapter": [
        ("PPC1", "every-chapter-has-an-episode", gate_every_chapter_has_an_episode),
        ("PPC2", "completed-slugs-cover-contracts", gate_completed_slugs_cover_contracts),
    ],
    "per-chapter-slides": [("PPS1", "slide-decks-present", gate_slide_decks_present)],
    "0book-render": [("PBR1", "rendered-pdf-present", gate_rendered_pdf_present)],
    "publish": [("PP1", "publication-status-flipped", gate_publication_status_flipped)],
}

#: Why a phase has no gate of its own. EXHAUSTIVE with `OWN_GATES` over `_progress.PHASES`
#: — a test asserts every phase appears in exactly one of the two, so a new phase cannot
#: quietly join the pipeline unexamined. "No gate" is then a decision on the record
#: rather than an oversight, which is the whole difference between the two.
NO_OWN_GATE_REASON: dict[str, str] = {
    # Bookkeeping — these move git or state and produce no artifact to inspect. Their
    # failure mode is an exception, which already fails the phase.
    "pre-flight": "environment check; produces nothing to inspect",
    "branch": "creates the content branch; git is the record",
    "scaffold": "creates empty directories; 0a is the first phase with output",
    "merge": "merges the content branch; git is the record",
    "done": "terminal marker, not work",
    "trainer": "proposes spec refinements on a branch; its own regression suite is the gate",
    # Human halts — these deliberately stop for review and record `halted`, not
    # `completed`, so a completion gate would never run. Verified on disk: of the books
    # with a 0f block, six are `halted` and none is `completed`.
    "06a": "human approval halt",
    "0f": "series-plan review halt — records `halted`, never `completed`",
    "finalize": "the reviewable-deliverable halt — records `halted`, never `completed`",
    # No dependable universal artifact. Each of these was probed against all 22 books
    # and the candidate gate failed on healthy ones, so it was dropped rather than
    # softened into something that passes everything.
    "0c": (
        "phonetic pass; candidate gates on unified-book.md and glossary.yml both failed "
        "on healthy books (6 of 8 and 1 of 8) — it rewrites in place and its artifacts "
        "are route-dependent"
    ),
    "0ci": "book-intelligence gap analysis; advisory output, no required artifact",
    "0literary": "literary pass; rewrites in place, no artifact of its own",
    # Optional or engine-dependent, and no book has ever COMPLETED them — every book on
    # disk records `skipped` (the manual NotebookLM engine) or has no block at all. A
    # gate written against zero evidence is a guess, and the first book to reach the
    # phase would be the one it cried wolf on.
    "audio-script": "no book has completed this phase; manual-engine books record `skipped`",
    "audio-render": "no book has completed this phase; manual-engine books record `skipped`",
    "audio-ingest": "no book has completed this phase; manual-engine books record `skipped`",
    "0book-illustrate": "no book has completed this phase; gate it when one has",
    "0book-slide-import": "no book has completed this phase; gate it when one has",
    "per-chapter-optimize": "opt-in Sonnet pass, default off; records `skipped` for most books",
}

#: CHEAP, read-only gates that every LATER phase re-runs. This is the cross-phase
#: re-verification: a defect introduced early is caught at the next checkpoint
#: rather than surviving into the finished PDF. Keep these to a stat, a word count
#: or a JSON parse — a phase near the end re-runs all of them.
RECHECK_GATES: dict[str, list[Gate]] = {
    "0a": [("RA1", "source-text-still-present", gate_source_text_present)],
    "0b": [
        ("RB1", "refined-text-still-present", gate_refined_text_present),
        ("RB2", "refined-still-covers-source", gate_refined_covers_source),
        ("RB3", "window-cache-intact", gate_window_cache_intact),
    ],
    "0d": [("RD1", "chapter-contracts-still-exist", gate_chapter_contracts_exist)],
    "0book-design": [("RG1", "book-toc-still-parses", gate_book_toc_parses)],
}

#: Only these gate ids may fail a phase. Everything else reports and is ignored.
#:
#: THE LINE (2026-08-09). A gate blocks when its failure means the phase provably did
#: not produce its own required output — a missing file, a chapter never shipped, a
#: status never flipped. Those cannot be wrong about a healthy book: there is no
#: judgement in "the PDF is not there".
#:
#: A gate stays ADVISORY when it applies a HEURISTIC — a word-count ratio, a heading
#: count, a re-run shape. Those are worth reporting and must never strand a book,
#: because the threshold is a guess and the first false positive would be a finished
#: book halted for a rule nobody can argue with at 2am.
#:
#: Every id below was run against all 22 books on disk, over each book that actually
#: completed that phase: 17 gates, zero failures, zero crashes. That sweep is the
#: evidence for promotion — the policy this replaces asked for gates to be watched
#: reporting correctly on real books first, and this is that check done at once
#: rather than one gate at a time.
#:
#: A promoted gate can never permanently strand a book: it records the phase `failed`
#: with the gate's own reason, and `--resume <slug> --retry-phase <phase>` resets that
#: phase and everything downstream. Blocking can also be turned off wholesale for a
#: run — see `blocking_enabled`.
BLOCKING_GATES: frozenset[str] = frozenset(
    {
        "PA1",  # source text present
        "PB1",  # refined text present
        "PD1",  # chapter contracts exist
        "PG1",  # book toc parses
        "PC1",  # book.md present
        "PC3",  # no page-altering compose step failed (was blocking before this list grew)
        "PE1",  # enrichment recorded
        "PGG1",  # audit bundle written
        "PPC1",  # every chapter has an episode
        "PPC2",  # completed slugs cover contracts
        "PPS1",  # slide decks present
        "PBR1",  # rendered pdf present
        "PP1",  # publication status flipped
    }
)

#: Advisory by deliberate choice, listed so the split is legible rather than implied by
#: absence: PB2 (60% word-count floor), PB3 (re-run shape), PC2 (depends on the ledger
#: being complete), PC4 (heading count vs declared chapters).

#: Set to any of these to turn blocking off for a run. The review still runs and still
#: records everything it finds — only the ability to fail a phase is withdrawn. Exists so
#: a false positive can never be a reason to wait for a code change, and so a book can be
#: pushed through under supervision.
_OFF_VALUES = frozenset({"0", "off", "false", "no"})
BLOCKING_ENV = "PODCAST_PHASE_GATES"


def blocking_enabled() -> bool:
    """False when the operator has turned blocking off for this run."""
    import os

    return os.environ.get(BLOCKING_ENV, "on").strip().lower() not in _OFF_VALUES


#: Phase order, used to decide which recheck tiers a phase inherits. Read from
#: `_progress.PHASES` rather than restated, so a new phase cannot drift out of order.
def _phase_order() -> tuple[str, ...]:
    from _progress import PHASES

    return PHASES


def phase_has_gates(phase: str) -> bool:
    """True when reviewing `phase` would actually check something.

    `_progress.update_phase` consults this so the twenty-four phases with no gates
    of their own and nothing earlier to re-verify pay nothing at all. A phase with
    only RECHECK ancestors still counts — re-verifying 0a's work at 0d is the whole
    point of the recheck tier.
    """
    if phase in OWN_GATES:
        return True
    order = _phase_order()
    try:
        cutoff = order.index(phase)
    except ValueError:
        return False
    return any(earlier in RECHECK_GATES for earlier in order[:cutoff])


# ─── the review ──────────────────────────────────────────────────────────────


def review_phase(book_dir: Path, phase: str, *, log=None) -> dict[str, Any]:
    """Run `phase`'s own gates plus every earlier phase's recheck gates.

    Never raises. A gate that blows up is recorded as its own result — neither a
    pass nor a silent omission — for the same reason `validate_book_ready` records
    an UNKNOWN verdict when its gate crashes: "the check that would have told us
    broke" must not read as "the work is sound".
    """
    book_dir = Path(book_dir).resolve()
    order = _phase_order()
    try:
        cutoff = order.index(phase)
    except ValueError:
        cutoff = len(order)

    gates: list[dict[str, Any]] = []
    blocking_fail: str | None = None

    def _run(gid: str, name: str, fn, kind: str) -> None:
        nonlocal blocking_fail
        try:
            passed, note = fn(book_dir)
        except Exception as e:  # a broken gate is not a pass
            gates.append(
                {
                    "gate": gid,
                    "name": name,
                    "kind": kind,
                    "passed": None,
                    "note": f"gate crashed: {type(e).__name__}: {e}",
                }
            )
            return
        gates.append({"gate": gid, "name": name, "kind": kind, "passed": bool(passed), "note": note})
        if not passed and gid in BLOCKING_GATES and blocking_fail is None:
            blocking_fail = f"{gid} {name}: {note}"

    for gid, name, fn in OWN_GATES.get(phase, []):
        _run(gid, name, fn, "own")

    # Every phase at or before this one re-verifies. `0book-compose` re-checks 0a,
    # 0b, 0d and 0book-design; `0b` re-checks only 0a.
    #
    # ONLY phases this book actually COMPLETED. A recheck asks "is the work of an
    # earlier phase still intact", which is meaningless for a phase that never ran —
    # and every route skips something: a `source-ready` book (explainers, sites) never
    # does OCR, so demanding its `raw-extract.md` complains about work it was never
    # asked to do. That accounted for 95 of the 162 failures in the 2026-08-08 sweep
    # across 23 books, i.e. most of the noise, none of it a defect.
    #
    # `None` means the state file is unreadable or absent, and then EVERY recheck runs:
    # a standalone review over a book with no orchestrator state must still report
    # something rather than silently checking nothing. "Cannot tell" must never be the
    # quiet path.
    completed = _completed_phases(book_dir)
    for earlier in order[: cutoff + 1]:
        if earlier == phase:
            continue
        if completed is not None and earlier not in completed:
            continue
        for gid, name, fn in RECHECK_GATES.get(earlier, []):
            _run(gid, f"{name} (from {earlier})", fn, "recheck")

    failed = [g for g in gates if g["passed"] is False]
    crashed = [g for g in gates if g["passed"] is None]
    if blocking_fail:
        verdict = VERDICT_BROKEN
    elif failed or crashed:
        verdict = VERDICT_CONCERNS
    else:
        verdict = VERDICT_SOUND

    report = {
        "schema": SCHEMA,
        "phase": phase,
        "verdict": verdict,
        "blocking_fail": blocking_fail,
        "counts": {"total": len(gates), "failed": len(failed), "crashed": len(crashed)},
        "gates": gates,
    }

    _write_report(book_dir, phase, report)
    if log:
        _log_report(report, log)
    return report


def _write_report(book_dir: Path, phase: str, report: dict[str, Any]) -> None:
    """Persist the report. Guarded — a recorder must never fail the phase."""
    try:
        out_dir = book_dir / "_system" / "phase-reviews"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{phase}.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except Exception:
        pass


def _log_report(report: dict[str, Any], log) -> None:
    counts = report["counts"]
    log(
        f"    review[{report['phase']}]: {report['verdict']} — "
        f"{counts['total'] - counts['failed'] - counts['crashed']}/{counts['total']} gate(s) passed"
    )
    for g in report["gates"]:
        if g["passed"] is not True:
            marker = "FAIL" if g["passed"] is False else "CRASH"
            log(f"      {marker} {g['gate']} {g['name']}: {g['note']}")


def review_and_record(book_dir: Path, phase: str, *, log=None) -> dict[str, Any]:
    """`review_phase`, plus a one-line summary into the phase's state block.

    Kept separate so a caller that only wants the report (a CLI, a test) does not
    write state as a side effect.
    """
    report = review_phase(book_dir, phase, log=log)
    try:
        from _progress import read_state, write_state

        state = read_state(book_dir)
        if state is not None:
            block = state.get("phases", {}).get(phase)
            if isinstance(block, dict):
                block["review"] = {
                    "verdict": report["verdict"],
                    "failed": report["counts"]["failed"],
                    "crashed": report["counts"]["crashed"],
                    "total": report["counts"]["total"],
                }
                write_state(book_dir, state)
    except Exception:
        pass
    return report
