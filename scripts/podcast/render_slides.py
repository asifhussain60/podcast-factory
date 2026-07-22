#!/usr/bin/env python3
"""render_slides.py — Pillow-based teaching-slide renderer for Islamic scholarly content.

Renders 1920×1080 PNG slides in teaching_hybrid style:
  - Scenic Imagen3 background darkened to ~30% opacity (or solid navy fallback)
  - Text content overlaid using the Islamic teaching palette
  - Slide types: title, verse, hadith, numbered_list, concept, quote, scenic_break

PALETTE
    Background solid : #1a1a2e  (deep navy)
    Overlay alpha    : 175      (68% opacity black over image)
    Heading text     : #d4af37  (gold)
    Body text        : #f4e4c1  (cream)
    Accent line      : #d4af37  (gold, 4px)
    Dim text         : #a09070  (muted cream for attributions)

USAGE (module)
    from render_slides import render_all_slides
    n = render_all_slides(manifest, backgrounds_dir, output_dir)

USAGE (CLI — for single slide debugging)
    python3 scripts/podcast/render_slides.py <manifest.json> <output_dir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("ERROR: Pillow not installed. Run: pip3 install Pillow")

# ─── Palette ──────────────────────────────────────────────────────────────────

W, H = 1920, 1080
MARGIN = 120  # safe-area margin on each side
SAFE_W = W - 2 * MARGIN
SAFE_H = H - 2 * MARGIN

COL_BG = (26, 26, 46)  # #1a1a2e navy
COL_OVERLAY = (0, 0, 0, 175)  # 68% black overlay over image
COL_GOLD = (212, 175, 55)  # #d4af37
COL_CREAM = (244, 228, 193)  # #f4e4c1
COL_DIM = (160, 144, 112)  # muted cream for attributions
COL_ACCENT_H = 4  # accent-bar height (px)

# ─── Fonts ────────────────────────────────────────────────────────────────────


def _find_font(names: list[str], size: int) -> "ImageFont.FreeTypeFont":
    """Try multiple font names across macOS font directories; fall back to default."""
    dirs = [
        "/Library/Fonts",
        "/System/Library/Fonts",
        "/System/Library/Fonts/Supplemental",
        "/usr/share/fonts/truetype",
        "/usr/share/fonts",
    ]
    for name in names:
        for d in dirs:
            for ext in (".ttf", ".ttc", ".otf"):
                p = Path(d) / f"{name}{ext}"
                if p.exists():
                    try:
                        return ImageFont.truetype(str(p), size)
                    except Exception:
                        continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _fonts(scale: float = 1.0) -> dict[str, "ImageFont.FreeTypeFont"]:
    """Return the font set scaled by `scale` (1.0 = default, 0.8 = smaller)."""
    s = scale
    return {
        "heading_lg": _find_font(
            ["HelveticaNeue-Bold", "Helvetica-Bold", "Arial-BoldMT", "DejaVuSans-Bold"], int(72 * s)
        ),
        "heading_md": _find_font(
            ["HelveticaNeue-Bold", "Helvetica-Bold", "Arial-BoldMT", "DejaVuSans-Bold"], int(54 * s)
        ),
        "heading_sm": _find_font(["HelveticaNeue-Medium", "Helvetica", "ArialMT", "DejaVuSans"], int(40 * s)),
        "body": _find_font(["HelveticaNeue", "Helvetica", "ArialMT", "DejaVuSans"], int(36 * s)),
        "body_sm": _find_font(["HelveticaNeue", "Helvetica", "ArialMT", "DejaVuSans"], int(28 * s)),
        "italic": _find_font(
            ["HelveticaNeue-Italic", "Helvetica-Oblique", "Arial-ItalicMT", "DejaVuSans-Oblique"], int(34 * s)
        ),
        "dim": _find_font(["HelveticaNeue", "Helvetica", "ArialMT", "DejaVuSans"], int(26 * s)),
    }


# ─── Text helpers ─────────────────────────────────────────────────────────────


def _wrap(text: str, font: "ImageFont.FreeTypeFont", max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Break `text` into lines that fit within `max_w` pixels."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _text_block_height(
    lines: list[str], font: "ImageFont.FreeTypeFont", draw: ImageDraw.ImageDraw, line_gap: int = 8
) -> int:
    total = 0
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        total += (bbox[3] - bbox[1]) + line_gap
    return max(0, total - line_gap)


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: "ImageFont.FreeTypeFont",
    color: tuple,
    x: int,
    y: int,
    line_gap: int = 8,
    align: str = "left",
) -> int:
    """Draw wrapped lines starting at (x, y). Returns final y position."""
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        dx = 0
        if align == "center":
            dx = (SAFE_W - w) // 2
        elif align == "right":
            dx = SAFE_W - w
        draw.text((x + dx, y), ln, font=font, fill=color)
        y += h + line_gap
    return y


def _accent_bar(draw: ImageDraw.ImageDraw, y: int, width: int = 80) -> None:
    """Draw a short gold accent bar at the safe-area left margin."""
    draw.rectangle([MARGIN, y, MARGIN + width, y + COL_ACCENT_H], fill=COL_GOLD)


# ─── Background composer ──────────────────────────────────────────────────────


def _make_base(bg_path: Path | None) -> Image.Image:
    """Return 1920×1080 RGBA base: darkened scenic image or solid navy."""
    if bg_path and bg_path.exists():
        try:
            img = Image.open(bg_path).convert("RGBA").resize((W, H), Image.LANCZOS)
            overlay = Image.new("RGBA", (W, H), COL_OVERLAY)
            return Image.alpha_composite(img, overlay)
        except Exception:
            pass
    base = Image.new("RGBA", (W, H), (*COL_BG, 255))
    return base


# ─── Slide renderers ──────────────────────────────────────────────────────────


def _render_title_slide(draw: ImageDraw.ImageDraw, content: dict, fonts: dict) -> None:
    title = content.get("title", "")
    subtitle = content.get("subtitle", "")

    title_lines = _wrap(title.upper(), fonts["heading_lg"], SAFE_W, draw)
    sub_lines = _wrap(subtitle, fonts["body"], SAFE_W, draw) if subtitle else []

    title_h = _text_block_height(title_lines, fonts["heading_lg"], draw, line_gap=12)
    sub_h = _text_block_height(sub_lines, fonts["body"], draw, line_gap=10) if sub_lines else 0
    gap = 32 if sub_lines else 0
    bar_h = COL_ACCENT_H + 16

    total_h = title_h + bar_h + gap + sub_h
    y_start = (H - total_h) // 2

    y = _draw_lines(draw, title_lines, fonts["heading_lg"], COL_GOLD, MARGIN, y_start, line_gap=12, align="center")
    _accent_bar(draw, y + 16, width=120)
    y += bar_h + gap
    if sub_lines:
        _draw_lines(draw, sub_lines, fonts["body"], COL_CREAM, MARGIN, y, line_gap=10, align="center")


def _render_verse_slide(draw: ImageDraw.ImageDraw, content: dict, fonts: dict) -> None:
    text = content.get("text", "")
    attribution = content.get("attribution", "")
    accent = content.get("accent", "")  # e.g. "Quran 99:7"

    if accent:
        draw.text((MARGIN, MARGIN), accent.upper(), font=fonts["dim"], fill=COL_GOLD)

    verse_lines = _wrap(f"“{text}”", fonts["heading_sm"], SAFE_W, draw)
    attr_lines = _wrap(attribution, fonts["dim"], SAFE_W, draw) if attribution else []

    verse_h = _text_block_height(verse_lines, fonts["heading_sm"], draw, line_gap=14)
    attr_h = _text_block_height(attr_lines, fonts["dim"], draw, line_gap=8) + 20

    total_h = verse_h + attr_h
    y = max(MARGIN + 60, (H - total_h) // 2)

    y = _draw_lines(draw, verse_lines, fonts["heading_sm"], COL_CREAM, MARGIN, y, line_gap=14, align="center")
    _accent_bar(draw, y + 12, width=60)
    y += COL_ACCENT_H + 20
    if attr_lines:
        _draw_lines(draw, attr_lines, fonts["dim"], COL_DIM, MARGIN, y, align="center")


def _render_hadith_slide(draw: ImageDraw.ImageDraw, content: dict, fonts: dict) -> None:
    text = content.get("text", "")
    attribution = content.get("attribution", "")

    draw.text((MARGIN, MARGIN), "PROPHETIC SAYING", font=fonts["dim"], fill=COL_GOLD)

    hadith_lines = _wrap(f"“{text}”", fonts["italic"], SAFE_W, draw)
    attr_lines = _wrap(f"— {attribution}", fonts["dim"], SAFE_W, draw) if attribution else []

    hadith_h = _text_block_height(hadith_lines, fonts["italic"], draw, line_gap=14)
    attr_h = _text_block_height(attr_lines, fonts["dim"], draw, line_gap=8) + 20

    total_h = hadith_h + attr_h
    y = max(MARGIN + 60, (H - total_h) // 2)

    y = _draw_lines(draw, hadith_lines, fonts["italic"], COL_CREAM, MARGIN, y, line_gap=14, align="center")
    y += 20
    if attr_lines:
        _draw_lines(draw, attr_lines, fonts["dim"], COL_DIM, MARGIN, y, align="center")


def _render_numbered_list(draw: ImageDraw.ImageDraw, content: dict, fonts: dict) -> None:
    title = content.get("title", "")
    items = content.get("items", [])

    # Scale down fonts if many items
    scale = 0.75 if len(items) > 6 else 1.0
    f = _fonts(scale)

    y = MARGIN
    if title:
        title_lines = _wrap(title.upper(), f["heading_md"], SAFE_W, draw)
        y = _draw_lines(draw, title_lines, f["heading_md"], COL_GOLD, MARGIN, y, line_gap=10)
        _accent_bar(draw, y + 8, width=80)
        y += COL_ACCENT_H + 28

    for i, item in enumerate(items, 1):
        num_str = f"{i}."
        num_bbox = draw.textbbox((0, 0), num_str, font=f["body"])
        num_w = num_bbox[2] - num_bbox[0] + 16
        item_lines = _wrap(item, f["body"], SAFE_W - num_w, draw)

        draw.text((MARGIN, y), num_str, font=f["body"], fill=COL_GOLD)
        y0 = y
        for ln in item_lines:
            bbox = draw.textbbox((0, 0), ln, font=f["body"])
            draw.text((MARGIN + num_w, y), ln, font=f["body"], fill=COL_CREAM)
            y += (bbox[3] - bbox[1]) + 6
        _ = y0  # suppress unused warning
        y += 10  # extra gap between items


def _render_concept_slide(draw: ImageDraw.ImageDraw, content: dict, fonts: dict) -> None:
    term = content.get("term", "")
    phonetic = content.get("phonetic", "")
    definition = content.get("definition", "")

    y = MARGIN + 80

    # Term (large gold) + phonetic (cream, smaller)
    term_lines = _wrap(term.upper(), fonts["heading_lg"], SAFE_W, draw)
    y = _draw_lines(draw, term_lines, fonts["heading_lg"], COL_GOLD, MARGIN, y, line_gap=10, align="center")

    if phonetic:
        ph_lines = _wrap(f"({phonetic})", fonts["body_sm"], SAFE_W, draw)
        y = _draw_lines(draw, ph_lines, fonts["body_sm"], COL_DIM, MARGIN, y + 4, line_gap=8, align="center")

    _accent_bar(draw, y + 16, width=80)
    y += COL_ACCENT_H + 32

    if definition:
        def_lines = _wrap(definition, fonts["body"], SAFE_W, draw)
        _draw_lines(draw, def_lines, fonts["body"], COL_CREAM, MARGIN, y, line_gap=12, align="center")


def _render_quote_slide(draw: ImageDraw.ImageDraw, content: dict, fonts: dict) -> None:
    text = content.get("text", "")
    speaker = content.get("speaker", "")

    q_lines = _wrap(f"“{text}”", fonts["heading_sm"], SAFE_W, draw)
    sp_lines = _wrap(f"— {speaker}", fonts["dim"], SAFE_W, draw) if speaker else []

    q_h = _text_block_height(q_lines, fonts["heading_sm"], draw, line_gap=14)
    sp_h = _text_block_height(sp_lines, fonts["dim"], draw, line_gap=8) + 24

    y = max(MARGIN, (H - q_h - sp_h) // 2)
    y = _draw_lines(draw, q_lines, fonts["heading_sm"], COL_CREAM, MARGIN, y, line_gap=14, align="center")
    y += 24
    if sp_lines:
        _draw_lines(draw, sp_lines, fonts["dim"], COL_DIM, MARGIN, y, align="center")


# ─── Dispatch ─────────────────────────────────────────────────────────────────

_RENDERERS = {
    "title_slide": _render_title_slide,
    "verse_slide": _render_verse_slide,
    "hadith_slide": _render_hadith_slide,
    "numbered_list": _render_numbered_list,
    "concept_slide": _render_concept_slide,
    "quote_slide": _render_quote_slide,
    "scenic_break": None,  # background only — no text
}


def render_slide(slide: dict, bg_path: Path | None, output_path: Path) -> None:
    """Render one slide to output_path as a 1920×1080 PNG."""
    slide_type = slide.get("slide_type", "scenic_break")
    content = slide.get("content", {})

    base = _make_base(bg_path)
    image = base.convert("RGB")  # drop alpha before drawing opaque text
    draw = ImageDraw.Draw(image)
    fonts = _fonts()

    renderer = _RENDERERS.get(slide_type)
    if renderer is not None:
        renderer(draw, content, fonts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(output_path), "PNG", optimize=False)


def render_all_slides(
    manifest: dict,
    images_dir: Path,
    ep_id: str,
) -> int:
    """Render all slides in the manifest.  Returns count of slides rendered.

    manifest  — the dict loaded from video-prompts.json (teaching_hybrid schema)
    images_dir — where to write s01_*.png … sNN_*.png
    ep_id      — for naming / logging
    """
    backgrounds = {
        b["bg_id"]: images_dir / b.get("image_path", f"{b['bg_id']}.jpg") for b in manifest.get("backgrounds", [])
    }

    slides = manifest.get("slides", [])
    if not slides:
        print(f"  WARN: no slides in manifest for {ep_id}")
        return 0

    ep_slug = ep_id.split("-", 1)[1] if "-" in ep_id else ep_id
    n = 0
    for slide in slides:
        seg_id = slide.get("segment_id", f"s{n + 1:02d}")
        slide_type = slide.get("slide_type", "scenic_break")
        bg_id = slide.get("background_id", "bg01")
        bg_path = backgrounds.get(bg_id)

        filename = f"{seg_id}_{slide_type}_{ep_slug[:24]}.png"
        out_path = images_dir / filename

        if out_path.exists():
            print(f"    {filename} already exists, skipping")
            n += 1
            continue

        try:
            render_slide(slide, bg_path, out_path)
            print(f"    rendered {filename}")
            n += 1
        except Exception as exc:
            print(f"    FAILED {filename}: {exc}")

    return n


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifest", help="Path to video-prompts.json")
    parser.add_argument("output_dir", help="Directory to write PNG slides")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        sys.exit(f"ERROR: manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    images_dir = Path(args.output_dir)

    ep_id = manifest_path.parent.name
    n = render_all_slides(manifest, images_dir, ep_id)
    print(f"\nRendered {n} slide(s) → {images_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
