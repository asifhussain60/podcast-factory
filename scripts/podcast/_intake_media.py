"""Companion media for a transcript intake: the audio, and the timestamps.

Split out of `intake_book.py` (2026-08-30) rather than added to it — that module
is grandfathered under the DR-005 line-count gate and may shrink, never grow. Its
own header records that a FULL split was declined (the five intake modes are one
cohesive operation sharing ~10 helpers plus test-patched module globals), so this
takes only the genuinely new surface and leaves the intake modes where they are.

Search roots are PASSED IN rather than imported. `intake_book.RAW_DIR` and
`REPO_ROOT` are monkeypatched by `test_intake_volume.py` against THAT module, so
reaching for them here would silently escape the patch and make those tests lie.

Neither artifact is read by any pipeline phase. The audio is provenance; the
timestamps are preserved because every existing intake path drops timing data on
the floor, and a re-derived transcript is not the one the operator verified.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

AUDIO_EXT = frozenset({".mp3", ".m4a", ".wav"})
TIMELINE_NAME = "transcript-timeline.json"


def resolve_input(raw: str, search_roots: list[Path]) -> Path | None:
    """Resolve a user-supplied path, trying each search root for a relative one."""
    p = Path(raw).expanduser()
    if p.is_absolute():
        return p if p.exists() else None
    for root in search_roots:
        if (root / p).exists():
            return root / p
    return p if p.exists() else None


def copy_audio(src: Path, book_dir: Path) -> list[Path]:
    """Copy audio into ``<book>/source/`` — the layout every audio book uses.

    ``src`` is a directory of recordings or a single file. Returns what landed, in
    filename order. Raises ValueError when the path holds no audio, so the caller
    fails loudly instead of stamping an intake that quietly carried nothing.
    """
    candidates = sorted(
        p for p in (src.iterdir() if src.is_dir() else [src]) if p.is_file() and p.suffix.lower() in AUDIO_EXT
    )
    if not candidates:
        raise ValueError(f"no audio files ({', '.join(sorted(AUDIO_EXT))}) found in {src}")
    dest_dir = book_dir / "source"
    dest_dir.mkdir(parents=True, exist_ok=True)
    landed = []
    for a in candidates:
        dst = dest_dir / a.name
        if dst.resolve() != a.resolve():
            shutil.copy2(a, dst)
        landed.append(dst)
    return landed


def copy_timestamps(src: Path, book_dir: Path) -> Path:
    """Copy the per-sentence timestamp file to its one canonical name, verbatim.

    Renamed on the way in so downstream work looks in exactly one place, and NOT
    parsed here — validating a format nothing consumes yet would invent a contract
    ahead of its reader.
    """
    dst = book_dir / "_system" / "source" / "text" / TIMELINE_NAME
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def transcript_state(
    *,
    slug: str,
    category: str,
    source_path: str,
    source_fidelity: str,
    companion_path: str | None,
    audio_paths: list[str],
    timestamps_path: str | None,
) -> dict:
    """The orchestrator-state a --from-transcript intake stamps.

    Lives beside the staging above because two of its fields are exactly what that
    staging produced; keeping them apart is how one grows a field the other never
    fills. Phase 0a is recorded COMPLETE, not skipped-and-pending: the transcript is
    the extracted text, so there is nothing for OCR to do and a later resume must
    not try.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": 1,
        "book_slug": slug,
        "source_path": source_path,
        "source_kind": "audio-transcript",
        "input_type": "audio-transcript",
        "source_language": "en",
        "source_fidelity": source_fidelity,
        "companion_source_path": companion_path,
        "audio_source_paths": audio_paths or None,
        "timestamps_path": timestamps_path,
        "phase": "0b",
        "phase_status": "pending",
        "last_completed_phase": "0a",
        "last_error": None,
        "category": category,
        "status": "draft",
        "started": now,
        "updated": now,
        "phases": {
            "0a": {
                "completed_via": "audio-transcript-intake",
                "completed_at": now,
                "note": "Phase 0a skipped — source is a pre-extracted transcript",
            }
        },
        "intake_via": "scripts/podcast/intake_book.py --from-transcript",
    }


def add_cli_args(parser) -> None:
    """Register the two --from-transcript companion flags on ``parser``.

    Lives here, beside the code that consumes them, so the flag and its handling
    cannot drift apart — and so `intake_book.py` stays under its DR-005 ceiling.
    """
    parser.add_argument(
        "--audio",
        dest="transcript_audio",
        metavar="PATH",
        default=None,
        help="For --from-transcript: matching audio (dir or file) copied to source/ for provenance.",
    )
    parser.add_argument(
        "--timestamps",
        dest="transcript_timestamps",
        metavar="PATH",
        default=None,
        help="For --from-transcript: per-sentence-timestamped transcript, kept as transcript-timeline.json.",
    )


def report(audio: list[str], timeline: Path | None, repo_root: Path) -> list[str]:
    """Operator-facing lines for what was staged. Empty when nothing was given."""
    lines = []
    if audio:
        lines.append(f"    Copied {len(audio)} audio file(s) → source/ (provenance only)")
    if timeline:
        lines.append(f"    Copied timestamps → {timeline.relative_to(repo_root)} (stored, not consumed yet)")
    return lines


def stage_companions(
    book_dir: Path,
    search_roots: list[Path],
    audio_source: str | None,
    timestamps_path: str | None,
) -> tuple[list[Path], Path | None]:
    """Resolve and copy both companions. Raises ValueError with a caller-ready message."""
    landed: list[Path] = []
    if audio_source:
        src = resolve_input(audio_source, search_roots)
        if src is None:
            raise ValueError(f"audio source not found: {audio_source}")
        landed = copy_audio(src, book_dir)
    timeline = None
    if timestamps_path:
        src = resolve_input(timestamps_path, search_roots)
        if src is None:
            raise ValueError(f"timestamps file not found: {timestamps_path}")
        timeline = copy_timestamps(src, book_dir)
    return landed, timeline
