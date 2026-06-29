#!/usr/bin/env python3
"""export_distribution.py — Copy finished book assets to a distribution folder.

Assembles a clean handoff package from the pipeline's canonical locations and
copies (never moves) to Google Drive or an explicit output directory.

Package layout:
    <output-root>/
      Podcast Library/
        <Book Title>/
          <Book Title>.pdf          ← book/book.pdf
          Episodes/
            Audio/
              EP01 - <Human Title>.m4a
              ...
            Video/
              EP01 - <Human Title>.mp4
              ...

USAGE

    # Auto-detect Google Drive; default target
    python3 scripts/podcast/export_distribution.py <book-slug>

    # Explicit output root (for CI or non-Drive machines)
    python3 scripts/podcast/export_distribution.py <book-slug> --output-dir ~/Desktop/export

    # Dry-run: print what would be copied without copying
    python3 scripts/podcast/export_distribution.py <book-slug> --dry-run

NOTES

    - Idempotent: safe to re-run; existing files are overwritten.
    - Graceful: missing assets are warned, not fatal.
    - The Google Drive mount is auto-detected from ~/Library/CloudStorage/.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _paths import resolve_content  # noqa: E402

GOOGLE_DRIVE_CLOUD = Path.home() / "Library" / "CloudStorage"
PODCAST_LIBRARY    = "Podcast Library"


# ─── Google Drive detection ───────────────────────────────────────────────────

def _find_google_drive_root() -> Path | None:
    """Return the 'My Drive' root if Google Drive Desktop is mounted.

    macOS CloudStorage uses a virtual FUSE-like filesystem where Path.exists()
    on the GoogleDrive-* subdirectory raises PermissionError even when the
    actual drive is accessible for reads/writes.  We therefore skip the
    existence check on the inner path and return it unconditionally — the
    subsequent mkdir / shutil.copy2 call will fail gracefully if wrong.
    """
    if not GOOGLE_DRIVE_CLOUD.exists():
        return None
    try:
        for entry in sorted(GOOGLE_DRIVE_CLOUD.iterdir()):
            if entry.name.startswith("GoogleDrive-"):
                return entry / "My Drive"
    except PermissionError:
        pass
    return None


# ─── Meta + naming helpers ────────────────────────────────────────────────────

def _read_title(book_dir: Path) -> str:
    """Read title from meta.yml; fall back to slug."""
    meta = book_dir / "meta.yml"
    if meta.exists():
        for line in meta.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^title:\s*['\"]?(.+?)['\"]?\s*$", line)
            if m:
                return m.group(1).strip()
    return book_dir.name.replace("-", " ").title()


_LOWERCASE_WORDS = frozenset({
    "a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet",
    "at", "by", "in", "of", "on", "to", "up", "as", "if",
})


def _title_case(slug: str) -> str:
    """Convert kebab-slug to title case, keeping articles/preps lowercase mid-title."""
    words = slug.replace("-", " ").split()
    out = []
    for i, w in enumerate(words):
        if i == 0 or i == len(words) - 1 or w.lower() not in _LOWERCASE_WORDS:
            out.append(w.capitalize())
        else:
            out.append(w.lower())
    return " ".join(out)


def _ep_human_title(ep_dir_name: str) -> tuple[str, str]:
    """'EP01-knowledge-without-action' → ('01', 'Knowledge Without Action')."""
    m = re.match(r"^EP(\d+)-(.+)$", ep_dir_name)
    if not m:
        return ("??", ep_dir_name)
    return m.group(1), _title_case(m.group(2))


def _ep_label(num: str, human: str) -> str:
    return f"EP{num} - {human}"


# ─── Asset discovery ──────────────────────────────────────────────────────────

def _find_pdf(book_dir: Path) -> Path | None:
    pdf = book_dir / "book" / "book.pdf"
    return pdf if pdf.exists() else None


def _find_audio(book_dir: Path) -> dict[str, Path]:
    """Return {ep_num: path} for all m4a files in m4a/ dir."""
    m4a_dir = book_dir / "m4a"
    result: dict[str, Path] = {}
    if not m4a_dir.exists():
        return result
    for f in sorted(m4a_dir.glob("ch*.m4a")):
        m = re.match(r"^ch(\d+)", f.stem)
        if m:
            result[m.group(1)] = f
    return result


def _find_video(book_dir: Path) -> dict[str, Path]:
    """Return {ep_num: path} for one MP4 per episode directory."""
    episodes_dir = book_dir / "episodes"
    result: dict[str, Path] = {}
    if not episodes_dir.exists():
        return result
    for ep_dir in sorted(episodes_dir.iterdir()):
        if not ep_dir.is_dir():
            continue
        m = re.match(r"^EP(\d+)-", ep_dir.name)
        if not m:
            continue
        mp4s = sorted(ep_dir.glob("video-*.mp4"))
        if mp4s:
            result[m.group(1)] = mp4s[0]
    return result


def _episode_map(book_dir: Path) -> dict[str, str]:
    """Return {ep_num: human_title} from episode .txt files or directories.

    The type-first layout stores episodes as flat EP##-<slug>.txt files;
    older books used EP##-<slug>/ subdirectories.  Both forms are scanned.
    """
    episodes_dir = book_dir / "episodes"
    result: dict[str, str] = {}
    if not episodes_dir.exists():
        return result
    for ep_entry in sorted(episodes_dir.iterdir()):
        if ep_entry.is_dir():
            name = ep_entry.name
        elif ep_entry.suffix == ".txt":
            name = ep_entry.stem          # strip .txt → EP##-<slug>
        else:
            continue
        num, human = _ep_human_title(name)
        if num != "??":
            result[num] = human
    return result


# ─── Core export logic ────────────────────────────────────────────────────────

def _copy(src: Path, dst: Path, dry_run: bool) -> bool:
    try:
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        size_mb = src.stat().st_size / (1024 * 1024)
        label = "would copy" if dry_run else "copied"
        print(f"  {label}: {src.name} → {dst.name} ({size_mb:.0f} MB)")
        return True
    except Exception as exc:
        print(f"  WARN: failed to copy {src.name}: {exc}", file=sys.stderr)
        return False


def export(
    slug: str,
    output_root: Path | None = None,
    dry_run: bool = False,
) -> int:
    """Export distribution package for `slug`.

    Returns 0 on success (including partial — missing assets are warned).
    Returns 1 if the book directory is not found.
    """
    book_dir = resolve_content(slug)
    if not book_dir.exists():
        print(f"export_distribution: book dir not found for '{slug}'",
              file=sys.stderr)
        return 1

    title = _read_title(book_dir)

    # Resolve output root: explicit > Google Drive > fail
    if output_root is None:
        drive = _find_google_drive_root()
        if drive is None:
            print(
                "export_distribution: Google Drive not mounted and no --output-dir "
                "supplied; skipping export.",
                file=sys.stderr,
            )
            return 0   # non-fatal — publish succeeded, export skipped
        output_root = drive

    dest_book   = output_root / PODCAST_LIBRARY / title
    dest_audio  = dest_book / "Episodes" / "Audio"
    dest_video  = dest_book / "Episodes" / "Video"

    if not dry_run:
        dest_audio.mkdir(parents=True, exist_ok=True)
        dest_video.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Distribution export: {slug} ===")
    print(f"    title:  {title}")
    print(f"    target: {dest_book}")
    print()

    ep_titles = _episode_map(book_dir)
    copied = 0
    skipped = 0

    # PDF
    pdf = _find_pdf(book_dir)
    if pdf:
        if _copy(pdf, dest_book / f"{title}.pdf", dry_run):
            copied += 1
    else:
        print(f"  WARN: book/book.pdf not found — PDF not exported")
        skipped += 1

    # Audio
    audio_map = _find_audio(book_dir)
    for num, src in sorted(audio_map.items()):
        human = ep_titles.get(num, f"Episode {num}")
        dst   = dest_audio / f"{_ep_label(num, human)}.m4a"
        if _copy(src, dst, dry_run):
            copied += 1

    if not audio_map:
        print(f"  WARN: no m4a files found in {book_dir / 'm4a'}")
        skipped += 1

    # Video
    video_map = _find_video(book_dir)
    for num, src in sorted(video_map.items()):
        human = ep_titles.get(num, f"Episode {num}")
        dst   = dest_video / f"{_ep_label(num, human)}.mp4"
        if _copy(src, dst, dry_run):
            copied += 1

    if not video_map:
        print(f"  WARN: no video/*.mp4 files found in {book_dir / 'episodes'}")
        skipped += 1

    status = "DRY RUN — " if dry_run else ""
    print(f"\n  {status}{copied} file(s) copied, {skipped} asset(s) missing.")
    if not dry_run and copied > 0:
        print(f"  Google Drive Desktop will sync from: {dest_book}")
    return 0


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("slug", help="Book slug, e.g. ayyuhal-walad")
    parser.add_argument(
        "--output-dir", metavar="DIR",
        help="Root output directory (default: auto-detect Google Drive My Drive)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be copied without writing anything",
    )
    args = parser.parse_args(argv)

    out = Path(args.output_dir).expanduser() if args.output_dir else None
    return export(args.slug, output_root=out, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
