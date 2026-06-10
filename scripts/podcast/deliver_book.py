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
  python3 deliver_book.py <slug> [<target-folder>] [--dry-run]

  <target-folder> is optional. Default:
    ~/Library/CloudStorage/.../My Drive/Podcast Library/<series title>/
  where <series title> = meta.yml `title`.

  --dry-run  Print the proposed rename + copy plan without touching the filesystem.

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
import sys
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


# ─── delivery ────────────────────────────────────────────────────────────────

def deliver(
    slug: str,
    target: Path | str | None = None,
    *,
    dry_run: bool = False,
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

    pdf = _find_pdf(book_dir)
    ep_titles = _episode_titles(book_dir)
    audio_plan = _match_audio_to_episodes(book_dir, ep_titles)

    if not pdf and not audio_plan:
        log(f"ERROR: no PDF and no audio found for '{slug}'")
        return 1

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

    log(f"book-publisher: '{slug}'")
    log(f"  source  : {book_dir.relative_to(REPO_ROOT)}")
    log(f"  target  : {target_path}")
    log(f"  PDF     : {pdf.name if pdf else '(none)'} → {target_path.name}/")
    log(f"  audio   : {len(audio_plan)} file(s) → Episodes/"
        + (f" ({len(sessions)} sessions)" if sessions else ""))
    for src, ep_num, title in audio_plan:
        dest_name = f"EP-{ep_num:02d}-{title}.m4a"
        log(f"    EP-{ep_num:02d}  {src.name}")
        log(f"         → Episodes/{_episode_subpath(ep_num, dest_name)}")

    if dry_run:
        log("  [dry-run] no files written")
        return 0

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
            log(f"  ✗ {pdf.name} — {exc}")
            failures += 1

    # Audio → target/Episodes/ (per-session subfolders when sessioned)
    for src, ep_num, title in audio_plan:
        dest_name = f"EP-{ep_num:02d}-{title}.m4a"
        rel = _episode_subpath(ep_num, dest_name)
        dest = episodes_path / rel
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
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
    args = [a for a in args if not a.startswith("--")]
    slug = args[0]
    target = args[1] if len(args) > 1 else None
    return deliver(slug, target, dry_run=dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
