#!/usr/bin/env python3
"""import_transcript.py — Bring-your-own-transcript path into the podcast pipeline.

PURPOSE

    Some lectures and interviews are transcribed externally (TurboScribe,
    Otter, human transcription) because the source is non-English audio
    that off-the-shelf Azure Speech handles poorly, or because a polished
    transcript already exists. This script imports such a transcript into
    the canonical per-episode shape that downstream pipeline stages
    (build_episode_txt.py, extract_chapter.py, challenger) consume —
    matching what transcribe_episode.py produces from raw audio.

    The MP3 (or other audio) is NOT pipeline input on this path; it stays
    in BOOK_DIR/_source/audio/ as a reference for human spot-check.

USAGE

    python3 scripts/podcast/import_transcript.py <BOOK_DIR> <EP##-slug> <source-txt>

OUTPUTS

    <BOOK_DIR>/transcripts/<EP##-slug>.transcript.txt    — cleaned text
    <BOOK_DIR>/transcripts/<EP##-slug>.provenance.json   — audit sidecar

INPUT FORMATS SUPPORTED

    TurboScribe export (.txt):
        (MM:SS - MM:SS)        ← timestamp lines on their own row, stripped
        body text...            ← preserved
        (H:MM:SS - H:MM:SS)    ← long-form timestamps also stripped

    Any plain text file:
        Lines that look like timestamps are stripped; everything else is
        kept. Multiple consecutive blank lines collapse to one.

NON-GOALS

    - Refinement (punctuation cleanup, ASR error correction). That's an
      LLM step run interactively by the agent after import.
    - Chapter segmentation. Phase 0d of the pipeline handles that.
    - Translation. Use Translator separately if the source is non-English.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# (M:SS - M:SS), (MM:SS - MM:SS), (H:MM:SS - H:MM:SS), with flexible spacing.
TIMESTAMP_RE = re.compile(
    r"^\s*\(\s*\d{1,2}(?::\d{2}){1,2}\s*-\s*\d{1,2}(?::\d{2}){1,2}\s*\)\s*$"
)


def strip_timestamps(raw: str) -> tuple[str, int]:
    """Drop timestamp-only lines; collapse runs of blank lines to one.

    Returns (cleaned_text, count_of_stripped_lines).
    """
    stripped = 0
    out_lines: list[str] = []
    prev_blank = False
    for line in raw.splitlines():
        if TIMESTAMP_RE.match(line):
            stripped += 1
            continue
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        out_lines.append(line.rstrip())
        prev_blank = is_blank
    # Trim leading/trailing blank lines.
    while out_lines and not out_lines[0].strip():
        out_lines.pop(0)
    while out_lines and not out_lines[-1].strip():
        out_lines.pop()
    return "\n".join(out_lines) + "\n", stripped


def import_transcript(book_dir: Path, episode_id: str, source_path: Path) -> tuple[Path, Path]:
    if not book_dir.is_dir():
        raise SystemExit(f"ERROR: BOOK_DIR is not a directory: {book_dir}")
    if not source_path.is_file():
        raise SystemExit(f"ERROR: source transcript not found: {source_path}")

    transcripts_dir = book_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    raw = source_path.read_text(encoding="utf-8")
    cleaned, stripped_count = strip_timestamps(raw)

    out_path = transcripts_dir / f"{episode_id}.transcript.txt"
    prov_path = transcripts_dir / f"{episode_id}.provenance.json"

    out_path.write_text(cleaned, encoding="utf-8")

    word_count = len(cleaned.split())
    provenance = {
        "episode_id": episode_id,
        "source": "external-transcript",
        "source_path": str(source_path.relative_to(book_dir)) if source_path.is_relative_to(book_dir) else str(source_path),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "timestamps_stripped": stripped_count,
        "char_count": len(cleaned),
        "word_count": word_count,
    }
    prov_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    return out_path, prov_path


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(
            "Usage: import_transcript.py <BOOK_DIR> <EP##-slug> <source-txt>\n"
            "  Writes <BOOK_DIR>/transcripts/<EP##-slug>.transcript.txt\n"
            "        + <BOOK_DIR>/transcripts/<EP##-slug>.provenance.json"
        )
    book_dir = Path(sys.argv[1]).resolve()
    episode_id = sys.argv[2]
    source_path = Path(sys.argv[3]).resolve()

    out_path, prov_path = import_transcript(book_dir, episode_id, source_path)
    print(f"Wrote transcript: {out_path}")
    print(f"Wrote provenance: {prov_path}")


if __name__ == "__main__":
    main()
