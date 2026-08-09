"""_phase_gates.py — the individual checks the phase review runs.

Split out of `_phase_review` on 2026-08-09. That module was 783 lines against this
repo's 600-line ceiling (DR-005) after the twenty-four ungated phases got gates of their
own, and the seam is honest rather than arbitrary: everything here answers ONE question
about a book on disk and knows nothing about phases, verdicts, ordering or blocking.
`_phase_review` owns all of that and imports these.

Each gate is `fn(book_dir) -> (passed, note)`, the exact shape `validate_book_ready`'s
`gate_b1..b8` already use, so the two report identically and a reader learns one format.

A gate must never raise on a book that simply has not reached that phase yet: an early
book is not a broken one, and a gate that crashes on an empty directory would make every
new book noisy. `test_phase_own_gates.NoGateCrashesOnAnEmptyBookTests` drives every
declared gate against a bare directory for exactly this.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))


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


# ─── OWN gates for the phases that had none (2026-08-09) ─────────────────────
#
# Every gate below was validated against all 22 books on disk before being added:
# run over the books that ACTUALLY COMPLETED that phase, each one reports zero
# failures. A gate that cries wolf on healthy books is worse than no gate, because
# it teaches a reader to skim past the review — so a candidate that could not clear
# that bar was dropped rather than softened. Three were dropped for exactly that
# reason, and they are recorded in NO_OWN_GATE_REASON with what went wrong.


def _contract_slugs(book_dir: Path) -> list[str]:
    return sorted(p.stem for p in (book_dir / "chapter-contracts").glob("*.yml"))


def gate_contracts_have_chapter_files(book_dir: Path) -> tuple[bool, str]:
    """Phase 0d writes contracts AND the chapter text each one describes.

    A contract with no chapter file is the shape a truncated design run leaves
    behind: the plan looks complete and the chapter it names does not exist, which
    is not discovered until per-chapter tries to extract it and fails a chapter at a
    time, hours and dollars later.
    """
    slugs = _contract_slugs(book_dir)
    if not slugs:
        return False, "no chapter contracts — 0d produced nothing"
    orphans = [s for s in slugs if not list((book_dir / "chapters").glob(f"ch*-{s}.txt"))]
    if orphans:
        shown = ", ".join(orphans[:5]) + (" …" if len(orphans) > 5 else "")
        return False, f"{len(orphans)} of {len(slugs)} contract(s) have no chapter file: {shown}"
    return True, f"all {len(slugs)} contract(s) have a chapter file"


def gate_enrichment_recorded(book_dir: Path) -> tuple[bool, str]:
    """Phase 0e leaves a log of what it enriched.

    Enrichment rewrites chapter text in place, so on success it changes files it does
    not create. The log is the only artifact that says it ran at all.
    """
    p = book_dir / "_system" / "enrichment-log.md"
    n = _size(p)
    if n <= 0:
        return False, "enrichment-log.md is missing or empty — 0e left no record of enriching anything"
    return True, f"enrichment-log.md present ({n:,} bytes)"


def gate_audit_bundle_written(book_dir: Path) -> tuple[bool, str]:
    """Phase 0g sweeps the finished bundles and writes its audits.

    Checked on disk rather than from the state key `audit_outcomes`: that key was
    added later, so the one book which completed 0g before it existed
    (`kitab-al-riyad`, May 2026) has a perfectly good audit directory and no key. A
    gate keyed on the state field would have reported that healthy book broken.
    """
    d = book_dir / "audits"
    if not d.is_dir():
        return False, "no audits/ directory — 0g swept nothing"
    files = [p for p in d.iterdir() if p.is_file()]
    if not files:
        return False, "audits/ is empty — 0g swept nothing"
    return True, f"{len(files)} audit file(s) written"


def gate_every_chapter_has_an_episode(book_dir: Path) -> tuple[bool, str]:
    """The per-chapter lane's deliverable is one episode text per chapter."""
    slugs = _contract_slugs(book_dir)
    if not slugs:
        return True, "no chapter contracts — nothing to compare against"
    episodes = list((book_dir / "episodes").glob("*.txt"))
    if len(episodes) < len(slugs):
        return False, f"{len(episodes)} episode text(s) for {len(slugs)} chapter(s) — the lane is short"
    return True, f"{len(episodes)} episode text(s) for {len(slugs)} chapter(s)"


def gate_completed_slugs_cover_contracts(book_dir: Path) -> tuple[bool, str]:
    """A COMPLETED per-chapter phase must name every chapter as shipped.

    The loop already refuses to report completion while any chapter failed, so this
    catches the other shape: a chapter that was never attempted at all — dropped from
    the pending list, skipped by a resume that mis-read prior state — and therefore
    never failed, never shipped, and never mentioned.
    """
    slugs = set(_contract_slugs(book_dir))
    if not slugs:
        return True, "no chapter contracts — nothing to compare against"
    from _progress import read_state

    try:
        state = read_state(book_dir) or {}
    except Exception as e:
        return True, f"cannot read state ({e})"
    done = set(((state.get("phases") or {}).get("per-chapter") or {}).get("completed_slugs") or [])
    missing = sorted(slugs - done)
    if missing:
        shown = ", ".join(missing[:5]) + (" …" if len(missing) > 5 else "")
        return False, f"{len(missing)} chapter(s) never shipped and never failed: {shown}"
    return True, f"all {len(slugs)} chapter(s) recorded as shipped"


def gate_slide_decks_present(book_dir: Path) -> tuple[bool, str]:
    """A COMPLETED slide phase produced decks.

    Only ever asked of a completed phase: a book with decks turned off records the
    phase `skipped`, which no review runs against.
    """
    d = book_dir / "slide-decks"
    if not d.is_dir():
        return False, "no slide-decks/ directory"
    files = [p for p in d.iterdir() if p.is_file()]
    if not files:
        return False, "slide-decks/ is empty"
    return True, f"{len(files)} deck file(s)"


def gate_rendered_pdf_present(book_dir: Path) -> tuple[bool, str]:
    """The render phase's whole output is a PDF a human can open.

    A floor of 10 kB rather than "exists": a failed render can leave a valid but
    essentially empty PDF behind, which passes a presence check and fools a reader
    into thinking the edition printed.
    """
    d = book_dir / "book"
    if not d.is_dir():
        return False, "no book/ directory"
    pdfs = [(p, _size(p)) for p in d.glob("*.pdf")]
    real = [(p, n) for p, n in pdfs if n > 10_000]
    if not real:
        if pdfs:
            return False, f"{len(pdfs)} PDF(s) present but all under 10 kB — the render produced an empty edition"
        return False, "no PDF in book/ — the render produced nothing"
    name, n = max(real, key=lambda t: t[1])
    return True, f"{name.name} present ({n:,} bytes)"


def gate_publication_status_flipped(book_dir: Path) -> tuple[bool, str]:
    """Publish's entire job is one field. Did it actually change?"""
    from _progress import read_state

    try:
        state = read_state(book_dir) or {}
    except Exception as e:
        return True, f"cannot read state ({e})"
    status = str(state.get("status") or "")
    if status != "published":
        return False, f"publish completed but status is {status or 'unset'!r}, not 'published'"
    return True, "status is 'published'"
