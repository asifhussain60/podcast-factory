from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _visual_layout import (  # noqa: E402
    SCHEMA,
    WRAP_MAX_WIDTH_PCT,
    load_layout,
    normalize_placement,
    validate_layout,
)


def test_center_forces_standalone() -> None:
    p, w = normalize_placement({"visual_id": "a", "align": "center", "flow": "wrap"})
    assert p["flow"] == "standalone"
    assert any("standalone" in x for x in w)


def test_wide_wrap_promoted_to_standalone() -> None:
    p, w = normalize_placement(
        {"visual_id": "a", "align": "left", "flow": "wrap", "width_pct": 80}
    )
    assert p["flow"] == "standalone"
    assert any(f">{WRAP_MAX_WIDTH_PCT}" in x for x in w)


def test_valid_wrap_kept() -> None:
    p, w = normalize_placement(
        {"visual_id": "a", "align": "left", "flow": "wrap", "width_pct": 40}
    )
    assert p["flow"] == "wrap" and p["align"] == "left" and p["width_pct"] == 40
    assert w == []


def test_width_clamped() -> None:
    p, _ = normalize_placement({"visual_id": "a", "width_pct": 999})
    assert p["width_pct"] == 100
    p2, _ = normalize_placement({"visual_id": "a", "width_pct": -5})
    assert p2["width_pct"] == 1


def test_unknown_enums_fall_back() -> None:
    p, w = normalize_placement(
        {"visual_id": "a", "align": "sideways", "flow": "diagonal", "page_fit": "wherever"}
    )
    assert p["align"] == "center" and p["flow"] == "standalone" and p["page_fit"] == "avoid"
    assert len(w) >= 3


def test_validate_skips_placement_without_id() -> None:
    placements, warnings = validate_layout(
        {"schema": SCHEMA, "placements": [{"anchor": "## 1. X"}, {"visual_id": "ok", "anchor": "## 2"}]}
    )
    assert len(placements) == 1 and placements[0]["visual_id"] == "ok"
    assert any("without a visual_id" in x for x in warnings)


def test_validate_flags_wrong_schema() -> None:
    _, warnings = validate_layout({"schema": "bogus/v9", "placements": []})
    assert any("unexpected schema" in x for x in warnings)


def test_anchor_para_normalization() -> None:
    assert normalize_placement({"visual_id": "a"})[0]["anchor_para"] is None
    assert normalize_placement({"visual_id": "a", "anchor_para": 3})[0]["anchor_para"] == 3
    assert normalize_placement({"visual_id": "a", "anchor_para": 0})[0]["anchor_para"] == 0
    assert normalize_placement({"visual_id": "a", "anchor_para": -4})[0]["anchor_para"] == 0
    assert normalize_placement({"visual_id": "a", "anchor_para": "x"})[0]["anchor_para"] is None
    assert normalize_placement({"visual_id": "a", "anchor_para": ""})[0]["anchor_para"] is None


def test_load_absent_layout_is_empty(tmp_path: Path) -> None:
    placements, warnings = load_layout(tmp_path)
    assert placements == [] and warnings == []


def test_load_real_layout(tmp_path: Path) -> None:
    (tmp_path / "book").mkdir()
    (tmp_path / "book" / "visual-layout.json").write_text(
        json.dumps({
            "schema": SCHEMA,
            "placements": [
                {"visual_id": "fig1", "anchor": "## 2. Patience", "align": "left",
                 "flow": "wrap", "width_pct": 40, "caption": "A tree", "page_fit": "avoid"},
            ],
        }),
        encoding="utf-8",
    )
    placements, warnings = load_layout(tmp_path)
    assert len(placements) == 1 and placements[0]["caption"] == "A tree"
    assert warnings == []
