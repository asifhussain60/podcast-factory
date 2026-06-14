"""deliver_book.py — Copy a book's audio + reading-edition PDF to a delivery folder.

What gets delivered
  PDF → <target>/
    content/<Bucket>/<slug>/book/{Edition Title}.pdf (titled copy preferred; book.pdf fallback)

  Audio → <target>/Episodes/
    Each .m4a is renamed to:  EP-{NN}-{Episode Title}.m4a
    where {Episode Title} = H1 heading from episodes/EP{NN}-*.txt framing file.

    EP-number mapping for each m4a:
      1. If filename starts with NN-  (e.g. "04-Ismaili…")  →  use that number.
      2. Remaining files (no numeric prefix): sort alphabetically, assign to
         unoccupied EP slots in ascending order.

    Only top-level .m4a files are delivered — v1/, v2/ subdirs are skipped.

Usage
  python3 deliver_book.py <slug> [<target-folder>]
          [--dry-run] [--format m4a|mp3] [--bitrate 192k] [--clean]

  <target-folder> is optional. Default:
    ~/Library/CloudStorage/.../My Drive/Podcast Library/<series title>/
  where <series title> = meta.yml `title`.

  --dry-run        Print the proposed rename + copy plan without touching the filesystem.
  --format <fmt>   Delivered audio format: m4a (default, verbatim copy) or mp3
                   (transcoded via ffmpeg). mp3 requires ffmpeg on PATH.
  --bitrate <rate> mp3 CBR bitrate (default 192k). Ignored for m4a.
  --clean          Wipe the target's Episodes/ tree and any prior PDF before
                   writing, so only the latest delivered set survives. Important
                   when switching format (old .m4a would otherwise linger).

Notes
  - shutil.copy2 is used directly for Drive paths. Do NOT test with `ls` first —
    ~/Library/CloudStorage/ always says "Operation not permitted" from ls even
    when the copy succeeds. See memory: feedback_google_drive_publish.md.
  - The target folder and the Episodes/ subfolder are created if absent.
  - Existing files are overwritten (idempotent).
  - Exit codes: 0 = all files copied, 1 = one or more copies failed, 2 = usage error.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import find_content, REPO_ROOT  # noqa: E402
from _sessions import load_sessions_for_book, session_for_episode  # noqa: E402

_GDRIVE_LIBRARY = Path(
    "~/Library/CloudStorage/GoogleDrive-asifhussain60@gmail.com"
    "/My Drive/Podcast Library"
).expanduser()


# ─── title helpers ───────────────────────────────────────────────────────────

def _edition_title(book_dir: Path) -> str | None:
    """Reading-edition title from book-toc.json (used as the PDF filename)."""
    toc = book_dir / "book" / "book-toc.json"
    if toc.exists():
        try:
            title = (json.loads(toc.read_text(encoding="utf-8")).get("book_title") or "").strip()
            if title:
                return title
        except Exception:
            pass
    return None


def _series_title(book_dir: Path) -> str:
    """Original work title from meta.yml (used as the Drive per-book folder name)."""
    meta = book_dir / "meta.yml"
    if meta.exists():
        try:
            import yaml  # type: ignore[import]
            title = (yaml.safe_load(meta.read_text(encoding="utf-8")) or {}).get("title", "").strip()
            if title:
                return title
        except Exception:
            pass
    return book_dir.name


# ─── episode title map ───────────────────────────────────────────────────────

def _episode_titles(book_dir: Path) -> dict[int, str]:
    """Return {ep_number: title} from H1 headings in episodes/EP*.txt framing files."""
    ep_map: dict[int, str] = {}
    episodes_dir = book_dir / "episodes"
    if not episodes_dir.exists():
        return ep_map
    for txt in sorted(episodes_dir.glob("EP*.txt")):
        m = re.match(r"EP(\d+)", txt.name)
        if not m:
            continue
        ep_num = int(m.group(1))
        try:
            for line in txt.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("# "):
                    ep_map[ep_num] = line[2:].strip()
                    break
        except Exception:
            pass
    return ep_map


# ─── file discovery ──────────────────────────────────────────────────────────

def _find_pdf(book_dir: Path) -> Path | None:
    """Return the best PDF to deliver (titled copy preferred, book.pdf fallback)."""
    book_sub = book_dir / "book"
    if not book_sub.exists():
        return None
    edition = _edition_title(book_dir)
    if edition:
        titled = book_sub / f"{edition}.pdf"
        if titled.exists():
            return titled
    canonical = book_sub / "book.pdf"
    return canonical if canonical.exists() else None


def _match_audio_to_episodes(
    book_dir: Path,
    ep_titles: dict[int, str],
) -> list[tuple[Path, int, str]]:
    """Return [(src_path, ep_number, episode_title), ...] sorted by ep_number.

    Matching rules:
    1. Files with a leading NN- prefix (e.g. "04-…") → use that number.
    2. Unprefixed files: sort alphabetically, assign to unoccupied EP slots ascending.
    """
    m4a_dir = book_dir / "m4a"
    if not m4a_dir.exists():
        return []

    all_files = sorted(f for f in m4a_dir.iterdir() if f.is_file() and f.suffix == ".m4a")

    prefixed: dict[int, Path] = {}
    unprefixed: list[Path] = []
    for f in all_files:
        m = re.match(r"^(\d+)-", f.name)
        if m:
            prefixed[int(m.group(1))] = f
        else:
            unprefixed.append(f)

    # Fill gaps with unprefixed files (sorted alphabetically).
    all_ep_nums = sorted(ep_titles.keys()) if ep_titles else list(range(1, len(all_files) + 1))
    occupied = set(prefixed.keys())
    gaps = [n for n in all_ep_nums if n not in occupied]
    for ep_num, f in zip(gaps, sorted(unprefixed)):
        prefixed[ep_num] = f

    # Build result; fall back gracefully when ep_titles is empty.
    result: list[tuple[Path, int, str]] = []
    for ep_num in sorted(prefixed.keys()):
        src = prefixed[ep_num]
        title = ep_titles.get(ep_num) or src.stem.replace("_", " ")
        result.append((src, ep_num, title))
    return result


# ─── default target ──────────────────────────────────────────────────────────

def _default_target(book_dir: Path) -> Path:
    return _GDRIVE_LIBRARY / _series_title(book_dir)


# ─── audio transcode ─────────────────────────────────────────────────────────

# Supported delivery formats. Default (m4a) is a verbatim copy; mp3 is transcoded
# via ffmpeg. To add a future format (e.g. opus), add an entry here and a branch
# in _transcode().
AUDIO_FORMATS = ("m4a", "mp3")
DEFAULT_MP3_BITRATE = "192k"


def _ffmpeg() -> str | None:
    """Return the ffmpeg executable path, or None if not installed."""
    return shutil.which("ffmpeg")


def _transcode(src: Path, dst: Path, *, audio_format: str, mp3_bitrate: str) -> None:
    """Produce ``dst`` from ``src`` in ``audio_format``.

    m4a → straight copy. mp3 → ffmpeg transcode (libmp3lame, CBR, stereo,
    source sample-rate preserved, container metadata copied). Raises on failure.
    """
    if audio_format == "m4a":
        shutil.copy2(src, dst)
        return
    if audio_format == "mp3":
        cmd = [
            _ffmpeg() or "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src),
            "-codec:a", "libmp3lame", "-b:a", mp3_bitrate,
            "-map_metadata", "0",
            str(dst),
        ]
        subprocess.run(cmd, check=True)
        return
    raise ValueError(f"unsupported audio_format: {audio_format!r}")


# ─── delivery ────────────────────────────────────────────────────────────────

def deliver(
    slug: str,
    target: Path | str | None = None,
    *,
    dry_run: bool = False,
    audio_format: str = "m4a",
    mp3_bitrate: str = DEFAULT_MP3_BITRATE,
    clean: bool = False,
    log=print,
) -> int:
    """Deliver audio (Episodes/) + PDF for ``slug`` to ``target``.

    Returns 0 on full success, 1 if any copy fails, 2 on bad input.
    """
    found = find_content(slug)
    if found is None:
        log(f"ERROR: slug '{slug}' not found under content/")
        return 2
    _, _, book_dir = found

    if audio_format not in AUDIO_FORMATS:
        log(f"ERROR: unsupported --format '{audio_format}' (choose: {', '.join(AUDIO_FORMATS)})")
        return 2
    if audio_format == "mp3" and _ffmpeg() is None:
        log("ERROR: --format mp3 requires ffmpeg, which is not installed (brew install ffmpeg)")
        return 2

    pdf = _find_pdf(book_dir)
    ep_titles = _episode_titles(book_dir)
    audio_plan = _match_audio_to_episodes(book_dir, ep_titles)

    if not pdf and not audio_plan:
        log(f"ERROR: no PDF and no audio found for '{slug}'")
        return 1

    ext = audio_format  # delivered-file extension
    target_path = Path(target).expanduser() if target else _default_target(book_dir)
    episodes_path = target_path / "Episodes"

    # Session grouping (presence-gated): sessioned books deliver audio into
    # Episodes/Session N — Title/ subfolders; flat books keep Episodes/ flat.
    sessions = load_sessions_for_book(book_dir)

    def _episode_subpath(ep_num: int, dest_name: str) -> str:
        s = session_for_episode(sessions, ep_num)
        if s is None:
            return dest_name
        return f"Session {s['session_index']} — {s['session_title']}/{dest_name}"

    fmt_note = audio_format + (f" @{mp3_bitrate}" if audio_format == "mp3" else " (verbatim copy)")
    log(f"book-publisher: '{slug}'")
    log(f"  source  : {book_dir.relative_to(REPO_ROOT)}")
    log(f"  target  : {target_path}")
    log(f"  format  : {fmt_note}")
    if clean:
        log("  clean   : wipe existing Episodes/ + prior PDF(s) before writing")
    log(f"  PDF     : {pdf.name if pdf else '(none)'} → {target_path.name}/")
    log(f"  audio   : {len(audio_plan)} file(s) → Episodes/"
        + (f" ({len(sessions)} sessions)" if sessions else ""))
    for src, ep_num, title in audio_plan:
        dest_name = f"EP-{ep_num:02d}-{title}.{ext}"
        log(f"    EP-{ep_num:02d}  {src.name}")
        log(f"         → Episodes/{_episode_subpath(ep_num, dest_name)}")

    if dry_run:
        log("  [dry-run] no files written")
        return 0

    # Clean step — remove stale target content so only the latest set survives.
    # Done before writes; matters most when switching audio_format (old .m4a
    # would otherwise sit beside the new .mp3).
    #
    # Google Drive / macOS TCC caveat: a process WITHOUT Full Disk Access can
    # CREATE new files in the CloudStorage mount but CANNOT delete/overwrite a
    # file Drive has already synced (EPERM "Operation not permitted"). Directory
    # listing is also blocked, so glob() silently returns nothing — we therefore
    # unlink the EXACT known dest paths rather than scanning. If a delete is
    # refused, the file must be removed in Finder / drive.google.com (the Drive
    # app has the entitlement), or grant Full Disk Access to the controlling app.
    def _eperm_hint(exc: Exception) -> str:
        if isinstance(exc, PermissionError):
            return (" — Drive blocks mutating already-synced files without Full "
                    "Disk Access; delete it in Finder/drive.google.com or grant FDA")
        return ""

    if clean:
        if episodes_path.exists():
            try:
                shutil.rmtree(episodes_path)
                log("  ✓ wiped existing Episodes/")
            except Exception as exc:
                log(f"  ✗ wiping Episodes/ — {exc}{_eperm_hint(exc)}")
        if pdf:
            stale_pdf = target_path / pdf.name
            try:
                stale_pdf.unlink(missing_ok=True)
                log(f"  ✓ removed stale {pdf.name}")
            except Exception as exc:
                log(f"  ✗ removing {pdf.name} — {exc}{_eperm_hint(exc)}")

    target_path.mkdir(parents=True, exist_ok=True)
    episodes_path.mkdir(parents=True, exist_ok=True)

    failures = 0

    # PDF → target root
    if pdf:
        dest = target_path / pdf.name
        try:
            shutil.copy2(pdf, dest)
            log(f"  ✓ {pdf.name} ({dest.stat().st_size // 1024} KB)")
        except Exception as exc:
            log(f"  ✗ {pdf.name} — {exc}{_eperm_hint(exc)}")
            failures += 1

    # Audio → target/Episodes/ (per-session subfolders when sessioned).
    # mp3 is transcoded into a scratch dir first, then copied to the target so
    # no transient mp3 is left in the repo or a half-written file on Drive.
    with tempfile.TemporaryDirectory(prefix="deliver-mp3-") as scratch:
        scratch_dir = Path(scratch)
        for src, ep_num, title in audio_plan:
            dest_name = f"EP-{ep_num:02d}-{title}.{ext}"
            rel = _episode_subpath(ep_num, dest_name)
            dest = episodes_path / rel
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if audio_format == "m4a":
                    shutil.copy2(src, dest)
                else:
                    staged = scratch_dir / dest_name
                    _transcode(src, staged, audio_format=audio_format, mp3_bitrate=mp3_bitrate)
                    shutil.copy2(staged, dest)
                    staged.unlink(missing_ok=True)
                log(f"  ✓ Episodes/{rel} ({dest.stat().st_size // 1024} KB)")
            except Exception as exc:
                log(f"  ✗ Episodes/{rel} — {exc}")
                failures += 1

    total = (1 if pdf else 0) + len(audio_plan)
    copied = total - failures
    log(f"  {copied}/{total} delivered → {target_path}")
    return 0 if failures == 0 else 1


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    dry_run = "--dry-run" in args
    clean = "--clean" in args

    # --format <fmt> and --bitrate <rate> consume the following token.
    audio_format = "m4a"
    mp3_bitrate = DEFAULT_MP3_BITRATE
    for flag, setter in (("--format", "fmt"), ("--bitrate", "rate")):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"ERROR: {flag} requires a value", file=sys.stderr)
                return 2
            val = args[i + 1]
            if setter == "fmt":
                audio_format = val
            else:
                mp3_bitrate = val
            del args[i:i + 2]

    positional = [a for a in args if not a.startswith("--")]
    slug = positional[0]
    target = positional[1] if len(positional) > 1 else None
    return deliver(
        slug, target,
        dry_run=dry_run,
        audio_format=audio_format,
        mp3_bitrate=mp3_bitrate,
        clean=clean,
    )


if __name__ == "__main__":
    raise SystemExit(main())
