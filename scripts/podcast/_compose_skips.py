"""_compose_skips.py — the record of what a compose skipped, and how to judge it.

`compose_book_v2` wraps nineteen post-compose steps in a non-fatal try, so any one
of them can throw and the phase still records `completed`. That is the right call
for the podcast — a finished translation is worth more than an overlay, and a
broken apparatus must never cost a book its ship — but it means the state file
cannot answer "is this the book we asked for".

`_system/compose-skips.json` is that answer. This module owns all three halves of
it, which used to live in three different files:

  the WRITER          `record_skip`, called from every step in `_book_pipeline_v2`
  the CLASSIFICATION  which steps change the printed page and which only report
  the READER          `verdict`, which gate B8 in `validate_book_ready` reports

They belong together because they are one contract: a step added to compose must
be classified, or the reader cannot judge it. Split out of `_book_pipeline_v2` and
`validate_book_ready` on 2026-08-02 when the latter crossed the DR-005 line cap.

Until B8 existed the file had ZERO readers, while the comment above the writer
claimed "the ship gate and a human can both read" it. A book could reach
BOOK-SOUND having silently discarded the human's Composer edits, the Arabic
overlay, the vowelling and the whole introduction.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "book.compose-skips/v1"
RECORD_NAME = "compose-skips.json"

#: Steps whose absence CHANGES THE PRINTED PAGE. A skip here means the book on
#: disk is not the book the pipeline was asked to build — a chapter the human
#: authored in the Composer silently discarded, Arabic left romanized, tashkeel
#: missing from a page printed for a reader who cannot read unvowelled Arabic,
#: the introduction absent entirely. Gate B8 FAILS on these.
PAGE_ALTERING_STEPS = frozenset(
    {
        "composer-edits",  # the human's own edits — the worst thing to drop
        "translit",
        "quran-arabic",
        "citation-names",
        "glossary-harvest",  # without it the overlay has nothing to annotate WITH
        "annotation-policy",  # decides what the overlay may annotate
        "glossary-vowelling",  # must precede the overlay or it double-annotates
        "inline-arabic",  # the Arabic-script overlay itself
        "vowelling",
        "spelling",
        "front-matter",  # a whole missing section
        "opening-fold",  # the edition would begin on front matter instead of the book
        "bridges",  # human-authored orientation
        "honorifics",
        "arabic-alignment",
        "paragraph-mirror",
    }
)

#: Steps that only WRITE A REPORT or persist a side artifact. Losing one costs
#: visibility, never a page, so B8 reports them and does not block the ship.
ADVISORY_STEPS = frozenset(
    {
        "report-reconcile",
        "etymology",  # persists atoms under _system/, never into book.md
        "arabic-audit",
        "duplication",
        "visual-policy",
    }
)


def record_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / RECORD_NAME


def record_skip(book_dir: Path, step: str, exc: BaseException, log) -> None:
    """Log a non-fatal step failure AND persist it, so it cannot scroll away."""
    log(f"    {step}: skipped (non-fatal): {exc}")
    try:
        path = record_path(book_dir)
        existing: list[dict] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8")).get("skips", [])
            except Exception:
                existing = []
        existing.append({"step": step, "error": f"{type(exc).__name__}: {exc}"})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schema": SCHEMA, "skips": existing}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:  # a recorder must never become the failure it records
        pass


def verdict(book_dir: Path) -> tuple[bool, str]:
    """(ok, note) for gate B8 — did this compose run all its page-altering steps?

    An UNKNOWN step counts as page-altering. A step added without being classified
    is exactly the case this exists to catch, and guessing "advisory" would let it
    through in silence — the original failure mode all over again.
    """
    path = record_path(book_dir)
    if not path.exists():
        return True, "compose recorded no skipped steps"
    try:
        skips = json.loads(path.read_text(encoding="utf-8")).get("skips", [])
    except Exception as exc:  # noqa: BLE001 - an unreadable record is not a broken book
        return True, f"{RECORD_NAME} unreadable ({exc})"
    if not skips:
        return True, "compose recorded no skipped steps"

    blocking = [s for s in skips if str(s.get("step")) not in ADVISORY_STEPS]
    advisory = [s for s in skips if str(s.get("step")) in ADVISORY_STEPS]

    def _names(rows: list[dict]) -> str:
        return ", ".join(dict.fromkeys(str(r.get("step")) for r in rows))

    if blocking:
        unclassified = [str(s.get("step")) for s in blocking if str(s.get("step")) not in PAGE_ALTERING_STEPS]
        note = f"{len(blocking)} page-altering step(s) skipped during compose: {_names(blocking)}"
        if unclassified:
            note += f" (unclassified, treated as page-altering: {', '.join(dict.fromkeys(unclassified))})"
        return False, f"{note} — first error: {blocking[0].get('error')}"

    return True, f"{len(advisory)} advisory step(s) skipped, page unaffected: {_names(advisory)}"
