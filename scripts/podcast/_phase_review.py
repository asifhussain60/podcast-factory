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

  Every gate is ADVISORY unless its id is in `BLOCKING_GATES`. A brand-new review
  layer that can halt a run is a layer that can strand a finished book, and the
  cost of a false positive here is a human unblocking a book that was fine. This
  mirrors the split `_compose_skips` already draws between page-altering steps
  (which fail gate B8) and advisory ones (which only report). Gates get promoted
  one at a time, after being watched reporting correctly on real books.

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


# ─── helpers ─────────────────────────────────────────────────────────────────


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return -1


def _words(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").split())
    except OSError:
        return -1


def _steps(book_dir: Path, phase: str) -> dict[str, dict[str, Any]]:
    """The latest record per step for `phase`, from the most recent run."""
    from _step_ledger import last_by_step, latest_steps

    return last_by_step(latest_steps(book_dir, phase=phase))


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


def _derives_from_container(book_dir: Path) -> bool:
    """True when this book is a VOLUME that takes its source from a parent container.

    The nested multi-volume series do not each own an OCR scan: the whole work is
    scanned once at the container and each volume works from its own slice. Verified on
    disk 2026-08-08 — `asaas-al-taveel/vol-02` and `al-anwaar-al-lateefah/vol-01` both
    carry `refined-english.md` and legitimately no `raw-extract.md`, while the container
    holds the scan (`asaas-al-taveel/_source/`).

    TWO signals, because the two series do NOT declare it the same way and a single
    check missed half of them on the first attempt:

      * `content-range.md` — an explicit declaration of which pages this volume covers.
        All six `asaas-al-taveel` volumes have one; no `al-anwaar-al-lateefah` volume
        does.
      * a `vol-*` directory with sibling `vol-*` directories beside it — structural, and
        what catches the second series. The `vol-` prefix follows the one precedent in
        the repo (`fill_glossary_cross_book.py:95`); requiring SIBLINGS is what keeps it
        from firing on a coincidentally-named folder.
    """
    book_dir = Path(book_dir)
    if (book_dir / "_system" / "source" / "text" / "content-range.md").exists():
        return True
    if not book_dir.name.startswith("vol-"):
        return False
    try:
        siblings = [d for d in book_dir.parent.iterdir() if d.is_dir() and d.name.startswith("vol-")]
    except OSError:
        return False
    return len(siblings) >= 2


# ─── OWN gates ───────────────────────────────────────────────────────────────


def gate_source_text_present(book_dir: Path) -> tuple[bool, str]:
    p = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    n = _size(p)
    if n <= 0:
        # A volume of a nested series has no scan of its own — the whole work is
        # scanned once at the container and each volume declares its slice. Reporting
        # those as broken accounted for 22 of the 162 failures in the 2026-08-08 sweep,
        # across eleven perfectly healthy volumes.
        if _derives_from_container(book_dir):
            return True, "no scan of its own — this volume slices a container's source (content-range.md)"
        return False, f"raw-extract.md is missing or empty ({p.name})"
    return True, f"raw-extract.md present ({n:,} bytes)"


def gate_refined_text_present(book_dir: Path) -> tuple[bool, str]:
    p = book_dir / "_system" / "source" / "text" / "refined-english.md"
    n = _size(p)
    if n <= 0:
        return False, "refined-english.md is missing or empty"
    return True, f"refined-english.md present ({n:,} bytes)"


def gate_refined_covers_source(book_dir: Path) -> tuple[bool, str]:
    """Refinement rewrites prose; it must not LOSE most of it.

    A generous floor on purpose (60% of the source's words). Refinement legitimately
    drops OCR apparatus, headers and page furniture, so a strict ratio would cry
    wolf on every book. What this catches is the failure that actually happens: a
    windowed run that stitched only some of its windows, so the refined text is a
    fraction of the source and every later phase works from a truncated book.
    """
    src = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    out = book_dir / "_system" / "source" / "text" / "refined-english.md"
    sw, ow = _words(src), _words(out)
    if sw <= 0 or ow <= 0:
        return True, "cannot compare (one side missing) — see the presence gates"
    ratio = ow / sw
    if ratio < 0.60:
        return False, f"refined text is {ratio:.0%} of the source ({ow:,} of {sw:,} words) — likely truncated"
    return True, f"refined text is {ratio:.0%} of the source ({ow:,} of {sw:,} words)"


def gate_windows_not_repaid(book_dir: Path) -> tuple[bool, str]:
    """Did this windowed phase pay again for windows it already had?

    The evidence is the step ledger's own distinction between a window that was
    COMPUTED (`ok`) and one served from cache (`noop`). Phase 0b re-refined all 28
    windows of `spiritual-ethos` five times on 2026-08-05 — $8.38, 81% of that
    book's entire real spend — and nothing on disk afterwards said so.

    Advisory: a first run legitimately computes every window. What this surfaces is
    the SHAPE of a re-run, for a human reading the review.
    """
    rows = _steps(book_dir, "0b")
    wins = {k: v for k, v in rows.items() if k.startswith("win-")}
    if not wins:
        return True, "no window records for this run"
    computed = [k for k, v in wins.items() if v.get("outcome") == "ok"]
    cached = [k for k, v in wins.items() if v.get("outcome") == "noop"]
    if computed and not cached:
        return True, f"computed all {len(computed)} window(s) — consistent with a first run"
    if computed and cached:
        return True, f"{len(cached)} window(s) from cache, {len(computed)} recomputed"
    return True, f"all {len(cached)} window(s) served from cache — no spend"


def gate_window_cache_intact(book_dir: Path) -> tuple[bool, str]:
    """The window cache must not vanish while its source is unchanged.

    On 2026-08-05 the 0b cache was absent at the start of five separate runs on the
    same unchanged source, and each run re-paid for all 28 windows. Nothing in this
    repo deletes it and the `Cleanup Mac` script cannot reach `~/PROJECTS`, so the
    cause is still unidentified — which is exactly why the CONDITION is worth
    reporting rather than the cause worth guessing. `**/_chunks/` is gitignored, so
    a hand-typed `git clean -fdx` removes it.
    """
    src = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    out = book_dir / "_system" / "source" / "text" / "refined-english.md"
    cache = book_dir / "_system" / "source" / "text" / "_chunks" / "0b"
    if _size(out) <= 0:
        return True, "0b has not produced output yet — nothing to cache"
    present = sorted(cache.glob("win-*.out.md")) if cache.is_dir() else []
    if present:
        return True, f"window cache intact ({len(present)} window(s))"
    if _size(src) <= 0:
        return True, "no source on disk — cache absence is expected"
    return (
        False,
        "0b produced refined text but its window cache is GONE while the source is "
        "still present — a re-run will re-pay for every window (~$8 on a 28-window "
        "book). Nothing in this repo deletes it; `**/_chunks/` is gitignored, so a "
        "`git clean -fdx` would.",
    )


def gate_chapter_contracts_exist(book_dir: Path) -> tuple[bool, str]:
    d = book_dir / "chapter-contracts"
    n = len(list(d.glob("*.yml"))) if d.is_dir() else 0
    if n == 0:
        return False, "no chapter contracts — phase 0d produced nothing"
    return True, f"{n} chapter contract(s)"


def gate_book_toc_parses(book_dir: Path) -> tuple[bool, str]:
    p = book_dir / "book" / "book-toc.json"
    if _size(p) <= 0:
        return False, "book-toc.json is missing or empty"
    try:
        toc = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"book-toc.json does not parse: {e}"
    chapters = toc.get("chapters") or []
    if not chapters:
        return False, "book-toc.json parses but declares no chapters"
    return True, f"book-toc.json declares {len(chapters)} chapter(s)"


def gate_book_md_present(book_dir: Path) -> tuple[bool, str]:
    p = book_dir / "book" / "book.md"
    n = _size(p)
    if n <= 0:
        return False, "book/book.md is missing or empty"
    return True, f"book.md present ({n:,} bytes)"


def gate_book_md_covers_toc(book_dir: Path) -> tuple[bool, str]:
    """Every chapter the design declared must have a heading in the composed book."""
    toc_path = book_dir / "book" / "book-toc.json"
    md_path = book_dir / "book" / "book.md"
    if _size(toc_path) <= 0 or _size(md_path) <= 0:
        return True, "cannot compare (toc or book.md missing) — see the presence gates"
    try:
        toc = json.loads(toc_path.read_text(encoding="utf-8"))
        md = md_path.read_text(encoding="utf-8")
    except Exception as e:
        return True, f"cannot compare ({e})"
    declared = [str(c.get("title") or "") for c in (toc.get("chapters") or [])]
    headings = md.count("\n## ")
    if not declared:
        return True, "toc declares no chapters"
    if headings < len(declared):
        return False, f"book.md has {headings} chapter heading(s) for {len(declared)} declared chapter(s)"
    return True, f"{headings} heading(s) for {len(declared)} declared chapter(s)"


def gate_apparatus_steps_all_ran(book_dir: Path) -> tuple[bool, str]:
    """Every declared apparatus step must have left a record.

    This is the question no gate could ask before the step ledger existed: not
    "did anything fail" but "did each step that was supposed to run actually run".
    A step deleted from the sequence, or never reached because an earlier one
    returned early, used to be undetectable — nothing failed, so nothing reported.
    """
    from _book_apparatus import APPARATUS_STEPS

    recorded = _steps(book_dir, "0book-compose")
    if not recorded:
        return True, "no step records for this run (compose may not have run yet)"
    missing = [s for s in APPARATUS_STEPS if s not in recorded]
    if missing:
        return False, f"{len(missing)} apparatus step(s) left no record: {', '.join(missing)}"
    return True, f"all {len(APPARATUS_STEPS)} apparatus step(s) recorded"


def gate_no_page_altering_step_failed(book_dir: Path) -> tuple[bool, str]:
    """Delegates the classification to `_compose_skips`, which already owns it.

    Re-deriving "which steps change the printed page" here would be a second
    answer to a question that already has one, and the two would drift.
    """
    from _compose_skips import verdict

    return verdict(book_dir)


def gate_no_step_failed(book_dir: Path) -> tuple[bool, str]:
    """Any failed step in the most recent run, across every phase. Advisory."""
    from _step_ledger import latest_steps

    failed = [r for r in latest_steps(book_dir) if r.get("outcome") == "failed"]
    if not failed:
        return True, "no step failed in this run"
    names = ", ".join(dict.fromkeys(str(r.get("step")) for r in failed))
    return False, f"{len(failed)} step(s) failed: {names}"


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
    ],
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
#: Deliberately small to begin with — see the module docstring on blocking policy.
#: PC3 is here because it delegates to gate B8, which was already blocking at ship
#: time; promoting it to the compose boundary changes WHEN it is enforced, not
#: WHETHER, so it introduces no new way to strand a book.
BLOCKING_GATES: frozenset[str] = frozenset({"PC3"})


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
