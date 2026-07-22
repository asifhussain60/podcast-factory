"""Which files the spelling sweep is allowed to touch.

This is the rule that actually failed. The first run of `normalize_spelling.py`
matched on "is there a `/chapters/` in the path?" and swept 78 transcribed
LECTURES under `augmentation/*/chapters/` — a real person's recorded speech,
used as grounding input, not prose the pipeline wrote. Caught before commit on
2026-07-21. Respelling evidence would break the same verbatim guarantee that the
OCR and source-library exclusions exist to protect, so the boundary is pinned
here rather than left to a reviewer noticing a large diff.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from normalize_spelling import eligible, in_scope  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
C = REPO / "content"


def test_the_reading_edition_is_in_scope() -> None:
    assert in_scope(C / "Islamic" / "some-book" / "book" / "book.md") is True


def test_notebooklm_chapters_and_episodes_are_in_scope() -> None:
    assert in_scope(C / "Islamic" / "b" / "chapters" / "ch01-x.txt") is True
    assert in_scope(C / "Islamic" / "b" / "episodes" / "EP01-x.txt") is True
    assert in_scope(C / "Islamic" / "b" / "slide-decks" / "deck.txt") is True


def test_transcribed_lectures_are_never_in_scope() -> None:
    """The live regression: these live under a `chapters/` directory and would
    otherwise pass the chapter test."""
    p = C / "Islamic" / "b" / "augmentation" / "hazrat-zia" / "chapters" / "lec01.txt"
    assert eligible(p) is False


def test_ocr_and_source_records_are_never_in_scope() -> None:
    assert in_scope(C / "Islamic" / "b" / "_system" / "source" / "ocr" / "raw-extract.md") is False
    assert in_scope(C / "Islamic" / "b" / "_system" / "source" / "text" / "refined-english.md") is False


def test_third_party_research_is_never_in_scope() -> None:
    assert in_scope(C / "Islamic" / "b" / "research" / "sources" / "thesis.txt") is False


def test_shared_source_library_is_never_in_scope() -> None:
    p = C / "_shared" / "source-library" / "extracted" / "w" / "x" / "chapters" / "a.md"
    assert eligible(p) is False


def test_compose_caches_and_archives_are_never_in_scope() -> None:
    assert in_scope(C / "Islamic" / "b" / "book" / "_chunks" / "translation" / "bk-01.md") is False
    assert in_scope(C / "Islamic" / "b" / "chapters" / "_curator-archive" / "old.txt") is False


def test_non_prose_extensions_are_never_in_scope() -> None:
    assert in_scope(C / "Islamic" / "b" / "book" / "book-toc.json") is False
    assert in_scope(C / "Islamic" / "b" / "book" / "visuals" / "slide-1.svg") is False


def test_the_live_tree_has_no_transcript_in_scope() -> None:
    """Belt and braces against the real repo, not just synthetic paths."""
    if not C.exists():  # tests must pass on a content-less checkout
        return
    caught = [p for p in C.rglob("*") if p.is_file() and "augmentation" in p.parts and eligible(p)]
    assert caught == [], f"transcripts in scope: {caught[:3]}"
