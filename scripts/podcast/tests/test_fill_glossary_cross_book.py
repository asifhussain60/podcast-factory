"""Borrowing Arabic script another book proved against a real scan.

`al-anwaar-al-lateefah` has no Arabic source at all, so it cannot be filled from
the Quranic corpus: measured 2026-08-03, a corpus-only fill resolved 31 terms
"uniquely" and got at least six of the first fourteen WRONG. What it can do is
borrow from a book that HAS a scan — which makes "has a scan" the load-bearing
question this module has to get right.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402
from fill_glossary_cross_book import (  # noqa: E402
    _has_own_scan,
    apply,
    build_pool,
    plan,
)

ARABIC_PAGE = "قال الشيخ إن الحدود مراتب ومنازل والتأويل باطن الشريعة " * 60


def _book(root: Path, name: str, entries: list[dict], *, arabic_source: str | None) -> Path:
    bd = root / name
    (bd / "_system" / "source" / "ocr").mkdir(parents=True)
    (bd / "_system" / "glossary.yml").write_text(
        yaml.safe_dump({"schema_version": 2, "entries": entries}, allow_unicode=True), encoding="utf-8"
    )
    if arabic_source is not None:
        (bd / "_system" / "source" / "ocr" / "raw-extract.md").write_text(arabic_source, encoding="utf-8")
    return bd


def test_a_book_without_arabic_in_its_extract_has_no_scan(tmp_path: Path) -> None:
    """THE PROVENANCE HOLE, and it was live.

    `_system/source/text/raw-extract.md` is the ENGLISH extract and carries zero
    Arabic. Testing that the file EXISTS admitted `kitab-al-riyad` — which has no
    Arabic anywhere — to the pool, and it lent a spelling to `al-anwaar` as though
    it had been read off a page.
    """
    english = _book(tmp_path, "english-only", [], arabic_source="An English page. " * 200)
    arabic = _book(tmp_path, "scanned", [], arabic_source=ARABIC_PAGE)
    none = _book(tmp_path, "no-source", [], arabic_source=None)
    assert _has_own_scan(english) is False
    assert _has_own_scan(none) is False
    assert _has_own_scan(arabic) is True


def test_a_handful_of_stray_characters_is_not_a_scan(tmp_path: Path) -> None:
    """`kunooz-al-hikmah` carries SEVEN Arabic runs. Books with a real scan carry
    six to sixty-eight thousand, so nothing sits near the line."""
    stray = _book(tmp_path, "stray", [], arabic_source="Mostly English. " * 300 + "الحدود مراتب")
    assert _has_own_scan(stray) is False


def test_only_scanned_books_contribute_to_the_pool(tmp_path: Path) -> None:
    scanned = _book(tmp_path, "scanned", [{"phonetic": "hudud", "arabic_script": "حُدُود"}], arabic_source=ARABIC_PAGE)
    unscanned = _book(tmp_path, "unscanned", [{"phonetic": "tawil", "arabic_script": "تَأْوِيل"}], arabic_source=None)
    pool = build_pool([scanned, unscanned])
    assert "hudud" in pool and "tawil" not in pool


def test_a_fill_records_where_it_came_from(tmp_path: Path) -> None:
    scanned = _book(tmp_path, "scanned", [{"phonetic": "hudud", "arabic_script": "حُدُود"}], arabic_source=ARABIC_PAGE)
    target = _book(
        tmp_path,
        "needs-fill",
        [{"phonetic": "hudud", "arabic_script": ""}, {"phonetic": "suradiq", "arabic_script": ""}],
        arabic_source=None,
    )
    p = plan(target, build_pool([scanned, target]))
    assert [f["phonetic"] for f in p["fills"]] == ["hudud"]
    assert p["missing"] == ["suradiq"]
    assert apply(target, p) == 1

    entries = yaml.safe_load((target / "_system" / "glossary.yml").read_text())["entries"]
    filled = next(e for e in entries if e["phonetic"] == "hudud")
    assert filled["arabic_script"] == "حُدُود"
    assert filled["script_source"] == "cross-book:scanned"
    assert (target / "_system" / "glossary-cross-fill.json").exists()


def test_a_term_no_scanned_book_carries_is_left_empty(tmp_path: Path) -> None:
    """It will not guess. That is the whole contract."""
    scanned = _book(tmp_path, "scanned", [], arabic_source=ARABIC_PAGE)
    target = _book(tmp_path, "target", [{"phonetic": "suradiq", "arabic_script": ""}], arabic_source=None)
    p = plan(target, build_pool([scanned]))
    assert p["fills"] == [] and p["missing"] == ["suradiq"]
    assert apply(target, p) == 0
