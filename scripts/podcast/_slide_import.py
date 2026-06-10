#!/usr/bin/env python3
"""_slide_import.py — Phase 0book-slide-import: weave NotebookLM-exported
per-chapter slide decks into the reading edition.

Runs inside the 0book chain (book_driver) between 0book-illustrate and
0book-render. The human round happened back at the finalize halt: the slide
card listed, per framed chapter, the framing to paste into NotebookLM's
"Slide deck → Describe" box and the exact drop path for the exported PDF
(slide-decks/chNN-<slug>.pdf). This phase turns those drops into inline
figures, autonomously:

  1. GATE — a chapter participates iff slide-decks/chNN-framing-<slug>.md
     exists (density-skipped chapters never get a framing). An empty
     slide-decks/chNN-<slug>.SKIP marker exempts a chapter. A book-level
     slide-decks/book-deck.pdf (+ _manifests/book-manifest.json) is also
     processed when present (manual mode, e.g. the-master-and-the-disciple).
     Any framed, non-exempt chapter without its PDF -> AuthoringHalt that
     re-prints the generation card and names the missing files exactly.
  2. EXTRACT — deck pages -> slide-decks/_pages/<ch>/page-NN.jpg (pdftoppm),
     page titles via pdftotext (both reused from inject_slide_deck.py).
  3. MANIFEST — ONE claude -p call per chapter authors
     slide-decks/_manifests/<ch>-manifest.json mapping each slide to a
     verbatim anchor in the book prose (cover/synthesis-only slides -> null).
     Validated dry against the REAL injection source (book-illustrated.md when
     present — an anchor unique in book.md can be ambiguous there); one retry
     with the validator's problem list appended; second failure ->
     AuthoringError (book branch records `failed`, render proceeds without
     slides — non-blocking contract).
     Sig cache: _manifests/.<ch>-sig = sha256(deck pdf)+sha256(source md);
     hit -> the LLM call is skipped (mirrors the framing .framing-sig cache).
  4. INJECT — ONE combined inject_slides() call across all chapters (pages
     re-keyed uniquely; figure placed BEFORE its anchor paragraph) ->
     book/book-slides.md, which build_book_pdf prefers at render.

Standalone:
  python3 scripts/podcast/_slide_import.py <BOOK_DIR> [--force]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _authoring._core import (  # noqa: E402
    AuthoringError,
    AuthoringHalt,
    _assert_artifact,
    _run_claude_p,
)
from _notebooklm_table import (  # noqa: E402
    build_slide_deck_card,
    discover_slide_framings,
    expected_deck_pdf,
    repo_rel_href,
)
from inject_slide_deck import (  # noqa: E402
    extract_pages,
    injection_source,
    inject_slides,
    load_manifest,
    page_titles,
    _page_map,
)

_PHASE = "0book-slide-import"
_MANIFEST_TIMEOUT = 900
# Synthetic page-key stride: chapter index N's deck page P -> N*1000 + P.
# Keeps multi-deck page numbers collision-free in the single combined
# inject_slides() call (decks are well under 1000 pages).
_STRIDE = 1000


# ── sig cache ────────────────────────────────────────────────────────────────

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sig(deck_pdf: Path, source_md: Path) -> str:
    return f"{_sha(deck_pdf)}:{_sha(source_md)}"


def _sig_path(book_dir: Path, ch: str) -> Path:
    return book_dir / "slide-decks" / "_manifests" / f".{ch}-sig"


def _manifest_path(book_dir: Path, ch: str) -> Path:
    return book_dir / "slide-decks" / "_manifests" / f"{ch}-manifest.json"


# ── manifest authoring (claude -p) ───────────────────────────────────────────

def _manifest_prompt(book_md_path: Path, titles: list[str], ch: str,
                     out_path: Path, problems: list[str] | None = None) -> str:
    numbered = "\n".join(f"  page {i}: {t or '(untitled page)'}"
                         for i, t in enumerate(titles, start=1))
    retry_block = ""
    if problems:
        retry_block = (
            "\nA PREVIOUS ATTEMPT FAILED validation. Fix EXACTLY these problems "
            "(choose different anchors where named):\n"
            + "\n".join(f"  - {p}" for p in problems) + "\n")
    return f"""You are mapping slide-deck pages to the passages of a book they illustrate.

READ this book markdown file IN FULL:
  {book_md_path}

THE DECK ({ch}) has these pages (titles extracted from the PDF):
{numbered}

TASK: write a JSON file at exactly this path:
  {out_path}

The file is a JSON LIST with ONE object per deck page, in page order:
  {{"slide_id": "{ch}-sNN", "page": <int>, "title": "<page title>",
    "anchor_text": "<verbatim substring>" | null}}

ANCHOR RULES (hard requirements — the file is validated mechanically):
- anchor_text is a VERBATIM substring of the book markdown, 20-70 characters,
  copied EXACTLY (punctuation, capitalization, spacing).
- It must occur EXACTLY ONCE in the whole book file.
- Choose it from the START of the passage the slide illustrates: the slide is
  placed BEFORE the paragraph containing the anchor, so the anchor's paragraph
  should be where the explanation BEGINS.
- Prefer distinctive mid-sentence phrases. NEVER use a heading line, a single
  common word, or text that appears inside an SVG/figure block.
- Cover pages, agenda/outline pages, and pure synthesis-recap pages that have
  no single home in the text get anchor_text null.
{retry_block}
OUTPUT: write the JSON file at the path above. No other output is needed.
Do not modify any other file."""


def _author_manifest(book_dir: Path, ch: str, slug: str, deck_pdf: Path,
                     source_md: Path, source_text: str, pages_rel: dict[int, str],
                     *, log=print) -> list[dict]:
    """Author + validate the chapter manifest, with one retry. Returns entries."""
    titles = page_titles(deck_pdf)
    out_path = _manifest_path(book_dir, ch)
    problems: list[str] | None = None

    for attempt in (1, 2):
        prompt = _manifest_prompt(source_md, titles, ch, out_path, problems)
        rc, stdout, stderr = _run_claude_p(
            prompt, timeout=_MANIFEST_TIMEOUT, book_dir=book_dir,
            phase=_PHASE, step=f"slide-manifest/{slug}/attempt-{attempt}")
        _assert_artifact(
            _PHASE, out_path, rc, stdout, stderr,
            manual_fallback=f"Author {out_path} by hand (slide_id/page/title/anchor_text).")
        entries = load_manifest(out_path)
        try:
            # Dry validation against the REAL injection source.
            inject_slides(source_text, entries, pages=pages_rel)
            return entries
        except AuthoringError as e:
            problems = [ln.strip() for ln in str(e).splitlines() if ln.strip()][1:]
            log(f"    {_PHASE}: {ch} manifest attempt {attempt} failed validation "
                f"({len(problems)} problem(s))")
            out_path.unlink(missing_ok=True)
    raise AuthoringError(
        phase=_PHASE,
        message=f"{ch}: manifest failed validation twice — last problems:\n  "
                + "\n  ".join(problems or ["(unknown)"]),
        manual_fallback=f"Author {out_path} by hand, then re-run --resume.")


# ── main phase entry ─────────────────────────────────────────────────────────

def author_phase_slide_import(book_dir: Path, *, force: bool = False,
                              log=print) -> dict:
    """Weave dropped deck PDFs into book/book-slides.md.

    Raises AuthoringHalt (PDF drops missing) or AuthoringError (manifest
    convergence failure / no injection source). Returns a summary dict:
    {"imported": {ch: n_slides}, "exempt": [...], "out": <path>} — or
    {"skipped": reason} when no chapter participates.
    """
    book_dir = Path(book_dir).resolve()
    deck_dir = book_dir / "slide-decks"

    framings = discover_slide_framings(book_dir)
    book_level_pdf = deck_dir / "book-deck.pdf"
    book_framing = deck_dir / "book-framing.md"
    # Book-level participates when the deck PDF was dropped; the manifest is
    # LLM-authored when absent (a pre-existing/hand-authored book-manifest.json
    # is honored as-is — the legacy manual mode).
    has_book_level = book_level_pdf.exists()

    if not framings and not has_book_level and not book_framing.exists():
        return {"skipped": "no slide-deck framings and no book-deck.pdf"}

    # ── gate: every framed, non-exempt chapter needs its dropped PDF ─────────
    work: list[tuple[str, str, Path]] = []   # (ch, slug, deck_pdf)
    exempt: list[str] = []
    missing: list[str] = []
    for ch, slug, _framing, _deck_txt in framings:
        skip_marker = deck_dir / f"{ch}-{slug}.SKIP"
        if skip_marker.exists():
            exempt.append(ch)
            continue
        pdf = expected_deck_pdf(book_dir, ch, slug)
        if pdf.exists():
            work.append((ch, slug, pdf))
        else:
            missing.append(repo_rel_href(pdf, book_dir) or str(pdf))
    # Book mode (slide_deck_mode: book): the authored book-framing.md means ONE
    # deck is expected at slide-decks/book-deck.pdf — gate on it like a chapter.
    if book_framing.exists() and not book_level_pdf.exists() \
            and not (deck_dir / "book.SKIP").exists():
        missing.append(repo_rel_href(book_level_pdf, book_dir) or str(book_level_pdf))
    if missing:
        card = "\n".join(build_slide_deck_card(book_dir))
        raise AuthoringHalt(
            phase=_PHASE,
            message=("slide decks not yet dropped for "
                     f"{len(missing)} chapter(s):\n  " + "\n  ".join(missing)
                     + "\n\n" + card),
            manual_fallback="Generate each deck in NotebookLM (card above), drop the "
                            "exported PDFs at the listed paths (or create the .SKIP "
                            "marker), then re-run --resume.")
    if has_book_level:
        work.append(("book", book_dir.name, book_level_pdf))

    source_md = injection_source(book_dir)
    source_text = source_md.read_text(encoding="utf-8")

    # ── per-deck: extract pages, analyze/replicate, author/load manifest ────
    combined_entries: list[dict] = []
    combined_pages: dict[int, str] = {}
    combined_svgs: dict[int, Path] = {}
    imported: dict[str, int] = {}
    svg_counts: dict[str, int] = {}
    for idx, (ch, slug, pdf) in enumerate(work, start=1):
        pages_dir = deck_dir / "_pages" / ch
        extract_pages(pdf, pages_dir, force=force, log=log)
        raw_map = _page_map(pages_dir)
        pages_rel = {n: f"slide-decks/_pages/{ch}/{p.name}" for n, p in raw_map.items()}

        # Slide intelligence (2026-06-10): OCR/vision-analyze every page;
        # high-value diagram slides are replicated as verified inline SVG,
        # everything else keeps the raster JPEG. Degrades to {} on failure
        # (non-blocking contract — the import proceeds all-raster).
        from _slide_replicate import analyze_and_replicate_slides
        svg_overrides = analyze_and_replicate_slides(
            book_dir, ch, pdf, pages_dir, force=force, log=log)
        svg_counts[ch] = len(svg_overrides)

        manifest_file = _manifest_path(book_dir, ch)
        sig_file = _sig_path(book_dir, ch)
        sig = _sig(pdf, source_md)
        if (ch == "book" and manifest_file.exists() and not sig_file.exists()):
            # Hand-authored book manifest (legacy manual mode, no sig) — honor as-is.
            entries = load_manifest(manifest_file)
        elif manifest_file.exists() and sig_file.exists() \
                and sig_file.read_text(encoding="utf-8").strip() == sig and not force:
            log(f"    {_PHASE}: {ch} manifest cache hit — skipping LLM")
            entries = load_manifest(manifest_file)
        else:
            entries = _author_manifest(book_dir, ch, slug, pdf, source_md,
                                       source_text, pages_rel, log=log)
            sig_file.parent.mkdir(parents=True, exist_ok=True)
            sig_file.write_text(sig, encoding="utf-8")

        offset = idx * _STRIDE
        for e in entries:
            re_keyed = dict(e)
            re_keyed["page"] = offset + e["page"]
            combined_entries.append(re_keyed)
        for n, src in pages_rel.items():
            combined_pages[offset + n] = src
        for n, svg in svg_overrides.items():
            combined_svgs[offset + n] = svg
        imported[ch] = sum(1 for e in entries if e["anchor_text"])

    # ── single combined injection ────────────────────────────────────────────
    out = inject_slides(source_text, combined_entries, pages=combined_pages,
                        svg_overrides=combined_svgs)
    out_path = book_dir / "book" / "book-slides.md"
    out_path.write_text(out, encoding="utf-8")
    total = sum(imported.values())
    total_svg = sum(svg_counts.values())
    log(f"    {_PHASE}: {source_md.name} + {total} slides "
        f"({len(work)} deck(s), {total_svg} as SVG) -> {out_path.name}")
    return {"imported": imported, "exempt": exempt, "svg": svg_counts,
            "out": str(out_path.relative_to(book_dir))}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    if not args:
        print("usage: _slide_import.py <BOOK_DIR> [--force]", file=sys.stderr)
        return 2
    try:
        result = author_phase_slide_import(Path(args[0]), force=force)
    except AuthoringHalt as e:
        print(f"[{_PHASE}] HALT: {e}", file=sys.stderr)
        return 3
    except AuthoringError as e:
        print(f"[{_PHASE}] {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
