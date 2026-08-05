from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _visual_candidates import (
    VISUALS_SCHEMA,
    clean_slide_watermark,
    emit_diagram_candidates,
    emit_slide_candidates,
    load_index,
    merge_entries,
)


def _bookdir(tmp_path: Path) -> Path:
    bd = tmp_path / "bd"
    (bd / "book").mkdir(parents=True)
    return bd


def test_merge_is_idempotent_by_id(tmp_path: Path) -> None:
    bd = _bookdir(tmp_path)
    e = [{"id": "a", "caption": "one"}, {"id": "b", "caption": "two"}]
    merge_entries(bd, e)
    merge_entries(bd, [{"id": "a", "caption": "updated"}])
    idx = load_index(bd)
    ids = [x["id"] for x in idx]
    assert ids == ["a", "b"]  # order preserved, no dup
    assert next(x for x in idx if x["id"] == "a")["caption"] == "updated"


def test_index_has_schema(tmp_path: Path) -> None:
    bd = _bookdir(tmp_path)
    merge_entries(bd, [{"id": "a"}])
    data = json.loads((bd / "book" / "visuals" / "index.json").read_text())
    assert data["schema"] == VISUALS_SCHEMA


def test_emit_diagram_candidates_copies_and_registers(tmp_path: Path) -> None:
    bd = _bookdir(tmp_path)
    diagrams = bd / "book" / "_diagrams"
    diagrams.mkdir(parents=True)
    svg = diagrams / "ch1-1.svg"
    svg.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
    manifest = [
        {
            "diagram_id": "ch1-1",
            "section": "## 1. Knowledge",
            "anchor_text": "Seek",
            "caption": "A ladder",
            "svg_path": str(svg),
            "structure_type": "mermaid-flowchart",
        }
    ]
    entries = emit_diagram_candidates(bd, manifest, log=lambda *a: None)
    assert (bd / "book" / "visuals" / "ch1-1.svg").exists()
    assert entries[0]["type"] == "mermaid-flowchart"
    assert entries[0]["suggested_anchor"] == "## 1. Knowledge"
    assert entries[0]["cleaned"] is True


def test_emit_diagram_skips_missing_svg(tmp_path: Path) -> None:
    bd = _bookdir(tmp_path)
    entries = emit_diagram_candidates(bd, [{"diagram_id": "x", "svg_path": str(bd / "nope.svg")}], log=lambda *a: None)
    assert entries == []


def test_emit_slide_candidates_prefers_vector(tmp_path: Path) -> None:
    bd = _bookdir(tmp_path)
    vec = bd / "replica.svg"
    vec.write_text("<svg/>", encoding="utf-8")
    entries = emit_slide_candidates(
        bd,
        [{"page": 5, "anchor_text": "the seven", "title": "The Seven"}],
        pages={},
        svg_overrides={5: vec},
        log=lambda *a: None,
    )
    assert entries[0]["type"] == "slide-vector"
    assert entries[0]["embedded_title"] == "The Seven"  # for caption de-dup
    assert (bd / "book" / "visuals" / "slide-5.svg").exists()


def test_clean_slide_watermark_fallback_copies(tmp_path: Path) -> None:
    # A non-image file exercises the graceful fallback (no Pillow crash).
    src = tmp_path / "fake.jpg"
    src.write_bytes(b"not-an-image")
    dst = tmp_path / "out" / "fake.jpg"
    cropped = clean_slide_watermark(src, dst)
    assert dst.exists()
    assert cropped is False  # fell back to copy


def test_emit_slide_candidates_cleans_raster(tmp_path: Path) -> None:
    bd = _bookdir(tmp_path)
    raster_rel = "slide-decks/_pages/ch01/page-01.png"
    raster = bd / raster_rel
    raster.parent.mkdir(parents=True)
    raster.write_bytes(b"fake-png-bytes")
    entries = emit_slide_candidates(
        bd,
        [{"page": 2, "anchor_text": "a", "title": "T"}],
        pages={2: raster_rel},
        svg_overrides={},
        log=lambda *a: None,
    )
    assert entries[0]["type"] == "slide"
    assert (bd / "book" / "visuals" / "slide-2.png").exists()


# ── chapter stamping (2026-07-22) ───────────────────────────────────────────
# The palette-flood bug: book-deck slide anchors quote the deck NARRATION
# (book-slides.md), the Composer resolved anchors against book.md alone, so
# every slide fell to "book-wide" and appeared in every chapter's palette.
# The producer now resolves the chapter at emit time, where both surfaces are
# on disk, and stamps it explicitly.

from _visual_candidates import resolve_candidate_chapter  # noqa: E402


def _surfaces(bd: Path) -> None:
    (bd / "book" / "book.md").write_text(
        "# T\n\n## 1. The Garden\n\nA rose grew by the wall.\n\n## 2. The Sea\n\nThe tide came in slowly.\n",
        encoding="utf-8",
    )
    (bd / "book" / "book-slides.md").write_text(
        "# T (narration)\n\n## 1. The Garden\n\nPicture a rose, stubborn by the wall.\n\n"
        "## 2. The Sea\n\nWatch the tide crawl up the sand.\n",
        encoding="utf-8",
    )


def test_resolve_chapter_needle_from_narration(tmp_path: Path) -> None:
    # The needle exists ONLY in book-slides.md — the exact shape of the flood bug.
    bd = _bookdir(tmp_path)
    _surfaces(bd)
    assert resolve_candidate_chapter(bd, "Watch the tide crawl up the sand") == "2. The Sea"


def test_resolve_chapter_heading_anchor_via_anchor_key(tmp_path: Path) -> None:
    # Illustrate manifests put the section heading in the anchor; resolved
    # through the fixture-pinned anchor_key, so numbering differences don't matter.
    bd = _bookdir(tmp_path)
    _surfaces(bd)
    assert resolve_candidate_chapter(bd, "The Garden") == "1. The Garden"
    assert resolve_candidate_chapter(bd, "2. The Sea") == "2. The Sea"


def test_resolve_chapter_empty_or_unresolvable_is_book_wide(tmp_path: Path) -> None:
    bd = _bookdir(tmp_path)
    _surfaces(bd)
    assert resolve_candidate_chapter(bd, "") == ""
    assert resolve_candidate_chapter(bd, "no such passage anywhere") == ""


def test_emit_slide_candidates_stamps_chapter(tmp_path: Path) -> None:
    bd = _bookdir(tmp_path)
    _surfaces(bd)
    vec = bd / "replica.svg"
    vec.write_text("<svg/>", encoding="utf-8")
    entries = emit_slide_candidates(
        bd,
        [
            {"page": 1, "anchor_text": "stubborn by the wall", "title": "Rose"},
            {"page": 2, "anchor_text": "", "title": "Cover"},
            {"page": 3, "anchor_text": "x", "title": "Pre", "chapter": "2. The Sea"},
        ],
        pages={},
        svg_overrides={1: vec, 2: vec, 3: vec},
        log=lambda *a: None,
    )
    by_id = {e["id"]: e for e in entries}
    assert by_id["slide-1"]["chapter"] == "1. The Garden"  # resolved from narration
    assert by_id["slide-2"]["chapter"] == ""  # cover stays book-wide
    assert by_id["slide-3"]["chapter"] == "2. The Sea"  # explicit stamp wins
