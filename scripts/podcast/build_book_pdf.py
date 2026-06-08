"""build_book_pdf.py — Phase 0book-render: book.md -> book/book.pdf.

Thin Python wrapper over plan-dashboard/scripts/render-book-pdf.mjs, which renders
the reading edition to a print PDF via the site's Playwright chromium (the same
browser the diagram renderer uses). The in-site reader view is the always-available
review surface; this produces the shippable PDF.

After rendering, two copies are written:
  book/book.pdf               — canonical pipeline name (unchanged, for tooling)
  book/{Edition Title}.pdf    — human-readable copy, name from book-toc.json

The edition-titled copy is also synced to Google Drive:
  My Drive/Podcast Library/{Series Title}/{Edition Title}.pdf

where {Series Title} comes from meta.yml ``title`` (the original work title used
as the per-book Drive folder name) and {Edition Title} from book-toc.json
``book_title`` (the authored reading-edition title).

GUARANTEED step (per plan): if the chromium binary is missing, this raises an
actionable AuthoringError naming the one-time setup command rather than skipping.

Standalone:
  python3 build_book_pdf.py <BOOK_DIR>
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _authoring._core import AuthoringError  # noqa: E402
from _paths import REPO_ROOT  # noqa: E402

_DASHBOARD = REPO_ROOT / "plan-dashboard"
_RENDER_SCRIPT = _DASHBOARD / "scripts" / "render-book-pdf.mjs"
_THEME_CSS = _DASHBOARD / "src" / "styles" / "theme.css"
_INSTALL_HINT = ("Run `npx playwright install chromium` in plan-dashboard/ "
                 "(one-time browser download), then re-run 0book-render.")

# Google Drive root for the Podcast Library.
# Structure: Podcast Library/{Series Title}/{Edition Title}.pdf
# Series Title  = meta.yml ``title``  (the original work title — used as folder name)
# Edition Title = book-toc.json ``book_title`` (the reading-edition title — used as PDF name)
_GDRIVE_LIBRARY = Path(
    "~/Library/CloudStorage/GoogleDrive-asifhussain60@gmail.com"
    "/My Drive/Podcast Library"
).expanduser()


def _edition_title(book_dir: Path) -> str:
    """Reading-edition title for the PDF filename.

    Priority:
    1. book/book-toc.json ``book_title`` — the authored reading-edition title
       (e.g. "The Book of the Master and the Boy").
    2. meta.yml ``title`` — original work title (fallback).
    3. slug (book_dir.name) — last resort.
    """
    toc = book_dir / "book" / "book-toc.json"
    if toc.exists():
        try:
            title = (json.loads(toc.read_text(encoding="utf-8")).get("book_title") or "").strip()
            if title:
                return title
        except Exception:
            pass
    return _series_title(book_dir)


def _series_title(book_dir: Path) -> str:
    """Original work title from meta.yml — used as the Drive per-book folder name."""
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


# Keep _book_title as a stable alias so callers outside this module don't break.
def _book_title(book_dir: Path) -> str:
    return _edition_title(book_dir)


def build_book(book_dir: Path, *, log=print, book_md: Path | None = None) -> Path:
    book_dir = Path(book_dir).resolve()
    # Prefer book-illustrated.md (from 0book-illustrate) when present; fall back to book.md.
    if book_md is None:
        illustrated = book_dir / "book" / "book-illustrated.md"
        book_md = illustrated if illustrated.exists() else book_dir / "book" / "book.md"
    book_md = Path(book_md)
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-render",
            message=f"missing {book_md} — run 0book-compose (and 0book-illustrate) first.",
            manual_fallback="python3 _book_compose.py <BOOK_DIR>")
    out_pdf = book_dir / "book" / "book.pdf"
    src_label = book_md.name

    log(f"    0book-render: {book_dir.name}: {src_label} -> book.pdf (Playwright)")
    proc = subprocess.run(
        ["node", str(_RENDER_SCRIPT), str(book_md.resolve()), str(out_pdf), str(_THEME_CSS)],
        cwd=_DASHBOARD, capture_output=True, text=True)
    if proc.returncode == 3:
        raise AuthoringError(
            phase="0book-render",
            message="Playwright chromium binary is not installed.",
            manual_fallback=_INSTALL_HINT)
    if proc.returncode != 0:
        raise AuthoringError(
            phase="0book-render",
            message=f"render-book-pdf.mjs exited rc={proc.returncode}.\n{proc.stderr[:600]}",
            manual_fallback="Inspect the Node error above; ensure `node` + Playwright are available.")
    if not out_pdf.exists():
        raise AuthoringError(
            phase="0book-render",
            message="render reported success but book.pdf was not written.",
            manual_fallback=_INSTALL_HINT)
    log(f"    0book-render: wrote {out_pdf.name} ({out_pdf.stat().st_size // 1024} KB)")

    # Write a titled copy alongside book.pdf so the PDF filename matches the book.
    # book.pdf stays in place for pipeline compatibility (export_distribution.py etc.).
    edition = _edition_title(book_dir)
    titled_pdf = out_pdf.parent / f"{edition}.pdf"
    try:
        shutil.copy2(str(out_pdf), str(titled_pdf))
        log(f"    0book-render: titled copy → {titled_pdf.name}")
    except Exception as exc:
        log(f"    0book-render: titled copy failed (non-fatal): {exc}")

    # Copy to Google Drive:  Podcast Library/{Series Title}/{Edition Title}.pdf
    # Series Title = meta.yml title (original work title, used as the per-book folder).
    # Edition Title = book-toc.json book_title (reading-edition title, used as PDF name).
    series = _series_title(book_dir)
    gdrive_dest = _GDRIVE_LIBRARY / series / f"{edition}.pdf"
    drive_copied = False
    if _GDRIVE_LIBRARY.exists():
        try:
            gdrive_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(out_pdf), str(gdrive_dest))
            log(f"    0book-render: Google Drive → Podcast Library/{series}/{gdrive_dest.name}")
            drive_copied = True
        except Exception as exc:
            log(f"    0book-render: Google Drive copy failed (non-fatal): {exc}")
    else:
        log(f"    0book-render: Google Drive Podcast Library not found — skipping Drive copy")

    if not drive_copied:
        # Surface the titled copy in Finder so Asif can drag it to Drive manually.
        import subprocess as _sp
        _sp.run(["open", str(titled_pdf.parent)], check=False)
        log(f"    0book-render: opened Finder → drag {titled_pdf.name} to Drive manually")

    return out_pdf


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: build_book_pdf.py <BOOK_DIR>", file=sys.stderr)
        return 2
    try:
        build_book(Path(args[0]))
        return 0
    except AuthoringError as e:
        print(f"ERROR [{e.phase}]: {e}\n  → {e.manual_fallback}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
