#!/usr/bin/env python3
"""_book_cover.py — generated title-cover image for the reading edition.

Every book PDF gets a cover page: build_book_pdf.py renders book/cover.png
full-bleed as page one (title + author overlaid by the renderer — the image
itself must carry NO text). This module generates that image when absent,
via the same Gemini image model the video layer uses (standing Azure/Gemini
spend authorization, 2026-05-29).

Non-blocking contract: any failure (no key, network, refusal) logs a warning
and returns None — the renderer simply falls back to the typographic title
page. A human-supplied book/cover.png is always honored (never overwritten;
pass force=True to regenerate).

Standalone:
    python3 scripts/podcast/_book_cover.py <BOOK_DIR> [--force]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_STYLE = (
    "Painterly editorial book-cover art, portrait orientation 3:4. Restrained, "
    "elegant, contemplative; warm palette of deep browns, ochre, parchment cream "
    "and a touch of gold. Subtle period-appropriate architectural or natural "
    "setting with strong sense of light. Absolutely no text, no lettering, no "
    "calligraphy, no borders, no title."
)


def _read_theme(book_dir: Path) -> str:
    """One-line scene brief from the book's TOC (best effort)."""
    toc = book_dir / "book" / "book-toc.json"
    if not toc.exists():
        return ""
    try:
        data = json.loads(toc.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    title = data.get("book_title", "")
    chapters = ", ".join(c.get("title", "") for c in data.get("chapters", [])[:6])
    return (
        f"The book is titled '{title}'. Its chapters include: {chapters}. "
        f"Depict ONE quiet, emblematic scene evoking the book's heart — "
        f"figures small within the setting, never portrait close-ups."
    )


def ensure_cover(book_dir: Path, *, force: bool = False, log=print) -> Path | None:
    """Generate book/cover.png if missing. Returns the path or None."""
    book_dir = Path(book_dir).resolve()
    out = book_dir / "book" / "cover.png"
    if out.exists() and not force:
        return out
    try:
        from generate_video_layer import IMAGE_MODEL, _gemini_client
        from google.genai import types

        client, _ = _gemini_client()
        prompt = f"{_read_theme(book_dir)} {_STYLE}"
        log(f"    0book-render: generating cover.png ({IMAGE_MODEL})")
        resp = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["image", "text"]),
        )
        image_bytes = None
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                image_bytes = part.inline_data.data
                break
        if not image_bytes:
            log("    0book-render: cover generation returned no image — rendering without a cover")
            return None
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(image_bytes)
        log(f"    0book-render: wrote cover.png ({len(image_bytes) // 1024}KB)")
        return out
    except Exception as e:
        log(f"    0book-render: cover generation skipped ({e}) — rendering without a cover")
        return None


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: _book_cover.py <BOOK_DIR> [--force]", file=sys.stderr)
        return 2
    path = ensure_cover(Path(args[0]), force="--force" in sys.argv)
    return 0 if path else 1


if __name__ == "__main__":
    raise SystemExit(main())
