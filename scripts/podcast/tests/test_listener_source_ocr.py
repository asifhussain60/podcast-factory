"""The source text a chapter was made from, for the moderators' Source pane."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _listener_source_ocr as ocr  # noqa: E402


@dataclass
class _Chapter:
    anchor: str


def _book(tmp_path: Path, *, scan: str | None, text: str | None, crosswalk: dict | None) -> Path:
    if scan is not None:
        (tmp_path / "_system/source/ocr").mkdir(parents=True)
        (tmp_path / "_system/source/ocr/raw-extract.md").write_text(scan, encoding="utf-8")
    if text is not None:
        (tmp_path / "_system/source/text").mkdir(parents=True)
        (tmp_path / "_system/source/text/refined-english.md").write_text(text, encoding="utf-8")
    if crosswalk is not None:
        (tmp_path / "book").mkdir()
        (tmp_path / "book/source-crosswalk.json").write_text(json.dumps(crosswalk), encoding="utf-8")
    return tmp_path


SCAN = "<!-- page 1 -->\nبسم الله الرحمن الرحيم\nScanned with CamScanner\n\n<!-- page 2 -->\nالحمد لله رب العالمين\n\n<!-- page 3 -->\nمن كتاب إسعاف الطالب\n"
TEXT = "<!-- page 1 -->\nIn the name of God.\n\n<!-- page 2 -->\nPraise be to God.\n\n<!-- page 3 -->\nFrom the book.\n"
CROSSWALK = {
    "chapters": [
        {"title": "Faith", "source_pages": [1, 2], "arabic_source_pages": [1, 2]},
        {"title": "Purity", "source_pages": [3], "arabic_source_pages": [3]},
        {"title": "Lost", "source_pages": [99], "arabic_source_pages": [99]},
    ]
}


def test_pages_are_cut_on_the_markers_and_the_scanner_watermark_is_dropped(tmp_path):
    book = _book(tmp_path, scan=SCAN, text=TEXT, crosswalk=CROSSWALK)
    pages = ocr.read_source_pages(book)
    scan = [p for p in pages if p.kind == "scan"]
    assert [p.page for p in scan] == [1, 2, 3]
    assert "CamScanner" not in scan[0].text
    assert scan[0].text == "بسم الله الرحمن الرحيم"
    assert {p.kind for p in pages} == {"scan", "extracted"}


def test_a_book_with_no_source_files_has_no_rows_rather_than_an_error(tmp_path):
    assert ocr.read_source_pages(tmp_path) == []
    assert ocr.read_source_spans(tmp_path, [_Chapter("faith")], []) == []


def test_chapters_are_paired_to_their_pages_by_TITLE_not_by_position(tmp_path):
    book = _book(tmp_path, scan=SCAN, text=TEXT, crosswalk=CROSSWALK)
    pages = ocr.read_source_pages(book)
    # The library's chapter list carries a pipeline-written introduction the crosswalk never had.
    chapters = [_Chapter("introduction to the book"), _Chapter("faith"), _Chapter("purity")]
    spans = ocr.read_source_spans(book, chapters, pages)
    by = {(s.anchor, s.kind): (s.first_page, s.last_page) for s in spans}
    assert by[("faith", "scan")] == (1, 2)
    assert by[("purity", "extracted")] == (3, 3)
    assert not any(s.anchor == "introduction to the book" for s in spans)


def test_a_chapter_whose_pages_are_not_in_the_file_gets_no_span_never_a_guess(tmp_path):
    book = _book(tmp_path, scan=SCAN, text=TEXT, crosswalk=CROSSWALK)
    spans = ocr.read_source_spans(book, [_Chapter("lost")], ocr.read_source_pages(book))
    assert spans == []


def test_scan_quality_reads_fragment_lines_as_a_failed_recognition():
    clean = ["الحمد لله رب العالمين\nبسم الله الرحمن الرحيم"] * 5
    noisy = ["الحمد لله رب العالمين\n" * 9 + "ـ ا\n"]  # 1 of 10 lines is a fragment
    ruined = ["ـ\nا\n�\nab\nالحمد لله رب"]
    assert ocr.scan_quality(clean) == "clean"
    assert ocr.scan_quality(noisy) == "noisy"
    assert ocr.scan_quality(ruined) == "unreliable"
    assert ocr.scan_quality([]) == "clean"


def test_a_person_can_override_the_heuristic_for_a_scan_that_only_looks_clean(tmp_path):
    book = _book(tmp_path, scan=SCAN, text=TEXT, crosswalk=CROSSWALK)
    (book / "_system/source/ocr/quality.json").write_text('{"quality": "unreliable"}', encoding="utf-8")
    spans = ocr.read_source_spans(book, [_Chapter("faith")], ocr.read_source_pages(book))
    assert {s.kind: s.quality for s in spans} == {"scan": "unreliable", "extracted": "clean"}


def test_prose_version_changes_only_when_the_rendered_prose_does():
    from _listener_book import Chapter
    from publish_to_listener import prose_version

    class _Book:
        def __init__(self, *html):
            self.chapters = [
                Chapter(anchor=f"c{i}", idx=i, title="t", markdown="m", html=h) for i, h in enumerate(html)
            ]

    same_a, same_b = prose_version(_Book("<p>a</p>", "<p>b</p>")), prose_version(_Book("<p>a</p>", "<p>b</p>"))
    assert same_a == same_b and len(same_a) == 16
    # A same-LENGTH change — the case a length-based fingerprint would miss.
    assert prose_version(_Book("<p>a</p>", "<p>c</p>")) != same_a
    # Reordering is a change too.
    assert prose_version(_Book("<p>b</p>", "<p>a</p>")) != same_a
