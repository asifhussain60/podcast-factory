"""book.visual-layout/v1 — the human-curated visual placement contract (Python side).

The Astro "Book Composer" (Phase 4) writes ``book/visual-layout.json``; the PDF
renderer (``plan-dashboard/scripts/visual-layout.mjs``) consumes it. This module
is the Python MIRROR of that JS validator — both sides must agree on the schema,
the allowed enum values, and the normalization rules, so keep them in sync in the
same commit (per the repo's TS<->Python mirror contract).

Renderer semantics the contract encodes:
  * ``flow: wrap``  -> the image floats (``align: left|right``) with body text
    flowing beside it. Requires ``width_pct <= 50`` so the text has a real column;
    a wider wrap is coerced to ``standalone`` (a too-wide float leaves a sliver of
    text and reads as broken).
  * ``flow: standalone`` -> a full-column centered block. ``align: center`` always
    implies standalone.
  * ``page_fit: avoid`` -> never split the figure across a page break (default).
    ``before`` -> start the figure on a fresh page. ``isolate-plate`` -> give the
    figure its own page (used for a tall plate that would otherwise strand text).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

SCHEMA = "book.visual-layout/v1"

ALIGNS = ("left", "center", "right")
FLOWS = ("wrap", "standalone")
PAGE_FITS = ("avoid", "before", "isolate-plate")

WRAP_MAX_WIDTH_PCT = 50  # a float must leave a real text column beside it
DEFAULT_WIDTH_PCT = 60


def normalize_placement(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return (normalized placement, warnings). Never raises on a single bad field."""
    warnings: list[str] = []
    vid = str(raw.get("visual_id") or "").strip()
    anchor = str(raw.get("anchor") or "").strip()

    align = str(raw.get("align") or "center").strip().lower()
    if align not in ALIGNS:
        warnings.append(f"{vid or '?'}: unknown align {align!r} -> center")
        align = "center"

    flow = str(raw.get("flow") or "standalone").strip().lower()
    if flow not in FLOWS:
        warnings.append(f"{vid or '?'}: unknown flow {flow!r} -> standalone")
        flow = "standalone"

    try:
        width_pct = int(raw.get("width_pct") or DEFAULT_WIDTH_PCT)
    except (TypeError, ValueError):
        width_pct = DEFAULT_WIDTH_PCT
    width_pct = max(1, min(100, width_pct))

    # align:center is centered => cannot float.
    if align == "center" and flow == "wrap":
        warnings.append(f"{vid or '?'}: align=center forces flow=standalone")
        flow = "standalone"
    # A wrap wider than the cap has no real text column -> promote to standalone.
    if flow == "wrap" and width_pct > WRAP_MAX_WIDTH_PCT:
        warnings.append(
            f"{vid or '?'}: wrap width {width_pct}%>{WRAP_MAX_WIDTH_PCT}% -> standalone"
        )
        flow = "standalone"

    page_fit = str(raw.get("page_fit") or "avoid").strip().lower()
    if page_fit not in PAGE_FITS:
        warnings.append(f"{vid or '?'}: unknown page_fit {page_fit!r} -> avoid")
        page_fit = "avoid"

    return (
        {
            "visual_id": vid,
            "anchor": anchor,
            "align": align,
            "flow": flow,
            "width_pct": width_pct,
            "caption": str(raw.get("caption") or "").strip(),
            "page_fit": page_fit,
        },
        warnings,
    )


def validate_layout(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate + normalize a whole layout. Returns (placements, warnings).

    Tolerant by design: a malformed schema header or a bad placement produces a
    warning, not an exception — a partial contract must still render.
    """
    warnings: list[str] = []
    if not isinstance(data, dict):
        return [], ["layout is not an object"]
    if data.get("schema") != SCHEMA:
        warnings.append(f"unexpected schema {data.get('schema')!r} (expected {SCHEMA})")
    placements: list[dict[str, Any]] = []
    for raw in data.get("placements") or []:
        if not isinstance(raw, dict) or not str(raw.get("visual_id") or "").strip():
            warnings.append("placement without a visual_id skipped")
            continue
        norm, w = normalize_placement(raw)
        placements.append(norm)
        warnings.extend(w)
    return placements, warnings


def load_layout(book_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Load book/visual-layout.json if present. Absent contract => ([], [])."""
    import json

    path = Path(book_dir) / "book" / "visual-layout.json"
    if not path.exists():
        return [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [], [f"visual-layout.json unreadable: {e}"]
    return validate_layout(data)
