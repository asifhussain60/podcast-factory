#!/usr/bin/env python3
"""post_publish.py — single-command wrapper for the §post-publication SLA.

Closes the gap between "episode shipped to NotebookLM" and "Loop M findings in
the convergence loop" by chaining the three steps the SKILL.md §post-publication
block calls out:

    1. (optional) Transcribe an audio export via Azure Speech-to-Text
    2. Run the lexical audit (audit_transcript.py)
    3. Print the explicit podcast-challenger invocation for Loop M

USAGE

    python3 scripts/podcast/post_publish.py <BOOK_DIR> <EP##-slug> [<audio-path>]

    - With <audio-path>: transcribes via Azure Speech first, then audits.
    - Without <audio-path>: assumes a transcript is already at
      BOOK_DIR/transcripts/EP##-<slug>.transcript.txt (manual transcript drop
      OR a prior transcribe_episode.py run). Skips step 1.

NON-GOALS

    - This script does NOT invoke the podcast-challenger directly — Python
      cannot spawn a Claude Code subagent. It prints the exact invocation the
      human (or driving agent) issues next.
    - This script does NOT replace audit_transcript.py or transcribe_episode.py
      — it composes them. Both remain callable on their own.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Delegate to the two underlying scripts. Re-import their entry points rather
# than shelling out, so a single Python invocation runs the whole sequence.
import audit_transcript  # noqa: E402
import transcribe_episode  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        sys.exit(
            "Usage: post_publish.py <BOOK_DIR> <EP##-slug> [<audio-path>]\n"
            "  With <audio-path>: transcribe via Azure Speech, then audit.\n"
            "  Without:           audit the existing transcript file."
        )

    book_dir = Path(sys.argv[1]).resolve()
    episode_id = sys.argv[2]
    audio_path = Path(sys.argv[3]).resolve() if len(sys.argv) == 4 else None

    if not book_dir.is_dir():
        sys.exit(f"ERROR: BOOK_DIR is not a directory: {book_dir}")

    transcripts_dir = book_dir / "transcripts"
    transcript_path = transcripts_dir / f"{episode_id}.transcript.txt"

    # ── Step 1 — Transcribe (optional) ────────────────────────────────────
    if audio_path is not None:
        print(f"[1/3] Transcribing {audio_path.name} via Azure Speech…")
        transcribe_episode.transcribe(book_dir, episode_id, audio_path)
        print(f"      → {transcript_path}")
    else:
        if not transcript_path.is_file():
            sys.exit(
                f"ERROR: no transcript at {transcript_path} and no <audio-path> "
                f"provided.\n"
                f"  Either drop a manual transcript at that path, "
                f"or pass an audio file:\n"
                f"  python3 {sys.argv[0]} {book_dir} {episode_id} path/to/audio.mp3"
            )
        print(f"[1/3] Using existing transcript: {transcript_path}")

    # ── Step 2 — Lexical audit ────────────────────────────────────────────
    print(f"\n[2/3] Running empirical-transcript audit…")
    report_path = audit_transcript.audit(book_dir, episode_id, transcript_path)
    print(f"      → {report_path}")

    # ── Step 3 — Print challenger next-step ───────────────────────────────
    book_slug = book_dir.name
    print(
        f"\n[3/3] Next — invoke podcast-challenger to fold Loop M into convergence:\n"
        f"      Use the Agent tool with subagent_type=podcast-challenger,\n"
        f"      prompt: `{book_slug} --chapter {episode_id.split('-', 1)[-1]}`\n"
        f"      (or `{book_slug}` for the full per-book sweep).\n"
        f"\n"
        f"      The challenger reads {transcript_path.relative_to(book_dir.parents[3]) if book_dir.parents[3] in transcript_path.parents else transcript_path} directly per Category M / N / O\n"
        f"      of the canonical spec at .github/agents/podcast-challenger.agent.md.\n"
        f"\n"
        f"      SLA: every shipped episode is audited + challenged within 7 days\n"
        f"      (skills-staging/podcast/SKILL.md §post-publication)."
    )


if __name__ == "__main__":
    main()
