#!/usr/bin/env python3
"""Slice the Asas al-Taweel transcripts into per-volume files.

Book-specific script for Islamic/asaas-al-taveel only.
Do NOT merge to develop -- line ranges are hardcoded for this title.

Usage:
    python3 scripts/podcast/split_transcript_asaas.py --vol N

Reads:
  content/Islamic/asaas-al-taveel/english-transcript.md
  content/Islamic/asaas-al-taveel/_system/source/text/refined-english.md

Writes:
  content/Islamic/asaas-al-taveel-vol-N/english-transcript.md
  content/Islamic/asaas-al-taveel-vol-N/_system/source/text/raw-extract.md
  content/Islamic/asaas-al-taveel-vol-N/_system/source/text/refined-english.md

All three output files receive the same normalized text (sanitize_text()).
refined-english.md is required by Phase 0c as the Phase 0b prerequisite.
The line boundaries for refined-english.md differ from english-transcript.md
by a small offset (page markers sit at different lines in the two files).
"""

import argparse
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_FULL_BOOK = REPO_ROOT / "content" / "Islamic" / "asaas-al-taveel"
SOURCE = _FULL_BOOK / "english-transcript.md"
REFINED_SOURCE = _FULL_BOOK / "_system" / "source" / "text" / "refined-english.md"

# 1-indexed line ranges for english-transcript.md, inclusive on both ends.
# Boundaries are at the <!-- page N --> markers verified 2026-06-08.
VOLUMES = {
    1: {"lines": (1, 1013), "refined_lines": (1, 1022), "prophet": "Adam", "page_range": "1-75"},
    2: {"lines": (1014, 1633), "refined_lines": (1023, 1642), "prophet": "Noah", "page_range": "76-106"},
    3: {"lines": (1634, 3424), "refined_lines": (1643, 3433), "prophet": "Abraham", "page_range": "107-178"},
    4: {"lines": (3425, 6623), "refined_lines": (3434, 6632), "prophet": "Moses", "page_range": "179-298"},
    5: {"lines": (6624, 7031), "refined_lines": (6633, 7040), "prophet": "Jesus", "page_range": "299-314"},
    6: {"lines": (7032, 8133), "refined_lines": (7041, 8142), "prophet": "Muhammad and Qaim", "page_range": "315-368"},
}


def _slice_and_normalize(source: pathlib.Path, start: int, end: int, sanitize_text) -> tuple[str, int]:
    all_lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    total = len(all_lines)
    if end > total:
        print(f"  WARNING: end line {end} > total {total}; clamping", file=sys.stderr)
        end = total
    text = "".join(all_lines[start - 1 : end])
    normalized, report = sanitize_text(text)
    return normalized, report.total_changes


def split(vol: int) -> None:
    if vol not in VOLUMES:
        print(f"ERROR: --vol must be 1-6, got {vol}", file=sys.stderr)
        sys.exit(1)

    for src in (SOURCE, REFINED_SOURCE):
        if not src.exists():
            print(f"ERROR: source not found: {src}", file=sys.stderr)
            sys.exit(1)

    sys.path.insert(0, str(REPO_ROOT / "scripts" / "podcast"))
    from _tts_sanitize import sanitize_text

    info = VOLUMES[vol]
    vol_dir = REPO_ROOT / "content" / "Islamic" / f"asaas-al-taveel-vol-{vol}"
    system_text_dir = vol_dir / "_system" / "source" / "text"

    # english-transcript.md + raw-extract.md from english-transcript.md
    start, end = info["lines"]
    norm_transcript, n1 = _slice_and_normalize(SOURCE, start, end, sanitize_text)
    for out_path in [vol_dir / "english-transcript.md", system_text_dir / "raw-extract.md"]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(norm_transcript, encoding="utf-8")
        print(f"  -> {out_path.relative_to(REPO_ROOT)}")

    # refined-english.md from the Phase-0b output (different line offsets)
    rstart, rend = info["refined_lines"]
    norm_refined, n2 = _slice_and_normalize(REFINED_SOURCE, rstart, rend, sanitize_text)
    refined_out = system_text_dir / "refined-english.md"
    refined_out.parent.mkdir(parents=True, exist_ok=True)
    refined_out.write_text(norm_refined, encoding="utf-8")
    print(f"  -> {refined_out.relative_to(REPO_ROOT)}")

    n_lines = end - start + 1
    print(f"Vol {vol} ({info['prophet']}, pp {info['page_range']}): {n_lines} lines, {n1 + n2} normalizations applied")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vol", type=int, required=True, help="Volume number 1-6")
    args = parser.parse_args()
    split(args.vol)


if __name__ == "__main__":
    main()
