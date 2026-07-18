#!/usr/bin/env python3
"""transcribe_notebooklm.py — Azure batch transcription of NotebookLM output audio.

PURPOSE

    The OUTPUT side of the audio loop: after NotebookLM episodes are
    downloaded and normalized to canonical names (normalize_m4a.py), this
    script transcribes every canonical `m4a/ch<NN><s>-<slug>.m4a` that is
    missing its transcript — via Azure Speech Fast Transcription, the same
    proven caller the rest of the pipeline uses. No external service, no
    manual upload ritual.

    History: v1 of this script used local openai-whisper (never installed on
    the host — TurboScribe became the manual workaround) and pointed at the
    retired `content/drafts/<slug>/audio/` layout. Rebuilt 2026-06-12 on
    Azure + bucket-aware paths. External transcription (TurboScribe etc.)
    remains a FALLBACK drop path — normalize_m4a.py pairs those too.

ONE CALL, BOTH CONTRACTS

    The pipeline has two transcript homes with live consumers:

        m4a/transcripts/<ch-stem>.transcript.txt   <- SOURCE OF TRUTH
            (postprod-review pairing, normalize_m4a verification)
        transcripts/EP<NN>-<slug>.transcript.txt   <- derived copy
            (audit_transcript.py Loop M, stitch_video.py keyword sync)

    One Azure call writes both (the EP-keyed file is a byte-identical copy;
    suppress with --no-audit-copy). Re-deriving is always safe.

USAGE

    python3 scripts/podcast/transcribe_notebooklm.py <book-slug>             # all missing
    python3 scripts/podcast/transcribe_notebooklm.py <book-slug> --only ch19c-the-conspiracy-formula
    python3 scripts/podcast/transcribe_notebooklm.py <book-slug> --force     # re-transcribe all
    python3 scripts/podcast/transcribe_notebooklm.py <book-slug> --dry-run   # show the work plan

COST

    Azure Speech fast transcription, Standard tier (~$0.30/audio-hour).
    Every job appends an `azure-speech-stt-fast` row (duration-priced) to
    BOOK_DIR/_system/cost-ledger.jsonl. Standing Azure spend authorization
    (2026-05-29) covers this path.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _paths import find_content

CH_STEM_RE = re.compile(r"^ch(\d{2})([a-z]?)-([a-z0-9][a-z0-9-]*)$")


def _audio_duration_s(audio_path: Path) -> float | None:
    """Audio duration via ffprobe; None when ffprobe is unavailable."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio_path)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return float(out)
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        return None


def _episode_id(book_dir: Path, ch_stem: str) -> str:
    """EP-keyed id for a chapter stem: prefer the real episodes/ filename."""
    m = CH_STEM_RE.match(ch_stem)
    num, slug = int(m.group(1)), m.group(3)
    ep_file = book_dir / "episodes" / f"EP{num:02d}-{slug}.txt"
    if ep_file.exists():
        return ep_file.stem
    return f"EP{num:02d}-{slug}"


def plan_missing(book_dir: Path, *, only: str | None = None, force: bool = False) -> tuple[list[Path], list[Path]]:
    """Return (to_transcribe, non_canonical) among m4a/*.m4a."""
    m4a_dir = book_dir / "m4a"
    tx_dir = m4a_dir / "transcripts"
    todo: list[Path] = []
    non_canonical: list[Path] = []
    for p in sorted(m4a_dir.glob("*.m4a")) if m4a_dir.is_dir() else []:
        if not CH_STEM_RE.match(p.stem):
            non_canonical.append(p)
            continue
        if only and p.stem != only:
            continue
        if not force and (tx_dir / f"{p.stem}.transcript.txt").exists():
            continue
        todo.append(p)
    return todo, non_canonical


def transcribe_book(
    book_dir: Path,
    *,
    only: str | None = None,
    force: bool = False,
    locale: str = "en-US",
    audit_copy: bool = True,
    transcriber=None,  # injectable for tests: (audio_path, locale) -> str
    log=print,
) -> list[Path]:
    """Transcribe every canonical m4a missing a transcript. Returns written paths."""
    todo, non_canonical = plan_missing(book_dir, only=only, force=force)
    for p in non_canonical:
        log(f"  SKIP (non-canonical name): {p.name} — run normalize_m4a.py first")
    if not todo:
        log("  nothing to transcribe — every canonical m4a has a transcript.")
        return []

    if transcriber is None:
        import _azure
        from _engine import ENGINE_AZURE, TASK_TRANSCRIBE, engine_guard

        engine_guard(TASK_TRANSCRIBE, ENGINE_AZURE)
        creds = _azure.load_speech_creds()

        def transcriber(audio_path: Path, loc: str) -> str:
            return _azure.transcribe_audio(creds, audio_path.read_bytes(), audio_path.name, locale=loc)

    tx_dir = book_dir / "m4a" / "transcripts"
    tx_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for audio in todo:
        dur = _audio_duration_s(audio)
        dur_label = f"{dur / 60:.1f} min" if dur else "unknown length"
        log(f"  transcribing {audio.name} ({dur_label}, locale={locale})...")
        text = transcriber(audio, locale).strip()
        if not text:
            log(
                f"  ERROR: empty transcript for {audio.name} — skipped "
                "(silent/corrupt audio, >2h ceiling, or wrong locale)"
            )
            continue
        out = tx_dir / f"{audio.stem}.transcript.txt"
        out.write_text(text + "\n", encoding="utf-8")
        written.append(out)
        if audit_copy:
            ep_id = _episode_id(book_dir, audio.stem)
            ep_out = book_dir / "transcripts" / f"{ep_id}.transcript.txt"
            ep_out.parent.mkdir(parents=True, exist_ok=True)
            ep_out.write_text(text + "\n", encoding="utf-8")
            written.append(ep_out)
        # Duration-priced ledger row (matches Azure's actual per-second pricing).
        try:
            from _cost_ledger import append_azure_stt_cost

            row = append_azure_stt_cost(
                book_dir,
                phase="postprod",
                step=f"transcribe-notebooklm/{audio.stem}",
                duration_seconds=dur if dur else len(text) / 16.0,  # ~16 chars/s fallback
            )
            log(f"    wrote {out.name} ({len(text):,} chars) · Azure ${row.cost_usd:.4f}")
        except Exception as e:  # ledger failure never blocks the transcript
            log(f"    wrote {out.name} ({len(text):,} chars) · WARN ledger append failed: {e}")
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Transcribe NotebookLM output audio (m4a/) via Azure Speech.")
    ap.add_argument("slug", help="book slug (any bucket)")
    ap.add_argument("--only", help="single canonical stem, e.g. ch19c-the-conspiracy-formula")
    ap.add_argument("--force", action="store_true", help="re-transcribe even when a transcript exists")
    ap.add_argument("--locale", default="en-US", help="speech locale (default en-US)")
    ap.add_argument(
        "--no-audit-copy", action="store_true", help="skip the derived transcripts/EP##-<slug>.transcript.txt copy"
    )
    ap.add_argument("--dry-run", action="store_true", help="list the work plan, transcribe nothing")
    args = ap.parse_args()

    found = find_content(args.slug)
    if not found:
        print(f"ERROR: no content directory matches slug {args.slug!r}", file=sys.stderr)
        return 2
    book_dir = found[2]

    if args.dry_run:
        todo, non_canonical = plan_missing(book_dir, only=args.only, force=args.force)
        for p in non_canonical:
            print(f"  NON-CANONICAL (normalize first): {p.name}")
        for p in todo:
            print(f"  would transcribe: {p.name}")
        if not todo:
            print("  nothing to transcribe.")
        return 0

    written = transcribe_book(
        book_dir,
        only=args.only,
        force=args.force,
        locale=args.locale,
        audit_copy=not args.no_audit_copy,
    )
    print(f"\ndone: {len(written)} file(s) written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
