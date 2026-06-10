#!/usr/bin/env python3
"""inject_slide_deck.py — place a NotebookLM-exported slide deck inline in the
reading edition.

Optional, manual-invocation step (decks are exported from NotebookLM by hand,
so this is NOT an orchestrator phase). When a book has a polished deck PDF in
slide-deck/ plus a slide-manifest.json mapping slides to teaching passages,
this script:

  1. Extracts deck pages to slide-deck/_pages/page-NN.png via pdftoppm
     (poppler — already installed; no pip dependency).
  2. Reads book/book-illustrated.md (or book/book.md if absent), strips any
     previously injected slide figures, and re-injects one
     <figure class="book-diagram book-slide"> block per anchored slide,
     immediately after the paragraph containing its verbatim anchor_text —
     the same anchor mechanics as _book_illustrate._inject_figures, with one
     deliberate hardening: a missing OR ambiguous anchor fails loudly naming
     the slide_id (no silent skips).
  3. Writes book/book-slides.md. build_book_pdf.py prefers it over
     book-illustrated.md/book.md, so the next 0book-render picks it up.
     book.md and book-illustrated.md are never mutated.

MANIFEST  slide-deck/slide-manifest.json — list of entries:
  {"slide_id": "ch01-s02", "page": 2, "title": "...",
   "anchor_text": "verbatim 20-70 char substring of the book md" | null}
anchor_text null = combined-deck-only slide (e.g. the cover): validated
against the page count but never injected inline. slide_ids are chapter-keyed
(chNN-sNN), not episode-keyed — chapter/episode boundaries aren't 1:1 here.

USAGE
    python3 scripts/podcast/inject_slide_deck.py <slug-or-BOOK_DIR> [--force]

--force re-extracts the PNG pages even if present. Re-runs are idempotent.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _authoring._core import AuthoringError  # noqa: E402
from _paths import resolve_content  # noqa: E402

_PHASE = "slide-inject"
_DPI = 150
# JPEG, not PNG: NotebookLM decks carry textured raster backgrounds that PNG
# compresses poorly (~3 MB/page -> ~60 MB PDF). Quality 85 is visually clean
# for inline reading figures at this size.
_JPEG_QUALITY = 85
_PAGE_RE = re.compile(r"-(\d+)\.(?:png|jpg)$")
_SLIDE_FIGURE_RE = re.compile(
    r'<figure class="book-diagram book-slide">.*?</figure>\n*', re.DOTALL)
_REQUIRED_KEYS = ("slide_id", "page", "title", "anchor_text")


def load_manifest(manifest_path: Path) -> list[dict]:
    """Load + validate slide-manifest.json. Raises AuthoringError on any defect."""
    try:
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AuthoringError(phase=_PHASE, message=f"unreadable {manifest_path}: {exc}")
    if not isinstance(entries, list) or not entries:
        raise AuthoringError(phase=_PHASE, message=f"{manifest_path} must be a non-empty JSON list")

    seen: set[str] = set()
    for i, e in enumerate(entries):
        missing = [k for k in _REQUIRED_KEYS if k not in e]
        if missing:
            raise AuthoringError(
                phase=_PHASE,
                message=f"{manifest_path} entry {i} missing key(s): {', '.join(missing)}")
        if not isinstance(e["page"], int) or e["page"] < 1:
            raise AuthoringError(
                phase=_PHASE, message=f"slide {e['slide_id']}: page must be an int >= 1")
        if e["slide_id"] in seen:
            raise AuthoringError(
                phase=_PHASE, message=f"duplicate slide_id in manifest: {e['slide_id']}")
        seen.add(e["slide_id"])
    return entries


def _page_map(pages_dir: Path) -> dict[int, Path]:
    """Map page number -> image path, tolerant of pdftoppm's padding variants
    (page-1.jpg vs page-01.jpg — poppler pads to the digit count of the last page)."""
    out: dict[int, Path] = {}
    for img in list(pages_dir.glob("*.jpg")) + list(pages_dir.glob("*.png")):
        m = _PAGE_RE.search(img.name)
        if m:
            out[int(m.group(1))] = img
    return out


def extract_pages(deck_pdf: Path, pages_dir: Path, *, force: bool = False, log=print) -> int:
    """pdftoppm the deck to pages_dir/page-NN.png; return the extracted page count."""
    if force and pages_dir.exists():
        shutil.rmtree(pages_dir)
    existing = _page_map(pages_dir) if pages_dir.exists() else {}
    if existing:
        log(f"    {_PHASE}: {len(existing)} page PNGs present — skipping extraction (use --force to redo)")
        return len(existing)

    pages_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["pdftoppm", "-jpeg", "-jpegopt", f"quality={_JPEG_QUALITY}",
         "-r", str(_DPI), str(deck_pdf), str(pages_dir / "page")],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise AuthoringError(
            phase=_PHASE,
            message=f"pdftoppm failed rc={proc.returncode}: {proc.stderr[:400]}",
            manual_fallback="Install poppler (`brew install poppler`) and retry.")
    count = len(_page_map(pages_dir))
    if count == 0:
        raise AuthoringError(
            phase=_PHASE, message=f"pdftoppm produced no PNGs from {deck_pdf.name}")
    log(f"    {_PHASE}: extracted {count} pages from {deck_pdf.name} at {_DPI} dpi")
    return count


def strip_slide_figures(book_md: str) -> str:
    """Remove previously injected book-slide figures (idempotent re-run support).
    Plain book-diagram figures from 0book-illustrate are untouched."""
    return _SLIDE_FIGURE_RE.sub("", book_md)


def inject_slides(book_md: str, entries: list[dict], *, pages: dict[int, str]) -> str:
    """Inject one figure per anchored slide after its anchor paragraph.

    ``pages`` maps page number -> extracted image filename (from _page_map),
    so the figure src always matches a file that actually exists.

    Fail-loud contract (vs. _book_illustrate's soft-skip): every defect is
    collected and reported in ONE error naming the slide_ids, so a re-run
    after fixing the manifest converges instead of whack-a-mole."""
    result = strip_slide_figures(book_md)
    problems: list[str] = []
    insertions: list[tuple[int, str]] = []

    for e in entries:
        sid, page, anchor = e["slide_id"], e["page"], e["anchor_text"]
        if page not in pages:
            problems.append(f"{sid}: page {page} has no extracted image "
                            f"({len(pages)} pages present)")
            continue
        if anchor is None:  # combined-deck-only slide (cover) — never inline
            continue
        anchor = anchor.strip()
        first = result.find(anchor)
        if first == -1:
            problems.append(f"{sid}: anchor not found: {anchor[:60]!r}")
            continue
        if result.find(anchor, first + 1) != -1:
            problems.append(f"{sid}: anchor matches more than once: {anchor[:60]!r}")
            continue

        end_of_para = result.find("\n\n", first + len(anchor))
        insert_at = (end_of_para + 2) if end_of_para != -1 else len(result)
        figure_block = (
            f'<figure class="book-diagram book-slide">\n'
            f'<img src="slide-deck/_pages/{pages[page]}" alt="{e["title"]}">\n'
            f'<figcaption>{e["title"]}</figcaption>\n'
            f'</figure>\n\n'
        )
        insertions.append((insert_at, figure_block))

    if problems:
        raise AuthoringError(
            phase=_PHASE,
            message="slide injection failed — fix slide-manifest.json:\n  "
                    + "\n  ".join(problems),
            manual_fallback="Anchors must be verbatim substrings occurring exactly once.")

    insertions.sort(key=lambda x: x[0], reverse=True)
    for pos, block in insertions:
        result = result[:pos] + block + result[pos:]
    return result


def inject_slide_deck(book_dir: Path, *, force: bool = False, log=print) -> Path:
    """Main entry: extract pages + inject figures; returns book/book-slides.md."""
    book_dir = Path(book_dir).resolve()
    deck_dir = book_dir / "slide-deck"
    deck_pdfs = sorted(deck_dir.glob("*.pdf")) if deck_dir.exists() else []
    if len(deck_pdfs) != 1:
        raise AuthoringError(
            phase=_PHASE,
            message=f"expected exactly one slide-deck/*.pdf in {book_dir.name}, "
                    f"found {len(deck_pdfs)}",
            manual_fallback="Export the deck from NotebookLM and place one PDF in slide-deck/.")
    manifest_path = deck_dir / "slide-manifest.json"
    if not manifest_path.exists():
        raise AuthoringError(
            phase=_PHASE,
            message=f"missing {manifest_path.relative_to(book_dir)}",
            manual_fallback="Author the slide manifest (slide_id/page/title/anchor_text per slide).")

    entries = load_manifest(manifest_path)
    pages_dir = deck_dir / "_pages"
    extract_pages(deck_pdfs[0], pages_dir, force=force, log=log)
    pages = {n: p.name for n, p in _page_map(pages_dir).items()}

    src = book_dir / "book" / "book-illustrated.md"
    if not src.exists():
        src = book_dir / "book" / "book.md"
    if not src.exists():
        raise AuthoringError(
            phase=_PHASE,
            message=f"no book/book-illustrated.md or book/book.md in {book_dir.name}",
            manual_fallback="Run 0book-compose (and 0book-illustrate) first.")

    out = inject_slides(src.read_text(encoding="utf-8"), entries, pages=pages)
    out_path = book_dir / "book" / "book-slides.md"
    out_path.write_text(out, encoding="utf-8")
    anchored = sum(1 for e in entries if e["anchor_text"])
    log(f"    {_PHASE}: {src.name} + {anchored} slides -> {out_path.name}")
    return out_path


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    if not args:
        print("usage: inject_slide_deck.py <slug-or-BOOK_DIR> [--force]", file=sys.stderr)
        return 2
    target = Path(args[0])
    book_dir = target if target.is_dir() else resolve_content(args[0])
    try:
        inject_slide_deck(book_dir, force=force)
    except AuthoringError as exc:
        print(f"[{exc.phase}] {exc}", file=sys.stderr)
        if exc.manual_fallback:
            print(f"  fallback: {exc.manual_fallback}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
