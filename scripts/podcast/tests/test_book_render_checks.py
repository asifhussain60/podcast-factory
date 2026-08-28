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


def test_no_dup_for_bidi_arabic_fragment() -> None:
    # kitab-al-riyad pp.186/214/215/258: pdftotext linearizes a wrapped Qur'anic
    # verse into two adjacent "lines" that are each a single reordered
    # letter+diacritic wrapped in RTL embedding marks — not a duplicated
    # caption, a bidi extraction artifact of one line of scripture.
    frag = "‫ِإ‬"  # RLE + kasra + hamza-alif + PDF
    page = f"body\n{frag}\n{frag}\nmore body"
    assert scan_duplicate_captions([page]) == []


def test_dup_still_flagged_for_short_arabic_caption() -> None:
    # A genuine short Arabic caption/title duplicated verbatim must still fire.
    page = "body\nكتاب الرياض\nكتاب الرياض\nmore body"
    findings = scan_duplicate_captions([page])
    assert findings and findings[0]["check"] == "BR-CAPTION-DUP"


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


def test_running_head_must_name_the_chapter_that_owns_the_page() -> None:
    # The first implementation keyed its @page rules by array position over a
    # chapters list that leads with the preface, so every rule shifted by one and
    # pages deep in chapter 8 carried chapter 7's title. No other gate reads
    # margin-box text against chapter boundaries.
    from _book_render_checks import scan_running_heads

    pages = [
        "CHAPTER ONE\nThe Persian\nbody",
        "1. The Persian\nmore body",
        "CHAPTER TWO\nA Stranger\nbody",
        "1. The Persian\nstill chapter two's pages",
    ]

    findings = scan_running_heads(pages)

    assert [f["page"] for f in findings] == [4]
    assert "names chapter 1" in findings[0]["detail"]
    assert "belongs to chapter 2" in findings[0]["detail"]


def test_correct_running_heads_produce_nothing() -> None:
    from _book_render_checks import scan_running_heads

    pages = ["CHAPTER ONE\nThe Persian", "1. The Persian\nbody", "CHAPTER TWO\nA Stranger", "2. A Stranger\nbody"]

    assert scan_running_heads(pages) == []


def test_a_book_with_no_numbered_heads_is_not_this_probes_business() -> None:
    from _book_render_checks import scan_running_heads

    assert scan_running_heads(["CHAPTER ONE\nThe Persian", "The Master and the Disciple\nbody"]) == []


def test_a_chapter_past_twenty_is_recognised_as_a_chapter_open() -> None:
    # `_NUMBER_WORDS` stopped at TWENTY, so a book with more than twenty
    # chapters had every later chapter invisible to the owner scan: the cursor
    # froze at 20 and every page from chapter 21 onward was reported as a
    # mismatch. Kunooz al-Hikmah has 28 chapters and drew 78 such findings on a
    # correctly rendered 246-page book, which is what a P1 that cannot be true
    # costs — it blocked the render gate on the one book big enough to reach it.
    from _book_render_checks import _chapter_open_number

    assert _chapter_open_number("CHAPTER TWENTY-ONE") == 21
    assert _chapter_open_number("CHAPTER TWENTY-EIGHT") == 28
    assert _chapter_open_number("CHAPTER THIRTY") == 30
    assert _chapter_open_number("CHAPTER FORTY-TWO") == 42


def test_a_letter_spaced_hyphenated_eyebrow_is_read() -> None:
    # The exact string `pdftotext` extracts from Kunooz page 169. The compact
    # form keeps the hyphen, which `^CHAPTER([A-Z]+)$` rejected outright.
    from _book_render_checks import _chapter_open_number

    assert _chapter_open_number("C H A P T E R T W E N T Y- O N E") == 21
    assert _chapter_open_number("C H A P T E R T W E N T Y-T H R E E") == 23


def test_a_correct_book_of_more_than_twenty_chapters_is_silent() -> None:
    from _book_render_checks import scan_running_heads

    pages = [
        "CHAPTER TWENTY\nThe Cold Edges",
        "20. The Cold Edges\nbody",
        "C H A P T E R T W E N T Y- O N E\nRubies, Elephants, and Believers",
        "21. Rubies, Elephants, and Believers\nbody",
        "CHAPTER TWENTY-EIGHT\nThe Last Question",
        "28. The Last Question\nbody",
    ]

    assert scan_running_heads(pages) == []


def test_a_real_mismatch_past_twenty_is_still_caught() -> None:
    # The fix must not buy silence by making the scan blind past twenty.
    from _book_render_checks import scan_running_heads

    pages = [
        "CHAPTER TWENTY-ONE\nRubies",
        "20. The Cold Edges\nbody",
    ]

    findings = scan_running_heads(pages)

    assert [f["page"] for f in findings] == [2]
    assert "names chapter 20" in findings[0]["detail"]
    assert "belongs to chapter 21" in findings[0]["detail"]
