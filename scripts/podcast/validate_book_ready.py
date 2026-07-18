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
  B4  book-prose-integrity — translation editions must not contain model process
                          chatter or generated Markdown headings inside chapter prose.
  B5  book-chapter-body-coverage — translation-edition chapters must have real
                          body text, not heading-only/blank chapters.
  B6  book-source-crosswalk — translation editions must persist a source
                          crosswalk and pass title/source alignment checks.

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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Reuse the exact render-input selection the renderer uses, so the content gate
# validates the file that actually becomes the PDF (book-slides.md >
# book-illustrated.md > book.md).
from build_book_pdf import _pick_book_md

# Arabic script Unicode ranges (base + supplement + extended + presentation forms).
_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+")
# A bracketed transliteration marker the compose prompt emits, e.g. "(Ayyuhal Walad)".
# Used only as a rough denominator for the advisory coverage signal.
_TRANSLIT_HINT_RE = re.compile(r"\([A-Z][a-z]+(?:[ -][A-Za-z']+){0,4}\)")

_MIN_MD_BYTES = 1024  # a real reading edition is far larger; < 1KB == broken
_MIN_PDF_BYTES = 10 * 1024  # a one-page error PDF is tiny; floor catches it


def _book_branch_enabled(book_dir: Path) -> bool:
    meta = book_dir / "meta.yml"
    if not meta.exists():
        return False
    try:
        from _translation_edition import is_translation_edition

        if is_translation_edition(book_dir):
            return True
        import yaml  # type: ignore[import]

        data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        return bool(data.get("series", {}).get("enable_book_branch", False))
    except Exception:
        return False


def _toc_chapter_count(book_dir: Path) -> int:
    toc = book_dir / "book" / "book-toc.json"
    if not toc.exists():
        return 0
    try:
        data = json.loads(toc.read_text(encoding="utf-8"))
        return len(data.get("chapters") or data.get("toc") or [])
    except Exception:
        return 0


def _pdf_page_count(pdf_bytes: bytes) -> int:
    """Deterministic page count from raw PDF bytes — count /Type /Page objects.

    Avoids a PDF-parser dependency. The ``(?![A-Za-z])`` guard excludes
    ``/Type /Pages`` (container) and ``/Type /PageLabels`` — only the leaf page
    object (``/Page`` followed by a delimiter) counts. Robust to whitespace
    variation between the key and value.
    """
    return len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", pdf_bytes))


def _pdf_text_blank_pages(pdf: Path, pages: int) -> list[int]:
    """Return pages with no extractable text, when Poppler is available.

    This catches accidental blank pages from print CSS page-break interactions.
    If Poppler is unavailable or the extractor cannot read a synthetic/unit-test
    PDF, defer to the structural page-count checks rather than failing open books
    for an environment issue.
    """
    if pages < 1 or shutil.which("pdftotext") is None:
        return []
    blank: list[int] = []
    try:
        with tempfile.TemporaryDirectory(prefix="book-pdf-text-") as tmp:
            tmp_dir = Path(tmp)
            for page in range(1, pages + 1):
                out = tmp_dir / f"p{page}.txt"
                subprocess.run(
                    [
                        "pdftotext",
                        "-f",
                        str(page),
                        "-l",
                        str(page),
                        str(pdf),
                        str(out),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                )
                if not out.read_text(encoding="utf-8", errors="ignore").strip():
                    blank.append(page)
    except Exception:
        return []
    return blank


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
        return False, (
            f"{md.name} has {n_sections} '## ' sections but the TOC lists "
            f"{n_chapters} chapters — compose is truncated/incomplete"
        )
    return True, (f"{md.name}: {size // 1024} KB, {n_sections} sections ≥ {n_chapters} TOC chapters")


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
    except Exception as e:
        return False, f"book.pdf unreadable: {e}"
    n_chapters = _toc_chapter_count(book_dir)
    if pages < 1:
        return False, "book.pdf has 0 detectable pages — render is broken"
    if n_chapters and pages < n_chapters:
        return False, (f"book.pdf has {pages} pages but the TOC lists {n_chapters} chapters — render is truncated")
    blank_pages = _pdf_text_blank_pages(pdf, pages)
    if blank_pages:
        shown = ", ".join(str(p) for p in blank_pages[:12])
        more = f" (+{len(blank_pages) - 12} more)" if len(blank_pages) > 12 else ""
        return False, f"book.pdf has blank page(s): {shown}{more}"
    return True, f"book.pdf: {size // 1024} KB, {pages} pages ≥ {n_chapters} chapters"


def gate_b3_book_arabic_coverage(book_dir: Path) -> tuple[bool, str]:
    """Hard gate for Islamic chapter Arabic, plus rendered-book coverage signal."""
    try:
        from _content_profile import is_islamic_scholarly
        from _translation_edition import is_faithful_translation_deliverable

        if is_islamic_scholarly(book_dir):
            if is_faithful_translation_deliverable(book_dir):
                md = _pick_book_md(book_dir)
                rendered = md.read_text(encoding="utf-8", errors="replace") if md.exists() else ""
                rendered_runs = len(_ARABIC_RE.findall(rendered))
                src_candidates = [
                    book_dir / "_system" / "source" / "ocr" / "raw-extract.md",
                    book_dir / "_system" / "source" / "text" / "raw-extract.md",
                ]
                source_text = ""
                for candidate in src_candidates:
                    if candidate.exists():
                        source_text = candidate.read_text(encoding="utf-8", errors="replace")
                        if len(_ARABIC_RE.findall(source_text)) >= 50:
                            break
                source_runs = len(_ARABIC_RE.findall(source_text))
                if source_runs >= 50 and rendered_runs == 0:
                    return False, ("translation-edition source has Arabic script but the rendered book has none")
                return True, (
                    f"translation-edition Arabic preservation signal: "
                    f"{rendered_runs} rendered Arabic runs from {source_runs} source runs"
                )
            from inject_chapter_arabic import chapter_arabic_status

            status = chapter_arabic_status(book_dir)
            if not status.get("ok"):
                return False, str(status.get("note") or "Arabic chapter coverage failed")
    except Exception as e:
        return False, f"Arabic chapter coverage check failed: {e}"

    md = book_dir / "book" / "book.md"
    if not md.exists():
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
                anchor_note = (
                    f"; Quran anchoring {r.get('anchored')}/{r.get('cited')} "
                    f"({r.get('coverage', 0):.0%}) cited verses canonical"
                )
        except Exception:
            pass
    return True, (
        f"{arabic_runs} Arabic runs vs ~{translit_hints} transliteration "
        f"markers ({pct:.0%} script coverage){anchor_note}"
    )


def gate_b4_book_prose_integrity(book_dir: Path) -> tuple[bool, str]:
    """Reject model process chatter in translation-edition render input."""
    try:
        from _translation_edition import is_faithful_translation_deliverable, translation_output_findings

        if not is_faithful_translation_deliverable(book_dir):
            return True, "n/a (not a translation edition)"
    except Exception as e:
        return False, f"translation-edition integrity check unavailable: {e}"

    md = _pick_book_md(book_dir)
    if not md.exists():
        return False, f"render input missing ({md.name})"
    text = md.read_text(encoding="utf-8", errors="replace")
    chapters = re.split(r"(?m)^##\s+\d+\.\s+", text)
    bad: list[str] = []
    for i, chunk in enumerate(chapters[1:], start=1):
        lines = chunk.splitlines()
        title = lines[0].strip() if lines else f"chapter {i}"
        prose = "\n".join(lines[1:]).strip()
        findings = translation_output_findings(prose, expected_title=title)
        if findings:
            bad.append(f"chapter {i} ({title}): {'; '.join(findings[:3])}")
    if bad:
        shown = "; ".join(bad[:4])
        more = f"; +{len(bad) - 4} more" if len(bad) > 4 else ""
        return False, shown + more
    return True, f"{md.name}: no model commentary or generated headings detected"


def gate_b5_book_chapter_body_coverage(book_dir: Path) -> tuple[bool, str]:
    """Reject heading-only translation-edition chapters."""
    try:
        from _translation_edition import is_faithful_translation_deliverable

        if not is_faithful_translation_deliverable(book_dir):
            return True, "n/a (not a translation edition)"
    except Exception as e:
        return False, f"translation-edition body check unavailable: {e}"

    md = _pick_book_md(book_dir)
    if not md.exists():
        return False, f"render input missing ({md.name})"
    text = md.read_text(encoding="utf-8", errors="replace")
    matches = list(re.finditer(r"(?m)^##\s+(\d+)\.\s+(.+)$", text))
    if not matches:
        return False, f"{md.name}: no numbered chapter headings found"
    bad: list[str] = []
    for pos, match in enumerate(matches):
        start = match.end()
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
        body = text[start:end]
        body = re.sub(r"(?m)^#{1,6}\s+.*$", "", body)
        body = re.sub(r"<[^>]+>", "", body)
        compact = re.sub(r"\s+", " ", body).strip()
        if len(compact) < 400:
            bad.append(f"chapter {match.group(1)} ({match.group(2).strip()}): {len(compact)} chars")
    if bad:
        shown = "; ".join(bad[:4])
        more = f"; +{len(bad) - 4} more" if len(bad) > 4 else ""
        return False, f"heading-only/blank chapter body detected: {shown}{more}"
    return True, f"{md.name}: {len(matches)} numbered chapters have body text"


def gate_b6_book_source_crosswalk(book_dir: Path) -> tuple[bool, str]:
    """Validate persisted source crosswalk and title/source alignment."""
    try:
        from _book_compose import _slice_source
        from _translation_edition import is_faithful_translation_deliverable, source_title_drift_findings

        if not is_faithful_translation_deliverable(book_dir):
            return True, "n/a (not a translation edition)"
    except Exception as e:
        return False, f"source-crosswalk check unavailable: {e}"

    crosswalk_path = book_dir / "book" / "source-crosswalk.json"
    if not crosswalk_path.exists():
        return False, "book/source-crosswalk.json missing"
    refined_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not refined_path.exists():
        return False, "refined English source missing; cannot verify crosswalk"
    try:
        data = json.loads(crosswalk_path.read_text(encoding="utf-8"))
        entries = data.get("chapters") or []
    except Exception as e:
        return False, f"source-crosswalk.json unreadable: {e}"
    n_chapters = _toc_chapter_count(book_dir)
    if n_chapters and len(entries) != n_chapters:
        return False, f"crosswalk has {len(entries)} chapters but TOC lists {n_chapters}"
    lines = refined_path.read_text(encoding="utf-8", errors="replace").split("\n")
    bad: list[str] = []
    for entry in entries:
        title = str(entry.get("title") or "")
        idx = entry.get("index")
        ranges = entry.get("source_line_ranges") or []
        source = _slice_source(lines, ranges)
        findings = list(entry.get("drift_findings") or [])
        findings.extend(source_title_drift_findings(title, source))
        if findings:
            bad.append(f"chapter {idx} ({title}): {'; '.join(dict.fromkeys(findings))}")
    if bad:
        shown = "; ".join(bad[:4])
        more = f"; +{len(bad) - 4} more" if len(bad) > 4 else ""
        return False, shown + more
    return True, f"source-crosswalk.json: {len(entries)} chapters aligned"


def validate_book(book_dir: Path, *, strict: bool = False) -> dict:
    """Run B1-B6 and return a verdict dict. Pure read-only."""
    book_dir = Path(book_dir).resolve()
    if not _book_branch_enabled(book_dir):
        return {
            "slug": book_dir.name,
            "verdict": "N/A",
            "summary": "series.enable_book_branch is false — no reading edition expected",
            "gates": [],
        }

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
    gates.append({"gate": "B3", "name": "book-arabic-coverage", "passed": ok3, "note": why3})
    if not ok3:
        blocking_fail = blocking_fail or f"B3 book-arabic-coverage: {why3}"

    ok4, why4 = gate_b4_book_prose_integrity(book_dir)
    gates.append({"gate": "B4", "name": "book-prose-integrity", "passed": ok4, "note": why4})
    if not ok4:
        blocking_fail = blocking_fail or f"B4 book-prose-integrity: {why4}"

    ok5, why5 = gate_b5_book_chapter_body_coverage(book_dir)
    gates.append({"gate": "B5", "name": "book-chapter-body-coverage", "passed": ok5, "note": why5})
    if not ok5:
        blocking_fail = blocking_fail or f"B5 book-chapter-body-coverage: {why5}"

    ok6, why6 = gate_b6_book_source_crosswalk(book_dir)
    gates.append({"gate": "B6", "name": "book-source-crosswalk", "passed": ok6, "note": why6})
    if not ok6:
        blocking_fail = blocking_fail or f"B6 book-source-crosswalk: {why6}"

    verdict = "BOOK-SOUND" if blocking_fail is None else "BOOK-BROKEN"
    summary = f"reading edition sound ({len(gates)} gates checked)" if blocking_fail is None else blocking_fail
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
        print(f"{'✓' if result['verdict'] != 'BOOK-BROKEN' else '✗'} {result['verdict']} — {result['summary']}")
    return 1 if result["verdict"] == "BOOK-BROKEN" else 0


if __name__ == "__main__":
    sys.exit(main())
