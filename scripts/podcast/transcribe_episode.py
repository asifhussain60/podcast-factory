#!/usr/bin/env python3
"""transcribe_episode.py — Azure Speech-to-Text → slug-aligned transcript file.

PURPOSE

  Replaces an external transcription step in the post-publication audit loop
  (skills-staging/podcast/SKILL.md §post-publication). Given a downloaded
  NotebookLM Audio Overview MP3/WAV, transcribes via Azure Speech Fast
  Transcription and writes the result to the canonical
  `BOOK_DIR/transcripts/EP##-<slug>.transcript.txt` path so `audit_transcript.py`
  and the podcast-challenger's Loop M consume it without changes.

USAGE

  python3 scripts/podcast/transcribe_episode.py <BOOK_DIR> <EP##-slug> <audio-path>

OUTPUTS

  Writes <BOOK_DIR>/transcripts/<EP##-slug>.transcript.txt
  Prints the next-step command (audit_transcript.py) on completion.

GATING

  Requires Azure Speech credentials in the macOS Keychain (or env vars). Run
  `infra/azure/store-keychain-keys.sh` after `infra/azure/provision-azure.sh`
  with ENABLE_SPEECH=true. Manual transcript drops remain a supported
  fallback — both paths write to the same filename contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _azure  # noqa: E402


def transcribe(book_dir: Path, episode_id: str, audio_path: Path) -> Path:
    """Transcribe `audio_path` and write the slug-aligned transcript file."""
    if not book_dir.is_dir():
        raise SystemExit(f"ERROR: BOOK_DIR is not a directory: {book_dir}")
    if not audio_path.is_file():
        raise SystemExit(f"ERROR: audio file not found: {audio_path}")

    transcripts_dir = book_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{episode_id}.transcript.txt"

    creds = _azure.load_speech_creds()
    audio_bytes = audio_path.read_bytes()
    audio_size_mb = len(audio_bytes) / (1024 * 1024)
    print(f"Transcribing {audio_path.name} ({audio_size_mb:.1f} MB) via Azure Speech ({creds.region})...")

    text = _azure.transcribe_audio(creds, audio_bytes, audio_path.name)
    if not text.strip():
        raise SystemExit(
            "ERROR: Speech returned an empty transcript. Audio may be silent, "
            "corrupted, or exceed the Fast Transcription 2-hour ceiling."
        )

    out_path.write_text(text + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(
            "Usage: transcribe_episode.py <BOOK_DIR> <EP##-slug> <audio-path>\n"
            "  Writes <BOOK_DIR>/transcripts/<EP##-slug>.transcript.txt"
        )
    book_dir = Path(sys.argv[1]).resolve()
    episode_id = sys.argv[2]
    audio_path = Path(sys.argv[3]).resolve()

    out_path = transcribe(book_dir, episode_id, audio_path)
    print(f"Wrote transcript: {out_path}")

    book_slug = book_dir.name
    print(
        "\nNext step (continues §post-publication, Loop M):\n"
        f"  python3 scripts/podcast/audit_transcript.py {book_dir} {episode_id}\n"
        f"  → then invoke podcast-challenger (subagent_type=podcast-challenger) on `{book_slug}`."
    )


if __name__ == "__main__":
    main()
