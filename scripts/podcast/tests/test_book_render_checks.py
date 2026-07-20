from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_render_checks import (
    run_all_scans,
    scan_blank_and_halfempty,
    scan_duplicate_captions,
    scan_watermark,
)


def test_watermark_flagged() -> None:
    findings = scan_watermark(["clean page", "made with NotebookLM", "also fine"])
    assert len(findings) == 1
    assert findings[0]["check"] == "BR-WATERMARK" and findings[0]["page"] == 2
    assert findings[0]["severity"] == "P0"


def test_watermark_spacing_variants() -> None:
    assert scan_watermark(["Notebook LM"])  # spaced variant caught
    assert scan_watermark(["notebooklm"])  # lowercase caught


def test_duplicate_caption_flagged() -> None:
    page = "Body text here.\nThe Seven Pillars\nThe Seven Pillars\nmore body"
    findings = scan_duplicate_captions([page])
    assert findings and findings[0]["check"] == "BR-CAPTION-DUP"


def test_no_dup_for_long_repeated_lines() -> None:
    # Two identical LONG lines are prose repetition, not a caption echo — not flagged.
    long = " ".join(["word"] * 20)
    assert scan_duplicate_captions([f"{long}\n{long}"]) == []


def test_blank_interior_page_flagged() -> None:
    pages = ["cover", "   ", "real content " * 30, "colophon"]  # page 2 blank
    findings = scan_blank_and_halfempty(pages)
    blanks = [f for f in findings if f["check"] == "BR-BLANK-PAGE"]
    assert blanks and blanks[0]["page"] == 2 and blanks[0]["severity"] == "P0"


def test_first_and_last_pages_exempt() -> None:
    # Sparse cover (p1) and colophon (last) do not trip the blank check.
    pages = ["x", "real content " * 30, "real content " * 30, "y"]
    findings = scan_blank_and_halfempty(pages)
    assert not any(f["check"] == "BR-BLANK-PAGE" for f in findings)


def test_half_empty_interior_flagged() -> None:
    # A realistically dense book (median ~960 chars): a page well above the blank
    # floor (120) but far below the interior median reads as half-empty.
    full = "content " * 120  # 960 chars
    pages = ["cover", full, full, full, "x" * 200, full, "colophon"]  # p5 half-empty
    findings = scan_blank_and_halfempty(pages)
    fills = [f for f in findings if f["check"] == "BR-PAGE-FILL"]
    assert fills and fills[0]["page"] == 5 and fills[0]["severity"] == "P1"


def test_dense_book_no_false_half_empty() -> None:
    # Uniformly full pages -> no half-empty findings.
    full = "content " * 120
    pages = ["cover", full, full, full, full, "colophon"]
    assert not any(f["check"] == "BR-PAGE-FILL" for f in scan_blank_and_halfempty(pages))


def test_run_all_scans_orders_p0_first() -> None:
    pages = ["cover", "NotebookLM " + "x" * 5, "real " * 40, "colophon"]
    findings = run_all_scans(pages)
    assert findings[0]["severity"] == "P0"


def test_placeholder_on_the_page_is_a_blocker() -> None:
    # A `.replace` hit a placeholder's own mention in a CSS comment, so every page
    # of a finished book printed `__BOOK_RUNNING_HEAD__`. Nothing in the pipeline
    # noticed; a human reading the PDF did.
    from _book_render_checks import scan_placeholders

    findings = scan_placeholders(["ordinary page", "__BOOK_RUNNING_HEAD__\nchapter text"])

    assert [f["check"] for f in findings] == ["BR-PLACEHOLDER"]
    assert findings[0]["severity"] == "P0"
    assert findings[0]["page"] == 2


def test_ordinary_prose_with_underscores_is_not_a_placeholder() -> None:
    from _book_render_checks import scan_placeholders

    assert scan_placeholders(["snake_case and __x__ and MACRO_NAME are not placeholders"]) == []


def test_a_missing_crosswalk_page_is_a_blocker_when_the_file_exists(tmp_path) -> None:
    from _book_render_checks import scan_crosswalk_present

    bd = tmp_path / "book"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "source-crosswalk.json").write_text("{}", encoding="utf-8")

    assert scan_crosswalk_present(["page one", "page two"], bd)[0]["check"] == "BR-CROSSWALK-MISSING"
    assert scan_crosswalk_present(["page one", "S O U R C E C R O S SWA L K"], bd) == []


def test_no_crosswalk_file_means_no_finding(tmp_path) -> None:
    # The companion route legitimately has none; absent is not the same as dropped.
    from _book_render_checks import scan_crosswalk_present

    bd = tmp_path / "book"
    (bd / "book").mkdir(parents=True)

    assert scan_crosswalk_present(["page one"], bd) == []
