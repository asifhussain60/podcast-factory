#!/usr/bin/env python3
"""render_sample_preview.py — quick 2-min voice-approval clip from any episode.

Renders the first N turns of a gated dialogue script into a single mp3 so
Asif can approve the voice pair BEFORE committing a full-episode render.
Does NOT pass through the Arabic-recitation scaffold (so you hear the clean
voice timbre, not the mixed-script result).

Usage:
    python3 scripts/podcast/render_sample_preview.py <slug> <EP-id> [--turns N] --confirm
    python3 scripts/podcast/render_sample_preview.py asaas-al-taveel-vol-01 \\
        EP01-what-ismaili-interpretation-is --turns 6 --confirm

Output:
    content/<Bucket>/<slug>/_system/scratchpad/<EP-id>-preview.mp3
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _audio_engines import ENGINE_ELEVENLABS, get_engine, voices_for_book
from _dialogue_script import parse_dialogue_script, script_path_for
from _elevenlabs import ElevenLabsClient
from _paths import find_content
from pronunciation_compiler import ensure_dictionary

DEFAULT_TURNS = 6
STABILITY = 0.0
OUTPUT_FORMAT = "mp3_44100_128"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", help="book slug")
    ap.add_argument("episode", help="episode id, e.g. EP01-what-ismaili-interpretation-is")
    ap.add_argument(
        "--turns", type=int, default=DEFAULT_TURNS, help=f"number of turns to render (default {DEFAULT_TURNS})"
    )
    ap.add_argument("--confirm", action="store_true", help="authorize ElevenLabs spend")
    ap.add_argument("--dry-run", action="store_true", help="show plan without rendering")
    args = ap.parse_args()

    found = find_content(args.slug)
    if not found:
        print(f"ERROR: no content dir for slug {args.slug!r}", file=sys.stderr)
        return 2
    book_dir = found[2]

    script = script_path_for(book_dir, args.episode)
    if not script.exists():
        print(f"ERROR: script not found: {script}", file=sys.stderr)
        return 2

    turns = parse_dialogue_script(script.read_text(encoding="utf-8"))
    sample_turns = turns[: args.turns]

    engine = get_engine(ENGINE_ELEVENLABS)
    voices = voices_for_book(book_dir)

    total_chars = sum(len(t.text) for t in sample_turns)
    print("Sample preview plan")
    print(f"  episode : {args.episode}")
    print(f"  turns   : {len(sample_turns)} of {len(turns)}")
    print(f"  chars   : {total_chars:,}  (~{total_chars / 13:.0f} sec at 13 cps)")
    print(f"  voices  : host_a={voices.get('host_a')}  host_b={voices.get('host_b')}")
    print(f"  model   : {engine.model_id}")

    out_dir = book_dir / "_system" / "scratchpad"
    out_path = out_dir / f"{args.episode}-preview.mp3"
    print(f"  output  : {out_path.relative_to(book_dir.parent.parent.parent)}")

    if args.dry_run or not args.confirm:
        print(f"\nDRY RUN — pass --confirm to render (~{total_chars:,} credits).")
        return 0

    client = ElevenLabsClient()

    # Pin pronunciation dictionary so the sample uses the same rules as
    # production (alias entries for Islamic terms). Failure is non-fatal.
    locators = None
    try:
        locator = ensure_dictionary(book_dir, client, log=print)
        locators = [locator] if locator else None
    except Exception as e:
        print(f"  WARN: dictionary pin failed ({e}) — rendering without")

    # Chunk turns to stay within the ElevenLabs per-request reliability limit.
    chunks: list[list] = []
    current: list = []
    current_chars = 0
    for t in sample_turns:
        tc = len(t.text)
        if current and current_chars + tc > engine.max_chunk_chars:
            chunks.append(current)
            current, current_chars = [], 0
        current.append(t)
        current_chars += tc
    if current:
        chunks.append(current)

    print(f"\nRendering {len(sample_turns)} turns in {len(chunks)} chunk(s)…")
    meter_start = int(client.subscription().get("character_count", 0))

    chunk_files: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, chunk in enumerate(chunks):
        chunk_chars = sum(len(t.text) for t in chunk)
        content_hash = hashlib.sha256("".join(t.text for t in chunk).encode()).hexdigest()
        seed = int(content_hash[:8], 16) % (2**31)
        payload = [{"text": t.text, "voice_id": voices[t.speaker.lower()]} for t in chunk]
        print(f"  chunk {i + 1}/{len(chunks)}: {len(chunk)} turns, {chunk_chars:,} chars, seed={seed}")
        audio = client.text_to_dialogue(
            payload,
            model_id=engine.model_id,
            seed=seed,
            settings={"stability": STABILITY},
            pronunciation_dictionary_locators=locators,
            output_format=OUTPUT_FORMAT,
        )
        cpath = out_dir / f"{args.episode}-preview-chunk{i}.mp3"
        cpath.write_bytes(audio)
        chunk_files.append(cpath)

    # Concatenate chunks if more than one.
    if len(chunk_files) == 1:
        chunk_files[0].rename(out_path)
    else:
        list_txt = out_dir / f"{args.episode}-preview-list.txt"
        list_txt.write_text("".join(f"file '{p.resolve()}'\n" for p in chunk_files), encoding="utf-8")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_txt), "-c", "copy", str(out_path)],
            check=True,
            capture_output=True,
        )
        list_txt.unlink(missing_ok=True)
        for p in chunk_files:
            p.unlink(missing_ok=True)

    meter_end = int(client.subscription().get("character_count", 0))
    credits_used = meter_end - meter_start
    print(f"Done — credits used: {credits_used:,}")
    print(f"Output: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
