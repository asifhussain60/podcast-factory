"""_svg_patterns.py — Pure-Python SVG rendering for Islamic esoteric diagram patterns.

Five rendering functions for structural shapes that Mermaid DSL cannot express cleanly.
Used by _book_illustrate.py (Phase 0book-illustrate) for the 'SVG-pattern-routed'
branch of the two-stage classification pipeline.

All output SVGs:
  - viewBox-only sizing (no hardcoded width/height)
  - Colour palette matched to editorial-modern theme (theme.css hex values)
  - <title> + <desc> elements for WCAG AA accessibility
  - font-family: 'Lato', system-ui, sans-serif  (matches render-mermaid.mjs output)
  - Zero external dependencies

Pattern types:
  concentric_layers   — nested cosmological levels (Zahir / Batin / Batin al-Batin)
  cosmic_pair         — two-column polarity contrast (Sun/Moon, Sky/Earth, Salty/Fresh)
  quadrant_map        — 2×2 state grid (outer×inner knowledge → spiritual station)
  hierarchy_tree      — top-down authority/proximity tree (Natiq→Imam→Hujja→Duʿāt)
  cascade_chain       — transmission chain (origin transforms → condenses → distributes)
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Palette — mirrors theme.css --c-* tokens exactly.
# Change here when the theme changes; nowhere else.
# ---------------------------------------------------------------------------
_C_BG           = "#f7f4ee"    # --c-bg
_C_BG_CARD      = "#fffdf8"    # --c-bg-card
_C_BG_SUNKEN    = "#efeae0"    # --c-bg-sunken
_C_INK          = "#1f1d18"    # --c-ink
_C_INK_DIM      = "#4d4a42"    # --c-ink-dim
_C_INK_MUTED    = "#87827a"    # --c-ink-muted
_C_RULE         = "#d9d3c4"    # --c-rule
_C_RULE_SOFT    = "#ebe6da"    # --c-rule-soft
_C_ACCENT       = "#8b4513"    # --c-accent  (saddle brown)
_C_ACCENT_SOFT  = "#d2b48c"    # --c-accent-soft (tan)
_C_ACCENT_MID   = "#c8956c"    # mid-point blend
_C_ACCENT_DARK  = "#a0522d"    # sienna (between accent and mid)

_FONT = "'Lato', system-ui, sans-serif"

# Concentric-layer fill gradient: index 0 = innermost (most esoteric, darkest),
# index 4 = outermost (most manifest, lightest). Up to 5 layers supported.
_LAYER_FILLS = [_C_ACCENT, _C_ACCENT_DARK, _C_ACCENT_MID, _C_ACCENT_SOFT, _C_BG_SUNKEN]
_LAYER_TEXTS = ["#fffdf8", "#fffdf8", _C_INK, _C_INK, _C_INK]

# Cascade-chain gradient endpoints (for blended fill across nodes)
_CASCADE_TOP_RGB = (0x8b, 0x45, 0x13)   # _C_ACCENT
_CASCADE_BOT_RGB = (0xef, 0xea, 0xe0)   # _C_BG_SUNKEN


# ---------------------------------------------------------------------------
# SVG primitives
# ---------------------------------------------------------------------------

def _esc(s: str) -> str:
    """XML-escape a string for safe SVG text content / attribute values."""
    return (s.replace("&", "&amp;")
              .replace("<", "&lt;")
              .replace(">", "&gt;")
              .replace('"', "&quot;"))


def _id_safe(title: str, max_len: int = 40) -> str:
    """Produce a safe XML id from an arbitrary title string."""
    raw = "".join(c if c.isalnum() else "_" for c in title)
    return (raw or "diagram")[:max_len].strip("_") or "diagram"


def _wrap_text(text: str, max_chars: int = 28) -> list[str]:
    """Split text into lines of at most max_chars characters, breaking at spaces."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        probe = (current + " " + word).strip()
        if len(probe) <= max_chars:
            current = probe
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text[:max_chars]]


def _multiline_text(x: float, y: float, text: str, *, fill: str = _C_INK,
                    size: int = 13, anchor: str = "middle", weight: str = "normal",
                    max_chars: int = 28, line_h: int = 17) -> tuple[str, float]:
    """Return (svg_string, total_height) for a multi-line <text> element."""
    lines = _wrap_text(text, max_chars)
    n = len(lines)
    total_h = n * line_h
    start_y = y - (n - 1) * line_h / 2
    spans = []
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else line_h
        spans.append(
            f'<tspan x="{x}" dy="{dy}">{_esc(line)}</tspan>'
        )
    svg = (
        f'<text x="{x}" y="{start_y}" text-anchor="{anchor}" '
        f'dominant-baseline="central" '
        f'font-size="{size}" font-weight="{weight}" fill="{_esc(fill)}">'
        + "".join(spans)
        + "</text>"
    )
    return svg, total_h


def _rect(x: float, y: float, w: float, h: float, fill: str, stroke: str,
          rx: float = 4, stroke_w: float = 1.0) -> str:
    rx_attr = f' rx="{rx}"' if rx else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"{rx_attr}/>'
    )


_ARROWHEAD_DEF = (
    "<defs>"
    '<marker id="svgp_arrow" viewBox="0 0 10 10" refX="9" refY="5" '
    'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
    f'<path d="M 0 1 L 9 5 L 0 9 z" fill="{_C_INK_MUTED}"/>'
    "</marker>"
    "</defs>"
)


def _svg_wrap(inner: str, viewbox: str, title: str, desc: str) -> str:
    """Wrap SVG content with root element, accessibility, and global style."""
    safe_id = _id_safe(title)
    style = (
        f"<style>"
        f"#{safe_id}{{font-family:{_FONT};font-size:14px;fill:{_C_INK};}}"
        f"#{safe_id} text{{font-family:{_FONT};}}"
        f"</style>"
    )
    return (
        f'<svg id="{safe_id}" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{viewbox}" role="img" '
        f'aria-labelledby="{safe_id}_t {safe_id}_d">\n'
        f'<title id="{safe_id}_t">{_esc(title)}</title>\n'
        f'<desc id="{safe_id}_d">{_esc(desc)}</desc>\n'
        f'{style}\n'
        f'{inner}\n'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# Pattern 1 — Concentric Layers
# ---------------------------------------------------------------------------

def concentric_layers(layers: list[dict], title: str) -> str:
    """
    Render nested concentric ellipses for cosmological / knowledge-level structures.

    layers: list from OUTERMOST to INNERMOST, each dict with:
      - label (str): name of the level (e.g. "Zahir / Outer")
      - description (str, optional): brief note shown below the label
    title: diagram title

    Innermost ellipse is darkest (most esoteric), outermost is lightest.
    Up to 5 layers supported; extra layers are silently truncated.
    """
    n = min(len(layers), 5)
    ls = layers[:n]

    cx, cy = 250, 225
    max_rx, max_ry = 210, 160
    # Radii: layers[0] (outermost) gets max, layers[n-1] (innermost) gets min
    rx_step = max_rx / n
    ry_step = max_ry / n

    parts: list[str] = [_ARROWHEAD_DEF]

    # Title
    title_svg, _ = _multiline_text(250, 22, title, fill=_C_ACCENT, size=16,
                                    weight="600", max_chars=40, line_h=20)
    parts.append(title_svg)

    # Draw rings from outermost (index 0) to innermost (index n-1).
    # Draw order: outermost first (background), innermost last (foreground).
    for i, layer in enumerate(ls):
        # i=0 → outermost (large, lightest); i=n-1 → innermost (small, darkest)
        inner_idx = n - 1 - i   # maps to _LAYER_FILLS index: 0=innermost=darkest
        rx = max_rx - i * rx_step + rx_step * 0.0  # full radius for this level
        ry = max_ry - i * ry_step

        fill  = _LAYER_FILLS[inner_idx]
        text_color = _LAYER_TEXTS[inner_idx]
        stroke = _C_ACCENT if inner_idx == 0 else _C_RULE

        parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
        )

    # Labels: place each label in the visible annular band of its ring.
    # Annular band top = cy - ry_this, bottom = cy - ry_inner (or cy for innermost).
    for i, layer in enumerate(ls):
        inner_idx = n - 1 - i
        text_color = _LAYER_TEXTS[inner_idx]

        ry_this  = max_ry - i * ry_step
        ry_inner = max_ry - (i + 1) * ry_step if i < n - 1 else 0.0
        # Midpoint of annular band (from top arc)
        label_y = cy - (ry_this + ry_inner) / 2

        label_svg, _ = _multiline_text(cx, label_y, layer["label"],
                                        fill=text_color, size=13, weight="700",
                                        max_chars=30, line_h=16)
        parts.append(label_svg)

        if layer.get("description"):
            desc_y = label_y + 18
            desc_svg, _ = _multiline_text(cx, desc_y, layer["description"],
                                           fill=text_color, size=10, max_chars=35,
                                           line_h=13)
            parts.append(desc_svg)

    vb_h = cy + max_ry + 16
    inner_svg = "\n".join(parts)
    return _svg_wrap(
        inner_svg,
        f"0 0 500 {vb_h:.0f}",
        title,
        f"Concentric diagram: {n} nested levels — "
        + ", ".join(l["label"] for l in ls)
    )


# ---------------------------------------------------------------------------
# Pattern 2 — Cosmic Pair
# ---------------------------------------------------------------------------

def cosmic_pair(rows: list[dict], left_label: str, right_label: str,
                title: str, principle: str = "") -> str:
    """
    Two-column contrast diagram for Zahir / Batin-style cosmic polarities.

    rows: list of {left: str, right: str} in any order
    left_label: header for the left (higher-rank) column
    right_label: header for the right (lower-rank) column
    title: diagram title
    principle: optional unifying principle shown as a subtitle
                (e.g. "Higher rank is always LEFT")

    Convention: left = higher-rank (filled with accent), right = lower-rank (lighter).
    """
    n_rows = len(rows)
    row_h = 46
    header_h = 48
    top_pad = 48 + (14 if principle else 0)
    vb_h = top_pad + header_h + n_rows * row_h + 12

    col_w = 218
    left_x  = 14
    right_x = 268
    cx = 250

    parts: list[str] = []

    # Title
    t_svg, t_h = _multiline_text(cx, 20, title, fill=_C_ACCENT, size=16,
                                   weight="600", max_chars=44, line_h=20)
    parts.append(t_svg)

    if principle:
        p_svg, _ = _multiline_text(cx, 40, principle, fill=_C_INK_MUTED,
                                    size=10, max_chars=55, line_h=12)
        parts.append(p_svg)

    # Header row
    y_hdr = top_pad
    parts.append(_rect(left_x, y_hdr, col_w, header_h, _C_ACCENT, _C_ACCENT, rx=4))
    parts.append(_rect(right_x, y_hdr, col_w, header_h, _C_BG_SUNKEN, _C_RULE, rx=4))

    lh_svg, _ = _multiline_text(left_x + col_w / 2, y_hdr + header_h / 2,
                                  left_label, fill="#fffdf8", size=12, weight="700",
                                  max_chars=24, line_h=15)
    rh_svg, _ = _multiline_text(right_x + col_w / 2, y_hdr + header_h / 2,
                                  right_label, fill=_C_INK, size=12, weight="700",
                                  max_chars=24, line_h=15)
    parts.append(lh_svg)
    parts.append(rh_svg)

    # Data rows
    for i, row in enumerate(rows):
        y_row = top_pad + header_h + i * row_h
        row_fill = _C_BG_CARD if i % 2 == 0 else _C_BG
        parts.append(_rect(left_x, y_row, col_w, row_h, row_fill, _C_RULE, rx=0))
        parts.append(_rect(right_x, y_row, col_w, row_h, row_fill, _C_RULE, rx=0))

        text_cy = y_row + row_h / 2
        lsvg, _ = _multiline_text(left_x + col_w / 2, text_cy, row.get("left", ""),
                                    fill=_C_INK, size=12, max_chars=24, line_h=14)
        rsvg, _ = _multiline_text(right_x + col_w / 2, text_cy, row.get("right", ""),
                                    fill=_C_INK, size=12, max_chars=24, line_h=14)
        parts.append(lsvg)
        parts.append(rsvg)

        # Thin divider between columns
        div_x = cx - 1
        parts.append(
            f'<line x1="{div_x}" y1="{y_row + 4}" x2="{div_x}" y2="{y_row + row_h - 4}" '
            f'stroke="{_C_RULE}" stroke-width="1"/>'
        )

    return _svg_wrap(
        "\n".join(parts),
        f"0 0 500 {vb_h:.0f}",
        title,
        f"Two-column contrast: {left_label} vs {right_label} — {n_rows} paired phenomena"
    )


# ---------------------------------------------------------------------------
# Pattern 3 — Quadrant Map
# ---------------------------------------------------------------------------

def quadrant_map(x_axis: dict, y_axis: dict, quadrants: list[dict],
                 title: str) -> str:
    """
    2×2 quadrant map for states defined by two binary axes.

    x_axis: {label, pos_label, neg_label}
             neg_label = left column, pos_label = right column
    y_axis: {label, pos_label, neg_label}
             pos_label = top row, neg_label = bottom row
    quadrants: list of exactly 4 dicts in order:
               [top-left, top-right, bottom-left, bottom-right]
               each: {label, note (optional), impossible (optional bool)}
    title: diagram title

    Convention: quadrant[1] (top-right) is highlighted as the ideal/synthesis state.
    Impossible quadrants receive a hatched background.
    """
    vb_w, vb_h = 510, 510
    grid_x, grid_y = 58, 72
    cell_w, cell_h = 195, 185
    total_grid_w = cell_w * 2
    total_grid_h = cell_h * 2
    cx_grid = grid_x + cell_w   # vertical divider x
    cy_grid = grid_y + cell_h   # horizontal divider y

    parts: list[str] = [_ARROWHEAD_DEF]

    # Title
    t_svg, _ = _multiline_text(vb_w / 2, 24, title, fill=_C_ACCENT, size=16,
                                 weight="600", max_chars=48, line_h=20)
    parts.append(t_svg)

    # Axis labels (outside the grid)
    # X-axis label (bottom centre)
    ax_svg, _ = _multiline_text(grid_x + cell_w, vb_h - 8, x_axis.get("label", ""),
                                  fill=_C_INK_DIM, size=11, weight="600",
                                  max_chars=30, line_h=13)
    parts.append(ax_svg)
    # Y-axis label (left, rotated)
    y_axis_label = y_axis.get("label", "")
    if y_axis_label:
        mid_grid_y = grid_y + cell_h
        parts.append(
            f'<text x="12" y="{mid_grid_y}" text-anchor="middle" '
            f'font-size="11" font-weight="600" fill="{_C_INK_DIM}" '
            f'transform="rotate(-90,12,{mid_grid_y})">'
            f'{_esc(y_axis_label)}</text>'
        )

    # Polarity labels (outside edges)
    for lbl, x, y, anchor in [
        (x_axis.get("neg_label", ""), grid_x + cell_w / 2, grid_y - 7, "middle"),
        (x_axis.get("pos_label", ""), grid_x + cell_w + cell_w / 2, grid_y - 7, "middle"),
        (y_axis.get("pos_label", ""), grid_x - 6, grid_y + cell_h / 2, "end"),
        (y_axis.get("neg_label", ""), grid_x - 6, grid_y + cell_h + cell_h / 2, "end"),
    ]:
        if lbl:
            svg, _ = _multiline_text(x, y, lbl, fill=_C_INK_MUTED, size=10,
                                      anchor=anchor, max_chars=20, line_h=12)
            parts.append(svg)

    # Quadrant cells: [top-left, top-right, bottom-left, bottom-right]
    positions = [
        (grid_x,          grid_y),
        (grid_x + cell_w, grid_y),
        (grid_x,          grid_y + cell_h),
        (grid_x + cell_w, grid_y + cell_h),
    ]
    # Default fills: index 1 (top-right) is the "ideal" state
    default_fills = [_C_BG, _C_ACCENT, _C_BG_SUNKEN, _C_BG]
    default_texts = [_C_INK, "#fffdf8", _C_INK, _C_INK]

    for qi in range(min(4, len(quadrants))):
        q = quadrants[qi]
        qx, qy = positions[qi]
        is_imp = q.get("impossible", False)

        if is_imp:
            fill = _C_BG_SUNKEN
            text_col = _C_INK_MUTED
        else:
            fill = default_fills[qi]
            text_col = default_texts[qi]

        parts.append(_rect(qx, qy, cell_w, cell_h, fill, _C_RULE, rx=0))

        # Hatching for impossible
        if is_imp:
            hatch_id = f"svgp_h{qi}"
            parts.append(
                f'<defs>'
                f'<pattern id="{hatch_id}" width="10" height="10" '
                f'patternUnits="userSpaceOnUse" patternTransform="rotate(40)">'
                f'<line x1="0" y1="0" x2="0" y2="10" '
                f'stroke="{_C_RULE}" stroke-width="1.5"/>'
                f'</pattern></defs>'
                f'<rect x="{qx}" y="{qy}" width="{cell_w}" height="{cell_h}" '
                f'fill="url(#{hatch_id})"/>'
            )

        # Label text
        note = q.get("note", "")
        main_y = qy + cell_h / 2 - (10 if note else 0)
        lbl_svg, _ = _multiline_text(qx + cell_w / 2, main_y, q.get("label", ""),
                                      fill=text_col, size=13, weight="700",
                                      max_chars=20, line_h=16)
        parts.append(lbl_svg)

        if note:
            note_svg, _ = _multiline_text(qx + cell_w / 2, qy + cell_h / 2 + 18,
                                           note, fill=text_col, size=10,
                                           max_chars=22, line_h=12)
            parts.append(note_svg)

    # Grid lines (drawn on top to make crisp dividers)
    parts.append(
        f'<line x1="{cx_grid}" y1="{grid_y}" '
        f'x2="{cx_grid}" y2="{grid_y + total_grid_h}" '
        f'stroke="{_C_RULE}" stroke-width="2"/>'
    )
    parts.append(
        f'<line x1="{grid_x}" y1="{cy_grid}" '
        f'x2="{grid_x + total_grid_w}" y2="{cy_grid}" '
        f'stroke="{_C_RULE}" stroke-width="2"/>'
    )

    return _svg_wrap(
        "\n".join(parts),
        f"0 0 {vb_w} {vb_h}",
        title,
        f"Quadrant map: {x_axis.get('label','')} × {y_axis.get('label','')} — four states"
    )


# ---------------------------------------------------------------------------
# Pattern 4 — Hierarchy Tree
# ---------------------------------------------------------------------------

def hierarchy_tree(root: str, levels: list[list[str]], title: str) -> str:
    """
    Top-down hierarchy tree for ranked spiritual / cosmological structures.

    root: label of the apex node (e.g. "Natiq / Speaking Prophet")
    levels: list of tiers below root, each a list of node label strings.
            e.g. [["Wasi / Interpreter"], ["Hujja × 12"], ["Duʿāt × many"]]
    title: diagram title

    Tier fills darken from bottom (outermost, lightest) to top (apex, darkest).
    Large tiers (>4 nodes) are collapsed to 3 visible + an overflow node.
    Up to 4 tiers (root + 3 levels) supported.
    """
    MAX_TIERS = 3
    levels = levels[:MAX_TIERS]

    node_w  = 168
    node_h  = 44
    h_gap   = 10   # horizontal gap between sibling nodes
    v_gap   = 52   # vertical gap between tiers
    top_pad = 52

    total_levels = len(levels) + 1  # root + N tiers
    vb_w = 500
    vb_h = top_pad + total_levels * (node_h + v_gap) + 16

    # Fill palette: root = darkest, last tier = lightest
    tier_fills = [_C_ACCENT, _C_ACCENT_DARK, _C_ACCENT_SOFT, _C_BG_SUNKEN]
    tier_texts = ["#fffdf8", "#fffdf8", _C_INK, _C_INK]

    parts: list[str] = [_ARROWHEAD_DEF]

    # Title
    t_svg, _ = _multiline_text(vb_w / 2, 24, title, fill=_C_ACCENT, size=16,
                                 weight="600", max_chars=44, line_h=20)
    parts.append(t_svg)

    # Store centre-x of each node per tier for connector drawing
    all_centres: list[list[float]] = []

    # Root node
    root_cx = vb_w / 2
    root_cy = top_pad + node_h / 2
    parts.append(_rect(root_cx - node_w / 2, root_cy - node_h / 2,
                        node_w, node_h, tier_fills[0], _C_ACCENT, rx=4))
    lbl, _ = _multiline_text(root_cx, root_cy, root, fill=tier_texts[0],
                               size=12, weight="700", max_chars=22, line_h=15)
    parts.append(lbl)
    all_centres.append([root_cx])

    for tier_idx, tier_nodes in enumerate(levels):
        fill = tier_fills[min(tier_idx + 1, len(tier_fills) - 1)]
        text_col = tier_texts[min(tier_idx + 1, len(tier_texts) - 1)]
        y_centre = top_pad + (tier_idx + 1) * (node_h + v_gap) + node_h / 2

        # Collapse large tiers
        if len(tier_nodes) > 4:
            display = tier_nodes[:3] + [f"+ {len(tier_nodes) - 3} more"]
        else:
            display = tier_nodes

        n_nodes = len(display)
        total_w = n_nodes * node_w + (n_nodes - 1) * h_gap
        start_x = (vb_w - total_w) / 2

        tier_centres: list[float] = []
        for j, label in enumerate(display):
            nx  = start_x + j * (node_w + h_gap)
            ncy = y_centre
            is_overflow = (j == n_nodes - 1 and len(tier_nodes) > 4)
            nfill = _C_BG if is_overflow else fill
            ntxt  = _C_INK_MUTED if is_overflow else text_col
            parts.append(_rect(nx, ncy - node_h / 2, node_w, node_h,
                               nfill, _C_RULE if is_overflow else _C_RULE, rx=4))
            lbl_svg, _ = _multiline_text(nx + node_w / 2, ncy, label,
                                          fill=ntxt,
                                          size=11, weight="normal" if is_overflow else "600",
                                          max_chars=22, line_h=14)
            parts.append(lbl_svg)
            tier_centres.append(nx + node_w / 2)

        all_centres.append(tier_centres)

    # Draw connectors tier → tier
    for t in range(len(all_centres) - 1):
        parents  = all_centres[t]
        children = all_centres[t + 1]
        parent_y  = top_pad + t * (node_h + v_gap) + node_h
        child_y   = top_pad + (t + 1) * (node_h + v_gap)
        mid_y     = (parent_y + child_y) / 2

        # Vertical line from each parent down to mid
        for pcx in parents:
            parts.append(
                f'<line x1="{pcx:.1f}" y1="{parent_y:.1f}" '
                f'x2="{pcx:.1f}" y2="{mid_y:.1f}" '
                f'stroke="{_C_INK_MUTED}" stroke-width="1.5"/>'
            )

        # Horizontal bar at mid connecting all child approach points
        if len(children) > 1:
            parts.append(
                f'<line x1="{min(children):.1f}" y1="{mid_y:.1f}" '
                f'x2="{max(children):.1f}" y2="{mid_y:.1f}" '
                f'stroke="{_C_INK_MUTED}" stroke-width="1.5"/>'
            )

        # Arrow from mid down to each child
        for ccx in children:
            # Vertical from (single parent's x OR ccx) to child top
            src_x = parents[0] if len(parents) == 1 else ccx
            parts.append(
                f'<line x1="{ccx:.1f}" y1="{mid_y:.1f}" '
                f'x2="{ccx:.1f}" y2="{child_y - 6:.1f}" '
                f'stroke="{_C_INK_MUTED}" stroke-width="1.5" '
                f'marker-end="url(#svgp_arrow)"/>'
            )

    return _svg_wrap(
        "\n".join(parts),
        f"0 0 {vb_w} {vb_h:.0f}",
        title,
        f"Hierarchy: {root} → "
        + " → ".join(
            (", ".join(t[:2]) + ("…" if len(t) > 2 else ""))
            for t in levels
        )
    )


# ---------------------------------------------------------------------------
# Pattern 5 — Cascade Chain
# ---------------------------------------------------------------------------

def cascade_chain(nodes: list[dict], title: str) -> str:
    """
    Vertical transmission chain for knowledge / authority flows.

    nodes: ordered list from SOURCE (top) to RECEIVER (bottom), each dict:
      - role (str): small label above the box describing the transformation
                    (e.g. "Transforms into Form", "Condenses and Distributes")
      - label (str): content of the box (e.g. "Imam / Hawl")
    title: diagram title

    The fill gradient fades from accent (source) to bg-sunken (receiver),
    conveying the successive dilution / adaptation of the original substance.
    """
    n       = len(nodes)
    node_w  = 288
    node_h  = 52
    role_h  = 20   # height of the role label above the box
    arrow_h = 38   # space for the connecting arrow between boxes
    step_h  = role_h + node_h + arrow_h
    top_pad = 52
    vb_w    = 400
    vb_h    = top_pad + n * step_h - arrow_h + 16   # last node has no arrow below

    parts: list[str] = [_ARROWHEAD_DEF]

    # Title
    t_svg, _ = _multiline_text(vb_w / 2, 24, title, fill=_C_ACCENT, size=16,
                                 weight="600", max_chars=38, line_h=20)
    parts.append(t_svg)

    # Gradient endpoint colours (source → receiver)
    src_r, src_g, src_b = _CASCADE_TOP_RGB
    bot_r, bot_g, bot_b = _CASCADE_BOT_RGB

    cx = vb_w / 2
    nx = cx - node_w / 2

    for i, node in enumerate(nodes):
        t = i / max(n - 1, 1)
        r = int(src_r + t * (bot_r - src_r))
        g = int(src_g + t * (bot_g - src_g))
        b = int(src_b + t * (bot_b - src_b))
        fill = f"#{r:02x}{g:02x}{b:02x}"

        # Decide text colour by luminance
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        text_col = "#fffdf8" if lum < 140 else _C_INK

        y_role = top_pad + i * step_h
        y_box  = y_role + role_h

        # Role label (small, muted, above box)
        if node.get("role"):
            role_svg, _ = _multiline_text(cx, y_role + 10, node["role"],
                                           fill=_C_INK_MUTED, size=10, weight="600",
                                           max_chars=38, line_h=12)
            parts.append(role_svg)

        # Box
        stroke = _C_ACCENT if i == 0 else _C_RULE
        parts.append(_rect(nx, y_box, node_w, node_h, fill, stroke, rx=4,
                           stroke_w=1.5 if i == 0 else 1.0))
        lbl_svg, _ = _multiline_text(cx, y_box + node_h / 2, node.get("label", ""),
                                      fill=text_col, size=13, weight="600",
                                      max_chars=32, line_h=16)
        parts.append(lbl_svg)

        # Arrow to next node
        if i < n - 1:
            y_arrow_start = y_box + node_h
            y_arrow_end   = y_arrow_start + arrow_h - 10
            parts.append(
                f'<line x1="{cx:.1f}" y1="{y_arrow_start:.1f}" '
                f'x2="{cx:.1f}" y2="{y_arrow_end:.1f}" '
                f'stroke="{_C_INK_MUTED}" stroke-width="1.5" '
                f'marker-end="url(#svgp_arrow)"/>'
            )

    return _svg_wrap(
        "\n".join(parts),
        f"0 0 {vb_w} {vb_h:.0f}",
        title,
        f"Cascade chain ({n} stages): "
        + " → ".join(nd.get("label", "") for nd in nodes)
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_PATTERN_REGISTRY: dict[str, object] = {
    "concentric-layers": concentric_layers,
    "cosmic-pair":       cosmic_pair,
    "quadrant-map":      quadrant_map,
    "hierarchy-tree":    hierarchy_tree,
    "cascade-chain":     cascade_chain,
}


def render_pattern(structure_type: str, parameters: dict) -> str | None:
    """
    Entry point used by _book_illustrate.py.

    Returns the SVG string for the given structure_type + parameters dict,
    or None if the structure_type is unknown or parameters are invalid.

    Expected parameter keys per type:
      concentric-layers: {title, layers: [{label, description?}]}
      cosmic-pair:       {title, left_label, right_label, rows: [{left, right}],
                          principle? (str)}
      quadrant-map:      {title, x_axis: {label, pos_label, neg_label},
                          y_axis: {label, pos_label, neg_label},
                          quadrants: [{label, note?, impossible?}] (exactly 4)}
      hierarchy-tree:    {title, root, levels: [[str, ...]]}
      cascade-chain:     {title, nodes: [{role, label}]}
    """
    fn = _PATTERN_REGISTRY.get(structure_type)
    if fn is None:
        return None
    try:
        p = parameters
        if structure_type == "concentric-layers":
            return concentric_layers(p["layers"], p["title"])
        elif structure_type == "cosmic-pair":
            return cosmic_pair(p["rows"], p["left_label"], p["right_label"],
                               p["title"], p.get("principle", ""))
        elif structure_type == "quadrant-map":
            return quadrant_map(p["x_axis"], p["y_axis"], p["quadrants"], p["title"])
        elif structure_type == "hierarchy-tree":
            return hierarchy_tree(p["root"], p["levels"], p["title"])
        elif structure_type == "cascade-chain":
            return cascade_chain(p["nodes"], p["title"])
    except (KeyError, TypeError, ValueError):
        return None
    return None
