#!/usr/bin/env python3
"""_svg_geometry.py — deterministic visual-defect lint for authored SVGs.

The semantic challengers never see pixels, so text that overflows its frame,
collides with a neighbour, or prints too small to read ships undetected
(observed on the-master-and-the-disciple reading edition, 2026-06-11).
This module estimates rendered text geometry straight from the SVG source —
no rasterization, no LLM — and reports findings:

  G1 overflow   — a text line's estimated extent escapes the viewBox
  G2 collision  — two text lines on the same baseline band overlap horizontally
  G3 min-type   — effective printed size falls below MIN_PRINT_MM at full
                  content width (the book renders SVGs at ~170mm wide)

Consumers:
  - _slide_replicate.verify_svg(): a replica with findings is demoted to its
    raster JPEG fallback (free, always correct).
  - audit CLI:  python3 _svg_geometry.py <file.svg|dir> [...]  — sweeps the
    reading edition's diagrams; used by 0book-render as an advisory gate.

Width estimation uses a flat average glyph factor (CHAR_W x font-size). It is
deliberately conservative on G1/G2 (slack margins) so findings are real.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

CHAR_W = 0.52          # avg glyph width as a fraction of font-size (Lato-ish)
SLACK = 0.03           # fraction of viewBox width forgiven before G1 fires
PRINT_WIDTH_MM = 170.0  # content-width the book PDF renders diagrams at
MIN_PRINT_MM = 2.4      # min acceptable cap-height-ish print size (~7pt)
DEFAULT_SIZE = 14.0

_NS = "{http://www.w3.org/2000/svg}"


@dataclass
class _Line:
    x: float
    y: float
    size: float
    anchor: str
    text: str

    @property
    def width(self) -> float:
        return len(self.text) * self.size * CHAR_W

    @property
    def x0(self) -> float:
        if self.anchor == "middle":
            return self.x - self.width / 2
        if self.anchor == "end":
            return self.x - self.width
        return self.x

    @property
    def x1(self) -> float:
        return self.x0 + self.width


def _floats(s: str | None, default: float) -> float:
    if not s:
        return default
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else default


def _collect_lines(root: ET.Element) -> list[_Line]:
    lines: list[_Line] = []
    for t in root.iter(f"{_NS}text"):
        tx = _floats(t.get("x"), 0.0)
        ty = _floats(t.get("y"), 0.0)
        size = _floats(t.get("font-size"), DEFAULT_SIZE)
        anchor = t.get("text-anchor", "start")
        tspans = list(t.findall(f"{_NS}tspan"))
        if not tspans:
            txt = (t.text or "").strip()
            if txt:
                lines.append(_Line(tx, ty, size, anchor, txt))
            continue
        cur_y = ty
        for sp in tspans:
            sx = _floats(sp.get("x"), tx)
            if sp.get("dy") is not None:
                cur_y += _floats(sp.get("dy"), 0.0)
            elif sp.get("y") is not None:
                cur_y = _floats(sp.get("y"), cur_y)
            sp_size = _floats(sp.get("font-size"), size)
            txt = "".join(sp.itertext()).strip()
            if txt:
                lines.append(_Line(sx, cur_y, sp_size, sp.get("text-anchor", anchor), txt))
    return lines


def geometry_findings(svg_source: str) -> list[str]:
    """Return human-readable findings (empty list == geometrically clean)."""
    try:
        root = ET.fromstring(svg_source)
    except ET.ParseError as e:
        return [f"unparseable SVG: {e}"]
    vb = root.get("viewBox")
    if not vb:
        return ["missing viewBox (sizing is unverifiable)"]
    parts = [float(p) for p in re.split(r"[ ,]+", vb.strip()) if p]
    if len(parts) != 4:
        return [f"malformed viewBox: {vb!r}"]
    vx, vy, vw, vh = parts
    lines = _collect_lines(root)
    findings: list[str] = []

    slack = vw * SLACK
    for ln in lines:
        if ln.x1 > vx + vw + slack or ln.x0 < vx - slack:
            findings.append(
                f"G1 overflow: {ln.text[:48]!r} spans x {ln.x0:.0f}..{ln.x1:.0f} "
                f"outside viewBox {vx:.0f}..{vx + vw:.0f}")
        if ln.y > vy + vh + ln.size:
            findings.append(
                f"G1 overflow: {ln.text[:48]!r} at y {ln.y:.0f} below viewBox {vy + vh:.0f}")

    # G2: same baseline band + horizontal intersection of estimated extents.
    for i, a in enumerate(lines):
        for b in lines[i + 1:]:
            band = min(a.size, b.size) * 0.7
            if abs(a.y - b.y) >= band:
                continue
            inter = min(a.x1, b.x1) - max(a.x0, b.x0)
            if inter > min(a.width, b.width) * 0.18 and inter > 4:
                findings.append(
                    f"G2 collision: {a.text[:36]!r} overlaps {b.text[:36]!r} "
                    f"by ~{inter:.0f} units at y {a.y:.0f}")

    # G3: effective printed size at full content width.
    for ln in lines:
        printed_mm = ln.size * PRINT_WIDTH_MM / vw
        if printed_mm < MIN_PRINT_MM:
            findings.append(
                f"G3 min-type: {ln.text[:40]!r} prints ~{printed_mm:.1f}mm "
                f"(font {ln.size:.0f} in viewBox {vw:.0f} wide; floor {MIN_PRINT_MM}mm)")

    # De-dup G3 spam: keep at most 3 examples per code.
    out: list[str] = []
    counts: dict[str, int] = {}
    for f in findings:
        code = f.split(" ", 1)[0]
        counts[code] = counts.get(code, 0) + 1
        if counts[code] <= 3:
            out.append(f)
    for code, n in counts.items():
        if n > 3:
            out.append(f"{code}: ... and {n - 3} more")
    return out


def lint_file(path: Path) -> list[str]:
    return geometry_findings(path.read_text(encoding="utf-8"))


def auto_expand_viewbox(svg_source: str, pad: float = 8.0) -> tuple[str, bool]:
    """Grow the viewBox horizontally to cover estimated text extents (G1 fix).

    Returns (source, changed). Vertical growth is intentionally not attempted —
    a y-overflow means the layout math is wrong, not the canvas.
    """
    try:
        root = ET.fromstring(svg_source)
    except ET.ParseError:
        return svg_source, False
    vb = root.get("viewBox")
    if not vb:
        return svg_source, False
    parts = [float(p) for p in re.split(r"[ ,]+", vb.strip()) if p]
    if len(parts) != 4:
        return svg_source, False
    vx, vy, vw, vh = parts
    lines = _collect_lines(root)
    if not lines:
        return svg_source, False
    min_x = min([vx] + [ln.x0 - pad for ln in lines])
    max_x = max([vx + vw] + [ln.x1 + pad for ln in lines])
    if min_x >= vx and max_x <= vx + vw:
        return svg_source, False
    new_vb = f"{min_x:.0f} {vy:.0f} {max_x - min_x:.0f} {vh:.0f}"
    return svg_source.replace(f'viewBox="{vb}"', f'viewBox="{new_vb}"', 1), True


def gate_svg(svg_source: str, label: str, *, log=print) -> str:
    """Pipeline gate: auto-fix what is deterministic, surface the rest.

    Used by _book_illustrate after every authored/rendered diagram. Returns
    the (possibly viewBox-expanded) source; remaining findings are logged
    loudly so the phase output shows exactly which diagram needs attention.
    """
    findings = geometry_findings(svg_source)
    if any(f.startswith("G1") for f in findings):
        svg_source, changed = auto_expand_viewbox(svg_source)
        if changed:
            findings = geometry_findings(svg_source)
            log(f"      [svg-geometry] {label}: viewBox auto-expanded to cover text")
    for f in findings:
        log(f"      [svg-geometry] WARNING {label}: {f}")
    return svg_source


def main() -> int:
    targets: list[Path] = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        targets.extend(sorted(p.rglob("*.svg")) if p.is_dir() else [p])
    if not targets:
        print("usage: _svg_geometry.py <file.svg|dir> [...]", file=sys.stderr)
        return 2
    dirty = 0
    for svg in targets:
        findings = lint_file(svg)
        if findings:
            dirty += 1
            print(f"FAIL {svg}")
            for f in findings:
                print(f"   {f}")
        else:
            print(f"OK   {svg}")
    print(f"\n{len(targets) - dirty} clean, {dirty} with findings")
    return 1 if dirty else 0


if __name__ == "__main__":
    raise SystemExit(main())
