#!/usr/bin/env python3
"""validate_book_ready.py — deterministic gates for the reading-edition deliverable.

PURPOSE

The companion reading-edition (book/book.md -> book/book.pdf) is built AFTER the
finalize halt, inside publish_driver._drive_publish_through_done. It is a
NON-BLOCKING companion to the podcast: a book-branch failure must never stop the
audio from publishing. But until now NOTHING validated the book deliverable's
*content* — `build_book` only asserts the PDF file was written, so a truncated
book.md (missing chapters) or a near-empty PDF would record 0book-render
``completed`` and ship to Google Drive unnoticed.

This module adds the missing deterministic post-render gates. They are PURE
functions (filesystem + regex only — no LLM, no network) so the verdict is
reproducible on identical input:

  B1  book-md-complete  — render-input markdown exists, is non-trivial, and has
                          at least one ``## `` section per TOC chapter (catches a
                          truncated / partial compose).
  B2  book-pdf-renderable — book.pdf exists, is non-trivially sized, and its page
                          count (parsed from the PDF object stream) is at least
                          the chapter count (catches an empty / 1-page render).
  B3  book-arabic-coverage — Islamic scholarly books must carry Arabic script
                          in every persisted chapter; missing Arabic blocks.

USAGE

    python3 scripts/podcast/validate_book_ready.py <slug-or-BOOK_DIR>
    python3 scripts/podcast/validate_book_ready.py <slug> --json

EXIT CODES

    0  — B1+B2 passed (or book branch not enabled → n/a); deliverable is sound
    1  — a blocking book gate failed; the reading edition is NOT sound
    2  — couldn't run (book dir missing)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Reuse the exact render-input selection the renderer uses, so the content gate
# validates the file that actually becomes the PDF (book-slides.md >
# book-illustrated.md > book.md).
from build_book_pdf import _pick_book_md  # noqa: E402

# Arabic script Unicode ranges (base + supplement + extended + presentation forms).
_ARABIC_RE = re.compile(
    r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+"
)
# A bracketed transliteration marker the compose prompt emits, e.g. "(Ayyuhal Walad)".
# Used only as a rough denominator for the advisory coverage signal.
_TRANSLIT_HINT_RE = re.compile(r"\([A-Z][a-z]+(?:[ -][A-Za-z']+){0,4}\)")

_MIN_MD_BYTES = 1024          # a real reading edition is far larger; < 1KB == broken
_MIN_PDF_BYTES = 10 * 1024    # a one-page error PDF is tiny; floor catches it


def _book_branch_enabled(book_dir: Path) -> bool:
    meta = book_dir / "meta.yml"
    if not meta.exists():
        return False
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        return bool(data.get("series", {}).get("enable_book_branch", False))
    except Exception:  # noqa: BLE001
        return False


def _toc_chapter_count(book_dir: Path) -> int:
    toc = book_dir / "book" / "book-toc.json"
    if not toc.exists():
        return 0
    try:
        data = json.loads(toc.read_text(encoding="utf-8"))
        return len(data.get("chapters") or data.get("toc") or [])
    except Exception:  # noqa: BLE001
        return 0


def _pdf_page_count(pdf_bytes: bytes) -> int:
    """Deterministic page count from raw PDF bytes — count /Type /Page objects.

    Avoids a PDF-parser dependency. The ``(?![A-Za-z])`` guard excludes
    ``/Type /Pages`` (container) and ``/Type /PageLabels`` — only the leaf page
    object (``/Page`` followed by a delimiter) counts. Robust to whitespace
    variation between the key and value.
    """
    return len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", pdf_bytes))


def gate_b1_book_md_complete(book_dir: Path) -> tuple[bool, str]:
    """Render-input markdown exists, is non-trivial, and covers every TOC chapter."""
    md = _pick_book_md(book_dir)
    if not md.exists():
        return False, f"render input missing ({md.name}) — 0book-compose did not produce a book"
    size = md.stat().st_size
    if size < _MIN_MD_BYTES:
        return False, f"{md.name} is only {size} bytes — compose produced a near-empty book"
    text = md.read_text(encoding="utf-8", errors="replace")
    n_sections = len(re.findall(r"(?m)^## ", text))
    n_chapters = _toc_chapter_count(book_dir)
    if n_chapters and n_sections < n_chapters:
        return False, (f"{md.name} has {n_sections} '## ' sections but the TOC lists "
                       f"{n_chapters} chapters — compose is truncated/incomplete")
    return True, (f"{md.name}: {size // 1024} KB, {n_sections} sections "
                  f"≥ {n_chapters} TOC chapters")


def gate_b2_book_pdf_renderable(book_dir: Path) -> tuple[bool, str]:
    """book.pdf exists, is non-trivially sized, and has a sane page count."""
    pdf = book_dir / "book" / "book.pdf"
    if not pdf.exists():
        return False, "book.pdf missing — 0book-render did not produce a PDF"
    size = pdf.stat().st_size
    if size < _MIN_PDF_BYTES:
        return False, f"book.pdf is only {size} bytes — render produced an empty/error PDF"
    try:
        pages = _pdf_page_count(pdf.read_bytes())
    except Exception as e:  # noqa: BLE001
        return False, f"book.pdf unreadable: {e}"
    n_chapters = _toc_chapter_count(book_dir)
    if pages < 1:
        return False, "book.pdf has 0 detectable pages — render is broken"
    if n_chapters and pages < n_chapters:
        return False, (f"book.pdf has {pages} pages but the TOC lists {n_chapters} "
                       f"chapters — render is truncated")
    return True, f"book.pdf: {size // 1024} KB, {pages} pages ≥ {n_chapters} chapters"


def gate_b3_book_arabic_coverage(book_dir: Path) -> tuple[bool, str]:
    """Hard gate for Islamic chapter Arabic, plus rendered-book coverage signal."""
    try:
        from _content_profile import is_islamic_scholarly
        if is_islamic_scholarly(book_dir):
            from inject_chapter_arabic import chapter_arabic_status
            status = chapter_arabic_status(book_dir)
            if not status.get("ok"):
                return False, str(status.get("note") or "Arabic chapter coverage failed")
    except Exception as e:  # noqa: BLE001
        return False, f"Arabic chapter coverage check failed: {e}"

    md = _pick_book_md(book_dir)
    if not md.exists():
        return True, "n/a (no render input)"
    text = md.read_text(encoding="utf-8", errors="replace")
    arabic_runs = len(_ARABIC_RE.findall(text))
    translit_hints = len(_TRANSLIT_HINT_RE.findall(text))
    denom = arabic_runs + translit_hints
    pct = (arabic_runs / denom) if denom else 0.0
    anchor_note = ""
    report = book_dir / "_system" / "quran-anchor-report.json"
    if report.exists():
        try:
            r = json.loads(report.read_text(encoding="utf-8"))
            if r.get("cited"):
                anchor_note = (f"; Quran anchoring {r.get('anchored')}/{r.get('cited')} "
                               f"({r.get('coverage', 0):.0%}) cited verses canonical")
        except Exception:  # noqa: BLE001
            pass
    return True, (f"{arabic_runs} Arabic runs vs ~{translit_hints} transliteration "
                  f"markers ({pct:.0%} script coverage){anchor_note}")


def validate_book(book_dir: Path, *, strict: bool = False) -> dict:
    """Run B1-B3 and return a verdict dict. Pure read-only."""
    book_dir = Path(book_dir).resolve()
    if not _book_branch_enabled(book_dir):
        return {"slug": book_dir.name, "verdict": "N/A",
                "summary": "series.enable_book_branch is false — no reading edition expected",
                "gates": []}

    gates: list[dict] = []
    blocking_fail: str | None = None

    ok1, why1 = gate_b1_book_md_complete(book_dir)
    gates.append({"gate": "B1", "name": "book-md-complete", "passed": ok1, "note": why1})
    if not ok1:
        blocking_fail = blocking_fail or f"B1 book-md-complete: {why1}"

    ok2, why2 = gate_b2_book_pdf_renderable(book_dir)
    gates.append({"gate": "B2", "name": "book-pdf-renderable", "passed": ok2, "note": why2})
    if not ok2:
        blocking_fail = blocking_fail or f"B2 book-pdf-renderable: {why2}"

    ok3, why3 = gate_b3_book_arabic_coverage(book_dir)
    gates.append({"gate": "B3", "name": "book-arabic-coverage",
                  "passed": ok3, "note": why3})
    if not ok3:
        blocking_fail = blocking_fail or f"B3 book-arabic-coverage: {why3}"

    verdict = "BOOK-SOUND" if blocking_fail is None else "BOOK-BROKEN"
    summary = (f"reading edition sound ({len(gates)} gates checked)"
               if blocking_fail is None else blocking_fail)
    return {"slug": book_dir.name, "verdict": verdict, "summary": summary, "gates": gates}


def _resolve_book_dir(slug_or_dir: str) -> Path | None:
    p = Path(slug_or_dir)
    if p.is_dir() and (p / "meta.yml").exists():
        return p.resolve()
    import publish_to_library as P  # reuse the canonical bucket-aware resolver
    ws = P.resolve_workspace(slug_or_dir)
    return ws if ws.is_dir() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("slug", help="book slug or BOOK_DIR")
    ap.add_argument("--strict", action="store_true", help="(reserved) treat advisories as fails")
    ap.add_argument("--json", action="store_true", help="emit JSON verdict")
    args = ap.parse_args()

    book_dir = _resolve_book_dir(args.slug)
    if book_dir is None:
        msg = f"book dir not found for: {args.slug}"
        if args.json:
            print(json.dumps({"verdict": "BLOCKED", "summary": msg, "gates": []}))
        else:
            print(f"validate_book_ready: {msg}", file=sys.stderr)
        return 2

    result = validate_book(book_dir, strict=args.strict)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"==> validate_book_ready: {result['slug']}")
        for g in result["gates"]:
            mark = "✓" if g["passed"] else "✗"
            tag = " (advisory)" if g.get("advisory") else ""
            print(f"  {mark} {g['gate']} {g['name']}{tag} — {g['note']}")
        print()
        print(f"{'✓' if result['verdict'] != 'BOOK-BROKEN' else '✗'} "
              f"{result['verdict']} — {result['summary']}")
    return 1 if result["verdict"] == "BOOK-BROKEN" else 0


if __name__ == "__main__":
    sys.exit(main())
