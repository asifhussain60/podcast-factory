"""ocr.py — step 2. Azure Doc Intelligence → the immutable source record.

Reuses the pipeline's existing `_azure.docintel_analyze_pdf` (prebuilt-read),
which iterates `analyzeResult.pages[*].lines` and preserves line breaks
verbatim. We keep the LINES, with page/line provenance, rather than the flat
markdown the podcast path uses — the facing-column layout needs addressable
atoms, and the integrity gate needs provenance.

OCR DIACRITIC FIDELITY — validated 2026-07-19 before this lane was built
------------------------------------------------------------------------
prebuilt-read was run over a real vocalised Arabic scan (15 pages, 20,187
Arabic letters). Result: 1,435 tashkeel marks recovered across all eight mark
types (shadda, fatha, kasra, damma, sukun, and all three tanween), and of 968
vocalised tokens exactly ONE carried a structurally impossible mark sequence.

Conclusion: OCR does NOT drop or mangle diacritics — the plan's headline risk is
retired. The residual, real risk is LETTER-level confusion on poor scans
(observed: ب read as و). That is precisely what the human review halt at step 4
exists to catch, and it is why review is a hard halt rather than a prompt.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _azure import DOCINTEL_API_VERSION, DOCINTEL_MODEL, docintel_analyze_pdf  # noqa: E402
from _azure_creds import load_docintel_creds  # noqa: E402

from .schema import SourceLine, SourceRecord, SupplicationError, line_id  # noqa: E402


def lines_from_result(result: dict) -> list[SourceLine]:
    """Flatten `analyzeResult.pages[*].lines` into ordered, addressable atoms.

    Blank lines are dropped (they carry no source text and would create units
    with empty sources); every surviving line keeps its ORIGINAL 1-based line
    number on its page, so an id always points at the same physical line even
    after blanks are removed.
    """
    pages = (result.get("analyzeResult") or {}).get("pages") or []
    out: list[SourceLine] = []
    for page in pages:
        pno = int(page.get("pageNumber") or 0)
        for lno, ln in enumerate(page.get("lines") or [], start=1):
            text = (ln.get("content") or "").strip()
            if not text:
                continue
            out.append(SourceLine(id=line_id(pno, lno), page=pno, line=lno, text=text))
    if not out:
        raise SupplicationError("OCR returned no text lines — is the source PDF a blank or image-only scan?")
    return out


def run(book_dir: Path, *, slug: str, source_language: str, pdf_path: Path) -> SourceRecord:
    """Run OCR and write `_system/source-record.json`. Refuses to overwrite."""
    if not pdf_path.is_file():
        raise SupplicationError(f"source PDF not found: {pdf_path}")

    result = docintel_analyze_pdf(load_docintel_creds(), pdf_path.read_bytes())
    record = SourceRecord(
        slug=slug,
        source_language=source_language,
        source_pdf=str(pdf_path),
        lines=lines_from_result(result),
        ocr={
            "provider": "azure-document-intelligence",
            "model": DOCINTEL_MODEL,
            "api_version": DOCINTEL_API_VERSION,
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pages": len((result.get("analyzeResult") or {}).get("pages") or []),
        },
    )
    record.write(record_path(book_dir))
    return record


def record_path(book_dir: Path) -> Path:
    return book_dir / "_system" / "source-record.json"
