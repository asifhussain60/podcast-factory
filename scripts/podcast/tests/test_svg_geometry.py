"""Tests for _svg_geometry — the deterministic visual-defect lint."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _svg_geometry import auto_expand_viewbox, geometry_findings  # noqa: E402


def _svg(body: str, viewbox: str = "0 0 500 300") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">'
            f"{body}</svg>")


def test_clean_svg_has_no_findings():
    svg = _svg('<text x="250" y="40" text-anchor="middle" font-size="14">Hello</text>')
    assert geometry_findings(svg) == []


def test_overflow_right_edge_flagged():
    long = "x" * 60
    svg = _svg(f'<text x="480" y="40" font-size="14">{long}</text>')
    assert any(f.startswith("G1") for f in geometry_findings(svg))


def test_negative_viewbox_origin_is_respected():
    # Text at x=-40 inside viewBox starting at -60 is NOT an overflow.
    svg = _svg('<text x="-40" y="40" font-size="14">Edge label</text>',
               viewbox="-60 0 560 300")
    assert not any(f.startswith("G1") for f in geometry_findings(svg))


def test_collision_same_band_flagged():
    svg = _svg(
        '<text x="100" y="50" font-size="12">A corpse. A body without a spirit.</text>'
        '<text x="120" y="52" font-size="12">A wraith. A spirit without a body.</text>')
    assert any(f.startswith("G2") for f in geometry_findings(svg))


def test_stacked_lines_not_collided():
    svg = _svg(
        '<text x="100" y="50" font-size="12">First line of text here</text>'
        '<text x="100" y="70" font-size="12">Second line of text here</text>')
    assert not any(f.startswith("G2") for f in geometry_findings(svg))


def test_min_type_flagged_on_wide_viewbox():
    svg = _svg('<text x="100" y="40" font-size="9">tiny label</text>',
               viewbox="0 0 1400 700")
    assert any(f.startswith("G3") for f in geometry_findings(svg))


def test_auto_expand_covers_escaping_text():
    long = "y" * 50
    svg = _svg(f'<text x="460" y="40" font-size="14">{long}</text>')
    fixed, changed = auto_expand_viewbox(svg)
    assert changed
    assert not any(f.startswith("G1") for f in geometry_findings(fixed))


def test_auto_expand_noop_when_clean():
    svg = _svg('<text x="250" y="40" text-anchor="middle" font-size="14">Hi</text>')
    _, changed = auto_expand_viewbox(svg)
    assert not changed
