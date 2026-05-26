#!/usr/bin/env python3
"""pack_bundle_for_gemini.py — flatten a podcast bundle into one Gemini-friendly markdown file.

Gemini Gems impose hard limits on uploaded zip files: max 10 files inside,
100 MB total, and no audio/video. A typical podcast bundle directory has well
over ten text-like artifacts (chapter prose, episode source, framing,
chapter-contract, transcripts, slide-deck plans, etc.), so a raw zip is
rejected on intake. This script consolidates a bundle into a single .md file
with deterministic file delimiters so the bundle-auditor Gem (and any other
single-context LLM auditor) can still emit JSON findings keyed to the original
file paths.

USAGE

    python3 scripts/podcast/pack_bundle_for_gemini.py <bundle_dir>
        [--out <path>] [--include-pdfs] [--max-mb 90]

The output is a single .md file. Each source file in the bundle becomes a
fenced block:

    <!-- FILE: <relative-path> START -->
    ```<lang>
    <file contents>
    ```
    <!-- FILE: <relative-path> END -->

`<lang>` is inferred from the suffix (md, txt, yaml, json, csv, python, …).
Anchors in downstream JSON findings should use the same `<relative-path>` so
Claude Code can map fixes back to the real files.

EXCLUSIONS (always)
  - audio / video: .m4a, .mp3, .wav, .mp4, .mov, .ogg, .flac
  - binary docs:  .pdf (unless --include-pdfs, in which case the file's
                  bytes are NOT embedded — only a stub noting the path)
  - images:       .png, .jpg, .jpeg, .gif, .webp, .svg
  - archives:     .zip, .tar, .gz, .bz2
  - bytecode:     .pyc, .pyo
  - dirs:         .git, __pycache__, node_modules, .DS_Store

SIZE BUDGET
  --max-mb caps the consolidated output at the given megabyte size. Default 90
  (Gemini's hard ceiling is 100 MB, leaving headroom for Gem framing). If the
  walk would exceed the cap, the largest files are dropped LAST and the script
  exits with a non-zero status, surfacing what was skipped.

EXIT CODES
  0 = consolidated file written successfully
  1 = bundle path invalid / unreadable
  2 = size cap exceeded; partial output written + dropped-file list printed

The packer is intentionally bundle-shape-agnostic. It does not require the
six-artifact canonical shape (framing, primary source, key passages, context
pack, discussion spine, show notes) — auditing the bundle's completeness is
the Gem's job, not the packer's.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# File-extension policy.
TEXT_LANG_BY_SUFFIX = {
    ".md": "markdown",
    ".txt": "text",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".csv": "csv",
    ".tsv": "tsv",
    ".py": "python",
    ".sh": "bash",
    ".html": "html",
    ".xml": "xml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".rst": "rst",
}

EXCLUDED_SUFFIXES = {
    ".m4a", ".mp3", ".wav", ".mp4", ".mov", ".ogg", ".flac", ".aac",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".zip", ".tar", ".gz", ".bz2", ".7z",
    ".pyc", ".pyo",
    ".DS_Store",
}

EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


def _is_excluded(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if path.name == ".DS_Store":
        return True
    return False


def _lang_for(path: Path) -> str:
    return TEXT_LANG_BY_SUFFIX.get(path.suffix.lower(), "")


def _walk_bundle(bundle_root: Path, include_pdfs: bool) -> list[Path]:
    files: list[Path] = []
    for p in sorted(bundle_root.rglob("*")):
        if not p.is_file():
            continue
        if _is_excluded(p):
            continue
        if p.suffix.lower() == ".pdf":
            if include_pdfs:
                files.append(p)  # included as a stub, not bytes
            continue
        files.append(p)
    return files


def _read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fall back to latin-1 so legacy transcripts that lost their BOM still pack.
        return path.read_text(encoding="latin-1", errors="replace")


def _format_block(rel_path: str, content: str, lang: str) -> str:
    fence_lang = lang if lang else ""
    return (
        f"<!-- FILE: {rel_path} START -->\n"
        f"```{fence_lang}\n"
        f"{content.rstrip()}\n"
        f"```\n"
        f"<!-- FILE: {rel_path} END -->\n"
    )


def _format_pdf_stub(rel_path: str, size_bytes: int) -> str:
    return (
        f"<!-- FILE: {rel_path} START -->\n"
        f"_(PDF file, {size_bytes:,} bytes — contents not embedded. "
        f"If auditing requires the prose, extract via `scripts/podcast/ingest_source.py` "
        f"and re-pack.)_\n"
        f"<!-- FILE: {rel_path} END -->\n"
    )


def _format_header(bundle_root: Path, files: list[Path], dropped: list[Path]) -> str:
    manifest_lines = [f"- `{p.relative_to(bundle_root)}` ({p.stat().st_size:,} bytes)" for p in files]
    manifest = "\n".join(manifest_lines)
    dropped_section = ""
    if dropped:
        dropped_lines = [f"- `{p.relative_to(bundle_root)}` ({p.stat().st_size:,} bytes)" for p in dropped]
        dropped_section = (
            "\n## Files dropped to fit the size budget\n\n"
            f"The following files were not included because the consolidated output "
            f"would have exceeded the size cap. Re-run with a larger `--max-mb` if you "
            f"need them:\n\n" + "\n".join(dropped_lines) + "\n"
        )
    return (
        f"# Podcast bundle (consolidated for Gemini)\n\n"
        f"**Source bundle:** `{bundle_root}`  \n"
        f"**Files included:** {len(files)}  \n"
        f"**Files dropped:** {len(dropped)}\n\n"
        f"This file is a flattened view of the bundle directory tree above. Every\n"
        f"original file appears as a fenced block delimited by HTML comments marking\n"
        f"the start and end of each file, with the original relative path embedded in\n"
        f"the marker. The auditor MUST use that path as the `file` field in any JSON\n"
        f"finding it emits, so the downstream Claude Code fix list can map back to\n"
        f"real files. See `prompts/gemini-bundle-auditor.md` for the exact marker\n"
        f"syntax (the marker text is intentionally not shown here so downstream\n"
        f"parsers cannot mistake the description for a real entry).\n\n"
        f"## Manifest\n\n{manifest}\n"
        f"{dropped_section}\n---\n\n"
    )


def pack(bundle_dir: Path, out_path: Path, include_pdfs: bool, max_mb: int) -> int:
    if not bundle_dir.exists() or not bundle_dir.is_dir():
        print(f"error: bundle directory not found: {bundle_dir}", file=sys.stderr)
        return 1

    max_bytes = max_mb * 1024 * 1024
    candidates = _walk_bundle(bundle_dir, include_pdfs=include_pdfs)

    blocks: list[str] = []
    included: list[Path] = []
    dropped: list[Path] = []
    running_bytes = 0
    # Reserve ~64KB of headroom for the header (rendered last but counted first).
    header_reserve = 65536

    for p in candidates:
        rel = p.relative_to(bundle_dir).as_posix()
        if p.suffix.lower() == ".pdf":
            block = _format_pdf_stub(rel, p.stat().st_size)
        else:
            content = _read_text_safely(p)
            block = _format_block(rel, content, _lang_for(p))
        block_bytes = len(block.encode("utf-8"))
        if running_bytes + block_bytes + header_reserve > max_bytes:
            dropped.append(p)
            continue
        blocks.append(block)
        included.append(p)
        running_bytes += block_bytes

    header = _format_header(bundle_dir, included, dropped)
    out_path.write_text(header + "\n".join(blocks), encoding="utf-8")

    total_bytes = out_path.stat().st_size
    total_mb = total_bytes / (1024 * 1024)
    # Rough token estimate: ~4 chars/token for English+code.
    token_estimate = total_bytes // 4

    print(f"wrote {out_path}")
    print(f"  files included: {len(included)}")
    print(f"  files dropped:  {len(dropped)}")
    print(f"  total size:     {total_bytes:,} bytes ({total_mb:.2f} MB)")
    print(f"  token estimate: ~{token_estimate:,}")
    if dropped:
        print("  WARNING: some files were dropped to fit --max-mb; see the header section.")
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Flatten a podcast bundle directory into one Gemini-friendly markdown file.",
    )
    parser.add_argument("bundle_dir", type=Path, help="Path to the bundle directory.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output file path. Defaults to <bundle_dir>.packed.md next to the bundle.",
    )
    parser.add_argument(
        "--include-pdfs",
        action="store_true",
        help="Include PDF files as stub entries (path-only, no bytes). Default: skip.",
    )
    parser.add_argument(
        "--max-mb",
        type=int,
        default=90,
        help="Hard cap on output size in megabytes. Default 90 (Gemini limit is 100).",
    )
    args = parser.parse_args()

    bundle_dir = args.bundle_dir.resolve()
    if args.out is None:
        out_path = bundle_dir.parent / f"{bundle_dir.name}.packed.md"
    else:
        out_path = args.out.resolve()

    return pack(bundle_dir=bundle_dir, out_path=out_path, include_pdfs=args.include_pdfs, max_mb=args.max_mb)


if __name__ == "__main__":
    sys.exit(main())
