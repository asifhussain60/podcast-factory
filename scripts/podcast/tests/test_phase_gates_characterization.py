"""Characterisation of the phase gates — the tests that pin what each one says today.

`_phase_gates` decides whether a phase "worked" and, through `_phase_review`, whether a run may advance or a book
may publish — 451 lines with no test naming it. Each case here is one gate, one input shape, one verdict; the point
is that a change to a gate's meaning shows up as a red test, not as a book that quietly ships broken. Every failing
gate is asserted to say WHAT is wrong, because the message is what a person reads at 2am.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _phase_gates as g  # noqa: E402


def w(book: Path, rel: str, text: str = "x") -> Path:
    p = book / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# ---- source and refined text ---------------------------------------------------------------------------------
def test_source_text_present_passes_with_content_and_fails_when_missing_or_empty(tmp_path):
    ok, msg = g.gate_source_text_present(tmp_path)
    assert not ok and "raw-extract.md" in msg
    w(tmp_path, "_system/source/text/raw-extract.md", "")
    assert not g.gate_source_text_present(tmp_path)[0], "an empty file is not a source"
    w(tmp_path, "_system/source/text/raw-extract.md", "some text")
    ok, msg = g.gate_source_text_present(tmp_path)
    assert ok and "present" in msg


def test_refined_text_present(tmp_path):
    assert not g.gate_refined_text_present(tmp_path)[0]
    w(tmp_path, "_system/source/text/refined-english.md", "refined")
    assert g.gate_refined_text_present(tmp_path)[0]


def test_refined_must_keep_at_least_sixty_percent_of_the_sources_words(tmp_path):
    w(tmp_path, "_system/source/text/raw-extract.md", " ".join(["word"] * 100))
    w(tmp_path, "_system/source/text/refined-english.md", " ".join(["word"] * 59))
    ok, msg = g.gate_refined_covers_source(tmp_path)
    assert not ok and "truncated" in msg
    w(tmp_path, "_system/source/text/refined-english.md", " ".join(["word"] * 60))
    assert g.gate_refined_covers_source(tmp_path)[0]


def test_refined_coverage_cannot_be_judged_when_a_side_is_missing_and_says_so(tmp_path):
    ok, msg = g.gate_refined_covers_source(tmp_path)
    assert ok and "cannot compare" in msg


# ---- design and contracts ------------------------------------------------------------------------------------
def test_chapter_contracts_exist(tmp_path):
    ok, msg = g.gate_chapter_contracts_exist(tmp_path)
    assert not ok and "0d produced nothing" in msg
    w(tmp_path, "chapter-contracts/a.yml")
    w(tmp_path, "chapter-contracts/b.yml")
    ok, msg = g.gate_chapter_contracts_exist(tmp_path)
    assert ok and "2 chapter contract" in msg


def test_a_contract_without_its_chapter_file_names_the_orphans(tmp_path):
    w(tmp_path, "chapter-contracts/alpha.yml")
    w(tmp_path, "chapter-contracts/beta.yml")
    w(tmp_path, "chapters/ch01-alpha.txt")
    ok, msg = g.gate_contracts_have_chapter_files(tmp_path)
    assert not ok and "1 of 2" in msg and "beta" in msg
    w(tmp_path, "chapters/ch02-beta.txt")
    assert g.gate_contracts_have_chapter_files(tmp_path)[0]


def test_contracts_gate_fails_when_there_are_no_contracts_at_all(tmp_path):
    ok, msg = g.gate_contracts_have_chapter_files(tmp_path)
    assert not ok and "0d produced nothing" in msg


# ---- the reading edition -------------------------------------------------------------------------------------
def test_book_toc_must_exist_parse_and_declare_chapters(tmp_path):
    assert "missing" in g.gate_book_toc_parses(tmp_path)[1]
    w(tmp_path, "book/book-toc.json", "{not json")
    ok, msg = g.gate_book_toc_parses(tmp_path)
    assert not ok and "does not parse" in msg
    w(tmp_path, "book/book-toc.json", json.dumps({"chapters": []}))
    ok, msg = g.gate_book_toc_parses(tmp_path)
    assert not ok and "no chapters" in msg
    w(tmp_path, "book/book-toc.json", json.dumps({"chapters": [{"title": "A"}, {"title": "B"}]}))
    ok, msg = g.gate_book_toc_parses(tmp_path)
    assert ok and "2 chapter" in msg


def test_book_md_present(tmp_path):
    assert not g.gate_book_md_present(tmp_path)[0]
    w(tmp_path, "book/book.md", "# Book\n")
    assert g.gate_book_md_present(tmp_path)[0]


def test_book_md_needs_a_heading_for_every_declared_chapter(tmp_path):
    w(tmp_path, "book/book-toc.json", json.dumps({"chapters": [{"title": "A"}, {"title": "B"}, {"title": "C"}]}))
    w(tmp_path, "book/book.md", "# Book\n\n## A\ntext\n\n## B\ntext\n")
    ok, msg = g.gate_book_md_covers_toc(tmp_path)
    assert not ok and "2 chapter heading" in msg and "3 declared" in msg
    w(tmp_path, "book/book.md", "# Book\n\n## A\nt\n\n## B\nt\n\n## C\nt\n")
    assert g.gate_book_md_covers_toc(tmp_path)[0]


def test_book_md_coverage_defers_to_the_presence_gates_when_a_file_is_missing(tmp_path):
    ok, msg = g.gate_book_md_covers_toc(tmp_path)
    assert ok and "cannot compare" in msg


# ---- rendered output -----------------------------------------------------------------------------------------
def test_a_rendered_pdf_must_be_more_than_a_stub(tmp_path):
    ok, msg = g.gate_rendered_pdf_present(tmp_path)
    assert not ok and "no book/" in msg
    (tmp_path / "book").mkdir()
    assert "produced nothing" in g.gate_rendered_pdf_present(tmp_path)[1]
    (tmp_path / "book" / "b.pdf").write_bytes(b"%PDF" + b"0" * 100)
    ok, msg = g.gate_rendered_pdf_present(tmp_path)
    assert not ok and "empty edition" in msg, "a valid-but-empty PDF must not read as a printed book"
    (tmp_path / "book" / "b.pdf").write_bytes(b"%PDF" + b"0" * 20_000)
    ok, msg = g.gate_rendered_pdf_present(tmp_path)
    assert ok and "b.pdf" in msg


def test_slide_decks_present(tmp_path):
    ok, msg = g.gate_slide_decks_present(tmp_path)
    assert not ok and "no slide-decks/" in msg
    (tmp_path / "slide-decks").mkdir()
    assert "empty" in g.gate_slide_decks_present(tmp_path)[1]
    w(tmp_path, "slide-decks/ch01.pdf")
    assert g.gate_slide_decks_present(tmp_path)[0]
