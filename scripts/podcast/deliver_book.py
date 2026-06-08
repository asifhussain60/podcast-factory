"""deliver_book.py — Copy a book's audio + reading-edition PDF to a delivery folder.

What gets delivered
  content/<Bucket>/<slug>/m4a/*.m4a     → <target>/     (top-level only; v1/, v2/ skipped)
  content/<Bucket>/<slug>/book/<Title>.pdf → <target>/  (titled copy preferred; book.pdf fallback)

Usage
  python3 deliver_book.py <slug> [<target-folder>] [--dry-run]

  If <target-folder> is omitted the default Drive path is used:
    ~/Library/CloudStorage/.../My Drive/Podcast Library/<series title>/
  where <series title> = meta.yml `title`.

  --dry-run  Print what would be copied without touching the filesystem.

Notes
  - `shutil.copy2` is used directly. Do NOT pre-check the path with `ls` —
    ~/Library/CloudStorage/ always returns "Operation not permitted" from ls
    even when copy succeeds. See memory: feedback_google_drive_publish.md.
  - The target folder is created if it does not exist (mkdir parents=True).
  - Existing files at the destination are overwritten (idempotent).
  - Exit codes: 0 = all files copied, 1 = one or more copies failed, 2 = usage error.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import find_content, REPO_ROOT  # noqa: E402

_GDRIVE_LIBRARY = Path(
    "~/Library/CloudStorage/GoogleDrive-asifhussain60@gmail.com"
    "/My Drive/Podcast Library"
).expanduser()


# ─── title helpers ───────────────────────────────────────────────────────────

def _edition_title(book_dir: Path) -> str | None:
    """Reading-edition title from book-toc.json (the PDF filename)."""
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
    """Original work title from meta.yml (used as the Drive folder name)."""
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


# ─── file discovery ──────────────────────────────────────────────────────────

def _find_pdf(book_dir: Path) -> Path | None:
    """Return the best PDF to deliver.

    Preference order:
    1. book/{Edition Title}.pdf  — titled reading-edition copy
    2. book/book.pdf             — canonical pipeline name
    """
    book_sub = book_dir / "book"
    if not book_sub.exists():
        return None
    edition = _edition_title(book_dir)
    if edition:
        titled = book_sub / f"{edition}.pdf"
        if titled.exists():
            return titled
    canonical = book_sub / "book.pdf"
    if canonical.exists():
        return canonical
    return None


def _find_audio(book_dir: Path) -> list[Path]:
    """Return top-level .m4a files from m4a/ (excludes v1/, v2/, etc.)."""
    m4a_dir = book_dir / "m4a"
    if not m4a_dir.exists():
        return []
    return sorted(f for f in m4a_dir.iterdir() if f.is_file() and f.suffix == ".m4a")


# ─── delivery ────────────────────────────────────────────────────────────────

def _default_target(book_dir: Path) -> Path:
    return _GDRIVE_LIBRARY / _series_title(book_dir)


def deliver(
    slug: str,
    target: Path | str | None = None,
    *,
    dry_run: bool = False,
    log=print,
) -> int:
    """Deliver audio + PDF for ``slug`` to ``target``.

    Returns 0 on full success, 1 if any copy fails.
    """
    found = find_content(slug)
    if found is None:
        log(f"ERROR: slug '{slug}' not found under content/")
        return 2
    _, _, book_dir = found

    pdf = _find_pdf(book_dir)
    audio = _find_audio(book_dir)

    if not pdf and not audio:
        log(f"ERROR: no PDF and no audio found for '{slug}'")
        return 1

    target_path = Path(target).expanduser() if target else _default_target(book_dir)

    log(f"book-publisher: delivering '{slug}'")
    log(f"  source : {book_dir.relative_to(REPO_ROOT)}")
    log(f"  target : {target_path}")
    log(f"  PDF    : {pdf.name if pdf else '(none)'}")
    log(f"  audio  : {len(audio)} file(s)")
    if dry_run:
        log("  [dry-run] no files written")
        for f in ([pdf] if pdf else []) + audio:
            log(f"    would copy → {target_path / f.name}")
        return 0

    target_path.mkdir(parents=True, exist_ok=True)

    failures = 0
    for src in ([pdf] if pdf else []) + audio:
        dest = target_path / src.name
        try:
            shutil.copy2(src, dest)
            size_kb = dest.stat().st_size // 1024
            log(f"  ✓ {src.name} ({size_kb} KB)")
        except Exception as exc:
            log(f"  ✗ {src.name} — {exc}")
            failures += 1

    total = (1 if pdf else 0) + len(audio)
    copied = total - failures
    log(f"  {copied}/{total} files delivered to {target_path}")
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
