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
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _azure  # noqa: E402
from _paths import REPO_ROOT  # noqa: E402

# Azure Document Intelligence prebuilt-read list price (first tier): USD per page.
DOCINTEL_USD_PER_PAGE = 1.50 / 1000.0

ROLE_PATTERNS = {
    "arabic": "*arabic*orig*",
    "english": "*english*",
    "scholarly": "*scholarly*",
}


def book_dir(slug: str) -> Path:
    return REPO_ROOT / "content" / "drafts" / "books" / slug


def find_pdf(slug: str, role: str) -> Path:
    pdf_dir = book_dir(slug) / "_system" / "source" / "multi" / "pdf"
    matches = sorted(pdf_dir.glob(ROLE_PATTERNS[role]))
    if not matches:
        raise SystemExit(f"No PDF for role '{role}' in {pdf_dir} (pattern {ROLE_PATTERNS[role]})")
    return matches[0]


def log_cost(slug: str, entry: dict) -> None:
    p = book_dir(slug) / "_system" / "cost-ledger.json"
    ledger = {"slug": slug, "entries": [], "total_usd": 0.0}
    if p.exists():
        try:
            ledger = json.loads(p.read_text())
        except Exception:
            pass
    ledger["entries"].append(entry)
    ledger["total_usd"] = round(sum(e.get("cost_usd", 0.0) for e in ledger["entries"]), 4)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ledger, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--role", required=True, choices=list(ROLE_PATTERNS))
    ap.add_argument("--force", action="store_true", help="re-OCR even if cached (re-spends)")
    args = ap.parse_args()

    ocr_dir = book_dir(args.slug) / "_system" / "source" / "multi" / "ocr"
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

    cost = round(pages * DOCINTEL_USD_PER_PAGE, 4)
    log_cost(args.slug, {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "op": "ocr",
        "service": "azure-docintel-prebuilt-read",
        "role": args.role,
        "pdf": pdf.name,
        "pages": pages,
        "unit_usd": DOCINTEL_USD_PER_PAGE,
        "cost_usd": cost,
    })
    print(f"[done] {pages} pages, {len(md):,} chars -> {out.relative_to(REPO_ROOT)}  (cost ${cost:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
