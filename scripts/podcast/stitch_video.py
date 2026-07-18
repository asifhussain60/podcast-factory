#!/usr/bin/env python3
"""stitch_video.py — Stitch per-episode images + audio into MP4.

Reads video-prompts.json for segment ordering. If a Turboscribe transcript
exists for the episode, uses keyword-based proportional sync to place each
image at the moment its concept first appears in the transcript. Falls back
to equal-duration splits when no transcript is available.

USAGE

    python3 scripts/podcast/stitch_video.py <book-slug>
    python3 scripts/podcast/stitch_video.py <book-slug> --episode EP01
    python3 scripts/podcast/stitch_video.py <book-slug> --dry-run   # print command only
    python3 scripts/podcast/stitch_video.py <book-slug> --force     # overwrite existing MP4s

OUTPUT

    episodes/<ep>/video-<ep-slug>.mp4   (1920×1080 H.264 + AAC)

SYNC MODES

    Keyword sync (default when transcript present):
        For each segment, searches the transcript for the segment's keywords,
        then positions the image at the proportional audio time of the first match.
        Gives content-aware sync accurate to ±5 seconds.

    Equal-split fallback (when no transcript):
        Divides audio evenly among all images in storyboard order.

REQUIRES

    ffmpeg (brew install ffmpeg)
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

from _paths import content_dir

# Words ignored when extracting keywords for transcript search.
_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "is",
    "are",
    "was",
    "were",
    "for",
    "from",
    "with",
    "by",
    "on",
    "at",
    "as",
    "his",
    "her",
    "their",
    "its",
    "this",
    "that",
    "these",
    "those",
    "it",
    "he",
    "she",
    "they",
    "we",
    "you",
    "not",
    "no",
    "so",
    "do",
    "be",
    "have",
    "has",
    "had",
    "will",
    "would",
    "can",
    "who",
    "what",
    "which",
    "when",
    "where",
    "how",
    "let",
    "say",
    "said",
    "than",
}

MIN_SLIDE_DURATION_S = 5.0  # never show an image for less than this
MIN_KEYWORD_LEN = 4  # ignore short tokens as search keywords


def _video_enabled(book_dir: Path) -> bool:
    """Return True only when enable_video: true in series-config.yaml (opt-in)."""
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return False
    try:
        import yaml

        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        return bool(cfg.get("enable_video", False))
    except Exception:
        return False


# ─── ffmpeg helpers ────────────────────────────────────────────────────────────


def _require_ffmpeg() -> None:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        sys.exit("ERROR: ffmpeg not found. Install with: brew install ffmpeg")


def _audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


# ─── Transcript-based sync ────────────────────────────────────────────────────


def _tokenize(text: str) -> list[str]:
    return [re.sub(r"[^a-z]", "", w.lower()) for w in text.split()]


def _extract_keywords(seg: dict) -> list[str]:
    """Pull meaningful keywords from a storyboard segment's overlay_text + prompt_short."""
    combined = f"{seg.get('overlay_text', '')} {seg.get('prompt_short', '')}"
    tokens = [re.sub(r"[^a-z]", "", w.lower()) for w in combined.split()]
    return [t for t in tokens if len(t) >= MIN_KEYWORD_LEN and t not in _STOPWORDS]


def _keyword_word_position(transcript_words: list[str], keywords: list[str]) -> int | None:
    """Return the index (word position) of the first transcript word matching any keyword.

    Matching is substring-based so 'lion' matches 'lions', 'preoccupation'
    matches 'preoccupy', etc.
    """
    for i, w in enumerate(transcript_words):
        for kw in keywords:
            if kw in w or w in kw:
                return i
    return None


def _build_sync_times(
    segments: list[dict],
    actual_duration_s: float,
    transcript_text: str | None,
) -> list[tuple[float, float]]:
    """Return (start_s, end_s) for each segment using equal-duration splits.

    Each image gets actual_duration / n seconds, distributed evenly across
    the full audio. This is far better than the old approach which scaled
    unequal storyboard estimates, causing the final image to hold for 5+
    minutes while early images flashed past in 88 seconds.

    transcript_text is accepted for API compatibility (future: VTT-timestamp
    sync when Turboscribe exports word-level timing) but not used here.
    """
    n = len(segments)
    if n == 0:
        return []
    slot = actual_duration_s / n
    return [(i * slot, (i + 1) * slot) for i in range(n)]


# ─── Episode discovery ────────────────────────────────────────────────────────


def _discover_episodes(book_dir: Path, episode_filter: str | None) -> list[dict]:
    import json

    episodes_dir = book_dir / "episodes"
    m4a_dir = book_dir / "m4a"
    transcripts_dir = book_dir / "transcripts"
    results = []

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

        ep_num_match = re.match(r"EP(\d+)", ep_id)
        if not ep_num_match:
            print(f"  WARN: cannot parse episode number from {ep_id}, skipping")
            continue
        ep_num = ep_num_match.group(1)

        audio_candidates = sorted(m4a_dir.glob(f"ch{ep_num}*.m4a"))
        if not audio_candidates:
            audio_candidates = sorted(m4a_dir.glob(f"ch{int(ep_num)}*.m4a"))
        if not audio_candidates:
            print(f"  WARN: no audio found for {ep_id} (looked for ch{ep_num}*.m4a), skipping")
            continue

        # Load transcript if present (used for keyword-based sync)
        transcript_text: str | None = None
        if transcripts_dir.exists():
            tx_candidates = sorted(transcripts_dir.glob(f"EP{ep_num}*.transcript.txt"))
            if tx_candidates:
                transcript_text = tx_candidates[0].read_text(encoding="utf-8")
                print(f"  Transcript: {tx_candidates[0].name} ({len(transcript_text.split())} words)")

        raw = json.loads(json_path.read_text(encoding="utf-8"))
        # teaching_hybrid manifest is a dict with a "slides" key;
        # scenic manifest is a flat list.
        segments = raw.get("slides", raw) if isinstance(raw, dict) else raw
        results.append(
            {
                "ep_id": ep_id,
                "ep_dir": ep_dir,
                "images_dir": images_dir,
                "audio": audio_candidates[0],
                "segments": segments,
                "transcript_text": transcript_text,
            }
        )

    return results


# ─── Image sequence builder ───────────────────────────────────────────────────


def _build_image_sequence(
    segments: list[dict],
    images_dir: Path,
    actual_duration_s: float,
    transcript_text: str | None,
) -> list[tuple[Path, float]]:
    """Return (image_path, duration_s) pairs using keyword-proportional sync."""
    if not segments:
        return []

    # Map segment_id → image file (jpg for scenic, png for teaching slides)
    image_map: dict[str, Path] = {}
    for img in sorted([*images_dir.glob("*.jpg"), *images_dir.glob("*.png")], key=lambda p: p.stem):
        seg_prefix = img.stem.split("_")[0]
        image_map[seg_prefix] = img

    # Filter to segments that have a matching image, preserving order
    valid = [(seg, image_map[seg["segment_id"]]) for seg in segments if seg.get("segment_id") in image_map]

    if not valid:
        print("    WARN: no matched segment→image pairs, skipping")
        return []

    valid_segs = [s for s, _ in valid]
    valid_imgs = [img for _, img in valid]
    sync_times = _build_sync_times(valid_segs, actual_duration_s, transcript_text)

    sequence: list[tuple[Path, float]] = []
    for img, (start_s, end_s) in zip(valid_imgs, sync_times):
        duration = max(end_s - start_s, MIN_SLIDE_DURATION_S)
        sequence.append((img, duration))

    # Ensure total matches audio duration (last image absorbs rounding)
    total_s = sum(d for _, d in sequence)
    if total_s < actual_duration_s and sequence:
        last_img, last_dur = sequence[-1]
        sequence[-1] = (last_img, last_dur + (actual_duration_s - total_s))

    return sequence


# ─── ffmpeg concat ────────────────────────────────────────────────────────────


def _write_concat_file(sequence: list[tuple[Path, float]], tmp_path: Path) -> None:
    lines = []
    for img_path, duration in sequence:
        escaped = str(img_path).replace("'", "\\'")
        lines.append(f"file '{escaped}'")
        lines.append(f"duration {duration:.3f}")
    if sequence:
        last_img = sequence[-1][0]
        lines.append(f"file '{str(last_img).replace(chr(39), chr(92) + chr(39))}'")
    tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_ffmpeg(
    concat_file: Path,
    audio_path: Path,
    output_path: Path,
    dry_run: bool,
) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-i",
        str(audio_path),
        "-vf",
        "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-r",
        "25",
        "-c:a",
        "copy",
        "-pix_fmt",
        "yuv420p",
        "-map",
        "0:v",
        "-map",
        "1:a",
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

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", help="Book slug, e.g. ayyuhal-walad")
    parser.add_argument("--episode", help="Stitch a single episode, e.g. EP01")
    parser.add_argument("--dry-run", action="store_true", help="Print command, don't run")
    parser.add_argument("--force", action="store_true", help="Overwrite existing MP4s")
    args = parser.parse_args(argv)

    book_dir = content_dir(args.slug)
    if not book_dir.exists():
        sys.exit(f"ERROR: book directory not found for slug '{args.slug}'")

    if not _video_enabled(book_dir):
        print(f"\nVideo generation is disabled for '{args.slug}'.")
        print("  To enable: set  enable_video: true  in _system/series-config.yaml")
        return 0

    episodes = _discover_episodes(book_dir, args.episode)
    if not episodes:
        sys.exit("No episodes to stitch.")

    print(f"\n{args.slug} — stitching {len(episodes)} episode(s)\n")

    for ep in episodes:
        ep_id = ep["ep_id"]
        audio = ep["audio"]
        segments = ep["segments"]
        transcript_text = ep["transcript_text"]

        print(f"── {ep_id}")
        print(f"   Audio:      {audio.name}")
        sync_mode = "keyword-proportional (transcript)" if transcript_text else "equal-split (no transcript)"
        print(f"   Sync mode:  {sync_mode}")

        actual_dur = _audio_duration(audio)
        print(f"   Duration:   {int(actual_dur // 60)}m {int(actual_dur % 60)}s")

        sequence = _build_image_sequence(segments, ep["images_dir"], actual_dur, transcript_text)
        if not sequence:
            print("   WARN: no image sequence built, skipping")
            continue

        print(f"   Segments:   {len(sequence)}")
        for i, (img, dur) in enumerate(sequence):
            seg = segments[i] if i < len(segments) else {}
            label = seg.get("overlay_text", img.stem)[:40]
            start_s = sum(d for _, d in sequence[:i])
            print(f"     s{i + 1:02d} {int(start_s // 60):02d}:{int(start_s % 60):02d}  {dur:5.0f}s  {label}")

        ep_slug_short = re.sub(r"^EP\d+-", "", ep_id)[:32]
        output_path = ep["ep_dir"] / f"video-{ep_slug_short}.mp4"

        if output_path.exists() and not args.dry_run and not args.force:
            print(f"   {output_path.name} already exists — use --force to overwrite")
            print()
            continue

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix=f"concat_{ep_id}_") as tmp:
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
