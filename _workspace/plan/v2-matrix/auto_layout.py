#!/usr/bin/env python3
"""--auto-layout: book/visuals/index.json -> book/visual-layout.json, non-interactively.

Automated stand-in for the Book Composer curation step during the Phase 4 v2
knob-matrix validation run. Every candidate is placed at its suggested_anchor;
placements alternate standalone-center / wrap-left / wrap-right so the render
exercises BOTH flow modes the renderer + book-render-challenger validate.
Schema: book.visual-layout/v1 (scripts/podcast/_visual_layout.py).
"""
import json
import sys
from pathlib import Path

book_dir = Path(sys.argv[1]).resolve()
idx = json.loads((book_dir / "book" / "visuals" / "index.json").read_text(encoding="utf-8"))
STYLES = [
    {"align": "center", "flow": "standalone", "width_pct": 60},
    {"align": "left", "flow": "wrap", "width_pct": 40},
    {"align": "right", "flow": "wrap", "width_pct": 40},
]
placements = [
    {"visual_id": v["id"], "anchor": v.get("suggested_anchor") or "",
     "caption": v.get("caption") or "", "page_fit": "avoid", **STYLES[i % 3]}
    for i, v in enumerate(idx.get("visuals", []))
]
out = book_dir / "book" / "visual-layout.json"
out.write_text(json.dumps({"schema": "book.visual-layout/v1", "placements": placements},
                          indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"auto-layout: {len(placements)} placement(s) -> {out}")
