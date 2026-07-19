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

import validate_book_ready as V
from phases.chapter_driver import _is_bad_slide_outcome

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


def _make_book(
    tmp_path: Path,
    *,
    enable=True,
    chapters=3,
    md_sections=3,
    md_bytes=4096,
    pdf=_VALID_PDF,
    md_name="book.md",
    content_profile="technical",
) -> Path:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "meta.yml").write_text(f"series:\n  enable_book_branch: {str(enable).lower()}\n", encoding="utf-8")
    (bd / "_system" / "series-config.yaml").write_text(f"content_profile: {content_profile}\n", encoding="utf-8")
    toc = {"book_title": "T", "chapters": [{"title": f"c{i}"} for i in range(chapters)]}
    (bd / "book" / "book-toc.json").write_text(json.dumps(toc), encoding="utf-8")
    body = "# Title\n" + "".join(f"## Section {i}\nbody\n" for i in range(md_sections))
    body += "x" * max(0, md_bytes - len(body))
    (bd / "book" / md_name).write_text(body, encoding="utf-8")
    if pdf is not None:
        (bd / "book" / "book.pdf").write_bytes(pdf)
    return bd


def _add_islamic_arabic_fixture(bd: Path) -> None:
    (bd / "_system" / "series-config.yaml").write_text("content_profile: islamic_scholarly\n", encoding="utf-8")
    (bd / "_system" / "glossary.yml").write_text(
        "schema_version: 2\n"
        "entries:\n"
        '  - phonetic: "tawhid"\n'
        '    transliteration: "tawhid"\n'
        '    arabic_script: "توحيد"\n'
        '    audio_phonetic: "taw-heed"\n'
        '    first_seen_snippet: "x"\n',
        encoding="utf-8",
    )
    ch = bd / "chapters"
    ch.mkdir(exist_ok=True)
    for i in range(1, 4):
        (ch / f"ch{i:02d}.txt").write_text(f"Chapter with tawhid (توحيد) {i}.", encoding="utf-8")


def _add_translation_crosswalk_fixture(bd: Path, *, chapters: int = 3) -> None:
    src = bd / "_system" / "source" / "text"
    src.mkdir(parents=True, exist_ok=True)
    lines = []
    entries = []
    for i in range(1, chapters + 1):
        start = len(lines) + 1
        lines.append(f"<!-- page {i} -->")
        lines.append(f"Marriage and household teaching source line {i}.")
        lines.append("More aligned source text.")
        end = len(lines)
        entries.append(
            {
                "index": i,
                "title": f"Marriage and the Household {i}",
                "source_line_ranges": [[start, end]],
                "source_pages": [i],
                "source_page_range": f"pp. {i}-{i}",
                "arabic_source_pages": [i],
                "arabic_source_page_range": f"pp. {i}-{i}",
                "source_headings": ["Marriage and household teaching"],
                "source_excerpt": f"Marriage and household teaching source line {i}.",
                "drift_findings": [],
            }
        )
    (src / "refined-english.md").write_text("\n".join(lines), encoding="utf-8")
    (bd / "book" / "source-crosswalk.json").write_text(
        json.dumps(
            {
                "schema": "podcast.translation-edition.source-crosswalk/v1",
                "book": bd.name,
                "chapters": entries,
            }
        ),
        encoding="utf-8",
    )


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


def test_b2_finds_the_titled_pdf_when_book_pdf_is_gone(tmp_path):
    """The collapsed-to-one-file contract: book/book.pdf no longer exists once
    build_book_pdf renames it, and B2 must resolve through the same shared
    picker (deliver_book._find_pdf) rather than a hardcoded book.pdf path."""
    bd = _make_book(tmp_path, chapters=3, md_sections=3, pdf=None)
    (bd / "book" / "T.pdf").write_bytes(_VALID_PDF)  # fixture's book-toc.json titles it "T"

    res = V.validate_book(bd)

    assert res["verdict"] != "BOOK-BROKEN", res["summary"]


def test_b2_fails_on_tiny_pdf(tmp_path):
    bd = _make_book(tmp_path, pdf=b"%PDF-1.4 tiny")
    res = V.validate_book(bd)
    assert res["verdict"] == "BOOK-BROKEN"
    assert "B2" in res["summary"]


def test_b2_fails_when_pages_below_chapter_count(tmp_path):
    # 1-page PDF but 5 chapters -> truncated render
    bd = _make_book(tmp_path, chapters=5, md_sections=5, pdf=_ONE_PAGE_PDF + b"x" * (V._MIN_PDF_BYTES))
    res = V.validate_book(bd)
    assert res["verdict"] == "BOOK-BROKEN"
    assert "truncated" in res["summary"].lower()


def test_b2_fails_on_blank_pdf_page(tmp_path, monkeypatch):
    bd = _make_book(tmp_path, chapters=3, md_sections=3)
    monkeypatch.setattr(V, "_pdf_text_blank_pages", lambda _pdf, _pages: [3])

    res = V.validate_book(bd)

    assert res["verdict"] == "BOOK-BROKEN"
    assert "blank page" in res["summary"].lower()


def test_picks_render_input_is_book_md(tmp_path):
    # Visuals are decoupled — the render input (and gate target) is always book.md,
    # even when legacy *-illustrated markdown happens to be present.
    bd = _make_book(tmp_path, chapters=2, md_sections=2)
    (bd / "book" / "book-illustrated.md").write_text("# T\n## a\n## b\n" + "y" * 4096, encoding="utf-8")
    ok, note = V.gate_b1_book_md_complete(bd)
    assert ok and "book.md" in note


def test_pdf_page_count_extraction():
    assert V._pdf_page_count(_ONE_PAGE_PDF) == 1
    # /Type /Pages container must NOT be counted as a page
    assert V._pdf_page_count(b"/Type /Pages /Count 9") == 0


def test_b3_fails_islamic_book_without_chapter_arabic(tmp_path):
    bd = _make_book(tmp_path, content_profile="islamic_scholarly")
    (bd / "_system" / "glossary.yml").write_text(
        "schema_version: 2\nentries:\n"
        '  - phonetic: "tawhid"\n'
        '    transliteration: "tawhid"\n'
        '    arabic_script: "توحيد"\n'
        '    audio_phonetic: "taw-heed"\n'
        '    first_seen_snippet: "x"\n',
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


def test_translation_edition_enabled_without_legacy_book_flag(tmp_path):
    bd = _make_book(tmp_path, enable=False, content_profile="islamic_scholarly")
    (bd / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_scholarly\n"
        "deliverable_mode: translation_edition\n"
        "visual_style: black_white\n"
        "translation_policy:\n"
        "  augmentation: forbidden\n"
        "  preserve_arabic_terms: true\n"
        "  monochrome_visuals: true\n",
        encoding="utf-8",
    )
    (bd / "book" / "book-toc.json").write_text(
        json.dumps(
            {
                "book_title": "T",
                "chapters": [{"title": f"Marriage and the Household {i}"} for i in range(1, 4)],
            }
        ),
        encoding="utf-8",
    )
    (bd / "book" / "book.md").write_text(
        "# Title\n"
        + "".join(f"## {i}. Marriage and the Household {i}\nBody text " + ("x " * 220) + "\n" for i in range(1, 4)),
        encoding="utf-8",
    )
    _add_translation_crosswalk_fixture(bd)

    res = V.validate_book(bd)

    assert res["verdict"] == "BOOK-SOUND", res["summary"]


def test_translation_edition_fails_when_arabic_source_dropped(tmp_path):
    bd = _make_book(tmp_path, content_profile="islamic_scholarly")
    (bd / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_scholarly\n"
        "deliverable_mode: translation_edition\n"
        "visual_style: black_white\n"
        "translation_policy:\n"
        "  augmentation: forbidden\n"
        "  preserve_arabic_terms: true\n"
        "  monochrome_visuals: true\n",
        encoding="utf-8",
    )
    ocr = bd / "_system" / "source" / "ocr"
    ocr.mkdir(parents=True)
    (ocr / "raw-extract.md").write_text(
        "<!-- page 1 -->\n" + ("قال رسول الله صلى الله عليه وسلم. " * 60),
        encoding="utf-8",
    )

    res = V.validate_book(bd)

    assert res["verdict"] == "BOOK-BROKEN"
    assert "rendered book has none" in res["summary"]


def test_translation_edition_passes_with_arabic_source_signal(tmp_path):
    bd = _make_book(tmp_path, content_profile="islamic_scholarly")
    (bd / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_scholarly\n"
        "deliverable_mode: translation_edition\n"
        "visual_style: black_white\n"
        "translation_policy:\n"
        "  augmentation: forbidden\n"
        "  preserve_arabic_terms: true\n"
        "  monochrome_visuals: true\n",
        encoding="utf-8",
    )
    ocr = bd / "_system" / "source" / "ocr"
    ocr.mkdir(parents=True)
    (ocr / "raw-extract.md").write_text(
        "<!-- page 1 -->\n" + ("قال رسول الله صلى الله عليه وسلم. " * 60),
        encoding="utf-8",
    )
    (bd / "book" / "book.md").write_text(
        "# Title\n"
        + "".join(
            f"## {i}. Marriage and the Household {i}\nقال رسول الله صلى الله عليه وسلم.\n" + ("x " * 220) + "\n"
            for i in range(1, 4)
        )
        + "x" * 4096,
        encoding="utf-8",
    )
    (bd / "book" / "book-toc.json").write_text(
        json.dumps(
            {
                "book_title": "T",
                "chapters": [{"title": f"Marriage and the Household {i}"} for i in range(1, 4)],
            }
        ),
        encoding="utf-8",
    )
    _add_translation_crosswalk_fixture(bd)

    res = V.validate_book(bd)

    assert res["verdict"] == "BOOK-SOUND", res["summary"]


def test_translation_edition_fails_on_model_commentary(tmp_path):
    bd = _make_book(tmp_path, chapters=1, md_sections=1, content_profile="islamic_scholarly")
    (bd / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_scholarly\n"
        "deliverable_mode: translation_edition\n"
        "visual_style: black_white\n"
        "translation_policy:\n"
        "  augmentation: forbidden\n"
        "  preserve_arabic_terms: true\n"
        "  monochrome_visuals: true\n",
        encoding="utf-8",
    )
    ocr = bd / "_system" / "source" / "ocr"
    ocr.mkdir(parents=True)
    (ocr / "raw-extract.md").write_text(
        "<!-- page 1 -->\n" + ("قال رسول الله صلى الله عليه وسلم. " * 60),
        encoding="utf-8",
    )
    (bd / "book" / "book.md").write_text(
        "# Title\n"
        "## 1. What We Wear\n"
        'Since you didn\'t pick an option, I cannot produce "What We Wear" '
        "from a source passage about hunting.\n"
        "قال رسول الله صلى الله عليه وسلم.\n" + "x" * 4096,
        encoding="utf-8",
    )

    res = V.validate_book(bd)

    assert res["verdict"] == "BOOK-BROKEN"
    assert "B4" in res["summary"]


def test_translation_edition_fails_on_heading_only_chapter(tmp_path):
    bd = _make_book(tmp_path, chapters=1, md_sections=1, content_profile="islamic_scholarly")
    (bd / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_scholarly\n"
        "deliverable_mode: translation_edition\n"
        "visual_style: black_white\n"
        "translation_policy:\n"
        "  augmentation: forbidden\n"
        "  preserve_arabic_terms: true\n"
        "  monochrome_visuals: true\n",
        encoding="utf-8",
    )
    (bd / "book" / "book-toc.json").write_text(
        json.dumps({"book_title": "T", "chapters": [{"title": "Marriage and the Household 1"}]}),
        encoding="utf-8",
    )
    (bd / "book" / "book.md").write_text(
        "# Title\n## 1. Marriage and the Household 1\n### Subhead\n" + "<!-- filler -->\n" * 120,
        encoding="utf-8",
    )
    _add_translation_crosswalk_fixture(bd, chapters=1)

    res = V.validate_book(bd)

    assert res["verdict"] == "BOOK-BROKEN"
    assert "B5" in res["summary"]


def test_translation_edition_fails_on_source_title_drift(tmp_path):
    bd = _make_book(tmp_path, chapters=1, md_sections=1, content_profile="islamic_scholarly")
    (bd / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_scholarly\n"
        "deliverable_mode: translation_edition\n"
        "visual_style: black_white\n"
        "translation_policy:\n"
        "  augmentation: forbidden\n"
        "  preserve_arabic_terms: true\n"
        "  monochrome_visuals: true\n",
        encoding="utf-8",
    )
    (bd / "book" / "book-toc.json").write_text(
        json.dumps({"book_title": "T", "chapters": [{"title": "What We Wear: Dress, Adornment, and Fragrance"}]}),
        encoding="utf-8",
    )
    (bd / "book" / "book.md").write_text(
        "# Title\n## 1. What We Wear: Dress, Adornment, and Fragrance\n" + ("قال رسول الله صلى الله عليه وسلم. " * 40),
        encoding="utf-8",
    )
    src = bd / "_system" / "source" / "text"
    src.mkdir(parents=True, exist_ok=True)
    (src / "refined-english.md").write_text(
        "<!-- page 1 -->\nA discussion of hunting, game, slaughter, sacrifice, prey, and the knife.",
        encoding="utf-8",
    )
    (bd / "book" / "source-crosswalk.json").write_text(
        json.dumps(
            {
                "schema": "podcast.translation-edition.source-crosswalk/v1",
                "book": bd.name,
                "chapters": [
                    {
                        "index": 1,
                        "title": "What We Wear: Dress, Adornment, and Fragrance",
                        "source_line_ranges": [[1, 2]],
                        "source_pages": [1],
                        "source_page_range": "pp. 1-1",
                        "drift_findings": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    res = V.validate_book(bd)

    assert res["verdict"] == "BOOK-BROKEN"
    assert "B6" in res["summary"]


@pytest.mark.parametrize(
    "verdict,bad",
    [
        ("BLOCKED", True),
        ("ERROR", True),
        ("STALLED", True),
        ("FAILED: x", True),
        ("FAILED", True),
        ("SHIP-READY", False),
        ("SHIP-WITH-CAUTION", False),
        ("SKIPPED", False),
        ("AUTHORED", False),
    ],
)
def test_is_bad_slide_outcome(verdict, bad):
    assert _is_bad_slide_outcome(verdict) is bad
