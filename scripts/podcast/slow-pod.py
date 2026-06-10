#!/usr/bin/env python3
"""slow-pod.py — NotebookLM Audio Post-Processor (CLI).

Converts NotebookLM .m4a downloads (and .wav/.aac) to .mp3 with pitch-preserving
tempo reduction via ffmpeg's `atempo` filter.  Zero dependencies beyond Python
3.10+ stdlib and a local ffmpeg installation.

USAGE EXAMPLES
--------------
  # Single file, default 85% speed:
  python3 slow-pod.py --input episode.m4a

  # Single file, custom tempo, custom output dir:
  python3 slow-pod.py --input episode.m4a --tempo 0.80 --output ~/Music/slow

  # Batch folder (all supported audio files, non-recursive):
  python3 slow-pod.py --input ~/Downloads/podcast-batch/

  # Batch folder, recursive:
  python3 slow-pod.py --input ~/Downloads/podcast-batch/ --recursive

  # Dry-run — print ffmpeg commands without executing:
  python3 slow-pod.py --input episode.m4a --dry-run

  # Force re-process even if output already exists:
  python3 slow-pod.py --input episode.m4a --force

  # Custom bitrate:
  python3 slow-pod.py --input episode.m4a --bitrate 128k

OUTPUT NAMING
-------------
  <original-stem>-slow<pct>.mp3
  e.g., EP01-deep-dive.m4a @ tempo=0.85 → EP01-deep-dive-slow85.mp3

EXIT CODES
----------
  0  success (all files processed or skipped)
  1  partial batch failure (at least one file errored)
  2  fatal (bad arguments / ffmpeg not found)
"""
from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

# ── constants -----------------------------------------------------------------
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".m4a", ".wav", ".aac", ".mp3", ".flac", ".ogg"})
TEMPO_MIN = 0.5
TEMPO_MAX = 1.0
TEMPO_DEFAULT = 0.85
BITRATE_DEFAULT = "192k"
# atempo filter accepts [0.5, 100.0] per instance; chain for values < 0.5
ATEMPO_MIN_SINGLE = 0.5


# ── ffmpeg discovery ----------------------------------------------------------

def _find_ffmpeg() -> str:
    """Return ffmpeg path, or raise SystemExit(2) with install instructions."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    install_hint = {
        "darwin": "  macOS:   brew install ffmpeg",
        "linux":  "  Linux:   sudo apt install ffmpeg  OR  sudo dnf install ffmpeg",
        "win32":  "  Windows: winget install ffmpeg  OR download from https://ffmpeg.org/download.html",
    }.get(sys.platform, "  See https://ffmpeg.org/download.html")
    print(
        "ERROR: ffmpeg not found on PATH.\n"
        "Install it first:\n"
        f"{install_hint}\n"
        "Then re-run this script.",
        file=sys.stderr,
    )
    sys.exit(2)


def _find_ffprobe() -> str | None:
    """Return ffprobe path for verification, or None if not available."""
    return shutil.which("ffprobe")


# ── atempo filter chain -------------------------------------------------------

def build_atempo_chain(tempo: float) -> str:
    """Return ffmpeg -af filter string for pitch-preserving tempo change.

    atempo accepts [0.5, 100.0] per instance.  For tempo < 0.5 we chain
    multiple atempo filters so the product equals the target.

    SELF-CHALLENGE: This MUST use atempo (time-stretch), NEVER asetrate.
    asetrate changes pitch by resampling — that is an automatic reject.

    Examples:
        tempo=0.85  →  "atempo=0.85"
        tempo=0.50  →  "atempo=0.5"
        tempo=0.25  →  "atempo=0.5,atempo=0.5"      (0.5 × 0.5 = 0.25)
        tempo=0.30  →  "atempo=0.5477,atempo=0.5477" (√0.30 ≈ 0.5477)
    """
    if tempo < ATEMPO_MIN_SINGLE:
        # Chain n equal stages so that stage^n ≈ tempo
        n_stages = math.ceil(math.log(tempo) / math.log(ATEMPO_MIN_SINGLE))
        stage = tempo ** (1.0 / n_stages)
        return ",".join(f"atempo={stage:.6f}" for _ in range(n_stages))
    return f"atempo={tempo}"


# ── output path --------------------------------------------------------------

def _output_path(input_path: Path, output_dir: Path | None, tempo: float) -> Path:
    """Compute output .mp3 path from input stem + tempo percentage."""
    pct = round(tempo * 100)
    stem = f"{input_path.stem}-slow{pct}"
    dest_dir = output_dir if output_dir is not None else input_path.parent
    return dest_dir / f"{stem}.mp3"


# ── ffmpeg command builder ----------------------------------------------------

def build_ffmpeg_cmd(
    input_path: Path,
    output_path: Path,
    tempo: float,
    bitrate: str,
    ffmpeg: str = "ffmpeg",
) -> list[str]:
    """Return the exact ffmpeg argument list for one file.

    Flags used:
      -y              overwrite output (caller ensures idempotency guard)
      -i <input>      source file
      -vn             strip any video stream (some m4a have cover art)
      -af <chain>     atempo time-stretch only — no pitch change
      -b:a <bitrate>  output audio bitrate
      -map_metadata 0 copy all metadata tags from input
      <output>        destination path
    """
    return [
        ffmpeg,
        "-y",
        "-i", str(input_path),
        "-vn",
        "-af", build_atempo_chain(tempo),
        "-b:a", bitrate,
        "-map_metadata", "0",
        str(output_path),
    ]


# ── per-file processing -------------------------------------------------------

def process_file(
    input_path: Path,
    output_dir: Path | None,
    tempo: float,
    bitrate: str,
    force: bool,
    dry_run: bool,
    ffmpeg: str = "ffmpeg",
) -> bool:
    """Process a single audio file.  Returns True on success/skip, False on error."""
    out = _output_path(input_path, output_dir, tempo)

    # FR-5: idempotency — skip if output already exists and not --force
    if out.exists() and not force:
        print(f"SKIP  {input_path.name}  →  {out.name}  (already exists; use --force to overwrite)")
        return True

    cmd = build_ffmpeg_cmd(input_path, out, tempo, bitrate, ffmpeg=ffmpeg)

    if dry_run:
        print(f"DRY-RUN  {' '.join(repr(c) for c in cmd)}")
        return True

    # Ensure output directory exists
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"PROCESSING  {input_path.name}  →  {out.name}  (tempo={tempo}, bitrate={bitrate})")
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"OK  {out}")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"ERROR  {input_path.name}: ffmpeg exited {exc.returncode}", file=sys.stderr)
        # Print last few lines of stderr for diagnosability
        stderr_tail = (exc.stderr or "").strip().splitlines()[-5:]
        for line in stderr_tail:
            print(f"  ffmpeg> {line}", file=sys.stderr)
        # Clean up partial output
        if out.exists():
            out.unlink(missing_ok=True)
        return False


# ── batch / folder mode -------------------------------------------------------

def collect_audio_files(root: Path, recursive: bool) -> list[Path]:
    """Return sorted list of supported audio files under root."""
    pattern = "**/*" if recursive else "*"
    files = [
        p for p in sorted(root.glob(pattern))
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return files


# ── CLI -----------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="slow-pod",
        description="Slow down NotebookLM audio downloads without changing pitch.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--input", "-i", required=True, metavar="PATH",
        help="Input file (.m4a / .wav / .aac) or directory.",
    )
    p.add_argument(
        "--tempo", type=float, default=TEMPO_DEFAULT, metavar="F",
        help=f"Playback speed factor, 0.5–1.0 (default {TEMPO_DEFAULT}). "
             "0.85 = 85%% speed, 15%% slower.",
    )
    p.add_argument(
        "--bitrate", default=BITRATE_DEFAULT, metavar="RATE",
        help=f"Output MP3 bitrate (default {BITRATE_DEFAULT}).",
    )
    p.add_argument(
        "--output", "-o", metavar="DIR",
        help="Output directory (default: alongside source file).",
    )
    p.add_argument(
        "--recursive", "-r", action="store_true",
        help="Recurse into subdirectories when --input is a folder.",
    )
    p.add_argument(
        "--force", "-f", action="store_true",
        help="Re-process even if output already exists.",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print ffmpeg commands without executing them.",
    )
    return p.parse_args()


def _validate_args(args: argparse.Namespace) -> tuple[Path, Path | None]:
    """Return (input_path, output_dir) or sys.exit(2)."""
    errors: list[str] = []

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        errors.append(f"--input path does not exist: {input_path}")

    output_dir: Path | None = None
    if args.output:
        output_dir = Path(args.output).expanduser().resolve()

    if not (TEMPO_MIN <= args.tempo <= TEMPO_MAX):
        errors.append(
            f"--tempo {args.tempo} is out of range [{TEMPO_MIN}, {TEMPO_MAX}]"
        )

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(2)

    return input_path, output_dir


def main() -> int:
    args = _parse_args()
    input_path, output_dir = _validate_args(args)
    ffmpeg = _find_ffmpeg()  # exits 2 if not found

    # Collect files
    if input_path.is_file():
        if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(
                f"ERROR: unsupported file type '{input_path.suffix}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
                file=sys.stderr,
            )
            return 2
        files = [input_path]
    else:
        files = collect_audio_files(input_path, recursive=args.recursive)
        if not files:
            print(
                f"No supported audio files found in {input_path}"
                + (" (try --recursive)" if not args.recursive else ""),
                file=sys.stderr,
            )
            return 2
        print(f"Found {len(files)} audio file(s) to process.")

    successes = 0
    failures = 0
    for f in files:
        ok = process_file(
            input_path=f,
            output_dir=output_dir,
            tempo=args.tempo,
            bitrate=args.bitrate,
            force=args.force,
            dry_run=args.dry_run,
            ffmpeg=ffmpeg,
        )
        if ok:
            successes += 1
        else:
            failures += 1

    if len(files) > 1:
        print(f"\nDone: {successes} succeeded, {failures} failed.")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
