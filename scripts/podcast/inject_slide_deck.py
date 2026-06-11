#!/usr/bin/env python3
"""inject_slide_deck.py — slide-deck → reading-edition injection primitives,
plus the manual BOOK-LEVEL import mode.

Two consumers:
  - Manual mode (this CLI): ONE NotebookLM-exported deck for the whole book at
    slide-decks/book-deck.pdf + slide-decks/_manifests/book-manifest.json
    (the-master-and-the-disciple pattern; manifest hand- or LLM-authored).
  - 0book-slide-import phase (_slide_import.py): PER-CHAPTER decks at
    slide-decks/chNN-<slug>.pdf with LLM-authored manifests — reuses every
    primitive here (extract_pages, pdf_page_texts, inject_slides, ...).

Mechanics:
  1. Extract deck pages to slide-decks/_pages/<key>/page-NN.jpg via pdftoppm
     (poppler — installed; no pip dependency; JPEG q85 — PNG balloons the PDF).
  2. Read book/book-illustrated.md (or book/book.md), strip previously injected
     slide figures, re-inject one <figure class="book-diagram book-slide"> per
     anchored slide at the paragraph containing its verbatim anchor_text —
     by default BEFORE that paragraph (the slide precedes the passage that
     explains it). Same anchor mechanics as _book_illustrate._inject_figures,
     hardened: a missing OR ambiguous anchor fails loudly naming the slide_id.
  3. Write book/book-slides.md. build_book_pdf.py prefers it over
     book-illustrated.md/book.md. book.md / book-illustrated.md never mutated.

MANIFEST entries:
  {"slide_id": "ch01-s02", "page": 2, "title": "...",
   "anchor_text": "verbatim 20-70 char substring of the book md" | null}
anchor_text null = combined-deck-only slide (e.g. the cover): validated
against the page count but never injected inline.

USAGE (manual book-level mode)
    python3 scripts/podcast/inject_slide_deck.py <slug-or-BOOK_DIR> [--force]

--force re-extracts the page images even if present. Re-runs are idempotent.
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
# Widened 2026-06-10: also strips the SVG-replicated variant
# (class="book-diagram book-slide book-slide-svg") so re-runs stay idempotent.
_SLIDE_FIGURE_RE = re.compile(
    r'<figure class="book-diagram book-slide[^"]*">.*?</figure>\n*', re.DOTALL)
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


def pdf_page_texts(pdf: Path) -> list[str]:
    """Per-page plain text of ``pdf`` (one entry per page, form-feed split).

    Used to recover slide TITLES from a NotebookLM-exported deck so the
    manifest-authoring LLM can map slides to book passages."""
    proc = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise AuthoringError(
            phase=_PHASE,
            message=f"pdftotext failed rc={proc.returncode}: {proc.stderr[:400]}",
            manual_fallback="Install poppler (`brew install poppler`) and retry.")
    pages = proc.stdout.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def page_titles(pdf: Path) -> list[str]:
    """First non-blank line of each page — the slide title, best-effort."""
    titles = []
    for text in pdf_page_texts(pdf):
        line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        titles.append(line)
    return titles


def strip_slide_figures(book_md: str) -> str:
    """Remove previously injected book-slide figures (idempotent re-run support).
    Plain book-diagram figures from 0book-illustrate are untouched."""
    return _SLIDE_FIGURE_RE.sub("", book_md)


def inject_slides(book_md: str, entries: list[dict], *, pages: dict[int, str],
                  position: str = "before",
                  svg_overrides: dict[int, Path] | None = None) -> str:
    """Inject one figure per anchored slide at its anchor paragraph.

    ``pages`` maps page number -> img SRC PATH relative to the book content dir
    (e.g. "slide-decks/_pages/ch01/page-02.jpg"), so the figure src always
    matches a file that actually exists AND multiple decks can be combined in
    one call without page-number collisions (callers re-key pages uniquely).

    ``svg_overrides`` (2026-06-10, slide intelligence): page number -> verified
    SVG file path. Pages present here are injected as INLINE <svg> figures
    (class "book-diagram book-slide book-slide-svg" — same pattern as
    _book_illustrate) instead of the raster <img>; all other pages keep the
    JPEG. Callers re-key svg_overrides with the same stride as ``pages``.

    ``position``: "before" (default — the slide precedes the passage that
    explains it, per the reading-edition design) inserts at the START of the
    paragraph containing the anchor; "after" inserts past its end.

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

        if position == "before":
            para_break = result.rfind("\n\n", 0, first)
            insert_at = (para_break + 2) if para_break != -1 else 0
        else:
            end_of_para = result.find("\n\n", first + len(anchor))
            insert_at = (end_of_para + 2) if end_of_para != -1 else len(result)
        # Caption discipline: a placeholder/empty title never reaches the page —
        # render a captionless figure instead of "(untitled page)".
        title = (e.get("title") or "").strip()
        if not title or title.lower() in ("(untitled page)", "untitled", "untitled page"):
            caption_html = ""
            alt_text = "slide"
        else:
            caption_html = f'<figcaption>{title}</figcaption>\n'
            alt_text = title
        svg_path = (svg_overrides or {}).get(page)
        if svg_path is not None:
            try:
                svg_markup = Path(svg_path).read_text(encoding="utf-8").strip()
            except OSError:
                svg_markup = ""
            if svg_markup.startswith("<svg"):
                figure_block = (
                    f'<figure class="book-diagram book-slide book-slide-svg">\n'
                    f'{svg_markup}\n'
                    f'{caption_html}'
                    f'</figure>\n\n'
                )
                insertions.append((insert_at, figure_block))
                continue
            # Unreadable/invalid SVG → fall through to the raster figure.
        figure_block = (
            f'<figure class="book-diagram book-slide">\n'
            f'<img src="{pages[page]}" alt="{alt_text}">\n'
            f'{caption_html}'
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


def injection_source(book_dir: Path) -> Path:
    """The markdown the figures are injected into (and anchors validated against)."""
    src = book_dir / "book" / "book-illustrated.md"
    if not src.exists():
        src = book_dir / "book" / "book.md"
    if not src.exists():
        raise AuthoringError(
            phase=_PHASE,
            message=f"no book/book-illustrated.md or book/book.md in {book_dir.name}",
            manual_fallback="Run 0book-compose (and 0book-illustrate) first.")
    return src


def inject_slide_deck(book_dir: Path, *, force: bool = False, log=print) -> Path:
    """Manual book-level mode: ONE deck for the whole book at the standardized
    location slide-decks/book-deck.pdf + _manifests/book-manifest.json.
    (Per-chapter decks are handled by the 0book-slide-import phase.)
    Returns book/book-slides.md."""
    book_dir = Path(book_dir).resolve()
    deck_dir = book_dir / "slide-decks"
    deck_pdf = deck_dir / "book-deck.pdf"
    if not deck_pdf.exists():
        raise AuthoringError(
            phase=_PHASE,
            message=f"missing slide-decks/book-deck.pdf in {book_dir.name}",
            manual_fallback="Export the deck from NotebookLM and drop it at "
                            "slide-decks/book-deck.pdf.")
    manifest_path = deck_dir / "_manifests" / "book-manifest.json"
    if not manifest_path.exists():
        raise AuthoringError(
            phase=_PHASE,
            message=f"missing {manifest_path.relative_to(book_dir)}",
            manual_fallback="Author the slide manifest (slide_id/page/title/anchor_text per slide).")

    entries = load_manifest(manifest_path)
    pages_dir = deck_dir / "_pages" / "book"
    extract_pages(deck_pdf, pages_dir, force=force, log=log)
    pages = {n: f"slide-decks/_pages/book/{p.name}"
             for n, p in _page_map(pages_dir).items()}

    src = injection_source(book_dir)
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
