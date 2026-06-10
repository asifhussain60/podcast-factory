#!/usr/bin/env python3
"""_slide_replicate.py — slide intelligence for 0book-slide-import (2026-06-10).

After the user drops a NotebookLM-exported deck PDF and extract_pages() rasters
it, this module:

  1. ANALYZE  — ONE batched `claude -p` vision call reads the page JPEGs and
     writes `slide-decks/_analysis/<ch>-analysis.json` (per page: title,
     text_blocks, diagram_type, arabic_terms, advisory value_class).
  2. CLASSIFY — `classify_value()` makes the FINAL high/low call
     deterministically (the LLM proposes, Python disposes); the decision +
     rubric reasons are recorded back into the analysis JSON (auditable, and
     a human can flip a page's decision by editing the file — the sig cache
     keys on the PDF only, so manual edits survive re-runs).
  3. REPLICATE — ONE batched call authors text-first SVGs for the high-value
     pages FROM THE ANALYSIS JSON ONLY (never from the raster) →
     `slide-decks/_svg/<ch>/page-NN.svg`, in the house style of
     `_svg_patterns.py` (real <text>, viewBox-only sizing, theme palette).
  4. VERIFY  — `verify_svg()` is deterministic (ElementTree): every analysis
     text block, every Arabic term, and every digit must survive EXACTLY in
     the SVG's text content. Any miss → the page falls back to its raster
     JPEG and the reason is recorded. Original JPEGs are never deleted.

The phase entry `analyze_and_replicate_slides()` returns {page_no: svg_path}
for VERIFIED pages only — `_slide_import.py` re-keys it alongside `pages` and
threads it into `inject_slides(svg_overrides=...)`. On ANY failure the
function degrades to {} (all-raster), preserving the slide-import phase's
non-blocking contract.

Cost: 2-3 `claude -p` calls per deck (flat-rate Max, $0 marginal — P0 cost
policy). Gemini Flash vision is the documented fallback engine if the
claude-image-read path proves unreliable.

Standalone:
  python3 scripts/podcast/_slide_replicate.py <BOOK_DIR> <ch> [--force]
  (expects slide-decks/<ch>*.pdf already dropped + pages extracted)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _authoring._core import _run_claude_p  # noqa: E402
from inject_slide_deck import page_titles, _page_map  # noqa: E402

_PHASE = "0book-slide-import"
_ANALYSIS_TIMEOUT = 1200
_SVG_TIMEOUT = 1800

# ── high-value rubric (deterministic) ────────────────────────────────────────
REPLICABLE_DIAGRAM_TYPES = {"list", "hierarchy", "table", "flow"}
MAX_TEXT_CHARS = 450     # dense slides replicate poorly as SVG
MAX_TEXT_BLOCKS = 14

# House style constants surfaced into the SVG prompt (mirrors _svg_patterns.py).
_SVG_STYLE_NOTE = (
    "viewBox=\"0 0 760 H\" (no width/height attributes; H sized to content), "
    "font-family 'Lato', system-ui, sans-serif; palette: ink #2b2117, "
    "accent #8b4513, muted #7a6a58, hairline #d9cdbd, panel fill #f7f1e6; "
    "real <text> elements only (NEVER paths-as-text, NEVER <foreignObject>)"
)


# ── paths + sig cache ────────────────────────────────────────────────────────

def _analysis_dir(book_dir: Path) -> Path:
    return book_dir / "slide-decks" / "_analysis"


def _analysis_path(book_dir: Path, ch: str) -> Path:
    return _analysis_dir(book_dir) / f"{ch}-analysis.json"


def _svg_dir(book_dir: Path, ch: str) -> Path:
    return book_dir / "slide-decks" / "_svg" / ch


def _replicate_sig_path(book_dir: Path, ch: str) -> Path:
    return _analysis_dir(book_dir) / f".{ch}-replicate-sig"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── prompts ──────────────────────────────────────────────────────────────────

def _analysis_prompt(pages: dict[int, Path], titles: list[str], ch: str,
                     out_path: Path) -> str:
    page_lines = "\n".join(
        f"  page {n}: {p}"
        + (f"  (pdftotext title: {titles[n-1]!r})" if n - 1 < len(titles) and titles[n - 1] else "")
        for n, p in sorted(pages.items()))
    return f"""You are analyzing the pages of a NotebookLM-exported slide deck ({ch}).
READ each page image listed below (use your Read tool on each JPEG path):
{page_lines}

TASK: write a JSON file at exactly this path:
  {out_path}

The file is a JSON LIST with ONE object per page, in page order:
  {{"page": <int>,
    "title": "<the slide's title as shown>",
    "content_summary": "<1 sentence — what the slide shows>",
    "text_blocks": ["<each distinct text element, EXACTLY as printed>", ...],
    "diagram_type": "none" | "list" | "hierarchy" | "table" | "flow" | "other",
    "arabic_terms": ["<transliterated Arabic terms appearing on the slide>", ...],
    "value_class": "high" | "low",
    "illegible": false}}

RULES (hard):
- text_blocks: transcribe EXACTLY — every word, number, and diacritic as
  printed. These are verified mechanically against any replica; transcription
  errors are rejected. Order top-to-bottom, left-to-right.
- diagram_type: "list" = numbered/ordered teaching points; "hierarchy" =
  ranked levels/tree; "table" = rows x columns; "flow" = arrows/sequence;
  "none" = cover/title/photo/prose-only; "other" = anything else.
- value_class is ADVISORY (a deterministic rubric makes the final call):
  "high" = a clean structural diagram whose content is fully legible;
  "low" = covers, photos, dense prose, decorative pages.
- illegible: true when any text on the page cannot be read with confidence.
OUTPUT: write the JSON file at the path above. Do not modify any other file."""


def _svg_prompt(entries: list[dict], ch: str, svg_dir: Path) -> str:
    payload = json.dumps(entries, ensure_ascii=False, indent=2)
    outputs = "\n".join(
        "  - " + str(svg_dir / ("page-%02d.svg" % int(e["page"]))) for e in entries)
    return f"""You are replicating high-value slide pages as clean vector SVG figures for a
book reading edition. Work ONLY from the structured analysis below — do NOT
read the original images; the analysis text_blocks are the verified content.

ANALYSIS ({ch}):
{payload}

OUTPUTS — write ONE .svg file per entry, at exactly these paths:
{outputs}

SVG RULES (hard — each file is verified mechanically):
- House style: {_SVG_STYLE_NOTE}.
- EVERY string in the entry's text_blocks must appear EXACTLY (character for
  character, including diacritics and digits) in <text>/<tspan> content.
  You may split a block across <tspan> lines at spaces, but never alter,
  abbreviate, or re-spell words or numbers.
- Layout by diagram_type: list -> numbered stack of rounded panels;
  hierarchy -> top-down levels connected by hairlines; table -> ruled grid;
  flow -> left-to-right or top-down boxes joined by arrows (marker-end).
- Title at top in accent color, 20px bold. Body text >= 13px.
- Each file starts with `<svg` (no XML prolog, no DOCTYPE, no code fences).
- Self-contained: no external refs, no <image>, no <script>, no <style> blocks
  (inline presentation attributes only).
Do not modify any other file."""


# ── deterministic classification ─────────────────────────────────────────────

def classify_value(entry: dict) -> tuple[str, list[str]]:
    """Final high/low decision + rubric reasons. The LLM's value_class is advisory."""
    reasons: list[str] = []
    dt = str(entry.get("diagram_type") or "none").lower()
    blocks = [str(b) for b in (entry.get("text_blocks") or [])]
    total_chars = sum(len(b) for b in blocks)
    if entry.get("illegible"):
        reasons.append("illegible text on page")
    if dt not in REPLICABLE_DIAGRAM_TYPES:
        reasons.append(f"diagram_type {dt!r} not replicable")
    if not blocks:
        reasons.append("no text blocks")
    if total_chars > MAX_TEXT_CHARS:
        reasons.append(f"{total_chars} chars > {MAX_TEXT_CHARS} (too dense for SVG)")
    if len(blocks) > MAX_TEXT_BLOCKS:
        reasons.append(f"{len(blocks)} text blocks > {MAX_TEXT_BLOCKS}")
    if reasons:
        return "low", reasons
    return "high", [f"replicable {dt}, {len(blocks)} blocks, {total_chars} chars"]


# ── deterministic SVG verification ───────────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def verify_svg(svg_path: Path, entry: dict) -> tuple[bool, str]:
    """True iff every text block, Arabic term, and digit survives exactly."""
    try:
        root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    except (ET.ParseError, OSError) as e:
        return False, f"unparseable SVG: {e}"
    svg_text = _norm(" ".join(root.itertext()))
    for block in (entry.get("text_blocks") or []):
        if _norm(str(block)) not in svg_text:
            return False, f"text block missing/altered: {str(block)[:60]!r}"
    for term in (entry.get("arabic_terms") or []):
        if _norm(str(term)) not in svg_text:
            return False, f"arabic term missing/altered: {term!r}"
    expected_digits = re.findall(r"\d+(?:[.,]\d+)?",
                                 " ".join(str(b) for b in (entry.get("text_blocks") or [])))
    for num in expected_digits:
        if num not in svg_text:
            return False, f"number missing/altered: {num!r}"
    return True, ""


# ── phase entry ──────────────────────────────────────────────────────────────

def analyze_and_replicate_slides(book_dir: Path, ch: str, deck_pdf: Path,
                                 pages_dir: Path, *, force: bool = False,
                                 log=print) -> dict[int, Path]:
    """Return {page_no: verified_svg_path}. Degrades to {} on any failure."""
    try:
        return _analyze_and_replicate(book_dir, ch, deck_pdf, pages_dir,
                                      force=force, log=log)
    except Exception as e:  # noqa: BLE001 — non-blocking contract: raster fallback
        log(f"    {_PHASE}: {ch} slide-intelligence degraded to all-raster: {e}")
        return {}


def _load_verified_svgs(book_dir: Path, ch: str, analysis: list[dict],
                        log=print) -> dict[int, Path]:
    """Re-verify existing SVGs against the (possibly hand-edited) analysis."""
    out: dict[int, Path] = {}
    svg_dir = _svg_dir(book_dir, ch)
    for entry in analysis:
        if entry.get("final_value_class") != "high":
            continue
        page = int(entry["page"])
        svg_path = svg_dir / f"page-{page:02d}.svg"
        if not svg_path.exists():
            continue
        ok, why = verify_svg(svg_path, entry)
        entry["svg_verified"] = ok
        if ok:
            out[page] = svg_path
        else:
            entry["fallback_reason"] = why
            log(f"    {_PHASE}: {ch} page {page} SVG fails verification "
                f"({why}) — raster fallback")
    return out


def _analyze_and_replicate(book_dir: Path, ch: str, deck_pdf: Path,
                           pages_dir: Path, *, force: bool, log=print) -> dict[int, Path]:
    raw_map = _page_map(pages_dir)
    if not raw_map:
        return {}
    analysis_path = _analysis_path(book_dir, ch)
    sig_path = _replicate_sig_path(book_dir, ch)
    sig = _sha(deck_pdf)

    # Cache hit: reuse analysis + SVGs (re-verifying so manual edits to either
    # the analysis JSON or the SVGs take effect without an LLM call).
    if (analysis_path.exists() and sig_path.exists()
            and sig_path.read_text(encoding="utf-8").strip() == sig and not force):
        log(f"    {_PHASE}: {ch} slide-analysis cache hit — skipping LLM")
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        verified = _load_verified_svgs(book_dir, ch, analysis, log=log)
        analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        return verified

    # ── 1. ANALYZE ────────────────────────────────────────────────────────────
    _analysis_dir(book_dir).mkdir(parents=True, exist_ok=True)
    titles = page_titles(deck_pdf)
    rc, stdout, stderr = _run_claude_p(
        _analysis_prompt(raw_map, titles, ch, analysis_path),
        timeout=_ANALYSIS_TIMEOUT, book_dir=book_dir,
        phase=_PHASE, step=f"slide-analysis/{ch}")
    if rc != 0 or not analysis_path.exists():
        raise RuntimeError(
            f"vision analysis failed (rc={rc}; "
            f"stderr={(stderr or '').strip()[:200]})")
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    if not isinstance(analysis, list) or not analysis:
        raise RuntimeError("analysis JSON is not a non-empty list")

    # ── 2. CLASSIFY (deterministic) ───────────────────────────────────────────
    high: list[dict] = []
    for entry in analysis:
        entry["llm_value_class"] = entry.get("value_class")
        final, reasons = classify_value(entry)
        entry["final_value_class"] = final
        entry["rubric_reasons"] = reasons
        if final == "high":
            high.append(entry)
    log(f"    {_PHASE}: {ch} slide-analysis: {len(analysis)} pages, "
        f"{len(high)} high-value → SVG")

    # ── 3. REPLICATE (one batched call) ──────────────────────────────────────
    verified: dict[int, Path] = {}
    if high:
        svg_dir = _svg_dir(book_dir, ch)
        svg_dir.mkdir(parents=True, exist_ok=True)
        for attempt in (1, 2):
            rc, stdout, stderr = _run_claude_p(
                _svg_prompt(high, ch, svg_dir),
                timeout=_SVG_TIMEOUT, book_dir=book_dir,
                phase=_PHASE, step=f"slide-svg/{ch}/attempt-{attempt}")
            if rc != 0:
                raise RuntimeError(f"SVG authoring rc={rc}")
            # ── 4. VERIFY (deterministic) ────────────────────────────────────
            failed: list[dict] = []
            verified = {}
            for entry in high:
                page = int(entry["page"])
                svg_path = svg_dir / f"page-{page:02d}.svg"
                if not svg_path.exists():
                    entry["svg_verified"] = False
                    entry["fallback_reason"] = "SVG not written"
                    failed.append(entry)
                    continue
                ok, why = verify_svg(svg_path, entry)
                entry["svg_verified"] = ok
                if ok:
                    entry.pop("fallback_reason", None)
                    verified[page] = svg_path
                else:
                    entry["fallback_reason"] = why
                    failed.append(entry)
            if not failed or attempt == 2:
                for entry in failed:
                    log(f"    {_PHASE}: {ch} page {entry['page']} → raster fallback "
                        f"({entry.get('fallback_reason')})")
                break
            # One re-author pass for only the failed pages, with reasons appended.
            high = [dict(e, _retry_reason=e.get("fallback_reason")) for e in failed]

    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    sig_path.write_text(sig, encoding="utf-8")
    return verified


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    if len(args) < 2:
        print("usage: _slide_replicate.py <BOOK_DIR> <ch> [--force]", file=sys.stderr)
        return 2
    book_dir = Path(args[0]).resolve()
    ch = args[1]
    deck_dir = book_dir / "slide-decks"
    pdf = deck_dir / "book-deck.pdf" if ch == "book" else next(
        iter(sorted(deck_dir.glob(f"{ch}-*.pdf"))), None)
    if pdf is None or not pdf.exists():
        print(f"deck PDF not found for {ch}", file=sys.stderr)
        return 2
    pages_dir = deck_dir / "_pages" / ch
    result = analyze_and_replicate_slides(book_dir, ch, pdf, pages_dir, force=force)
    print(json.dumps({str(k): str(v) for k, v in result.items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
