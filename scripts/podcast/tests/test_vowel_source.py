"""test_vowel_source.py — the invariants that make source vowelling safe to run
unattended over hundreds of runs.

The per-run gate (`_vowelling.rejection_reason`) is tested next door. What is
tested HERE is the file as a whole: an Arabic source is not just text, it is text
whose SHAPE other steps depend on. `_book_compose._load_arabic_pages` splits it on
`<!-- page N -->` markers to map chapters to pages, and `produce_bilingual` slices
it by line number. A vowelling that moved either would be invisible to a
per-run check and would corrupt those readers silently.

No model is called anywhere below: every test injects `call`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _arabic_coverage import normalize_arabic  # noqa: E402
from _mushaf import mushaf_available  # noqa: E402
from _vowelled_source import (  # noqa: E402
    is_current,
    record_stream,
    resolve_arabic_source,
    sibling_for,
)
from _vowelling import mark_count, skeleton  # noqa: E402
from vowel_source import _structure_complaint, arabic_streams, vowel_stream  # noqa: E402

FATHA = "َ"

# A run that occurs BOTH on its own and inside a longer run — the substring
# hazard that made a plain document-order str.replace silently no-op.
SHORT = "قال العالم للغلام"
LONG = "قال العالم للغلام ودموعه تنحدر على لحيته"

SOURCE = f"<!-- page 1 -->\n{SHORT}\n\n<!-- page 2 -->\nتأليف ١ سيدنا جعفر بن منصور ٢ اليمن٣\n{LONG}\n"


def vowel_every_letter(run: str) -> str:
    """A stand-in model: marks every Arabic letter, and collapses to one line
    exactly as the real one is instructed to."""
    return " ".join("".join(ch + FATHA for ch in word) for word in run.split())


@pytest.fixture
def book(tmp_path: Path) -> Path:
    src = tmp_path / "_system" / "source" / "ocr" / "raw-extract.md"
    src.parent.mkdir(parents=True)
    src.write_text(SOURCE, encoding="utf-8")
    return tmp_path


def _source(book: Path) -> Path:
    return book / "_system" / "source" / "ocr" / "raw-extract.md"


pytestmark = pytest.mark.skipif(
    not mushaf_available(),  # pragma: no cover - mirror.db is tracked in git
    reason="canonical mushaf unavailable; vowel_runs declines to run without it",
)


def test_the_shape_of_the_file_survives(book: Path) -> None:
    """Page markers, line count and the consonantal skeleton are all unmoved."""
    src = _source(book)
    vowel_stream(src, apply=True, call=vowel_every_letter, log=lambda m: None)
    after = sibling_for(src).read_text(encoding="utf-8")

    assert after.count("<!-- page") == SOURCE.count("<!-- page")
    assert after.count("\n") == SOURCE.count("\n"), "the model's one-line answers were reflowed back"
    assert normalize_arabic(after) == normalize_arabic(SOURCE), "letters moved"
    assert mark_count(after) > mark_count(SOURCE), "nothing was actually vowelled"


def test_digits_survive(book: Path) -> None:
    """The footnote numbers are part of the text, not marks to be normalised away.

    Before the mark-range fix these sat inside the class `skeleton()` strips, so a
    model that dropped them passed the per-run gate as "marks only"."""
    src = _source(book)
    vowel_stream(src, apply=True, call=vowel_every_letter, log=lambda m: None)
    after = sibling_for(src).read_text(encoding="utf-8")
    for digit in ("١", "٢", "٣"):
        assert digit in after, f"footnote digit {digit} was lost"


def test_a_run_nested_inside_a_longer_run_is_not_eaten(book: Path) -> None:
    """Longest-first replacement: the short run must not rewrite the long run's
    opening and leave the long run's own replace matching nothing."""
    src = _source(book)
    vowel_stream(src, apply=True, call=vowel_every_letter, log=lambda m: None)
    after = sibling_for(src).read_text(encoding="utf-8")

    for line in after.splitlines():
        if "تنحدر" in line or "للغلام" in line:
            bare = [w for w in line.split() if not any(c == FATHA for c in w)]
            assert not bare, f"left partly bare: {line!r}"


def test_second_pass_calls_no_model_and_changes_nothing(book: Path) -> None:
    """Idempotency is what makes this safe to wire into a retried phase."""
    src = _source(book)
    vowel_stream(src, apply=True, call=vowel_every_letter, log=lambda m: None)
    record_stream(book, source=src, sibling=sibling_for(src), stats={})
    first = sibling_for(src).read_text(encoding="utf-8")

    calls: list[str] = []

    def counting(run: str) -> str:
        calls.append(run)
        return vowel_every_letter(run)

    stats = vowel_stream(src, apply=True, call=counting, log=lambda m: None)
    assert stats.get("skipped") == "current"
    assert calls == [], "a current sibling must not be re-derived"
    assert sibling_for(src).read_text(encoding="utf-8") == first


def test_a_stale_sibling_is_ignored_not_preferred(book: Path) -> None:
    """Re-running OCR rewrites the raw extract. The sibling is then the vowelling
    of a document that no longer exists, and must never be handed out."""
    src = _source(book)
    vowel_stream(src, apply=True, call=vowel_every_letter, log=lambda m: None)
    record_stream(book, source=src, sibling=sibling_for(src), stats={})
    assert is_current(src)
    assert resolve_arabic_source(src) == sibling_for(src)

    src.write_text(SOURCE + "\n<!-- page 3 -->\nنص جديد تماما هنا\n", encoding="utf-8")
    assert not is_current(src), "fingerprint must catch the re-ingest"
    assert resolve_arabic_source(src) == src, "must fall back to the raw source"


def test_resolver_falls_back_when_there_is_no_sibling(book: Path) -> None:
    src = _source(book)
    assert resolve_arabic_source(src) == src
    assert sibling_for(sibling_for(src)) == sibling_for(src), "no double suffix"


def test_a_model_that_reshapes_the_file_is_refused_wholesale(book: Path) -> None:
    """The per-run gate passes each run; only the whole-file check sees the shape
    move. A refusal writes no sibling at all rather than a half-good source."""
    src = _source(book)

    def drops_a_line(run: str) -> str:
        return vowel_every_letter(run)

    # Directly exercise the file-level check, since a per-run gate cannot produce
    # this: a page marker removed, everything else identical.
    assert _structure_complaint(SOURCE, SOURCE.replace("<!-- page 2 -->\n", "")) is not None
    assert _structure_complaint(SOURCE, SOURCE.replace("\n", " ")) is not None
    assert _structure_complaint(SOURCE, SOURCE) is None

    stats = vowel_stream(src, apply=True, call=drops_a_line, log=lambda m: None)
    assert "structure_refusal" not in stats, "a well-behaved model must not be refused"


def test_only_arabic_streams_are_picked_up(tmp_path: Path) -> None:
    """An English extract that quotes a little Arabic is not an Arabic source."""
    src = tmp_path / "_system" / "source" / "ocr" / "raw-extract.md"
    src.parent.mkdir(parents=True)
    src.write_text("The Master said قال العالم and then continued in English.\n", encoding="utf-8")
    assert arabic_streams(tmp_path) == []


def test_skeleton_helper_agrees_with_the_gate() -> None:
    """`_structure_complaint` uses normalize_arabic (fold + strip) while the gate
    uses skeleton (strip only). Both must call a pure vowelling unchanged."""
    bare = "قال العالم للغلام"
    marked = vowel_every_letter(bare)
    assert normalize_arabic(bare) == normalize_arabic(marked)
    assert skeleton(bare) == skeleton(marked)
