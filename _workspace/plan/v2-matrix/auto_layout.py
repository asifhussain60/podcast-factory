#!/usr/bin/env python3
"""--auto-layout: book/visuals/index.json -> book/visual-layout.json, non-interactively.

Automated stand-in for the Book Composer curation step during the Phase 4 v2
knob-matrix validation run (schema: book.visual-layout/v1, see
scripts/podcast/_visual_layout.py and plan-dashboard/scripts/visual-layout.mjs).

The renderer resolves ``anchor`` against chapter <h2> headings and inserts the
figure AFTER the ``anchor_para``-th <p> of that chapter — so each candidate's
free-text ``suggested_anchor`` snippet must be resolved here to (chapter title,
paragraph index). Unresolvable/empty anchors round-robin across chapters at the
default position (after the intro paragraph). Placement styles alternate
standalone-center / wrap-left / wrap-right so both render flows get exercised.
"""
import json
import re
import sys
from pathlib import Path

book_dir = Path(sys.argv[1]).resolve()
idx = json.loads((book_dir / "book" / "visuals" / "index.json").read_text(encoding="utf-8"))
book_md = (book_dir / "book" / "book.md").read_text(encoding="utf-8")

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\"'‘’“”*_`]", "", s)).strip().lower()

# chapters: [(title, [normalized plain paragraphs])] — count only blocks the
# markdown renderer turns into <p> (skip headings/quotes/lists/tables/fences).
chapters: list[tuple[str, list[str]]] = []
for chunk in re.split(r"(?m)^## +", book_md)[1:]:
    lines = chunk.split("\n")
    title = lines[0].strip()
    paras = [norm(b) for b in re.split(r"\n\s*\n", "\n".join(lines[1:]))
             if b.strip() and not re.match(r"^\s*(#|>|[-*]\s|\d+\.\s|\||```)", b)]
    chapters.append((title, paras))

def resolve(snippet: str, i: int) -> tuple[str, int | None, bool]:
    target = norm(snippet)
    if target and chapters:
        for title, paras in chapters:
            for p_i, para in enumerate(paras, start=1):
                if target in para:
                    return title, p_i, True    # after the paragraph containing it
        # fuzzy: best word-overlap paragraph (deck narration ≠ book prose verbatim)
        words = {w for w in target.split() if len(w) > 3}
        best = (0.0, "", None)
        if words:
            for title, paras in chapters:
                for p_i, para in enumerate(paras, start=1):
                    pw = set(para.split())
                    score = len(words & pw) / len(words)
                    if score > best[0]:
                        best = (score, title, p_i)
        if best[0] >= 0.5:
            return best[1], best[2], True
    if chapters:                               # fallback: spread across chapters
        return chapters[i % len(chapters)][0], None, False
    return "", None, False

STYLES = [
    {"align": "center", "flow": "standalone", "width_pct": 60},
    {"align": "left", "flow": "wrap", "width_pct": 40},
    {"align": "right", "flow": "wrap", "width_pct": 40},
]
placements = []
resolved = 0
for i, v in enumerate(idx.get("visuals", [])):
    anchor, para, hit = resolve(v.get("suggested_anchor") or "", i)
    resolved += 1 if hit else 0
    placements.append({"visual_id": v["id"], "anchor": anchor, "anchor_para": para,
                       "caption": v.get("caption") or "", "page_fit": "avoid",
                       **STYLES[i % 3]})
out = book_dir / "book" / "visual-layout.json"
out.write_text(json.dumps({"schema": "book.visual-layout/v1", "placements": placements},
                          indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"auto-layout: {len(placements)} placement(s) ({resolved} snippet-resolved, "
      f"{len(placements) - resolved} round-robin) -> {out}")
