#!/usr/bin/env python3
"""ingest_source.py — Phase 0a normalization for PDF/scan sources (Horizon A).

This is the deterministic ingestion script the executive summary
(`_workspace/podcast-refactor-executive-summary.md` § Horizon A) calls for.
It wires the freshly-provisioned Azure stack (Doc Intelligence + Translator)
into the front of the podcast pipeline. The agent stays dumb; this script
widens the deterministic layer so Phase 0a is no longer "do whatever you can
with the tools you have".

INVOCATION

    python3 scripts/podcast/ingest_source.py <pdf-path> \\
        --book-slug rahat-al-aql \\
        [--src-lang ar] [--no-translate] [--category books] \\
        [--force]

PIPELINE

    PDF (local file)
        │
        ▼ Doc Intelligence prebuilt-read, api-version=2023-07-31
    raw OCR text with <!-- page N --> markers
        │
        ▼ Translator Text v3.0, src→en, chunked at ~10k chars
    English text
        │
        ▼ written to disk
    BOOK_DIR/_system/source/text/raw-extract.md
    BOOK_DIR/_system/source/text/_provenance.json

OUTPUTS

    raw-extract.md       — the canonical Phase 0a artifact named in SKILL.md §1.5
    _provenance.json     — sidecar with timestamps, char counts, doc IDs (audit trail)
    _extraction-notes.md — created empty if missing; Phase 0b/0c append to it

The book must already be scaffolded (run `scaffold_book.py` first). This script
refuses to write into a non-existent BOOK_DIR — it does not invent layout.

NON-GOALS

    - Phase 0b refinement (English smoothing of OCR artifacts).
    - Phase 0c phonetic index build.
    - Phase 0d chapter segmentation.

These are downstream phases that the agent handles in-conversation against the
known-good `raw-extract.md` this script produces.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Local imports — _azure.py is the credential + REST adapter.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _azure  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_DIR = REPO_ROOT / "content" / "podcast" / "library"

ALLOWED_CATEGORIES = {"books", "articles", "documents", "lectures", "interviews", "letters"}


def find_book_dir(book_slug: str, category: str | None) -> Path:
    """Locate the BOOK_DIR by slug, requiring it to already exist.

    If `category` is given, looks only there. Otherwise scans all categories
    and refuses on ambiguity (two books in different categories sharing a
    slug). The intent: this script does not scaffold; `scaffold_book.py` does.
    """
    if category:
        candidate = LIBRARY_DIR / category / book_slug
        if not candidate.is_dir():
            raise SystemExit(
                f"ERROR: book directory not found: {candidate}\n"
                f"Run: python3 scripts/podcast/scaffold_book.py {category} {book_slug} \"<Title>\""
            )
        return candidate

    matches = [
        LIBRARY_DIR / cat / book_slug
        for cat in ALLOWED_CATEGORIES
        if (LIBRARY_DIR / cat / book_slug).is_dir()
    ]
    if not matches:
        raise SystemExit(
            f"ERROR: no book directory found for slug '{book_slug}' under {LIBRARY_DIR}.\n"
            f"Run: python3 scripts/podcast/scaffold_book.py <category> {book_slug} \"<Title>\""
        )
    if len(matches) > 1:
        rendered = "\n  ".join(str(m) for m in matches)
        raise SystemExit(
            f"ERROR: slug '{book_slug}' resolves under multiple categories:\n  {rendered}\n"
            f"Disambiguate with --category."
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 0a ingestion: PDF → OCR (Doc Intel) → English (Translator) → "
            "BOOK_DIR/_system/source/text/raw-extract.md"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "After this script: agent runs Phase 0b (English refinement) → 0c "
            "(phonetic index) → 0d (chapter design) → 0e (enrichment), per SKILL.md §1.5."
        ),
    )
    parser.add_argument("pdf_path", help="Path to the source PDF.")
    parser.add_argument(
        "--book-slug",
        required=True,
        help="Slug of the already-scaffolded book under content/podcast/library/<cat>/<slug>/.",
    )
    parser.add_argument(
        "--category",
        choices=sorted(ALLOWED_CATEGORIES),
        help="Optional. Restrict slug lookup to this category.",
    )
    parser.add_argument(
        "--src-lang",
        default="ar",
        help="Source language code for the Translator step (default: ar).",
    )
    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="Skip the Translator step. Use when the source is already in English.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite raw-extract.md and _provenance.json if they exist.",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).expanduser().resolve()
    if not pdf_path.is_file():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 2
    if pdf_path.suffix.lower() != ".pdf":
        print(
            f"ERROR: this script only handles PDFs (got {pdf_path.suffix}). "
            f"For other formats see SKILL.md §1.5 Phase 0a normalization table.",
            file=sys.stderr,
        )
        return 2

    book_dir = find_book_dir(args.book_slug, args.category)
    out_dir = book_dir / "_system" / "source" / "text"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "raw-extract.md"
    prov_path = out_dir / "_provenance.json"
    notes_path = out_dir / "_extraction-notes.md"

    if raw_path.exists() and not args.force:
        print(
            f"ERROR: {raw_path} already exists. Pass --force to overwrite, "
            f"or delete the file and re-run.",
            file=sys.stderr,
        )
        return 2

    pdf_bytes = pdf_path.read_bytes()
    print(f"==> Source: {pdf_path}  ({len(pdf_bytes):,} bytes)")
    print(f"==> Book:   {book_dir.relative_to(REPO_ROOT)}")

    # ── Doc Intelligence ─────────────────────────────────────────────────
    print("==> Doc Intelligence: submitting prebuilt-read …")
    try:
        docintel = _azure.load_docintel_creds()
    except _azure.AzureCredsError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 3

    t0 = time.monotonic()
    result = _azure.docintel_analyze_pdf(docintel, pdf_bytes)
    di_elapsed = time.monotonic() - t0
    analyze = result.get("analyzeResult") or {}
    page_count = len(analyze.get("pages") or [])
    ocr_text = _azure.docintel_pages_to_markdown(result)
    print(f"    OCR done: {page_count} pages, {len(ocr_text):,} chars, {di_elapsed:.1f}s")

    # ── Translator (optional) ────────────────────────────────────────────
    if args.no_translate:
        final_text = ocr_text
        tr_elapsed = 0.0
        tr_region = None
    else:
        print(f"==> Translator: {args.src_lang} → en, chunked …")
        try:
            translator = _azure.load_translator_creds()
        except _azure.AzureCredsError as e:
            print(f"FATAL: {e}", file=sys.stderr)
            return 3
        t0 = time.monotonic()
        final_text = _azure.translate_text(
            translator, ocr_text, src_lang=args.src_lang, tgt_lang="en"
        )
        tr_elapsed = time.monotonic() - t0
        tr_region = translator.region
        print(f"    Translation done: {len(final_text):,} chars, {tr_elapsed:.1f}s")

    # ── Persist ──────────────────────────────────────────────────────────
    raw_path.write_text(final_text, encoding="utf-8")
    if not notes_path.exists():
        notes_path.write_text(
            "# Extraction notes\n\n"
            "Anything uncertain from Phase 0a/0b: low-confidence OCR spans, "
            "illegible passages, footnote-vs-body ambiguity, translator brackets. "
            "Append entries as they surface during refinement.\n",
            encoding="utf-8",
        )

    provenance = {
        "schema": "podcast.ingest-source/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(pdf_path),
            "byte_size": len(pdf_bytes),
        },
        "book_slug": args.book_slug,
        "book_dir": str(book_dir.relative_to(REPO_ROOT)),
        "doc_intelligence": {
            "endpoint": docintel.endpoint,
            "api_version": _azure.DOCINTEL_API_VERSION,
            "model": _azure.DOCINTEL_MODEL,
            "page_count": page_count,
            "ocr_char_count": len(ocr_text),
            "elapsed_seconds": round(di_elapsed, 2),
            "operation_id": (analyze.get("apiVersion") or "") and result.get("status"),
        },
        "translator": (
            None
            if args.no_translate
            else {
                "api_version": _azure.TRANSLATOR_API_VERSION,
                "src_lang": args.src_lang,
                "tgt_lang": "en",
                "region": tr_region,
                "output_char_count": len(final_text),
                "elapsed_seconds": round(tr_elapsed, 2),
            }
        ),
        "outputs": {
            "raw_extract": str(raw_path.relative_to(REPO_ROOT)),
            "extraction_notes": str(notes_path.relative_to(REPO_ROOT)),
        },
    }
    prov_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print(f"OK: wrote {raw_path.relative_to(REPO_ROOT)}")
    print(f"OK: wrote {prov_path.relative_to(REPO_ROOT)}")
    print()
    print("Next: Phase 0b (English refinement) — see SKILL.md §1.5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
