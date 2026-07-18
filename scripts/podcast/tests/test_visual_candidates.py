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
