#!/usr/bin/env python3
"""Generate a faithful translation-edition PDF and slide-deck pair.

This is the automated path for ``deliverable_mode: translation_edition``. It
reuses existing pipeline components:

  source PDF -> 0a ingest -> 0b refine -> 0book-design -> translation compose
  -> 0book-illustrate -> book-level NotebookLM slide pair -> 0book-render

It does not run podcast audio, phonetics, gap-analysis, or enrichment.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _authoring._book_design import author_phase_book_design  # noqa: E402
from _authoring._refine import author_phase_0b  # noqa: E402
from _authoring._core import AuthoringError  # noqa: E402
from _book_illustrate import author_phase_book_illustrate  # noqa: E402
from _paths import resolve_content  # noqa: E402
from _slide_authoring import author_book_deck_pair  # noqa: E402
from _translation_edition import (  # noqa: E402
    assert_translation_contract,
    author_translation_edition_compose,
)
from build_book_pdf import build_book  # noqa: E402
from validate_book_ready import validate_book  # noqa: E402

# Model policy for this path (2026-07-15): default to Sonnet, reserve Opus for
# steps where translation-fidelity or one-shot structural judgment is at stake.
#   0book-design (chapter segmentation of the whole book, one call, cascades
#     into every chapter) and 0book-compose (the faithful translation against
#     Arabic ground truth that book-challenger audits for fidelity/no-
#     augmentation) stay on the implicit default (Opus) — unchanged below.
#   0book-illustrate (diagram-classification triage) and the book-level
#     slide-deck pair (presentational NotebookLM framing over already-
#     translated content) are mechanical/presentational, not translation-
#     fidelity-critical, so they run on Sonnet via TRANSLATION_EDITION_LIGHT_MODEL.
TRANSLATION_EDITION_LIGHT_MODEL = "claude-sonnet-5"


def _info(msg: str) -> None:
    print(msg)


def _run_ingest(book_dir: Path, source_pdf: Path, slug: str, src_lang: str) -> None:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "ingest_source.py"),
        str(source_pdf),
        "--book-slug",
        slug,
        "--src-lang",
        src_lang,
        "--category",
        "books",
        "--force",
    ]
    proc = subprocess.run(cmd, cwd=SCRIPT_DIR.parents[1], capture_output=True, text=True)
    if proc.returncode != 0:
        raise AuthoringError(
            phase="0a",
            message=f"ingest_source.py failed rc={proc.returncode}\n{proc.stderr[:600]}\n{proc.stdout[:600]}",
            manual_fallback="Fix OCR/Translator credentials or source path, then re-run.",
        )


def generate_translation_edition(
    slug: str,
    *,
    source_pdf: Path | None = None,
    src_lang: str = "ar",
    confirm_ingest: bool = False,
    force_refine: bool = False,
    force_design: bool = False,
    force_compose: bool = False,
    force_illustrations: bool = False,
) -> int:
    book_dir = resolve_content(slug)
    if not book_dir.exists():
        print(f"ERROR: content folder not found for slug {slug!r}: {book_dir}", file=sys.stderr)
        return 2

    # DEPRECATED under book_pipeline_v2: the standalone translation-edition script
    # is superseded by the unified book path (book_augmentation/book_voice knobs)
    # driven through the orchestrator. It stays functional while the flag is OFF;
    # Phase 7 removes it once v2 is the default. Surface the deprecation loudly.
    from _pipeline_flags import book_pipeline_v2_enabled  # noqa: PLC0415
    if book_pipeline_v2_enabled(book_dir):
        _info(
            "NOTE: book_pipeline_v2 is ON for this book — the unified compose path "
            "(faithful base + knobs) supersedes generate_translation_edition.py. "
            "Prefer driving the book branch through the orchestrator."
        )

    assert_translation_contract(book_dir)

    raw = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    ocr_raw = book_dir / "_system" / "source" / "ocr" / "raw-extract.md"
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"

    ingested = False
    needs_ingest = not raw.exists() or (src_lang != "en" and not ocr_raw.exists())
    if needs_ingest:
        if not source_pdf:
            print(
                "ERROR: source artifacts are incomplete; pass --source-pdf and --confirm-ingest.",
                file=sys.stderr,
            )
            return 2
        if not confirm_ingest:
            print(
                "ERROR: ingest would call Azure OCR/Translator. Re-run with --confirm-ingest to spend.",
                file=sys.stderr,
            )
            return 2
        _info("phase 0a: OCR + translation")
        _run_ingest(book_dir, source_pdf, slug, src_lang)
        ingested = True
    else:
        _info("phase 0a: source artifacts exist - skip")

    if ingested or force_refine:
        shutil.rmtree(book_dir / "_system" / "source" / "text" / "_chunks" / "0b", ignore_errors=True)
        if refined.exists():
            refined.unlink()

    if not refined.exists():
        _info("phase 0b: faithful English refinement")
        author_phase_0b(book_dir, log=_info, category="books")
    else:
        _info("phase 0b: refined-english.md exists - skip")

    _info("phase 0book-design: translation edition structure")
    author_phase_book_design(book_dir, log=_info, force=force_design)

    _info("phase 0book-compose: faithful translation edition")
    author_translation_edition_compose(book_dir, log=_info, force=(force_compose or ingested or force_refine))

    _info("phase 0book-illustrate: monochrome SVG diagrams")
    author_phase_book_illustrate(
        book_dir, log=_info, force=(force_illustrations or force_compose or ingested or force_refine),
        model_flag=TRANSLATION_EDITION_LIGHT_MODEL,
    )

    _info("phase per-chapter-slides/book: monochrome NotebookLM slide pair")
    deck = author_book_deck_pair(book_dir, model_flag=TRANSLATION_EDITION_LIGHT_MODEL)
    if not deck.success:
        raise AuthoringError(
            phase="per-chapter-slides",
            message="book-level slide pair failed validation: " + "; ".join(deck.validation_findings[:5]),
            manual_fallback="Re-run generate_translation_edition.py after fixing the slide findings.",
        )

    _info("phase 0book-render: PDF")
    build_book(book_dir, log=_info)
    verdict = validate_book(book_dir)
    (book_dir / "_system" / "book-validation-report.json").write_text(
        json.dumps(verdict, indent=2), encoding="utf-8",
    )
    if verdict.get("verdict") == "BOOK-BROKEN":
        raise AuthoringError(
            phase="0book-render",
            message="translation edition failed validation: " + str(verdict.get("summary")),
            manual_fallback="Fix the reported manuscript/PDF issue, then rerun with targeted --force flags.",
        )
    _info("DONE: translation edition artifacts are under book/ and slide-decks/.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--source-pdf", type=Path)
    ap.add_argument("--src-lang", default="ar")
    ap.add_argument("--confirm-ingest", action="store_true")
    ap.add_argument("--force-refine", action="store_true")
    ap.add_argument("--force-design", action="store_true")
    ap.add_argument("--force-compose", action="store_true")
    ap.add_argument("--force-illustrations", action="store_true")
    args = ap.parse_args(argv)
    try:
        return generate_translation_edition(
            args.slug,
            source_pdf=args.source_pdf,
            src_lang=args.src_lang,
            confirm_ingest=args.confirm_ingest,
            force_refine=args.force_refine,
            force_design=args.force_design,
            force_compose=args.force_compose,
            force_illustrations=args.force_illustrations,
        )
    except AuthoringError as e:
        print(f"ERROR [{e.phase}]: {e}", file=sys.stderr)
        if e.manual_fallback:
            print(e.manual_fallback, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
