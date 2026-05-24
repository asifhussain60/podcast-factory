#!/usr/bin/env python3
"""ocr_image_pages.py — Stitch a folder of PNG page images into a PDF,
then OCR + translate via Azure for the master-and-the-disciple OCR-diff track.

Why this script exists:
The Phase 0a `ingest_source.py` path assumes a single source PDF. Some books
(notably the-master-and-the-disciple) arrive as a folder of per-page PNGs
already extracted from the original PDF. Stitching them back into a PDF lets
us reuse the same Doc Intelligence + Translator helpers in `_azure.py` instead
of writing a parallel image-only OCR path.

INVOCATION

    python3 scripts/podcast/ocr_image_pages.py \\
        --images-dir content/drafts/the-master-and-the-disciple/_system/source/images \\
        --out-dir   content/drafts/the-master-and-the-disciple/_system/source/ocr \\
        [--src-lang ar] [--no-translate] [--force]

PIPELINE

    page_0001.png … page_NNNN.png   (sorted lexically — pad your filenames)
        │
        ▼ Pillow Image.save(format='PDF', save_all=True, append_images=[...])
    source-stitched.pdf
        │
        ▼ Doc Intelligence prebuilt-read (api-version 2023-07-31)
    raw OCR text with <!-- page N --> markers
        │
        ▼ Translator Text v3.0, src→en, chunked at ~10k chars
    translated-en.md
        │
        ▼ written to out-dir
    OUT_DIR/source-stitched.pdf
    OUT_DIR/raw-extract.md      (the OCR'd original-language text)
    OUT_DIR/translated-en.md    (English; omitted with --no-translate)
    OUT_DIR/_provenance.json    (timestamps, sizes, doc IDs)

This is an OCR-DIFF artifact, not a replacement for curator-authored chapter
prose. The companion script `diff_ocr_vs_chapters.py` aligns the output
against existing chapters/ch??-*.md and emits a drift report.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.stderr.write(
        "Pillow is required: /usr/bin/python3 -m pip install --user pillow\n"
    )
    sys.exit(2)

# Local: pure-stdlib helpers, no pip-installs at runtime
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _azure import (  # noqa: E402
    AzureCredsError,
    docintel_analyze_pdf,
    docintel_pages_to_markdown,
    load_docintel_creds,
    load_translator_creds,
    translate_text,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stitch_subset(pngs: list[Path]) -> bytes:
    """Stitch a list of PNG paths into a single multi-page PDF as bytes."""
    first = Image.open(pngs[0]).convert("RGB")
    rest = [Image.open(p).convert("RGB") for p in pngs[1:]]
    buf = BytesIO()
    first.save(
        buf,
        format="PDF",
        save_all=True,
        append_images=rest,
        resolution=200.0,
    )
    return buf.getvalue()


def stitch_pngs_in_chunks(
    images_dir: Path,
    max_bytes: int = 3_500_000,
    max_pages: int = 2,
) -> list[tuple[bytes, int, int]]:
    """Stitch PNGs into chunked PDFs.

    Two ceilings applied per chunk:
    - max_bytes: respect Doc Intel's per-request size cap (free tier: 4MB)
    - max_pages: respect Doc Intel's per-request page cap (free tier F0: 2 pages,
      paid tier S0: 2000 pages). Hard-set to 2 by default because F0 silently
      truncates beyond page 2 instead of erroring.

    Returns list of (pdf_bytes, start_page_1indexed, end_page_1indexed).
    """
    pngs = sorted(p for p in images_dir.iterdir() if p.suffix.lower() == ".png")
    if not pngs:
        raise FileNotFoundError(f"No .png files found in {images_dir}")

    chunks: list[tuple[bytes, int, int]] = []
    i = 0
    while i < len(pngs):
        batch = pngs[i : i + max_pages]
        b = _stitch_subset(batch)
        # If even a single page > max_bytes, accept (rare for normal scans)
        if len(b) > max_bytes and len(batch) > 1:
            # Halve the batch and retry — defensive; shouldn't normally trigger
            batch = batch[: len(batch) // 2]
            b = _stitch_subset(batch)
        chunks.append((b, i + 1, i + len(batch)))
        i += len(batch)
    return chunks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--images-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument(
        "--src-lang",
        default="en",
        help="Source language for translation (default: en; use 'ar' for Arabic).",
    )
    ap.add_argument("--no-translate", action="store_true")
    ap.add_argument("--force", action="store_true", help="Overwrite existing out-dir artifacts.")
    args = ap.parse_args()

    images_dir: Path = args.images_dir.resolve()
    out_dir: Path = args.out_dir.resolve()

    if not images_dir.is_dir():
        sys.stderr.write(f"images-dir not found: {images_dir}\n")
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    stitched_pdf = out_dir / "source-stitched.pdf"
    raw_extract = out_dir / "raw-extract.md"
    translated = out_dir / "translated-en.md"
    provenance = out_dir / "_provenance.json"

    if stitched_pdf.exists() and not args.force:
        sys.stderr.write(
            f"Refusing to overwrite {stitched_pdf} — pass --force to re-run.\n"
        )
        return 3

    started = _utcnow_iso()
    t0 = time.monotonic()

    # 1. Stitch (chunked to ≤3.5MB per chunk for Doc Intel free-tier 4MB cap)
    print(f"[1/3] Stitching PNGs from {images_dir} (chunked ≤3.5MB) …", file=sys.stderr)
    chunks = stitch_pngs_in_chunks(images_dir, max_bytes=3_500_000)
    # Write the FIRST chunk to source-stitched.pdf for reference/debug
    stitched_pdf.write_bytes(chunks[0][0])
    total_pages = sum(end - start + 1 for _b, start, end in chunks)
    total_bytes = sum(len(b) for b, _s, _e in chunks)
    print(
        f"      → {len(chunks)} chunks, {total_pages} pages total, "
        f"{total_bytes:,} bytes (first chunk saved as {stitched_pdf.name})",
        file=sys.stderr,
    )
    for i, (b, s, e) in enumerate(chunks, 1):
        print(f"        chunk {i}: pages {s}-{e}  ({len(b):,} bytes)", file=sys.stderr)

    # 2. OCR (one Doc Intel call per chunk; concatenate markdown)
    try:
        docintel = load_docintel_creds()
    except AzureCredsError as e:
        sys.stderr.write(f"Azure creds error: {e}\n")
        return 4
    md_parts: list[str] = []
    pages_count = 0
    INTER_CHUNK_SLEEP_S = 5.0  # F0: 15 TPM hard cap → ~4s/req minimum
    MAX_RETRIES_429 = 4
    for i, (b, s, e) in enumerate(chunks, 1):
        print(
            f"[2/3] Doc Intel chunk {i}/{len(chunks)} (pages {s}-{e}) …",
            file=sys.stderr,
        )
        # Retry-on-429 loop. The 429 body says "retry after N seconds";
        # we honor that with exponential floor.
        attempt = 0
        while True:
            try:
                result = docintel_analyze_pdf(docintel, b, poll_interval_s=5.0)
                break
            except RuntimeError as exc:
                msg = str(exc)
                if "429" in msg and attempt < MAX_RETRIES_429:
                    # parse "retry after N seconds" if present, else 30s
                    backoff = 30.0
                    if "retry after " in msg:
                        try:
                            backoff = float(msg.split("retry after ")[1].split(" ")[0])
                        except (ValueError, IndexError):
                            backoff = 30.0
                    attempt += 1
                    print(
                        f"      [429] backing off {backoff:.0f}s (attempt {attempt}/{MAX_RETRIES_429}) …",
                        file=sys.stderr,
                    )
                    time.sleep(backoff + 2.0)
                    continue
                raise
        pages = (result.get("analyzeResult") or {}).get("pages") or []
        pages_count += len(pages)
        if i < len(chunks):
            time.sleep(INTER_CHUNK_SLEEP_S)
        # Renumber page markers to global page numbers, not per-chunk 1..N
        chunk_md = docintel_pages_to_markdown(result)
        # Replace `<!-- page N -->` markers with global page numbers (s + N - 1)
        # Simplest: scan line-by-line
        out_lines = []
        local_pages_seen = 0
        for line in chunk_md.splitlines():
            if line.startswith("<!-- page ") and line.endswith(" -->"):
                local_pages_seen += 1
                global_n = s + local_pages_seen - 1
                out_lines.append(f"<!-- page {global_n} -->")
            else:
                out_lines.append(line)
        md_parts.append("\n".join(out_lines))
    md = "\n\n".join(md_parts).rstrip() + "\n"
    pages = list(range(1, pages_count + 1))
    raw_extract.write_text(md, encoding="utf-8")
    print(
        f"      → {raw_extract.name} ({len(md):,} chars, {len(pages)} pages)",
        file=sys.stderr,
    )

    # 3. Translate (optional)
    translated_chars = 0
    if not args.no_translate and args.src_lang != "en":
        translator = load_translator_creds()
        print(
            f"[3/3] Translating {args.src_lang} → en via Azure Translator …",
            file=sys.stderr,
        )
        en_text = translate_text(
            translator, md, src_lang=args.src_lang, tgt_lang="en"
        )
        translated.write_text(en_text, encoding="utf-8")
        translated_chars = len(en_text)
        print(
            f"      → {translated.name} ({translated_chars:,} chars)",
            file=sys.stderr,
        )
    elif not args.no_translate:
        # Source is already English (master-disciple case): copy raw → translated
        # so downstream diff has a single canonical artifact to compare against.
        translated.write_text(md, encoding="utf-8")
        translated_chars = len(md)
        print(
            f"[3/3] Source is en — skipped translate, copied raw → {translated.name}",
            file=sys.stderr,
        )
    else:
        print("[3/3] --no-translate → skipped Translator", file=sys.stderr)

    # Provenance
    provenance.write_text(
        json.dumps(
            {
                "script": "ocr_image_pages.py",
                "started_at": started,
                "ended_at": _utcnow_iso(),
                "elapsed_s": round(time.monotonic() - t0, 1),
                "images_dir": str(images_dir),
                "pages_in": len(pages),
                "stitched_pdf_bytes_total": total_bytes,
                "n_chunks": len(chunks),
                "raw_extract_chars": len(md),
                "translated_chars": translated_chars,
                "src_lang": args.src_lang,
                "translate_skipped": args.no_translate,
                "docintel_api_version": "2023-07-31",
                "docintel_model": "prebuilt-read",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    elapsed = time.monotonic() - t0
    print(f"\n  done in {elapsed:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
