#!/usr/bin/env python3
"""composer_visual.py — on-demand visual-artifact ops for the Book Composer.

Two actions the Astro Book Composer spawns (via /api/studio/visual-op):

  generate  Create ONE raster artifact from a text description, OR edit an existing
            artifact (image + description -> new image), via Gemini's image model.
            Writes book/visuals/<id>.png and registers it in book/visuals/index.json.

  delete    Remove ONE artifact: drop its index entry and unlink its file.

Reuses the candidate-library writer (`_visual_candidates`) and the Gemini key
resolver (`_secrets.get_gemini_key`, Azure Key Vault — run `az login`). Prints a
single JSON line to stdout: {"ok": true, ...} or {"ok": false, "error": ...}.

Batch pipeline image generation still lives in generate_video_layer.py; this is the
single-image, human-in-the-loop path.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
import sys
from pathlib import Path

from _visual_candidates import index_path, load_index, merge_entries, visuals_dir, write_index

IMAGE_MODEL = "gemini-3.1-flash-image"


def _fail(msg: str) -> int:
    print(json.dumps({"ok": False, "error": msg}))
    return 1


def _gemini_client():
    from _secrets import get_gemini_key

    try:
        from google import genai
    except ImportError:
        raise RuntimeError("google-genai not installed. Run: pip3 install google-genai")
    return genai.Client(api_key=get_gemini_key()), genai


def _next_id(visuals: list[dict]) -> str:
    n = 0
    for v in visuals:
        vid = str(v.get("id", ""))
        if vid.startswith("gen-"):
            try:
                n = max(n, int(vid[4:]))
            except ValueError:
                pass
    return f"gen-{n + 1}"


def _extract_image_bytes(resp) -> bytes | None:
    for part in resp.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            return part.inline_data.data
    return None


def do_generate(book_dir: Path, prompt: str, from_file: str | None, anchor: str) -> int:
    prompt = (prompt or "").strip()
    if not prompt:
        return _fail("empty prompt")

    client, _ = _gemini_client()
    from google.genai import types

    contents: object
    if from_file:
        src = visuals_dir(book_dir) / Path(from_file).name
        if not src.exists():
            return _fail(f"base image not found: {from_file}")
        mime = mimetypes.guess_type(src.name)[0] or "image/png"
        edit_instruction = (
            "Edit the supplied image according to this instruction, keeping its subject "
            f"and composition unless the instruction says otherwise: {prompt}"
        )
        contents = [types.Part.from_bytes(data=src.read_bytes(), mime_type=mime), edit_instruction]
    else:
        contents = f"{prompt}\n\nClean editorial illustration. No watermark, no lettering unless requested."

    try:
        resp = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["image", "text"]),
        )
    except Exception as e:
        return _fail(f"Gemini request failed: {e}")

    image_bytes = _extract_image_bytes(resp)
    if not image_bytes:
        return _fail("no image returned by the model")

    visuals = load_index(book_dir)
    vid = _next_id(visuals)
    fname = f"{vid}.png"
    (visuals_dir(book_dir)).mkdir(parents=True, exist_ok=True)
    (visuals_dir(book_dir) / fname).write_bytes(image_bytes)

    caption = prompt if len(prompt) <= 140 else prompt[:137] + "…"
    entry = {
        "id": vid,
        "type": "generated",
        "aspect": "",
        "caption": caption,
        "file": fname,
        "suggested_anchor": anchor or "",
        "cleaned": True,
        "embedded_title": "",
    }
    merged = merge_entries(book_dir, [entry])
    write_index(book_dir, merged)
    print(json.dumps({"ok": True, "id": vid, "file": fname, "caption": caption, "kb": len(image_bytes) // 1024}))
    return 0


def do_delete(book_dir: Path, vid: str) -> int:
    vid = (vid or "").strip()
    if not vid:
        return _fail("missing id")
    visuals = load_index(book_dir)
    entry = next((v for v in visuals if str(v.get("id")) == vid), None)
    if entry is None:
        return _fail(f"artifact not found: {vid}")

    idx = index_path(book_dir)
    if idx.exists() and not idx.with_suffix(".json.bak").exists():
        shutil.copy2(idx, idx.with_suffix(".json.bak"))

    fname = str(entry.get("file", ""))
    removed_file = False
    if fname:
        fp = visuals_dir(book_dir) / Path(fname).name
        if fp.exists():
            fp.unlink()
            removed_file = True

    write_index(book_dir, [v for v in visuals if str(v.get("id")) != vid])
    print(json.dumps({"ok": True, "id": vid, "removedFile": removed_file}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book-dir", required=True)
    ap.add_argument("--action", required=True, choices=["generate", "delete"])
    ap.add_argument("--prompt", default="")
    ap.add_argument("--from-file", default="")
    ap.add_argument("--anchor", default="")
    ap.add_argument("--id", default="")
    ap.add_argument("--json", action="store_true")  # accepted for symmetry; output is always JSON
    args = ap.parse_args()

    book_dir = Path(args.book_dir)
    if not book_dir.exists():
        return _fail(f"book dir not found: {args.book_dir}")

    try:
        if args.action == "generate":
            return do_generate(book_dir, args.prompt, args.from_file or None, args.anchor)
        return do_delete(book_dir, args.id)
    except Exception as e:
        return _fail(str(e))


if __name__ == "__main__":
    sys.exit(main())
