#!/usr/bin/env python3
"""vowel_source.py — put the vowel marks on a book's Arabic SOURCE stream.

WHY AT THE SOURCE, when `vowel_book.py` already vowels the composed book. Three
things the later pass cannot do:

  * The GLOSSARY is filled from the OCR (`fill_glossary_arabic`). Marking the
    source is what puts marks on `arabic_script` at its root, so the inline terms
    the overlay weaves into English arrive already vowelled instead of depending
    on a second model pass to catch them afterwards.
  * `book.md` is REGENERATED on every compose, so marks applied to it are paid for
    again every time. A source is written once and every later compose inherits it.
  * The compose prompt is handed the Arabic pages as ground truth and asked to
    quote them; giving it vowelled text means the quotation arrives marked rather
    than being re-derived. `_narrative` already instructs every prose pass to keep
    whatever marks a run carries.

`vowel_book.py` STAYS as the net behind this: anything the model dropped in
transcription, and every glossary term woven in later, is still caught at compose
time. Because a run that already carries its marks is skipped, feeding it a
vowelled source makes it cheaper rather than redundant.

WHAT IS NOT DONE HERE. Only `vowel_runs` — the run sweep and the mushaf. The
third, "lexical" layer of `vowel_book` looks for bare Arabic inside quotes and
parentheses, which in ENGLISH prose means a word the author put there to be looked
at. In an Arabic critical edition the same brackets hold footnote markers and
manuscript-variant apparatus, and its three-letter floor counts Arabic-Indic
digits, so `(٥)` would qualify. Running it here would spend money marking
apparatus.

    python3 scripts/podcast/vowel_source.py the-master-and-the-disciple
    python3 scripts/podcast/vowel_source.py the-master-and-the-disciple --apply
    python3 scripts/podcast/vowel_source.py --all --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _arabic_coverage import normalize_arabic  # noqa: E402
from _paths import REPO_ROOT, content_dir  # noqa: E402
from _vowelled_source import (  # noqa: E402
    is_current,
    record_stream,
    sibling_for,
    write_atomic,
)
from _vowelling import ARABIC_RE  # noqa: E402

# The Arabic streams a book can carry, in the order they are reported. Lane A is
# the single-source PDF ingest; Lane B is the multi-source (WC8) intake, whose OCR
# and denoised copies are both vowelled — `produce_bilingual` reads the OCR one and
# `reconcile_book` the denoised one, and a re-denoise invalidates only its own
# sibling by fingerprint.
ARABIC_STREAMS = (
    Path("_system/source/ocr/raw-extract.md"),
    Path("_system/source/multi/ocr/arabic.md"),
    Path("_system/source/multi/denoised/arabic.md"),
)

# Below this an "Arabic source" is an English one that happens to quote a little
# Arabic — the same floor `_load_arabic_pages` applies before it will treat an
# extract as Arabic ground truth at all.
MIN_ARABIC_CHARS = 200


def arabic_streams(book_dir: Path) -> list[Path]:
    """The Arabic source files this book actually has."""
    out = []
    for rel in ARABIC_STREAMS:
        p = book_dir / rel
        if not p.exists():
            continue
        if len(ARABIC_RE.findall(p.read_text(encoding="utf-8"))) < MIN_ARABIC_CHARS:
            continue
        out.append(p)
    return out


def _structure_complaint(before: str, after: str, mushaf_pairs: list | None = None) -> str | None:
    """Why this vowelling must not be written, or None when it is safe.

    A last check on the whole FILE, after the per-run gate has already passed on
    each run separately. The per-run gate cannot see a page marker going missing
    or two lines merging at a run boundary, and these are the invariants the
    downstream readers depend on: `_load_arabic_pages` splits on `<!-- page N -->`
    and `produce_bilingual` slices by line number.

    `mushaf_pairs` is what keeps the skeleton check honest. Setting a Qur'anic run
    from the canonical mushaf REPLACES it with Uthmani text, letters and all — the
    one substitution in this repo that is right rather than a defect. Those
    replacements are applied to `before` first, so a correctly-restored verse does
    not read as the file having been corrupted. Without this every Arabic source
    carrying a recognised verse would be refused outright, which is what the first
    live run on a real book turned up.
    """
    expected = before
    for pair in mushaf_pairs or []:
        expected = expected.replace(pair[0], pair[1])
    if normalize_arabic(expected) != normalize_arabic(after):
        return "the consonantal skeleton of the file changed"
    if before.count("\n") != after.count("\n"):
        return f"line count changed ({before.count(chr(10))} -> {after.count(chr(10))})"
    if before.count("<!-- page") != after.count("<!-- page"):
        return "page markers were lost"
    return None


def vowel_stream(
    source: Path,
    *,
    log: Callable[[str], None] = print,
    apply: bool = False,
    force: bool = False,
    call: Callable[[str], str] | None = None,
) -> dict:
    """Vowel one Arabic source stream into its sibling. Returns the run's stats."""
    from vowel_book import vowel_runs

    if not force and is_current(source):
        log(f"    {source.name}: already vowelled for this exact source — skipped")
        return {"skipped": "current", "vowelled": 0}

    before = source.read_text(encoding="utf-8")
    after, stats = vowel_runs(before, log=log, dry_run=not apply, call=call)

    if not apply:
        log(
            f"    {source.name}: {stats.get('vowelled', 0)} run(s) would be marked, "
            f"{stats.get('already', 0)} already vowelled, "
            f"{stats.get('quranic', 0)} Qur'anic"
        )
        return stats
    if stats.get("skipped"):
        return stats

    complaint = _structure_complaint(before, after, stats.get("mushaf_pairs"))
    if complaint:
        # Refuse the whole file rather than write a source whose shape moved. Every
        # reader downstream keys off that shape.
        stats["structure_refusal"] = complaint
        log(f"    {source.name}: REFUSED — {complaint}")
        return stats

    sibling = sibling_for(source)
    write_atomic(sibling, after)
    log(
        f"    {source.name}: {stats.get('vowelled', 0)} run(s) marked "
        f"(+{stats.get('marks_added', 0)} marks), {stats.get('from_mushaf', 0)} from the mushaf, "
        f"{stats.get('already', 0)} already vowelled, {stats.get('refused', 0)} refused "
        f"-> {sibling.name}"
    )
    return stats


def vowel_source(
    book_dir: Path,
    *,
    log: Callable[[str], None] = print,
    apply: bool = False,
    force: bool = False,
    only: str | None = None,
) -> dict:
    """Vowel every Arabic source stream a book carries."""
    streams = arabic_streams(book_dir)
    if only:
        streams = [p for p in streams if only in p.as_posix()]
    if not streams:
        log("    no Arabic source stream — nothing to vowel")
        return {}

    from vowel_book import record_spend

    all_stats: dict[str, dict] = {}
    for source in streams:
        stats = vowel_stream(source, log=log, apply=apply, force=force)
        all_stats[source.name] = stats
        if apply and not stats.get("skipped") and not stats.get("structure_refusal"):
            record_stream(book_dir, source=source, sibling=sibling_for(source), stats=stats)
            record_spend(book_dir, phase="0a", step="vowel-source", stats=stats)
    return all_stats


def _books_with_an_arabic_source() -> list[Path]:
    seen: list[Path] = []
    for rel in ARABIC_STREAMS:
        for hit in (REPO_ROOT / "content").glob(f"*/**/{rel.as_posix()}"):
            book = hit
            for _ in rel.parts:
                book = book.parent
            if book not in seen:
                seen.append(book)
    return sorted(seen)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Vowel a book's Arabic source stream into a .vowelled.md sibling.",
        epilog="Dry run by default — this spends real money at sweep scale. Pass --apply to write.",
    )
    ap.add_argument("slug", nargs="?", help="one book; omit and pass --all to sweep every book")
    ap.add_argument("--all", action="store_true", help="sweep every book carrying an Arabic source")
    ap.add_argument("--apply", action="store_true", help="write the siblings (otherwise report only)")
    ap.add_argument("--force", action="store_true", help="re-vowel even when the sibling is current")
    ap.add_argument("--stream", help="restrict to streams whose path contains this substring")
    a = ap.parse_args()

    if bool(a.slug) == bool(a.all):
        print("Pass exactly one of <slug> or --all.", file=sys.stderr)
        return 2

    if a.all:
        targets = _books_with_an_arabic_source()
        if not targets:
            print("No books with an Arabic source found.", file=sys.stderr)
            return 1
    else:
        book_dir = content_dir(a.slug)
        if not book_dir or not book_dir.exists():
            print(f"Book not found: {a.slug}", file=sys.stderr)
            return 1
        targets = [book_dir]

    if not a.apply:
        print("DRY RUN — nothing is written and no model is called. Pass --apply to vowel.\n")
    for book_dir in targets:
        try:
            label = book_dir.relative_to(REPO_ROOT / "content")
        except ValueError:  # pragma: no cover
            label = book_dir
        print(f"==> {label}")
        vowel_source(book_dir, apply=a.apply, force=a.force, only=a.stream)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
