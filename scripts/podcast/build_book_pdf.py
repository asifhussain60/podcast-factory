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
from _authoring._core import AuthoringError
from _paths import REPO_ROOT

_DASHBOARD = REPO_ROOT / "plan-dashboard"
_RENDER_SCRIPT = _DASHBOARD / "scripts" / "render-book-pdf.mjs"
_THEME_CSS = _DASHBOARD / "src" / "styles" / "theme.css"
_INSTALL_HINT = (
    "Run `npx playwright install chromium` in plan-dashboard/ (one-time browser download), then re-run 0book-render."
)

# Google Drive root for the Podcast Library.
# Structure: Podcast Library/{Series Title}/{Edition Title}.pdf
# Series Title  = meta.yml ``title``  (the original work title — used as folder name)
# Edition Title = book-toc.json ``book_title`` (the reading-edition title — used as PDF name)
_GDRIVE_LIBRARY = Path(
    "~/Library/CloudStorage/GoogleDrive-asifhussain60@gmail.com/My Drive/Podcast Library"
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


def _pick_book_md(book_dir: Path) -> Path:
    """The render input is always the diagram-free book.md.

    Visuals are decoupled — figures come from the curated visual-layout.json,
    not from injected *-slides/-illustrated markdown — so 0book-compose's book.md
    is what the renderer consumes."""
    return book_dir / "book" / "book.md"


def build_book(
    book_dir: Path, *, log=print, book_md: Path | None = None, surface_finder: bool = True, self_study: bool = False
) -> Path:
    book_dir = Path(book_dir).resolve()
    if book_md is None:
        # The self-study deliverable renders the materialized book-self-study.md
        # (labeled Contextual-note + Study-summary asides); the reading edition
        # renders book.md. Either way the base book.md is never mutated.
        book_md = (book_dir / "book" / "book-self-study.md") if self_study else _pick_book_md(book_dir)
    book_md = Path(book_md)
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-render",
            message=f"missing {book_md} — run 0book-compose (and 0book-illustrate) first.",
            manual_fallback=(
                "python3 scripts/podcast/build_book_pdf.py --self-study <BOOK_DIR>"
                if self_study
                else "python3 scripts/podcast/orchestrate_book.py --resume <slug>"
            ),
        )
    out_pdf = book_dir / "book" / ("book-self-study.pdf" if self_study else "book.pdf")
    src_label = book_md.name

    # Cover page (2026-06-11): every reading edition gets a generated
    # book/cover.png (non-blocking — renders without one on any failure).
    from _book_cover import ensure_cover

    ensure_cover(book_dir, log=log)

    # The renderer honors book/visual-layout.json + the unified pagination CSS,
    # plus (when self_study) the opt-in self-study aside/list layer.
    log(f"    0book-render: {book_dir.name}: {src_label} -> {out_pdf.name} (Playwright)")
    proc = subprocess.run(
        [
            "node",
            str(_RENDER_SCRIPT),
            str(book_md.resolve()),
            str(out_pdf),
            str(_THEME_CSS),
            "1",
            "1" if self_study else "0",
        ],
        cwd=_DASHBOARD,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 3:
        raise AuthoringError(
            phase="0book-render", message="Playwright chromium binary is not installed.", manual_fallback=_INSTALL_HINT
        )
    if proc.returncode != 0:
        raise AuthoringError(
            phase="0book-render",
            message=f"render-book-pdf.mjs exited rc={proc.returncode}.\n{proc.stderr[:600]}",
            manual_fallback="Inspect the Node error above; ensure `node` + Playwright are available.",
        )
    if not out_pdf.exists():
        raise AuthoringError(
            phase="0book-render",
            message=f"render reported success but {out_pdf.name} was not written.",
            manual_fallback=_INSTALL_HINT,
        )
    log(f"    0book-render: wrote {out_pdf.name} ({out_pdf.stat().st_size // 1024} KB)")

    # The self-study edition is a distinct, in-repo study artifact
    # (book-self-study.pdf) — it does NOT get the edition-titled copy or the
    # Google Drive publish, which belong to the primary reading edition.
    if self_study:
        return out_pdf

    # Rename to the titled copy — the ONE PDF this book folder keeps. out_pdf was
    # only ever the Playwright render target; every consumer resolves the actual
    # deliverable through deliver_book._find_pdf (titled-preferred, book.pdf
    # fallback for the rare case this rename fails), never a hardcoded path, so
    # collapsing to one file needed no consumer left pointed at book.pdf.
    edition = _edition_title(book_dir)
    titled_pdf = out_pdf.parent / f"{edition}.pdf"
    try:
        out_pdf.replace(titled_pdf)
        log(f"    0book-render: titled → {titled_pdf.name}")
    except Exception as exc:
        # Keep the working file as the deliverable rather than lose the render.
        log(f"    0book-render: titled rename failed (non-fatal, keeping {out_pdf.name}): {exc}")
        titled_pdf = out_pdf

    # Copy to Google Drive:  Podcast Library/{Series Title}/{Edition Title}.pdf
    # Series Title = meta.yml title (original work title, used as the per-book folder).
    # Edition Title = book-toc.json book_title (reading-edition title, used as PDF name).
    series = _series_title(book_dir)
    gdrive_dest = _GDRIVE_LIBRARY / series / f"{edition}.pdf"
    drive_copied = False
    if _GDRIVE_LIBRARY.exists():
        try:
            gdrive_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(titled_pdf), str(gdrive_dest))
            log(f"    0book-render: Google Drive → Podcast Library/{series}/{gdrive_dest.name}")
            drive_copied = True
        except Exception as exc:
            log(f"    0book-render: Google Drive copy failed (non-fatal): {exc}")
    else:
        log("    0book-render: Google Drive Podcast Library not found — skipping Drive copy")

    if not drive_copied and surface_finder:
        # Surface the titled copy in Finder so Asif can drag it to Drive manually.
        # Skipped for API/headless renders (surface_finder=False) so a server-side
        # "Generate PDF" never pops a Finder window.
        import subprocess as _sp

        _sp.run(["open", str(titled_pdf.parent)], check=False)
        log(f"    0book-render: opened Finder → drag {titled_pdf.name} to Drive manually")

    # FINAL STEP of every PDF route. This is the seam the fiction builder also
    # comes through (build_fiction_book_pdf delegates here), so wiring it once
    # covers both. It reads the PDF a reader receives and records what would make
    # the book hard to follow — a term leaned on before it is explained, one idea
    # spelled two ways, a page carrying too many unexplained terms at once.
    # Report-only and non-fatal: a readability finding must never destroy a PDF
    # that was otherwise produced correctly.
    _final_comprehension_review(book_dir, log=log)

    return titled_pdf


def _final_comprehension_review(book_dir: Path, *, log=print) -> None:
    """Run the reader-facing review over the finished PDF. Never raises."""
    try:
        from _book_comprehension import run_comprehension_checks

        run_comprehension_checks(book_dir, log=log)
    except Exception as e:
        log(f"    comprehension: skipped (non-fatal): {e}")


def main() -> int:
    import json as _json

    argv = sys.argv[1:]
    as_json = "--json" in argv  # API/Composer mode: single JSON line, no Finder pop
    self_study = "--self-study" in argv
    skip_gen = "--no-generate" in argv  # render an existing book-self-study.md as-is
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print("usage: build_book_pdf.py <BOOK_DIR> [--json] [--self-study [--no-generate]]", file=sys.stderr)
        return 2
    book_dir = Path(args[0])
    log = (lambda *a: None) if as_json else print
    try:
        if self_study and not skip_gen:
            # Materialize book-self-study.md (study summaries + KB-grounded notes)
            # before rendering. $0 flat-rate claude -p; base book.md untouched.
            from _self_study import build_self_study_markdown

            build_self_study_markdown(book_dir, log=log)
        out = build_book(book_dir, log=log, surface_finder=not as_json, self_study=self_study)
        if as_json:
            print(_json.dumps({"ok": True, "pdf": str(out), "kb": out.stat().st_size // 1024}))
        return 0
    except AuthoringError as e:
        if as_json:
            print(_json.dumps({"ok": False, "error": str(e), "manual_fallback": e.manual_fallback}))
            return 1
        print(f"ERROR [{e.phase}]: {e}\n  → {e.manual_fallback}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
