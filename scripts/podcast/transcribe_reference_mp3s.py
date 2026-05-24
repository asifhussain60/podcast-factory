#!/usr/bin/env python3
"""transcribe_reference_mp3s.py — A/B baseline: transcribe a folder of
previously-generated NotebookLM episode MP3s for cross-reference against
our about-to-be-generated framings.

PURPOSE

The book the-master-and-the-disciple (and any future book where the user
already ran NotebookLM independently and has the reference audio) ships
with an `mp3/` folder of the prior episodes. To do the A/B comparison
the user asked for, we transcribe each MP3 via Azure Speech Fast
Transcription into `audits/ab-reference/transcripts/`. These transcripts
are READ-ONLY reference material for the per-chapter authoring step;
they are NOT inputs to phase 0d/0e/0f.

INVOCATION

    python3 scripts/podcast/transcribe_reference_mp3s.py \\
        --book-dir content/drafts/the-master-and-the-disciple

INPUTS

    BOOK_DIR/mp3/*.mp3 (any number; filenames preserved)

OUTPUTS

    BOOK_DIR/audits/ab-reference/transcripts/<safe-filename>.txt
    BOOK_DIR/audits/ab-reference/_provenance.json

GATING

    Requires Azure Speech credentials in keychain (azure-journal-speech-*).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _azure import (  # noqa: E402
    AzureCredsError,
    SPEECH_AUDIO_MIME,
    load_speech_creds,
    transcribe_audio,
)


def _safe_stem(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return s or "audio"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--book-dir", required=True, type=Path)
    ap.add_argument("--locale", default="en-US")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    book_dir: Path = args.book_dir.resolve()
    src_dir = book_dir / "mp3"
    out_dir = book_dir / "audits" / "ab-reference" / "transcripts"
    prov_path = book_dir / "audits" / "ab-reference" / "_provenance.json"

    if not src_dir.is_dir():
        sys.stderr.write(f"mp3 source dir not found: {src_dir}\n")
        return 2

    audios = sorted(src_dir.iterdir())
    audios = [p for p in audios if p.suffix.lower() in {f".{ext}" for ext in SPEECH_AUDIO_MIME}]
    if not audios:
        sys.stderr.write(f"no audio files in {src_dir} matching {set(SPEECH_AUDIO_MIME.keys())}\n")
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        creds = load_speech_creds()
    except AzureCredsError as e:
        sys.stderr.write(f"Azure Speech creds error: {e}\n")
        return 3

    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.monotonic()

    results = []
    for i, audio in enumerate(audios, 1):
        stem = _safe_stem(audio.stem)
        out_path = out_dir / f"{stem}.txt"
        if out_path.exists() and not args.force:
            print(f"[{i}/{len(audios)}] skip (exists): {out_path.name}", file=sys.stderr)
            results.append({"audio": audio.name, "transcript": out_path.name, "skipped": True})
            continue
        print(f"[{i}/{len(audios)}] transcribing {audio.name} …", file=sys.stderr)
        t_start = time.monotonic()
        audio_bytes = audio.read_bytes()
        text = transcribe_audio(creds, audio_bytes, audio.name, locale=args.locale)
        elapsed = time.monotonic() - t_start
        out_path.write_text(text, encoding="utf-8")
        print(
            f"      → {out_path.name} ({len(text):,} chars, {elapsed:.1f}s)",
            file=sys.stderr,
        )
        results.append({
            "audio": audio.name,
            "transcript": out_path.name,
            "audio_bytes": len(audio_bytes),
            "transcript_chars": len(text),
            "elapsed_s": round(elapsed, 1),
        })

    prov_path.write_text(
        json.dumps(
            {
                "script": "transcribe_reference_mp3s.py",
                "started_at": started,
                "ended_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_elapsed_s": round(time.monotonic() - t0, 1),
                "locale": args.locale,
                "speech_api_version": "2024-11-15",
                "items": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    elapsed = time.monotonic() - t0
    print(f"\n  done in {elapsed:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
