#!/usr/bin/env python3
"""stitch_video.py — Stitch per-episode JPEG images + audio into MP4.

Reads video-prompts.json for segment ordering, scales timestamps to the actual
audio duration, writes a temporary ffmpeg concat input file, then runs ffmpeg
to produce a 1080p MP4 in the episode directory.

USAGE

    python3 scripts/podcast/stitch_video.py <book-slug>
    python3 scripts/podcast/stitch_video.py <book-slug> --episode EP01
    python3 scripts/podcast/stitch_video.py <book-slug> --dry-run   # print command only

OUTPUT

    episodes/<ep>/video-<ep>.mp4   (1920×1080 H.264 + AAC, ~1.5–2GB/hour)

REQUIRES

    ffmpeg (brew install ffmpeg)

NOTES

    Timestamps in video-prompts.json are estimated from word counts at 130 wpm.
    This script scales them proportionally to the actual audio duration so the
    image transitions are evenly distributed. Expect 1–2 manual cut adjustments
    per minute in a video editor if you want frame-accurate sync.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _paths import content_dir  # noqa: E402

# ─── ffmpeg helpers ────────────────────────────────────────────────────────────

def _require_ffmpeg() -> None:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        sys.exit("ERROR: ffmpeg not found. Install with: brew install ffmpeg")


def _audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(audio_path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


# ─── Episode discovery ────────────────────────────────────────────────────────

def _discover_episodes(book_dir: Path, episode_filter: str | None) -> list[dict]:
    import json

    episodes_dir = book_dir / "episodes"
    m4a_dir      = book_dir / "m4a"
    results      = []

    if not episodes_dir.exists():
        sys.exit(f"ERROR: episodes/ directory not found at {book_dir}")

    for ep_dir in sorted(episodes_dir.iterdir()):
        if not ep_dir.is_dir():
            continue
        ep_id = ep_dir.name
        if episode_filter and not ep_id.startswith(episode_filter):
            continue

        json_path = ep_dir / "video-prompts.json"
        if not json_path.exists():
            print(f"  WARN: no video-prompts.json for {ep_id}, skipping")
            continue

        images_dir = ep_dir / "video-images"
        if not images_dir.exists() or not list(images_dir.glob("*.jpg")):
            print(f"  WARN: no images in {ep_dir}/video-images, skipping")
            continue

        # Match audio: ch##-<slug>.m4a where ## corresponds to EP## in ep_id
        ep_num_match = re.match(r"EP(\d+)", ep_id)
        if not ep_num_match:
            print(f"  WARN: cannot parse episode number from {ep_id}, skipping")
            continue
        ep_num = ep_num_match.group(1)  # e.g. "01"

        # Find audio file: glob for ch<ep_num>*
        audio_candidates = sorted(m4a_dir.glob(f"ch{ep_num}*.m4a"))
        if not audio_candidates:
            # Also try without leading zero
            audio_candidates = sorted(m4a_dir.glob(f"ch{int(ep_num)}*.m4a"))
        if not audio_candidates:
            print(f"  WARN: no audio found for {ep_id} (looked for ch{ep_num}*.m4a), skipping")
            continue

        segments = json.loads(json_path.read_text(encoding="utf-8"))
        results.append({
            "ep_id":      ep_id,
            "ep_dir":     ep_dir,
            "images_dir": images_dir,
            "audio":      audio_candidates[0],
            "segments":   segments,
        })

    return results


# ─── Stitch logic ─────────────────────────────────────────────────────────────

def _build_image_sequence(
    segments: list[dict],
    images_dir: Path,
    actual_duration_s: float,
) -> list[tuple[Path, float]]:
    """Return list of (image_path, duration_s) pairs scaled to actual audio length."""
    # Estimated total from JSON
    if not segments:
        return []
    estimated_total = max(s.get("est_end_s", 0) for s in segments)
    if estimated_total <= 0:
        estimated_total = actual_duration_s

    scale = actual_duration_s / estimated_total

    # Map segment_id → image file (glob images_dir for files starting with seg_id)
    image_map: dict[str, Path] = {}
    for img in sorted(images_dir.glob("*.jpg")):
        seg_prefix = img.stem.split("_")[0]   # e.g. "s01"
        image_map[seg_prefix] = img

    sequence: list[tuple[Path, float]] = []
    for seg in segments:
        seg_id   = seg.get("segment_id", "")
        img_path = image_map.get(seg_id)
        if img_path is None:
            print(f"    WARN: no image found for segment {seg_id}, skipping")
            continue
        start_s  = seg.get("est_start_s", 0) * scale
        end_s    = seg.get("est_end_s",   0) * scale
        duration = max(end_s - start_s, 1.0)   # minimum 1 second per image
        sequence.append((img_path, duration))

    if not sequence:
        return []

    # Clamp total to actual audio duration (last image absorbs any rounding)
    total_image_s = sum(d for _, d in sequence)
    if total_image_s < actual_duration_s:
        # Extend last image to cover any tail
        last_img, last_dur = sequence[-1]
        sequence[-1] = (last_img, last_dur + (actual_duration_s - total_image_s))

    return sequence


def _write_concat_file(
    sequence: list[tuple[Path, float]],
    tmp_path: Path,
) -> None:
    lines = []
    for img_path, duration in sequence:
        escaped = str(img_path).replace("'", "\\'")
        lines.append(f"file '{escaped}'")
        lines.append(f"duration {duration:.3f}")
    # FFmpeg concat demuxer: repeat last entry without duration to flush final frame
    if sequence:
        last_img = sequence[-1][0]
        lines.append(f"file '{str(last_img).replace(chr(39), chr(92)+chr(39))}'")
    tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_ffmpeg(
    concat_file: Path,
    audio_path: Path,
    output_path: Path,
    dry_run: bool,
) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(audio_path),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
               "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-r", "25",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        "-map", "0:v", "-map", "1:a",
        "-shortest",
        str(output_path),
    ]
    print(f"  $ {' '.join(cmd[:6])} … {output_path.name}")
    if dry_run:
        print(f"  [dry-run] full command:\n    {' '.join(cmd)}")
        return
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED:\n{result.stderr[-1000:]}")
    else:
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  Saved {output_path.name} ({size_mb:.0f} MB)")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    _require_ffmpeg()

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("slug",        help="Book slug, e.g. ayyuhal-walad")
    parser.add_argument("--episode",   help="Stitch a single episode, e.g. EP01")
    parser.add_argument("--dry-run",   action="store_true", help="Print command, don't run")
    args = parser.parse_args(argv)

    book_dir = content_dir(args.slug)
    if not book_dir.exists():
        sys.exit(f"ERROR: book directory not found for slug '{args.slug}'")

    episodes = _discover_episodes(book_dir, args.episode)
    if not episodes:
        sys.exit("No episodes to stitch.")

    print(f"\n{args.slug} — stitching {len(episodes)} episode(s)\n")

    for ep in episodes:
        ep_id    = ep["ep_id"]
        audio    = ep["audio"]
        segments = ep["segments"]

        print(f"── {ep_id}")
        print(f"   Audio: {audio.name}")

        actual_dur = _audio_duration(audio)
        print(f"   Duration: {int(actual_dur//60)}m {int(actual_dur%60)}s")

        sequence = _build_image_sequence(segments, ep["images_dir"], actual_dur)
        if not sequence:
            print(f"   WARN: no image sequence built, skipping")
            continue

        print(f"   Images: {len(sequence)} segments")

        ep_slug_short = re.sub(r"^EP\d+-", "", ep_id)[:32]
        output_path   = ep["ep_dir"] / f"video-{ep_slug_short}.mp4"

        if output_path.exists() and not args.dry_run:
            print(f"   {output_path.name} already exists — delete to re-stitch")
            continue

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix=f"concat_{ep_id}_"
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            _write_concat_file(sequence, tmp_path)
            _run_ffmpeg(tmp_path, audio, output_path, dry_run=args.dry_run)
        finally:
            tmp_path.unlink(missing_ok=True)

        print()

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
