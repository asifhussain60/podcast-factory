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

  python3 scripts/podcast/transcribe_episode.py <BOOK_DIR> <EP##-slug> <audio-path> [--locale <locale>]

  --locale defaults to en-US. Pass ur-PK for Urdu, ar-SA for Arabic, etc.
  Full list: https://learn.microsoft.com/azure/ai-services/speech-service/language-support

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


def transcribe(
    book_dir: Path,
    episode_id: str,
    audio_path: Path,
    *,
    locale: str = "en-US",
) -> Path:
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
    print(
        f"Transcribing {audio_path.name} ({audio_size_mb:.1f} MB) "
        f"via Azure Speech ({creds.region}, locale={locale})..."
    )

    text = _azure.transcribe_audio(creds, audio_bytes, audio_path.name, locale=locale)
    if not text.strip():
        raise SystemExit(
            "ERROR: Speech returned an empty transcript. Audio may be silent, "
            "corrupted, exceed the Fast Transcription 2-hour ceiling, or use a "
            "locale the speech model couldn't recognize."
        )

    out_path.write_text(text + "\n", encoding="utf-8")

    # F36 (2026-05-25): record Azure Speech spend in cost-ledger.jsonl.
    # Azure Speech Fast Transcription is priced per-character of TRANSCRIPT
    # (close approximation; actual API pricing is per-second but we don't
    # know audio duration without re-probing). Transcript char count is a
    # stable proxy that under-counts long silences.
    try:
        from _cost_ledger import append_azure_speech_cost
        cost_row = append_azure_speech_cost(
            book_dir=book_dir, phase="post-publish",
            step=f"transcribe/{episode_id}",
            char_count=len(text),
        )
        print(f"  Azure cost (speech): ${cost_row.cost_usd:.4f} for {len(text):,} transcript chars")
    except Exception as _e:
        print(f"  WARN: cost-ledger append failed: {_e}", file=sys.stderr)
    return out_path


def _parse_args(argv: list[str]) -> tuple[Path, str, Path, str]:
    """Parse positional args + optional --locale flag.

    Kept manual rather than argparse to preserve the historical 3-positional
    contract used by callers and docs across the skill.
    """
    locale = "en-US"
    positional: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--locale" and i + 1 < len(argv):
            locale = argv[i + 1]
            i += 2
            continue
        if tok.startswith("--locale="):
            locale = tok.split("=", 1)[1]
            i += 1
            continue
        positional.append(tok)
        i += 1
    if len(positional) != 3:
        sys.exit(
            "Usage: transcribe_episode.py <BOOK_DIR> <EP##-slug> <audio-path> [--locale <locale>]\n"
            "  Writes <BOOK_DIR>/transcripts/<EP##-slug>.transcript.txt\n"
            "  --locale defaults to en-US. Examples: ur-PK, ar-SA, hi-IN."
        )
    book_dir = Path(positional[0]).resolve()
    episode_id = positional[1]
    audio_path = Path(positional[2]).resolve()
    return book_dir, episode_id, audio_path, locale


def main() -> None:
    book_dir, episode_id, audio_path, locale = _parse_args(sys.argv[1:])
    out_path = transcribe(book_dir, episode_id, audio_path, locale=locale)
    print(f"Wrote transcript: {out_path}")

    book_slug = book_dir.name
    print(
        "\nNext step (continues §post-publication, Loop M):\n"
        f"  python3 scripts/podcast/audit_transcript.py {book_dir} {episode_id}\n"
        f"  → then invoke podcast-challenger (subagent_type=podcast-challenger) on `{book_slug}`."
    )


if __name__ == "__main__":
    main()
