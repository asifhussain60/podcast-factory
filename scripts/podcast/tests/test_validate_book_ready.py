"""Tests for the deterministic reading-edition gates (WS1).

These lock the contract that a truncated book.md or an empty/missing PDF is
caught deterministically (no LLM), so a broken reading edition can never record
0book-render `completed` and ship to Drive unnoticed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import validate_book_ready as V  # noqa: E402
from phases.chapter_driver import _is_bad_slide_outcome  # noqa: E402


# --- minimal one-page PDF fixture (valid enough for the page-count regex) ---
_ONE_PAGE_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type /Pages /Kids[3 0 R] /Count 1>>endobj\n"
    b"3 0 obj<</Type /Page /Parent 2 0 R>>endobj\n"
    b"%%EOF\n"
)
def _pdf_with_pages(n: int) -> bytes:
    """A size-floor-passing PDF whose /Type /Page count is exactly n."""
    body = b"%PDF-1.4\n1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj\n"
    body += b"2 0 obj<</Type /Pages /Count %d>>endobj\n" % n
    body += b"".join(b"%d 0 obj<</Type /Page>>endobj\n" % (i + 3) for i in range(n))
    return body + b"%%EOF\n" + b"%" + b"\x00" * (12 * 1024)


# Padded above the size floor (trailing bytes after %%EOF are ignored by readers;
# the /Type /Page regex still counts exactly one page).
_VALID_PDF = _pdf_with_pages(8)


def _make_book(tmp_path: Path, *, enable=True, chapters=3, md_sections=3,
               md_bytes=4096, pdf=_VALID_PDF, md_name="book.md",
               content_profile="technical") -> Path:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "meta.yml").write_text(
        f"series:\n  enable_book_branch: {str(enable).lower()}\n", encoding="utf-8")
    (bd / "_system" / "series-config.yaml").write_text(
        f"content_profile: {content_profile}\n", encoding="utf-8")
    toc = {"book_title": "T", "chapters": [{"title": f"c{i}"} for i in range(chapters)]}
    (bd / "book" / "book-toc.json").write_text(json.dumps(toc), encoding="utf-8")
    body = "# Title\n" + "".join(f"## Section {i}\nbody\n" for i in range(md_sections))
    body += "x" * max(0, md_bytes - len(body))
    (bd / "book" / md_name).write_text(body, encoding="utf-8")
    if pdf is not None:
        (bd / "book" / "book.pdf").write_bytes(pdf)
    return bd


def _add_islamic_arabic_fixture(bd: Path) -> None:
    (bd / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_scholarly\n", encoding="utf-8")
    (bd / "_system" / "glossary.yml").write_text(
        "schema_version: 2\n"
        "entries:\n"
        "  - phonetic: \"tawhid\"\n"
        "    transliteration: \"tawhid\"\n"
        "    arabic_script: \"توحيد\"\n"
        "    audio_phonetic: \"taw-heed\"\n"
        "    first_seen_snippet: \"x\"\n",
        encoding="utf-8",
    )
    ch = bd / "chapters"
    ch.mkdir(exist_ok=True)
    for i in range(1, 4):
        (ch / f"ch{i:02d}.txt").write_text(f"Chapter with tawhid (توحيد) {i}.", encoding="utf-8")


def test_na_when_book_branch_disabled(tmp_path):
    bd = _make_book(tmp_path, enable=False)
    assert V.validate_book(bd)["verdict"] == "N/A"


def test_sound_when_complete(tmp_path):
    bd = _make_book(tmp_path, chapters=3, md_sections=3)
    res = V.validate_book(bd)
    assert res["verdict"] == "BOOK-SOUND", res["summary"]


def test_b1_fails_on_truncated_md(tmp_path):
    bd = _make_book(tmp_path, chapters=5, md_sections=2)  # fewer sections than TOC
    res = V.validate_book(bd)
    assert res["verdict"] == "BOOK-BROKEN"
    assert "B1" in res["summary"] and "truncated" in res["summary"].lower()


def test_b1_fails_on_near_empty_md(tmp_path):
    bd = _make_book(tmp_path, chapters=1, md_sections=1, md_bytes=10)
    res = V.validate_book(bd)
    assert res["verdict"] == "BOOK-BROKEN"
    assert "B1" in res["summary"]


def test_b2_fails_on_missing_pdf(tmp_path):
    bd = _make_book(tmp_path, pdf=None)
    res = V.validate_book(bd)
    assert res["verdict"] == "BOOK-BROKEN"
    assert "B2" in res["summary"] and "missing" in res["summary"].lower()


def test_b2_fails_on_tiny_pdf(tmp_path):
    bd = _make_book(tmp_path, pdf=b"%PDF-1.4 tiny")
    res = V.validate_book(bd)
    assert res["verdict"] == "BOOK-BROKEN"
    assert "B2" in res["summary"]


def test_b2_fails_when_pages_below_chapter_count(tmp_path):
    # 1-page PDF but 5 chapters -> truncated render
    bd = _make_book(tmp_path, chapters=5, md_sections=5,
                    pdf=_ONE_PAGE_PDF + b"x" * (V._MIN_PDF_BYTES))
    res = V.validate_book(bd)
    assert res["verdict"] == "BOOK-BROKEN"
    assert "truncated" in res["summary"].lower()


def test_picks_render_input_priority(tmp_path):
    # book-illustrated.md should be validated over book.md when present
    bd = _make_book(tmp_path, chapters=2, md_sections=2)
    (bd / "book" / "book-illustrated.md").write_text(
        "# T\n## a\n## b\n" + "y" * 4096, encoding="utf-8")
    ok, note = V.gate_b1_book_md_complete(bd)
    assert ok and "book-illustrated.md" in note


def test_pdf_page_count_extraction():
    assert V._pdf_page_count(_ONE_PAGE_PDF) == 1
    # /Type /Pages container must NOT be counted as a page
    assert V._pdf_page_count(b"/Type /Pages /Count 9") == 0


def test_b3_fails_islamic_book_without_chapter_arabic(tmp_path):
    bd = _make_book(tmp_path, content_profile="islamic_scholarly")
    (bd / "_system" / "glossary.yml").write_text(
        "schema_version: 2\nentries:\n"
        "  - phonetic: \"tawhid\"\n"
        "    transliteration: \"tawhid\"\n"
        "    arabic_script: \"توحيد\"\n"
        "    audio_phonetic: \"taw-heed\"\n"
        "    first_seen_snippet: \"x\"\n",
        encoding="utf-8",
    )
    ch = bd / "chapters"
    ch.mkdir()
    (ch / "ch01.txt").write_text("Chapter with tawhid but no script.", encoding="utf-8")

    res = V.validate_book(bd)

    assert res["verdict"] == "BOOK-BROKEN"
    assert "B3" in res["summary"]


def test_b3_passes_islamic_book_with_chapter_arabic(tmp_path):
    bd = _make_book(tmp_path, content_profile="islamic_scholarly")
    _add_islamic_arabic_fixture(bd)

    res = V.validate_book(bd)

    assert res["verdict"] == "BOOK-SOUND", res["summary"]


@pytest.mark.parametrize("verdict,bad", [
    ("BLOCKED", True), ("ERROR", True), ("STALLED", True),
    ("FAILED: x", True), ("FAILED", True),
    ("SHIP-READY", False), ("SHIP-WITH-CAUTION", False),
    ("SKIPPED", False), ("AUTHORED", False),
])
def test_is_bad_slide_outcome(verdict, bad):
    assert _is_bad_slide_outcome(verdict) is bad
