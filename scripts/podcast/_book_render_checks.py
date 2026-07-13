"""_book_render_checks.py — deterministic probes over the RENDERED book PDF (v2).

Backs the ``book-render-challenger`` agent, which gates the PRINT deliverable that
``book-challenger`` (semantic) cannot see: the rendered page itself. These probes
are the mechanical half — the agent adds the visual judgment (split figures,
float-vs-standalone correctness, legibility) on top.

The scan functions are PURE (they take per-page extracted text) so they unit-test
without Playwright. ``run_render_checks`` does the pdftotext extraction and
orchestrates. Wired into ``0book-render`` ONLY under book_pipeline_v2, non-blocking
(records findings; a broken reading edition must not stop the podcast ship).

Checks (see docs/standards/book-print-quality.md for REQ text):
  BR-WATERMARK   (P0) — no "NotebookLM" watermark text survives on any page.
  BR-CAPTION-DUP (P1) — a caption is not printed twice (title echoed + figcaption).
  BR-BLANK-PAGE  (P0) — no blank interior page.
  BR-PAGE-FILL   (P1) — no half-empty interior page (text fills like a real book).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

_WATERMARK_RE = re.compile(r"notebook\s*lm", re.I)
# A "real" text page carries at least this many characters; interior pages far
# below the interior median read as half-empty.
_MIN_PAGE_CHARS = 120
_HALF_EMPTY_RATIO = 0.35


def scan_watermark(pages_text: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for i, text in enumerate(pages_text, start=1):
        if _WATERMARK_RE.search(text):
            findings.append({
                "check": "BR-WATERMARK", "severity": "P0", "page": i,
                "detail": "NotebookLM watermark text present on the rendered page",
            })
    return findings


def scan_duplicate_captions(pages_text: list[str]) -> list[dict[str, Any]]:
    """Flag a short line repeated consecutively on a page — the classic caption
    duplication (an embedded title echoed again as <figcaption>)."""
    findings: list[dict[str, Any]] = []
    for i, text in enumerate(pages_text, start=1):
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for a, b in zip(lines, lines[1:]):
            if a == b and 0 < len(a.split()) <= 12:
                findings.append({
                    "check": "BR-CAPTION-DUP", "severity": "P1", "page": i,
                    "detail": f"caption printed twice: {a[:60]!r}",
                })
                break
    return findings


def scan_blank_and_halfempty(pages_text: list[str]) -> list[dict[str, Any]]:
    """Blank interior pages (P0) and half-empty interior pages (P1).

    First and last pages are exempt (cover/title/colophon legitimately sparse).
    Half-empty is judged against the median fill of the interior pages, so a book
    of naturally short pages is not penalized wholesale.
    """
    findings: list[dict[str, Any]] = []
    n = len(pages_text)
    if n < 3:
        return findings
    interior = list(range(2, n))  # 1-indexed pages 2..n-1 -> indices below
    lengths = {p: len(pages_text[p - 1].strip()) for p in interior}
    for p in interior:
        if lengths[p] < _MIN_PAGE_CHARS:
            findings.append({
                "check": "BR-BLANK-PAGE", "severity": "P0", "page": p,
                "detail": f"blank/near-blank interior page ({lengths[p]} chars)",
            })
    non_blank = [v for v in lengths.values() if v >= _MIN_PAGE_CHARS]
    if len(non_blank) >= 3:
        srt = sorted(non_blank)
        median = srt[len(srt) // 2]
        for p in interior:
            if _MIN_PAGE_CHARS <= lengths[p] < _HALF_EMPTY_RATIO * median:
                findings.append({
                    "check": "BR-PAGE-FILL", "severity": "P1", "page": p,
                    "detail": f"half-empty interior page ({lengths[p]} vs median {median} chars)",
                })
    return findings


def run_all_scans(pages_text: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    findings.extend(scan_watermark(pages_text))
    findings.extend(scan_duplicate_captions(pages_text))
    findings.extend(scan_blank_and_halfempty(pages_text))
    findings.sort(key=lambda f: (f["severity"] != "P0", f.get("page", 0)))
    return findings


def _extract_pages_text(pdf: Path, max_pages: int = 400) -> list[str] | None:
    """Per-page text via pdftotext. None when Poppler is unavailable (defer)."""
    if shutil.which("pdftotext") is None or not pdf.exists():
        return None
    pages: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="book-render-text-") as tmp:
            tmp_dir = Path(tmp)
            for page in range(1, max_pages + 1):
                out = tmp_dir / f"p{page}.txt"
                rc = subprocess.run(
                    ["pdftotext", "-f", str(page), "-l", str(page), str(pdf), str(out)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
                ).returncode
                if rc != 0 or not out.exists():
                    break
                pages.append(out.read_text(encoding="utf-8", errors="ignore"))
                # pdftotext succeeds past the last page with empty output; stop on a
                # run of trailing empties once we have at least one page.
                if page > 1 and not pages[-1].strip() and not pages[-2].strip():
                    pages = pages[:-2]
                    break
    except Exception:  # noqa: BLE001
        return None
    return pages


def run_render_checks(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Run the deterministic render probes and write a report. Never raises."""
    book_dir = Path(book_dir).resolve()
    pdf = book_dir / "book" / "book.pdf"
    pages_text = _extract_pages_text(pdf)
    if pages_text is None:
        report = {"schema": "podcast.book-render-checks/v1", "verdict": "UNKNOWN",
                  "reason": "pdftotext unavailable or PDF missing", "findings": []}
    else:
        findings = run_all_scans(pages_text)
        p0 = [f for f in findings if f["severity"] == "P0"]
        report = {
            "schema": "podcast.book-render-checks/v1",
            "verdict": "RENDER-BROKEN" if p0 else ("RENDER-CAUTION" if findings else "RENDER-CLEAN"),
            "pages": len(pages_text),
            "findings": findings,
        }
    try:
        (book_dir / "_system" / "book-render-checks.json").write_text(
            __import__("json").dumps(report, indent=2) + "\n", encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        log(f"    0book-render: render-checks report write skipped (non-fatal): {e}")
    return report
