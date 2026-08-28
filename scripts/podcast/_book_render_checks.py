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
# Bidi isolate/embedding controls (LRM/RLM, LRE/RLE/PDF/LRO/RLO, LRI/RLI/FSI/PDI).
# A justified Quranic verse can line-wrap so that pdftotext emits several
# consecutive "lines" that are each just one Arabic glyph wrapped in these
# controls — identical by construction, and not a caption.
_BIDI_CONTROL_RE = re.compile("[‎‏‪-‮⁦-⁩]")
# A "real" text page carries at least this many characters; interior pages far
# below the interior median read as half-empty.
_MIN_PAGE_CHARS = 120
_HALF_EMPTY_RATIO = 0.35

# Unicode bidi control characters (RLE/LRE/PDF, isolates) that `pdftotext`
# emits around right-to-left runs. A Qur'anic/Arabic verse quotation that
# wraps mid-word across a line break can extract as two adjacent "lines" that
# are each just one reordered letter+diacritic wrapped in these marks — not a
# duplicated caption, a bidi-linearization artifact of the SAME line of
# scripture. Caught on kitab-al-riyad pp.186/214/215/258, e.g. '‫ِإ‬'
# (a lone kasra+hamza), and independently on spiritual-ethos. A caption worth
# flagging is a real title, in Latin or Arabic; `scan_duplicate_captions`
# strips `_BIDI_CONTROL_RE` (above) and requires >=4 chars and >=2 words left
# over — either guard alone was proven on real findings from one book, so both
# are kept together rather than picking one.

# REQ-BR-002 says it in words: "A chapter still opens on a fresh page — that
# opener is not half-empty." A numbered opener prints "CHAPTER <WORD>"
# (book-print.css .ch-eyebrow); front matter — the title page, Contents, and
# the Source Crosswalk apparatus (first page and any continuation, since a
# browser repeats a table's <thead> on every page it breaks across) — is the
# same category of legitimately-sparse-by-design page, just never named in
# REQ-BR-002 because it wasn't the page that was breaking. Both were flagged
# on kitab-al-riyad (an opener at p.29, front matter at pp.2/3/5) before this
# carve-out existed. BR-BLANK-PAGE is untouched — a front-matter page that is
# ACTUALLY blank is still a defect; only the P1 fill-ratio comparison, which
# was never meant to judge these pages against a body-chapter median, exempts
# them.
_CHAPTER_OPENER_RE = re.compile(r"CHAPTER\s+[A-Z][A-Za-z-]+")
_FRONT_MATTER_RE = re.compile(
    r"READING EDITION|^\s*CONTENTS\s*$|S\s*O\s*U\s*R\s*C\s*E\s*C\s*R\s*O\s*S|SOURCE SIGNAL",
    re.M | re.I,
)


def _is_page_fill_exempt(text: str) -> bool:
    return bool(_CHAPTER_OPENER_RE.search(text) or _FRONT_MATTER_RE.search(text))


def scan_watermark(pages_text: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for i, text in enumerate(pages_text, start=1):
        if _WATERMARK_RE.search(text):
            findings.append(
                {
                    "check": "BR-WATERMARK",
                    "severity": "P0",
                    "page": i,
                    "detail": "NotebookLM watermark text present on the rendered page",
                }
            )
    return findings


def scan_duplicate_captions(pages_text: list[str]) -> list[dict[str, Any]]:
    """Flag a short line repeated consecutively on a page — the classic caption
    duplication (an embedded title echoed again as <figcaption>)."""
    findings: list[dict[str, Any]] = []
    for i, text in enumerate(pages_text, start=1):
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for a, b in zip(lines, lines[1:]):
            if a != b or not (0 < len(a.split()) <= 12):
                continue
            # A genuine duplicated caption is a real phrase (a title or
            # figcaption echoed twice). A justified Quranic verse can
            # line-wrap so pdftotext emits several consecutive "lines" that
            # are each just one Arabic letter wrapped in bidi isolate marks —
            # identical by construction, not a caption. Requiring at least
            # two words once the bidi controls are stripped is what tells a
            # real caption apart from that artifact.
            stripped = _BIDI_CONTROL_RE.sub("", a).strip()
            if len(stripped) < 4 or len(stripped.split()) < 2:
                continue
            findings.append(
                {
                    "check": "BR-CAPTION-DUP",
                    "severity": "P1",
                    "page": i,
                    "detail": f"caption printed twice: {a[:60]!r}",
                }
            )
            break
    return findings


_TITLE_PAGE_MARKER = "Generated using podcast-factory AI"


def _structurally_sparse_pages(pages_text: list[str]) -> set[int]:
    """Pages that are legitimately short BY DESIGN, not by rendering defect.

    Three cases, none of them a broken render:
      - the interior title page (eyebrow + book title + author + the AI
        disclaimer panel, printed by every book this template builds — matched
        by the disclaimer's own fixed text rather than the book's own title so
        it needs no per-book knowledge);
      - the Contents page (a list of chapter titles is inherently sparser than
        a page of running prose — that is what a table of contents IS);
      - the last page of a chapter, immediately before a NEW numbered chapter
        opens. Every chapter in this template opens on a fresh page
        (`page-break-before`), so the page before it holds whatever was left
        of the previous chapter's final paragraph — routinely a fraction of a
        full page in ANY book, this one or one off a shelf, and not evidence
        that the render dropped or shrank anything.
    """
    sparse: set[int] = set()
    numbers: dict[int, int] = {}
    for i, text in enumerate(pages_text, start=1):
        stripped = text.strip()
        first_line = (stripped.split("\n") or [""])[0].strip()
        if _TITLE_PAGE_MARKER in text:
            sparse.add(i)
        if first_line == "CONTENTS":
            sparse.add(i)
        m = _HEAD_NUMBER_RE.match(first_line)
        if m:
            numbers[i] = int(m.group(1))
    for i in range(1, len(pages_text)):
        if i in numbers and (i + 1) in numbers and numbers[i + 1] > numbers[i]:
            sparse.add(i)
    return sparse


def scan_blank_and_halfempty(pages_text: list[str]) -> list[dict[str, Any]]:
    """Blank interior pages (P0) and half-empty interior pages (P1).

    First and last pages are exempt (cover/title/colophon legitimately sparse),
    and so — for the P1 fill check only — are the structurally-sparse-by-design
    pages named in `_structurally_sparse_pages`. BR-BLANK-PAGE stays strict for
    every interior page including those: a page that is not just short but
    functionally empty is worth a look even where sparse is expected. Half-empty
    is judged against the median fill of the (non-exempt) interior pages, so a
    book of naturally short pages is not penalized wholesale.
    """
    findings: list[dict[str, Any]] = []
    n = len(pages_text)
    if n < 3:
        return findings
    interior = list(range(2, n))  # 1-indexed pages 2..n-1 -> indices below
    lengths = {p: len(pages_text[p - 1].strip()) for p in interior}
    for p in interior:
        if lengths[p] < _MIN_PAGE_CHARS:
            findings.append(
                {
                    "check": "BR-BLANK-PAGE",
                    "severity": "P0",
                    "page": p,
                    "detail": f"blank/near-blank interior page ({lengths[p]} chars)",
                }
            )
    sparse_by_design = _structurally_sparse_pages(pages_text)
    fill_candidates = [p for p in interior if p not in sparse_by_design]
    non_blank = [lengths[p] for p in fill_candidates if lengths[p] >= _MIN_PAGE_CHARS]
    if len(non_blank) >= 3:
        srt = sorted(non_blank)
        median = srt[len(srt) // 2]
        for p in fill_candidates:
            if _is_page_fill_exempt(pages_text[p - 1]):
                continue
            if _MIN_PAGE_CHARS <= lengths[p] < _HALF_EMPTY_RATIO * median:
                findings.append(
                    {
                        "check": "BR-PAGE-FILL",
                        "severity": "P1",
                        "page": p,
                        "detail": f"half-empty interior page ({lengths[p]} vs median {median} chars)",
                    }
                )
    return findings


# Two assertions that the render did what the renderer intended. Both come from
# real defects that reached a finished PDF and were caught only because a human
# read it: a `.replace` that hit a placeholder's own mention in a CSS comment, so
# every page printed `__BOOK_RUNNING_HEAD__`; and a crosswalk regenerated in the
# wrong shape, which a strict-and-silent reader turned into a missing apparatus
# page plus eight missing provenance lines. Neither is a judgment call and neither
# costs anything, which is the argument for making them assertions rather than
# lessons.
_PLACEHOLDER_RE = re.compile(r"__[A-Z][A-Z0-9_]{3,}__")
_CROSSWALK_HEADING_RE = re.compile(r"S\s*O\s*U\s*R\s*C\s*E\s*C\s*R\s*O\s*S", re.I)


def scan_placeholders(pages_text: list[str]) -> list[dict[str, Any]]:
    """A `__TOKEN__` on the printed page means a substitution did not happen."""
    findings: list[dict[str, Any]] = []
    for i, text in enumerate(pages_text, start=1):
        for token in sorted(set(_PLACEHOLDER_RE.findall(text))):
            findings.append(
                {
                    "check": "BR-PLACEHOLDER",
                    "severity": "P0",
                    "page": i,
                    "detail": f"unsubstituted placeholder {token} printed on the page",
                }
            )
    return findings


def scan_crosswalk_present(pages_text: list[str], book_dir: Path) -> list[dict[str, Any]]:
    """A book WITH a crosswalk file must print its crosswalk page.

    Absent file, no finding — the companion route legitimately has none. Present
    file and no page is the artifact silently dropping content it holds.
    """
    if not (Path(book_dir) / "book" / "source-crosswalk.json").exists():
        return []
    if any(_CROSSWALK_HEADING_RE.search(text) for text in pages_text):
        return []
    return [
        {
            "check": "BR-CROSSWALK-MISSING",
            "severity": "P0",
            "page": 0,
            "detail": (
                "source-crosswalk.json exists but no Source Crosswalk page was printed — "
                "the render dropped the apparatus page and every per-chapter provenance line"
            ),
        }
    ]


# The running head names the chapter, and until this check nothing anywhere read
# margin-box text against chapter boundaries. The first implementation keyed its
# @page rules by array position over a chapters list that leads with the preface,
# so every rule was shifted by one and pages deep in chapter 8 carried chapter 7's
# title — a defect invisible to every other gate, in a book that had just gated
# RENDER-CLEAN.
_HEAD_NUMBER_RE = re.compile(r"^\s*(\d+)\.\s")
_CHAPTER_OPEN_LINE_RE = re.compile(r"^CHAPTER([A-Z-]+)$")
_UNITS = {
    w: i
    for i, w in enumerate(
        "ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE THIRTEEN "
        "FOURTEEN FIFTEEN SIXTEEN SEVENTEEN EIGHTEEN NINETEEN".split(),
        start=1,
    )
}
_TENS = {w: (i + 2) * 10 for i, w in enumerate("TWENTY THIRTY FORTY FIFTY SIXTY SEVENTY EIGHTY NINETY".split())}
# Built by composition rather than spelled out to TWENTY, which is where the
# list used to stop. A book of more than twenty chapters then had every later
# chapter invisible to the owner scan, so the cursor froze at 20 and every page
# after it drew a P1 that could not be true. Enumerating to some new ceiling
# would only move the cliff; a compound reader has none up to ninety-nine.
_NUMBER_WORDS = {
    **_UNITS,
    **_TENS,
    **{f"{t}-{u}": tv + uv for t, tv in _TENS.items() for u, uv in _UNITS.items() if uv < 10},
}


def _chapter_open_number(text: str) -> int | None:
    """The spelled-out chapter number on this page's own "CHAPTER <WORD>"
    eyebrow line, matched per LINE and tolerant of letter-spacing.

    A wide-tracking eyebrow can extract from the PDF as "CHAPTER TWELVE",
    "C H A P T E R T W E LV E" (a space — or nothing, where two glyphs kern
    into a ligature-like run — between letters), or anything between; a plain
    substring match on "CHAPTER\\s+WORD" only caught the first form. Collapsing
    all whitespace out of the line before matching makes the three forms
    identical. Anchored to the WHOLE line (not `.search`) so body prose that
    happens to contain the word "chapter" can never match — the eyebrow is
    printed alone on its own line by construction.
    """
    for line in text.splitlines():
        compact = re.sub(r"\s+", "", line).upper()
        m = _CHAPTER_OPEN_LINE_RE.match(compact)
        if m and m.group(1) in _NUMBER_WORDS:
            return _NUMBER_WORDS[m.group(1)]
    return None


def scan_running_heads(pages_text: list[str]) -> list[dict[str, Any]]:
    """Every numbered running head must name the chapter whose pages it sits on.

    Silent when the book has no numbered heads — a book title head, or none at
    all, is a legitimate choice and not this probe's business.
    """
    opens: list[tuple[int, int]] = []
    for i, text in enumerate(pages_text, start=1):
        n = _chapter_open_number(text)
        if n is not None and not any(num == n for _, num in opens):
            opens.append((i, n))
    if not opens:
        return []
    opens.sort()

    def owner(page: int) -> int:
        current = 0
        for start, num in opens:
            if page >= start:
                current = num
        return current

    findings: list[dict[str, Any]] = []
    for i, text in enumerate(pages_text, start=1):
        first = (text.strip().split("\n") or [""])[0]
        m = _HEAD_NUMBER_RE.match(first)
        if not m:
            continue
        claimed, actual = int(m.group(1)), owner(i)
        if claimed != actual:
            findings.append(
                {
                    "check": "BR-RUNNING-HEAD",
                    "severity": "P1",
                    "page": i,
                    "detail": f"running head names chapter {claimed}; the page belongs to chapter {actual}",
                }
            )
    return findings


def run_all_scans(pages_text: list[str], book_dir: Path | None = None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    findings.extend(scan_watermark(pages_text))
    findings.extend(scan_duplicate_captions(pages_text))
    findings.extend(scan_blank_and_halfempty(pages_text))
    findings.extend(scan_placeholders(pages_text))
    findings.extend(scan_running_heads(pages_text))
    if book_dir is not None:
        findings.extend(scan_crosswalk_present(pages_text, book_dir))
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
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                ).returncode
                if rc != 0 or not out.exists():
                    break
                pages.append(out.read_text(encoding="utf-8", errors="ignore"))
                # pdftotext succeeds past the last page with empty output; stop on a
                # run of trailing empties once we have at least one page.
                if page > 1 and not pages[-1].strip() and not pages[-2].strip():
                    pages = pages[:-2]
                    break
    except Exception:
        return None
    return pages


def run_render_checks(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Run the deterministic render probes and write a report. Never raises."""
    book_dir = Path(book_dir).resolve()
    from deliver_book import _find_pdf

    pdf = _find_pdf(book_dir)
    pages_text = _extract_pages_text(pdf) if pdf else None
    if pages_text is None:
        report = {
            "schema": "podcast.book-render-checks/v1",
            "verdict": "UNKNOWN",
            "reason": "pdftotext unavailable or PDF missing",
            "findings": [],
        }
    else:
        findings = run_all_scans(pages_text, book_dir)
        p0 = [f for f in findings if f["severity"] == "P0"]
        report = {
            "schema": "podcast.book-render-checks/v1",
            "verdict": "RENDER-BROKEN" if p0 else ("RENDER-CAUTION" if findings else "RENDER-CLEAN"),
            "pages": len(pages_text),
            "findings": findings,
        }
    try:
        (book_dir / "_system" / "book-render-checks.json").write_text(
            __import__("json").dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    except Exception as e:
        log(f"    0book-render: render-checks report write skipped (non-fatal): {e}")
    return report
