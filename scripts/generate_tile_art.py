#!/usr/bin/env python3
"""generate_tile_art.py — the watercolour painting behind a chooser tile.

The Podcast Factory Library's home page is a row of tiles, one per collection,
each carrying an abstract watercolour held well back behind frosted glass. The
first two were generated in a session on 2026-08-29 and committed as finished
files with no record of how; the third needed one, and a third painting made by
a route nobody can repeat is how the fourth becomes impossible. So the recipe
lives here.

WHAT MAKES THE THREE A SET, and what has to differ:

  SAME  Loose abstract watercolour on warm cream paper. Ivory ground, wet edges,
        visible paper grain, a thread of ochre running through every one. The
        composition is weighted to the RIGHT and left almost empty on the LEFT —
        the tile prints its words over that empty half, and `background-position:
        top right` is what keeps the paint out of them.

  DIFFER  The motif and the hue, and the motif carries the meaning:
        books      navy + ochre, VERTICAL strokes fanning out — a book's
                   fore-edge, the stacked pages seen end-on.
        sessions   plum + gold, CONCENTRIC ARCS radiating — sound leaving a
                   voice.
        audiobooks teal + ochre, HORIZONTAL RULED BANDS dissolving into ripples
                   — the page becoming a waveform, which is exactly what an
                   audiobook is. Distinct from both at a glance rather than only
                   from one, the same test the teal accent had to pass.

COSTS REAL MONEY — one Gemini image per run, about four cents. It refuses to
overwrite an existing painting without `--force`, because the two committed ones
are the set this has to match and regenerating them casually would drift it.

    python3 scripts/generate_tile_art.py audiobooks
    python3 scripts/generate_tile_art.py audiobooks --force
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

OUT_DIR = REPO / "listener" / "public" / "brand"
SIZE = (1600, 1000)
MODEL = "gemini-3.1-flash-image"

#: The shared half of every prompt. Written once so a new tile cannot quietly be
#: painted in a different medium from the two it sits beside.
COMMON = (
    "A loose abstract watercolour painting on warm cream paper, in the style of "
    "a fine-art editorial book cover. Visible paper grain and soft wet bleeding "
    "edges. The LEFT HALF of the image is almost entirely empty ivory paper with "
    "only the faintest wash; all of the colour and movement is gathered in the "
    "RIGHT HALF and toward the top right corner. Muted, restrained, elegant. A "
    "thread of soft ochre runs through the pigment. No text, no lettering, no "
    "figures, no objects, no recognisable subject — pure abstract brushwork."
)

MOTIFS: dict[str, str] = {
    "books": (
        "Long vertical brushstrokes in deep navy blue and ochre, fanning outward "
        "toward the upper right like the stacked page edges of a thick book seen "
        "end-on."
    ),
    "sessions": (
        "Concentric sweeping arcs in dusty plum, violet and warm gold, radiating "
        "outward from the upper right like sound leaving a voice."
    ),
    "audiobooks": (
        "Horizontal ruled bands in deep teal and soft ochre, evenly spaced like "
        "the lines of a printed page on the left, then loosening and dissolving "
        "toward the right into rippling waveform curves — a page becoming sound. "
        "The teal is the dominant pigment, deep and slightly blue-green, never "
        "emerald and never navy."
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("collection", choices=sorted(MOTIFS))
    ap.add_argument("--force", action="store_true", help="repaint an existing tile")
    args = ap.parse_args()

    out = OUT_DIR / f"tile-{args.collection}.webp"
    if out.exists() and not args.force:
        print(f"{out.name} already exists — pass --force to repaint it", file=sys.stderr)
        return 1

    from _secrets import get_gemini_key

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("ERROR: google-genai not installed. Run: pip3 install google-genai")

    prompt = f"{COMMON} {MOTIFS[args.collection]}"
    print(f"  painting {out.name} — one image, about $0.04")

    client = genai.Client(api_key=get_gemini_key())
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["image", "text"]),
    )

    data = None
    for part in resp.candidates[0].content.parts:
        inline = getattr(part, "inline_data", None)
        if inline is not None and inline.data:
            data = inline.data
            break
    if data is None:
        print("no image came back", file=sys.stderr)
        return 1

    from PIL import Image

    # Cropped to the tiles' own 1600x1000 rather than scaled: the model returns
    # whatever aspect it likes, and squashing a watercolour changes the shape of
    # every brushstroke in it. The crop keeps the top-right weighting the layout
    # depends on.
    img = Image.open(io.BytesIO(data)).convert("RGB")
    target = SIZE[0] / SIZE[1]
    w, h = img.size
    if w / h > target:
        new_w = int(h * target)
        img = img.crop((w - new_w, 0, w, h))
    else:
        new_h = int(w / target)
        img = img.crop((0, 0, w, new_h))
    img = img.resize(SIZE, Image.LANCZOS)
    img.save(out, "WEBP", quality=88, method=6)
    print(f"  wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
