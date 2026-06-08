#!/usr/bin/env python3
"""Slice the Asas al-Taweel english-transcript.md into per-volume files.

Book-specific script for Islamic/asaas-al-taveel only.
Do NOT merge to develop -- line ranges are hardcoded for this title.

Usage:
    python3 scripts/podcast/split_transcript_asaas.py --vol N

Reads:  content/Islamic/asaas-al-taveel/english-transcript.md
Writes: content/Islamic/asaas-al-taveel-vol-N/english-transcript.md
        content/Islamic/asaas-al-taveel-vol-N/_system/source/text/raw-extract.md

The slice is run through sanitize_text() (typographic + diacritic normalization)
before writing. Both output files receive the same normalized text.
"""

import argparse
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "content" / "Islamic" / "asaas-al-taveel" / "english-transcript.md"

# 1-indexed line ranges, inclusive on both ends.
# Boundaries are at the <!-- page N --> markers for each prophetic section.
VOLUMES = {
    1: {"lines": (1, 1013),    "prophet": "Adam",              "page_range": "1-75"},
    2: {"lines": (1014, 1633), "prophet": "Noah",              "page_range": "76-106"},
    3: {"lines": (1634, 3424), "prophet": "Abraham",           "page_range": "107-178"},
    4: {"lines": (3425, 6623), "prophet": "Moses",             "page_range": "179-298"},
    5: {"lines": (6624, 7031), "prophet": "Jesus",             "page_range": "299-314"},
    6: {"lines": (7032, 8133), "prophet": "Muhammad and Qaim", "page_range": "315-368"},
}


def split(vol: int) -> None:
    if vol not in VOLUMES:
        print(f"ERROR: --vol must be 1-6, got {vol}", file=sys.stderr)
        sys.exit(1)

    if not SOURCE.exists():
        print(f"ERROR: source transcript not found: {SOURCE}", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, str(REPO_ROOT / "scripts" / "podcast"))
    from _tts_sanitize import sanitize_text  # noqa: PLC0415

    info = VOLUMES[vol]
    start, end = info["lines"]

    all_lines = SOURCE.read_text(encoding="utf-8").splitlines(keepends=True)
    total = len(all_lines)
    if end > total:
        print(
            f"WARNING: end line {end} > total lines {total}; clamping to {total}",
            file=sys.stderr,
        )
        end = total

    slice_text = "".join(all_lines[start - 1 : end])
    normalized, report = sanitize_text(slice_text)

    vol_dir = REPO_ROOT / "content" / "Islamic" / f"asaas-al-taveel-vol-{vol}"
    system_text_dir = vol_dir / "_system" / "source" / "text"

    for out_path in [
        vol_dir / "english-transcript.md",
        system_text_dir / "raw-extract.md",
    ]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(normalized, encoding="utf-8")
        print(f"  -> {out_path.relative_to(REPO_ROOT)}")

    n_lines = end - start + 1
    print(
        f"Vol {vol} ({info['prophet']}, pp {info['page_range']}): "
        f"{n_lines} lines, {report.total_changes} normalizations applied"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vol", type=int, required=True, help="Volume number 1-6")
    args = parser.parse_args()
    split(args.vol)


if __name__ == "__main__":
    main()
