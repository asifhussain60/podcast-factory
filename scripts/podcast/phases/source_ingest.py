"""phases/source_ingest.py — Phase 0a for SKIP_OCR_CATEGORIES (pre-written sources).

Replaces the Azure OCR path (ingest_source.py) for categories whose source
material is already written in English: `explainers` and `sites`.

Rather than running Azure Doc Intelligence + Translator, this module reads the
pre-written .md files from BOOK_DIR/source/, concatenates them into the
standard raw-extract.md artifact, and writes the _provenance.json sidecar.
The rest of the pipeline (0b refinement, 0d chapter design, 0e enrichment,
per-chapter framing) then runs unchanged via category-aware routing that
already exists in _authoring/_refine.py, _chapter_design.py, _framing.py,
and _enrichment.py.

OUTPUTS
    BOOK_DIR/_system/source/text/raw-extract.md        — concatenated source
    BOOK_DIR/_system/source/text/_provenance.json      — audit sidecar
    BOOK_DIR/_system/source/text/_extraction-notes.md  — stub for 0b/0c

INVOCATION (internal — called by _drive_source_ready_through_0f)
    from phases.source_ingest import phase_0a_ingest_source_md
    phase_0a_ingest_source_md(book_dir, category="explainers", slug="my-slug")
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent  # scripts/podcast
sys.path.insert(0, str(_HERE))

from _authoring._core import SKIP_OCR_CATEGORIES
from _paths import REPO_ROOT


def _word_count(text: str) -> int:
    return len(text.split())


def phase_0a_ingest_source_md(
    book_dir: Path,
    category: str,
    slug: str,
    *,
    force: bool = False,
) -> None:
    """Ingest pre-written .md source files for SKIP_OCR_CATEGORIES content.

    Reads all *.md files from BOOK_DIR/source/ in alphabetical order,
    concatenates them into raw-extract.md with <!-- source: filename -->
    section markers, and writes the standard Phase 0a sidecar files.

    Args:
        book_dir: Path to the book's content directory.
        category:  Content category (must be in SKIP_OCR_CATEGORIES).
        slug:      Book slug (used in provenance metadata only).
        force:     If True, overwrites an existing raw-extract.md.

    Raises:
        RuntimeError: category not in SKIP_OCR_CATEGORIES, source/ missing,
                      no .md files found, or raw-extract.md exists and
                      force=False.
    """
    if category not in SKIP_OCR_CATEGORIES:
        raise RuntimeError(
            f"phase_0a_ingest_source_md: category {category!r} is not in "
            f"SKIP_OCR_CATEGORIES {sorted(SKIP_OCR_CATEGORIES)}. "
            f"For PDF-sourced books use phase_0a_ingest (Azure OCR path)."
        )

    source_dir = book_dir / "source"
    if not source_dir.is_dir():
        raise RuntimeError(
            f"phase_0a_ingest_source_md: source directory not found at "
            f"{source_dir.relative_to(REPO_ROOT)}. "
            f"Place pre-written .md episode files there before running."
        )

    source_files = sorted(source_dir.glob("*.md"))
    if not source_files:
        raise RuntimeError(
            f"phase_0a_ingest_source_md: no .md files found in "
            f"{source_dir.relative_to(REPO_ROOT)}. "
            f"Expected at least one episode source file."
        )

    out_dir = book_dir / "_system" / "source" / "text"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_extract = out_dir / "raw-extract.md"
    if raw_extract.exists() and not force:
        raise RuntimeError(
            f"phase_0a_ingest_source_md: {raw_extract.relative_to(REPO_ROOT)} "
            f"already exists. Pass force=True to overwrite, or delete the file "
            f"before retrying phase 0a."
        )

    # ── Build concatenated source with section markers ─────────────────────
    sections: list[str] = []
    file_meta: list[dict] = []

    for f in source_files:
        text = f.read_text(encoding="utf-8")
        wc = _word_count(text)
        sections.append(f"<!-- source: {f.name} -->\n\n{text}")
        file_meta.append(
            {
                "name": f.name,
                "byte_size": f.stat().st_size,
                "word_count": wc,
            }
        )

    concatenated = "\n\n".join(sections)
    total_words = sum(m["word_count"] for m in file_meta)

    raw_extract.write_text(concatenated, encoding="utf-8")

    # ── Provenance sidecar ─────────────────────────────────────────────────
    provenance = {
        "schema": "podcast.ingest-source-md/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "book_slug": slug,
        "book_dir": str(book_dir.relative_to(REPO_ROOT)),
        "category": category,
        "source_files": file_meta,
        "total_word_count": total_words,
        "azure_ocr": None,
        "translator": None,
    }
    (out_dir / "_provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── Extraction notes stub (0b/0c append here) ─────────────────────────
    notes_path = out_dir / "_extraction-notes.md"
    if not notes_path.exists():
        notes_path.write_text(
            f"# Extraction Notes — {slug}\n\n"
            f"Source type: pre-written English ({category})\n"
            f"Files ingested: {len(source_files)}\n"
            f"Total words: {total_words:,}\n\n"
            f"Anything uncertain from Phase 0a/0b: document here.\n",
            encoding="utf-8",
        )

    print(
        f"  phase 0a (source-md) · ingested {len(source_files)} file(s), "
        f"{total_words:,} words → {raw_extract.relative_to(REPO_ROOT)}"
    )
