#!/usr/bin/env python3
"""Transcribe NotebookLM-generated audio (.m4a) for a book slug.

Post-production utility — run after downloading generated audio from NotebookLM.
Uses local openai-whisper (CPU / Apple Silicon). No Azure credential required.

Distinct from transcribe_audio.py, which transcribes lecture INPUT videos via
Azure Speech (WC8.6 intake path). This script handles the OUTPUT side: the .m4a
files NotebookLM produces after generation.

Usage:
    python3 scripts/podcast/transcribe_notebooklm.py <book-slug>

Reads:   content/drafts/<slug>/audio/*.m4a
Writes:  content/drafts/<slug>/audio/transcripts/<stem>.txt

Install dependency (first run only):
    pip install openai-whisper
"""
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: transcribe_notebooklm.py <book-slug>", file=sys.stderr)
        return 1

    slug = sys.argv[1]
    audio_dir = Path("content/drafts") / slug / "audio"
    out_dir = audio_dir / "transcripts"

    if not audio_dir.exists():
        print(f"Audio directory not found: {audio_dir}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    m4a_files = sorted(audio_dir.glob("*.m4a"))
    if not m4a_files:
        print(f"No .m4a files found in {audio_dir}", file=sys.stderr)
        return 1

    try:
        import whisper
    except ImportError:
        print("Install: pip install openai-whisper", file=sys.stderr)
        return 1

    model = whisper.load_model("base")
    for f in m4a_files:
        out_path = out_dir / (f.stem + ".txt")
        if out_path.exists():
            print(f"  {f.name} → already transcribed, skipping")
            continue
        print(f"  {f.name} → transcribing…")
        result = model.transcribe(str(f))
        out_path.write_text(result["text"], encoding="utf-8")
        print(f"  {f.name} → {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
