#!/usr/bin/env python3
"""intake_stage.py — WC8.1 intake stage-producer (OCR the multi-format sources).

The source PDFs for Ayyuhal Walad are scanned/garbled (no free text layer), so intake REQUIRES
Azure Document Intelligence OCR. This script OCRs one source PDF, caches the result (so re-runs
never re-spend), records the cost in a per-book ledger, and writes the raw OCR markdown.

Chapter segmentation + the common-denominator CORE (cross-source alignment) are done downstream
by the agent (Claude reasoning is free via the Max subscription) reading these OCR caches.

USAGE
    python3 scripts/podcast/intake_stage.py --slug ayyuhal-walad --role english [--force]
    # role in {arabic, english, scholarly} -> reads _system/source/multi/pdf/<slug>-<role>*.pdf

OUTPUTS
    _system/source/multi/ocr/<role>.md          — cached OCR markdown (page-anchored)
    _system/cost-ledger.json                     — running cost ledger (appended)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _azure  # noqa: E402
from _paths import REPO_ROOT, content_dir  # noqa: E402
from _cost_ledger import append_azure_docintel_cost  # noqa: E402

ROLE_PATTERNS = {
    "arabic": "*arabic*orig*",
    "english": "*english*",
    "scholarly": "*scholarly*",
}


def find_pdf(slug: str, role: str) -> Path:
    pdf_dir = content_dir(slug) / "_system" / "source" / "multi" / "pdf"
    matches = sorted(pdf_dir.glob(ROLE_PATTERNS[role]))
    if not matches:
        raise SystemExit(f"No PDF for role '{role}' in {pdf_dir} (pattern {ROLE_PATTERNS[role]})")
    return matches[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--role", required=True, choices=list(ROLE_PATTERNS))
    ap.add_argument("--force", action="store_true", help="re-OCR even if cached (re-spends)")
    args = ap.parse_args()

    book = content_dir(args.slug)
    ocr_dir = book / "_system" / "source" / "multi" / "ocr"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    out = ocr_dir / f"{args.role}.md"

    if out.exists() and not args.force:
        chars = len(out.read_text())
        print(f"[cached] {out.relative_to(REPO_ROOT)} ({chars:,} chars) — no spend. Use --force to re-OCR.")
        return 0

    pdf = find_pdf(args.slug, args.role)
    print(f"[ocr] {pdf.name} -> Azure Doc Intelligence (prebuilt-read)…")
    creds = _azure.load_docintel_creds()
    result = _azure.docintel_analyze_pdf(creds, pdf.read_bytes())
    pages = len((result.get("analyzeResult") or {}).get("pages") or [])
    md = _azure.docintel_pages_to_markdown(result)
    out.write_text(md)

    append_azure_docintel_cost(book, phase="wc8/ocr", step=args.role, pages=pages)
    print(f"[done] {pages} pages, {len(md):,} chars -> {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
