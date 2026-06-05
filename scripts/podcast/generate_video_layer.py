#!/usr/bin/env python3
"""generate_video_layer.py — WC8.9: per-episode visual storyboard + image generation.

Category-aware video generation. Reads video_style from series-config.yaml
and routes to the appropriate image pipeline:

  teaching_hybrid (Islamic scholarly — default for islamic_scholarly profile)
    Gemini Flash generates a slide manifest (25–40 slides per episode).
    Imagen 3 generates 3–5 atmospheric background images.
    render_slides.py overlays Pillow text onto darkened backgrounds.
    Result: teaching slides — title cards, verse slides, numbered lists,
    concept definitions — that match the lecture structure of the episode.

  scenic (fiction / narrative — default for non-scholarly profiles)
    Gemini Flash generates 8–12 image prompts.
    Imagen 3 generates all images directly.
    Result: atmospheric scene images (current v1 approach).

  technical (deferred — auto-falls back to scenic until implemented)
    Will produce Graphviz/Mermaid diagrams for flowcharts and mind maps.

USAGE

    python3 scripts/podcast/generate_video_layer.py <book-slug> --prompts-only
    python3 scripts/podcast/generate_video_layer.py <book-slug> --confirm
    python3 scripts/podcast/generate_video_layer.py <book-slug> --episode EP01 --confirm

OUTPUTS PER EPISODE

    episodes/<ep>/video-prompts.json   machine-readable manifest (compat with stitch_video.py)
    episodes/<ep>/video-prompts.md     human-readable table
    episodes/<ep>/video-images/        1920×1080 images (PNG for slides, JPG for scenic)

COST GUARDRAIL

    Always prints estimate and requires --confirm before generating images.
    Use --prompts-only to review the manifest for free first.
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

WORDS_PER_MINUTE     = 130
PREAMBLE_FACTOR      = 1.10
IMAGES_PER_EP_SCENIC = 10     # cost estimate for scenic mode
BG_PER_EP_HYBRID     = 4      # cost estimate for teaching_hybrid backgrounds

IMAGE_MODEL         = "gemini-3.1-flash-image"
IMAGE_COST_ESTIMATE = 0.04
TEXT_MODEL          = "gemini-2.5-flash"

# ─── Scenic mode (v1 — fiction / narrative) ───────────────────────────────────

_SCENIC_STYLE = (
    "Editorial illustration style. Warm amber/ochre palette, fine-line Islamic "
    "geometric border frame. NOT photorealistic. NOT generic stock art. Scholarly "
    "aesthetic. High contrast, readable text overlays. 1920x1080 landscape."
)

_SCENIC_PROMPT = f"""You are a visual storyboard writer for a narrative/fiction podcast series.
Given an enriched chapter text and its episode framing, produce a JSON array of image segments.

Aim for 8–12 segments per episode, spread across the full episode duration.
Visual types: scenery, quran_verse, hadith_text, flowchart, concept, portrait.

Rules:
- quran_verse / hadith_text ONLY for explicitly quoted text — never invent.
- portrait ONLY for named scholars/figures.
- flowchart ONLY for explicit numbered/bulleted lists in the source.
- Every segment needs a distinct prompt_full (≥30 words).
- overlay_text: ≤10 words to render on the image, or empty string.
- style_directive: always "{_SCENIC_STYLE}".

Return ONLY valid JSON — no markdown fences.
Schema per element:
{{
  "segment_id": "s01",
  "visual_type": "<scenery|quran_verse|hadith_text|flowchart|concept|portrait>",
  "est_start_s": <int>,
  "est_end_s": <int>,
  "prompt_short": "<≤12 word summary>",
  "prompt_full": "<detailed generative prompt ≥30 words>",
  "style_directive": "{_SCENIC_STYLE}",
  "overlay_text": "<≤10 words or empty string>"
}}
"""

# ─── Teaching-hybrid mode (Islamic scholarly) ─────────────────────────────────

_HYBRID_PROMPT = """You are designing teaching slides for an Islamic scholarly podcast episode.
Given the chapter text and episode framing, produce a JSON object with two parts:

1. "backgrounds": 3–5 atmospheric scenic image prompts (for Imagen3 — these become
   darkened backgrounds behind the text slides).
2. "slides": 25–40 teaching slide definitions following the episode's narrative arc.

Background themes (choose the most atmospherically appropriate for each section):
  dawn_library        warm amber dawn on a scholarly library interior, books, lanterns
  night_study         candlelit private study, open manuscripts, deep shadows
  mosque_courtyard    quiet mosque courtyard at golden hour, arched colonnade
  desert_sunrise      vast desert at sunrise, contemplative emptiness, soft light
  calligraphy_studio  ink and parchment studio, geometric light patterns

Slide types and their content fields:
  title_slide      content: {title, subtitle}
  verse_slide      content: {text (transliteration+English), attribution, accent (e.g. "Quran 99:7")}
  hadith_slide     content: {text, attribution}
  numbered_list    content: {title, items: [str, ...]}   ← use for 8 admonitions, 4 conditions, etc.
  concept_slide    content: {term, phonetic, definition}
  quote_slide      content: {text, speaker}
  scenic_break     content: {}                            ← background only, no text

Rules for slides (read carefully — every rule prevents a real production defect):
  - Open with a title_slide.
  - Immediately follow any named list in the chapter with a numbered_list slide.
  - Use verse_slide for every Quran verse explicitly quoted in the text.
  - Use hadith_slide for every hadith explicitly quoted in the text.
  - Use concept_slide for key Arabic terms when they are defined in the text.
  - Use scenic_break for major section transitions.
  - Spread slides evenly — do not cluster everything at the start.
  - Every slide must carry est_start_s, est_end_s, overlay_text (≤10 words), prompt_short.

  HARD RULES — violations cause production defects:
  - verse_slide "text" field must contain the ENGLISH TRANSLATION only. Never put Arabic
    phonetics or transliteration in the text field. Use the attribution field for the source.
  - A recurring spine quote (the episode's thesis sentence) appears AT MOST TWICE:
    once as the second slide (s02) and once as the final slide. Never repeat it mid-episode.
  - Never place two consecutive title_slides. If you need a section header, use a
    quote_slide or scenic_break instead of another title_slide.
  - scenic_break must use the same background_id as the slides immediately surrounding it —
    never jump back to the opening background mid-episode.
  - numbered_list items: maximum 8 per slide. If a list has more than 8 items (e.g. 11
    Divine Names), split into two numbered_list slides with clear sub-titles.
  - concept_slide: one concept per slide. Never combine two concepts in a single entry
    (e.g. "Al-Malik & Al-Wahhab" is two slides). The phonetic field is required; if a term
    has no standard phonetic, leave it empty ("") but the definition must be substantive.
  - concept_slide is for established Islamic terms only — not for paraphrases of episode
    themes or narrator observations. If you cannot provide a phonetic and a concise
    definition, use a quote_slide instead.

Return ONLY valid JSON — no markdown fences, no commentary outside the object.
Top-level schema:
{
  "mode": "teaching_hybrid",
  "backgrounds": [
    {"bg_id": "bg01", "theme": "<theme>", "prompt": "<detailed Imagen3 prompt ≥30 words>"}
  ],
  "slides": [
    {
      "segment_id": "s01",
      "slide_type": "<type>",
      "background_id": "<bg_id>",
      "content": { ... },
      "est_start_s": <int>,
      "est_end_s": <int>,
      "overlay_text": "<≤10 words or empty string>",
      "prompt_short": "<≤12 word summary>"
    }
  ]
}
"""


# ─── Category routing ────────────────────────────────────────────────────────

def _is_video_enabled(book_dir: Path) -> bool:
    """Return True only when enable_video: true is set in series-config.yaml.

    Defaults to False — video generation is opt-in per book. Set
    enable_video: true in _system/series-config.yaml to enable.
    """
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return False
    try:
        import yaml
    except ImportError:
        return False
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return False
    return bool(cfg.get("enable_video", False))


def _read_video_style(book_dir: Path) -> str:
    """Read video_style from series-config.yaml.

    Returns one of: teaching_hybrid | scenic | technical.
    Falls back by content_profile when video_style is not set:
      islamic_scholarly → teaching_hybrid
      everything else   → scenic
    """
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return "scenic"
    try:
        import yaml
    except ImportError:
        return "scenic"
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return "scenic"

    if "video_style" in cfg:
        return str(cfg["video_style"]).strip().lower()

    profile = str(cfg.get("content_profile", "")).strip().lower()
    if "islamic_scholarly" in profile or "scholarly" in profile:
        return "teaching_hybrid"
    return "scenic"


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
    """Spread scenic segments evenly across total_s."""
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


def _assign_timestamps_hybrid(manifest: dict, total_s: int) -> dict:
    """Spread teaching slides evenly across total_s."""
    slides = manifest.get("slides", [])
    if not slides:
        return manifest
    slice_s = total_s // len(slides)
    for i, s in enumerate(slides):
        if s.get("est_start_s", 0) == 0 and i > 0:
            s["est_start_s"] = i * slice_s
        if s.get("est_end_s", 0) == 0:
            s["est_end_s"] = min((i + 1) * slice_s, total_s)
    slides[0]["est_start_s"] = 0
    slides[-1]["est_end_s"]  = total_s
    return manifest


# ─── Gemini helpers ───────────────────────────────────────────────────────────

def _gemini_client():
    from _secrets import get_gemini_key
    try:
        from google import genai
    except ImportError:
        sys.exit("ERROR: google-genai not installed. Run: pip3 install google-genai")
    return genai.Client(api_key=get_gemini_key()), genai


def _strip_fences(raw: str) -> str:
    raw = re.sub(r"^```json\s*", "", raw.strip())
    raw = re.sub(r"^```\s*",     "", raw)
    raw = re.sub(r"\s*```$",     "", raw)
    return raw.strip()


def _call_gemini_scenic(chapter_text: str, framing_text: str, ep_id: str) -> list[dict]:
    """Generate scenic image prompts (flat JSON array)."""
    client, genai = _gemini_client()
    from google.genai import types

    user_content = (
        f"## Episode framing\n\n{framing_text}\n\n"
        f"## Enriched chapter text\n\n{chapter_text}"
    )
    print(f"  Calling Gemini Flash for {ep_id} (scenic prompts)…")
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=_SCENIC_PROMPT,
            temperature=0.2,
            max_output_tokens=8192,
        ),
    )
    raw = _strip_fences(response.text)
    try:
        segments = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: Gemini returned non-JSON for {ep_id}: {exc}\n---\n{raw[:400]}")
    if not isinstance(segments, list):
        sys.exit(f"ERROR: expected JSON array for {ep_id}, got {type(segments)}")
    return segments


def _call_gemini_hybrid(chapter_text: str, framing_text: str, ep_id: str) -> dict:
    """Generate teaching-hybrid manifest (JSON object with backgrounds + slides)."""
    client, genai = _gemini_client()
    from google.genai import types

    user_content = (
        f"## Episode framing\n\n{framing_text}\n\n"
        f"## Enriched chapter text\n\n{chapter_text}"
    )
    print(f"  Calling Gemini Flash for {ep_id} (teaching-hybrid manifest)…")
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=_HYBRID_PROMPT,
            temperature=0.2,
            max_output_tokens=16384,
        ),
    )
    raw = _strip_fences(response.text)
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: Gemini returned non-JSON for {ep_id}: {exc}\n---\n{raw[:400]}")
    if not isinstance(manifest, dict):
        sys.exit(f"ERROR: expected JSON object for {ep_id}, got {type(manifest)}")
    return manifest


# ─── Output writers ───────────────────────────────────────────────────────────

def _write_json(data: Any, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown_scenic(segments: list[dict], ep_id: str, out_path: Path) -> None:
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
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown_hybrid(manifest: dict, ep_id: str, out_path: Path) -> None:
    slides = manifest.get("slides", [])
    bgs    = {b["bg_id"]: b["theme"] for b in manifest.get("backgrounds", [])}
    lines  = [
        f"# Teaching slides — {ep_id}\n",
        "| # | Type | Background | Start | End | Content summary | Overlay |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in slides:
        start   = f"{s.get('est_start_s',0)//60}:{s.get('est_start_s',0)%60:02d}"
        end     = f"{s.get('est_end_s',0)//60}:{s.get('est_end_s',0)%60:02d}"
        bg_name = bgs.get(s.get("background_id",""), "?")
        summary = s.get("prompt_short","?")[:40]
        lines.append(
            f"| {s.get('segment_id','?')} "
            f"| {s.get('slide_type','?')} "
            f"| {bg_name} "
            f"| {start} | {end} "
            f"| {summary} "
            f"| {s.get('overlay_text','') or '—'} |"
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ─── Imagen 3 generation ──────────────────────────────────────────────────────

def _generate_background_images(
    manifest: dict,
    images_dir: Path,
    book_dir: Path,
    ep_id: str,
) -> int:
    """Generate the 3–5 Imagen3 background images for a teaching_hybrid episode."""
    client, genai = _gemini_client()
    from google.genai import types

    images_dir.mkdir(parents=True, exist_ok=True)
    generated = 0

    for bg in manifest.get("backgrounds", []):
        bg_id    = bg.get("bg_id", f"bg{generated+1:02d}")
        filename = f"{bg_id}_{bg.get('theme','bg')}.jpg"
        out_path = images_dir / filename

        # Update the manifest so render_slides.py can find this file
        bg["image_path"] = filename

        if out_path.exists():
            print(f"    {filename} already exists, skipping")
            generated += 1
            continue

        # Add darkening intent to the prompt — the image will be darkened 68%
        # by render_slides.py; ask for a slightly brighter source to survive it.
        prompt = (
            f"{bg.get('prompt', '')} "
            "Painterly editorial style. Warm amber/ochre palette. Atmospheric depth. "
            "No text or lettering. 1920x1080 landscape."
        )

        print(f"    Generating background {filename}…", end=" ", flush=True)
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
                    step=f"bg/{ep_id}/{bg_id}",
                    input_tokens=0, output_tokens=0,
                    cost_usd=IMAGE_COST_ESTIMATE,
                )
            except Exception:
                pass
        except Exception as exc:
            print(f"FAILED: {exc}")

    return generated


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
    parser.add_argument("--episode",      help="Run for a single episode, e.g. EP01")
    parser.add_argument("--prompts-only", action="store_true", help="Generate manifests but not images")
    parser.add_argument("--fast-preview", action="store_true", help="(deprecated, kept for CLI compat)")
    parser.add_argument("--confirm",      action="store_true", help="Required to trigger image generation")
    args = parser.parse_args(argv)

    book_dir = content_dir(args.slug)
    if not book_dir.exists():
        sys.exit(f"ERROR: book directory not found for slug '{args.slug}'")

    if not _is_video_enabled(book_dir):
        print(f"\nVideo generation is disabled for '{args.slug}'.")
        print(f"  To enable: set  enable_video: true  in _system/series-config.yaml")
        return 0

    video_style = _read_video_style(book_dir)

    episodes = _discover_episodes(book_dir)
    if not episodes:
        sys.exit(f"ERROR: no episode pairs found in {book_dir}")

    if args.episode:
        episodes = [e for e in episodes if e["ep_id"].startswith(args.episode)]
        if not episodes:
            sys.exit(f"ERROR: --episode '{args.episode}' did not match any discovered episodes")

    if video_style == "teaching_hybrid":
        est_images = len(episodes) * BG_PER_EP_HYBRID
        mode_label = "teaching_hybrid (Pillow slides + Imagen3 backgrounds)"
    else:
        est_images = len(episodes) * IMAGES_PER_EP_SCENIC
        mode_label = f"{video_style} (Imagen3 scenic)"

    est_cost = est_images * IMAGE_COST_ESTIMATE
    print(f"\n{args.slug} video layer — {len(episodes)} episode(s)")
    print(f"  Mode:        {mode_label}")
    print(f"  Text model:  {TEXT_MODEL}")
    print(f"  Image model: {IMAGE_MODEL} (~${IMAGE_COST_ESTIMATE}/image)")
    print(f"  Estimated:   ~{est_images} Imagen3 images ≈ ${est_cost:.2f}")

    if not args.prompts_only and not args.confirm:
        print(f"\n  Add --confirm to generate images, or --prompts-only to review manifest first.")
        print("  Re-run with --confirm to proceed.\n")
        return 0

    for ep in episodes:
        ep_id   = ep["ep_id"]
        ch_text = ep["chapter"].read_text(encoding="utf-8")
        fr_text = ep["framing"].read_text(encoding="utf-8")
        total_s = _estimate_total_seconds(ch_text)

        print(f"\n── {ep_id} ({len(ch_text.split())} words, ~{total_s//60}m estimated)")

        out_dir   = book_dir / "episodes" / ep_id
        json_path = out_dir / "video-prompts.json"
        md_path   = out_dir / "video-prompts.md"
        images_dir = out_dir / "video-images"

        # ── Teaching-hybrid path ──────────────────────────────────────────────
        if video_style == "teaching_hybrid":
            if json_path.exists():
                print(f"  Loading existing manifest from {json_path.name}")
                manifest = json.loads(json_path.read_text(encoding="utf-8"))
                # Re-detect mode in case this is an old scenic manifest
                if not isinstance(manifest, dict) or manifest.get("mode") != "teaching_hybrid":
                    print(f"  WARN: existing manifest is not teaching_hybrid — regenerating")
                    json_path.unlink(missing_ok=True)
                    manifest = None
            else:
                manifest = None

            if manifest is None:
                manifest = _call_gemini_hybrid(ch_text, fr_text, ep_id)
                manifest = _assign_timestamps_hybrid(manifest, total_s)
                _write_json(manifest, json_path)
                _write_markdown_hybrid(manifest, ep_id, md_path)
                slides = manifest.get("slides", [])
                bgs    = manifest.get("backgrounds", [])
                print(f"  Wrote {len(slides)} slides + {len(bgs)} backgrounds → {json_path.relative_to(book_dir)}")

            if args.prompts_only:
                slides = manifest.get("slides", [])
                print(f"  --prompts-only: {len(slides)} slides defined, skipping image generation")
                continue

            # Generate background images
            bgs = manifest.get("backgrounds", [])
            print(f"  Generating {len(bgs)} background image(s)…")
            n_bg = _generate_background_images(manifest, images_dir, book_dir, ep_id)
            # Re-save manifest with updated image_path fields
            _write_json(manifest, json_path)

            # Render teaching slides via Pillow
            from render_slides import render_all_slides
            slides = manifest.get("slides", [])
            print(f"  Rendering {len(slides)} teaching slide(s)…")
            n_slides = render_all_slides(manifest, images_dir, ep_id)
            print(f"  {n_bg} background(s) + {n_slides} slide(s) generated for {ep_id}")

        # ── Scenic path (fiction / fallback) ──────────────────────────────────
        else:
            if json_path.exists():
                print(f"  Loading existing prompts from {json_path.name}")
                raw = json.loads(json_path.read_text(encoding="utf-8"))
                # Handle old dict manifests (teaching_hybrid written to scenic path)
                segments = raw if isinstance(raw, list) else raw.get("slides", [])
            else:
                segments = _call_gemini_scenic(ch_text, fr_text, ep_id)
                segments = _assign_timestamps(segments, total_s)
                _write_json(segments, json_path)
                _write_markdown_scenic(segments, ep_id, md_path)
                print(f"  Wrote {len(segments)} segments → {json_path.relative_to(book_dir)}")

            if args.prompts_only:
                print(f"  --prompts-only: {len(segments)} segments, skipping image generation")
                continue

            print(f"  Generating {len(segments)} scenic image(s)…")
            n = _generate_images(segments, images_dir, book_dir, ep_id)
            print(f"  {n} image(s) generated for {ep_id}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
