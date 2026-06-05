#!/usr/bin/env python3
"""generate_video_layer.py — WC8.9: per-episode visual storyboard + Imagen 3 images.

For each episode, reads the enriched chapter text + framing beat structure,
calls Gemini Flash to generate 8–12 image prompts with estimated timestamps,
then calls Imagen 3 to produce the actual PNG files.

USAGE

    # Generate prompts only (no images) — dry-run to review storyboard first
    python3 scripts/podcast/generate_video_layer.py <book-slug> --prompts-only

    # Generate prompts + fast-preview images ($0.02/image)
    python3 scripts/podcast/generate_video_layer.py <book-slug> --fast-preview --confirm

    # Generate prompts + final quality images ($0.04/image)  ← DEFAULT
    python3 scripts/podcast/generate_video_layer.py <book-slug> --confirm

    # Single episode
    python3 scripts/podcast/generate_video_layer.py <book-slug> --episode EP01 --confirm

OUTPUTS PER EPISODE

    episodes/<ep>/video-prompts.json   machine-readable storyboard
    episodes/<ep>/video-prompts.md     human-readable table for review
    episodes/<ep>/video-images/        1920×1080 PNGs named NN_type_slug.png

VISUAL TYPES

    scenery       Historical Islamic setting (Nishapur, Baghdad, desert)
    quran_verse   Arabic calligraphy + phonetic overlay + English gloss
    hadith_text   Stylised text on parchment / textured background
    flowchart     Numbered-list diagram (eight benefits, four conditions)
    concept       Abstract symbolic (tawil=inner light, aql=first intellect)
    portrait      Calligraphic scholar representation

COST GUARDRAIL

    Always prints cost estimate and requires --confirm before generating images.
    Use --prompts-only to review the storyboard for free first.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _paths import content_dir  # noqa: E402
from _cost_ledger import append_gemini_cost  # noqa: E402


# ─── Constants ────────────────────────────────────────────────────────────────

WORDS_PER_MINUTE = 130          # dialogue pace (130 wpm = empirical NotebookLM baseline)
PREAMBLE_FACTOR  = 1.10         # +10% for intro music + host preamble
IMAGES_PER_EP_ESTIMATE = 10     # used for cost display only

IMAGE_MODEL         = "gemini-3.1-flash-image"   # native image gen via generate_content
IMAGE_COST_ESTIMATE = 0.04                        # approximate; actual is token-based
TEXT_MODEL          = "gemini-2.5-flash"

STYLE_DIRECTIVE = (
    "Editorial illustration style. Warm amber/ochre palette, fine-line Islamic "
    "geometric border frame. NOT photorealistic. NOT generic stock art. Scholarly "
    "aesthetic. High contrast, readable text overlays. 1920x1080 landscape."
)

VISUAL_TYPES = ("scenery", "quran_verse", "hadith_text", "flowchart", "concept", "portrait")

SYSTEM_PROMPT = f"""You are a visual storyboard writer for an Islamic scholarly podcast series.
Given an enriched chapter text and its episode framing, produce a JSON array of image segments.

Each segment is one significant arc beat in the episode. Aim for 8–12 segments per episode.
Spread across the full episode; do not cluster everything at the start.

Visual types: {", ".join(VISUAL_TYPES)}
- scenery:     historical Islamic setting — Nishapur library, Baghdad study circle, desert caravan, Kaaba courtyard
- quran_verse: a Quranic citation present in the text — calligraphic style with phonetic + English gloss overlay
- hadith_text: a hadith or prophetic saying present in the text — stylised text on parchment
- flowchart:   numbered list content (eight admonitions, four conditions, stations of the path)
- concept:     abstract idea (tawil = inner light; aql = first intellect; mujahadah = inner struggle)
- portrait:    named scholar referenced in the text — calligraphic or illustrated (NOT photorealistic)

Rules:
- quran_verse and hadith_text ONLY when the text explicitly quotes a verse or hadith — never invent.
- portrait ONLY for named scholars (Ghazali, Junaid, Hasan al-Basri etc.) — NOT anonymous figures.
- flowchart ONLY when a numbered or bulleted list exists in the source text.
- Every segment has a distinct prompt_full (≥30 words) that a generative model can act on directly.
- overlay_text: short phrase (≤10 words) to render as text overlay on the image; empty string if none.
- style_directive: always use the global style constant verbatim.
- Timestamps are estimates; first segment always est_start_s=0.

Return ONLY valid JSON — no markdown fences, no commentary outside the array.
Schema for each element:
{{
  "segment_id": "s01",
  "visual_type": "<one of the 6 types>",
  "est_start_s": <int>,
  "est_end_s": <int>,
  "prompt_short": "<≤12 word summary>",
  "prompt_full": "<detailed generative prompt ≥30 words>",
  "style_directive": "{STYLE_DIRECTIVE}",
  "overlay_text": "<≤10 words or empty string>"
}}
"""


# ─── Episode discovery ────────────────────────────────────────────────────────

def _discover_episodes(book_dir: Path) -> list[dict[str, Any]]:
    """Return list of dicts with ep_id, chapter_path, framing_path, for all episodes."""
    episodes_dir  = book_dir / "_system" / "episode-drafts"
    chapters_dir  = book_dir / "chapters"

    if not episodes_dir.exists():
        sys.exit(f"ERROR: no episode-drafts directory at {episodes_dir}")

    results = []
    for ep_dir in sorted(episodes_dir.iterdir()):
        if not ep_dir.is_dir():
            continue
        ep_id = ep_dir.name                        # e.g. EP01-knowledge-without-action
        framing = ep_dir / "00-framing.md"
        if not framing.exists():
            continue

        # Match chapter: slug after EP##- in ep_id matches slug in chapter filename
        ep_slug = re.sub(r"^EP\d+-", "", ep_id)   # "knowledge-without-action"
        chapter = None
        for ch in sorted(chapters_dir.glob("ch*.txt")):
            ch_slug = re.sub(r"^ch\d+[a-z]?-", "", ch.stem)  # strip ch##- prefix
            if ch_slug == ep_slug:
                chapter = ch
                break
        if chapter is None:
            print(f"  WARN: no chapter file found for {ep_id} (slug: {ep_slug}), skipping")
            continue
        results.append({"ep_id": ep_id, "chapter": chapter, "framing": framing})
    return results


# ─── Timestamp estimation ──────────────────────────────────────────────────────

def _estimate_total_seconds(chapter_text: str) -> int:
    words = len(chapter_text.split())
    return int((words / WORDS_PER_MINUTE) * 60 * PREAMBLE_FACTOR)


def _assign_timestamps(segments: list[dict], total_s: int) -> list[dict]:
    """Spread segments evenly across total_s when model timestamps are absent/zero."""
    if not segments:
        return segments
    slice_s = total_s // len(segments)
    for i, seg in enumerate(segments):
        if seg.get("est_start_s", 0) == 0 and i > 0:
            seg["est_start_s"] = i * slice_s
        if seg.get("est_end_s", 0) == 0:
            seg["est_end_s"] = min((i + 1) * slice_s, total_s)
    segments[0]["est_start_s"] = 0
    segments[-1]["est_end_s"]  = total_s
    return segments


# ─── Gemini prompt generation ─────────────────────────────────────────────────

def _call_gemini(chapter_text: str, framing_text: str, ep_id: str) -> list[dict]:
    from _secrets import get_gemini_key
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("ERROR: google-genai not installed. Run: pip3 install google-genai")

    api_key = get_gemini_key()
    client  = genai.Client(api_key=api_key)

    user_content = (
        f"## Episode framing\n\n{framing_text}\n\n"
        f"## Enriched chapter text\n\n{chapter_text}"
    )

    print(f"  Calling Gemini Flash for {ep_id} prompts…")
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=8192,
        ),
    )

    raw = response.text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*",     "", raw)
    raw = re.sub(r"\s*```$",     "", raw)

    try:
        segments = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: Gemini returned non-JSON for {ep_id}: {exc}\n---\n{raw[:400]}")

    if not isinstance(segments, list):
        sys.exit(f"ERROR: expected JSON array for {ep_id}, got {type(segments)}")

    return segments


# ─── Output writers ───────────────────────────────────────────────────────────

def _write_json(segments: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(segments, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(segments: list[dict], ep_id: str, out_path: Path) -> None:
    lines = [
        f"# Video storyboard — {ep_id}\n",
        "| # | Type | Start | End | Short description | Overlay |",
        "|---|---|---|---|---|---|",
    ]
    for seg in segments:
        start = f"{seg.get('est_start_s', 0)//60}:{seg.get('est_start_s', 0)%60:02d}"
        end   = f"{seg.get('est_end_s',   0)//60}:{seg.get('est_end_s',   0)%60:02d}"
        lines.append(
            f"| {seg.get('segment_id','?')} "
            f"| {seg.get('visual_type','?')} "
            f"| {start} | {end} "
            f"| {seg.get('prompt_short','?')} "
            f"| {seg.get('overlay_text','') or '—'} |"
        )
    lines.append("")
    lines.append("## Full prompts\n")
    for seg in segments:
        lines.append(f"### {seg.get('segment_id','?')} — {seg.get('visual_type','?')}")
        lines.append(f"> {seg.get('prompt_full','')}")
        lines.append(f"> *Style:* {seg.get('style_directive','')}")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ─── Imagen 3 generation ──────────────────────────────────────────────────────

def _generate_images(
    segments: list[dict],
    images_dir: Path,
    book_dir: Path,
    ep_id: str,
    fast: bool = False,  # kept for API compat; currently unused
) -> int:
    from _secrets import get_gemini_key
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("ERROR: google-genai not installed. Run: pip3 install google-genai")

    api_key = get_gemini_key()
    client  = genai.Client(api_key=api_key)
    images_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    for seg in segments:
        seg_id  = seg.get("segment_id", f"s{generated+1:02d}")
        vtype   = seg.get("visual_type", "scenery")
        ep_slug = re.sub(r"^EP\d+-", "", ep_id)[:24]
        filename = f"{seg_id}_{vtype}_{ep_slug}.jpg"   # Gemini returns JPEG
        out_path = images_dir / filename

        if out_path.exists():
            print(f"    {filename} already exists, skipping")
            continue

        prompt = f"{seg.get('prompt_full', '')}. {seg.get('style_directive', STYLE_DIRECTIVE)}"
        overlay = seg.get("overlay_text", "")
        if overlay:
            prompt += f" Text overlay reads: \"{overlay}\"."

        print(f"    Generating {filename}…", end=" ", flush=True)
        try:
            resp = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["image", "text"],
                ),
            )
            image_bytes = None
            for part in resp.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    image_bytes = part.inline_data.data
                    break
            if not image_bytes:
                print("FAILED: no image in response")
                continue
            out_path.write_bytes(image_bytes)
            print(f"saved ({len(image_bytes)//1024}KB)")
            generated += 1
            try:
                append_gemini_cost(
                    book_dir=book_dir, phase="video",
                    step=f"image/{ep_id}/{seg_id}",
                    input_tokens=0, output_tokens=0,
                    cost_usd=IMAGE_COST_ESTIMATE,
                )
            except Exception:
                pass
        except Exception as exc:
            print(f"FAILED: {exc}")

    return generated


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug",           help="Book slug, e.g. ayyuhal-walad")
    parser.add_argument("--episode",      help="Run for a single episode, e.g. EP01-knowledge-without-action")
    parser.add_argument("--prompts-only", action="store_true", help="Generate prompts but not images")
    parser.add_argument("--fast-preview", action="store_true", help="(deprecated, kept for CLI compat)")
    parser.add_argument("--confirm",      action="store_true", help="Required to trigger image generation")
    args = parser.parse_args(argv)

    book_dir = content_dir(args.slug)
    if not book_dir.exists():
        sys.exit(f"ERROR: book directory not found for slug '{args.slug}'")

    episodes = _discover_episodes(book_dir)
    if not episodes:
        sys.exit(f"ERROR: no episode pairs found in {book_dir}")

    if args.episode:
        episodes = [e for e in episodes if e["ep_id"].startswith(args.episode)]
        if not episodes:
            sys.exit(f"ERROR: --episode '{args.episode}' did not match any discovered episodes")

    total_images = len(episodes) * IMAGES_PER_EP_ESTIMATE
    est_cost     = total_images * IMAGE_COST_ESTIMATE

    print(f"\n{args.slug} video layer — {len(episodes)} episode(s)")
    print(f"  Text model:  {TEXT_MODEL} (prompts, ~$0.00)")
    print(f"  Image model: {IMAGE_MODEL} (~${IMAGE_COST_ESTIMATE}/image est.)")
    print(f"  Estimated:   ~{total_images} images ≈ ${est_cost:.2f}")

    if not args.prompts_only and not args.confirm:
        print(f"\n  Add --confirm to generate images, or --prompts-only to review storyboard first.")
        print("  Re-run with --confirm to proceed.\n")
        return 0

    for ep in episodes:
        ep_id     = ep["ep_id"]
        ch_text   = ep["chapter"].read_text(encoding="utf-8")
        fr_text   = ep["framing"].read_text(encoding="utf-8")
        total_s   = _estimate_total_seconds(ch_text)

        print(f"\n── {ep_id} ({len(ch_text.split())} words, ~{total_s//60}m estimated)")

        out_dir   = book_dir / "episodes" / ep_id
        json_path = out_dir / "video-prompts.json"
        md_path   = out_dir / "video-prompts.md"

        if json_path.exists():
            print(f"  Loading existing prompts from {json_path.name}")
            segments = json.loads(json_path.read_text(encoding="utf-8"))
        else:
            segments = _call_gemini(ch_text, fr_text, ep_id)
            segments = _assign_timestamps(segments, total_s)
            _write_json(segments, json_path)
            _write_markdown(segments, ep_id, md_path)
            print(f"  Wrote {len(segments)} segments → {json_path.relative_to(book_dir)}")
            print(f"  Wrote storyboard → {md_path.relative_to(book_dir)}")

        if args.prompts_only:
            print(f"  --prompts-only: skipping image generation for {ep_id}")
            continue

        images_dir = out_dir / "video-images"
        print(f"  Generating images → {images_dir.relative_to(book_dir)}")
        n = _generate_images(segments, images_dir, book_dir, ep_id, fast=args.fast_preview)
        print(f"  {n} image(s) generated for {ep_id}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
