#!/usr/bin/env python3
"""Split the Asas al-Taweel source PDF into prophet volumes.

Book-specific script for Islamic/asaas-al-taveel only.
Do NOT merge to develop -- page ranges are hardcoded for this title.
(Flagged 2026-07-16: this file is currently present on develop despite that
note — pre-existing, not touched by this review; Asif chose to flag rather
than delete it, so left as-is.)

Usage:
    python3 scripts/podcast/split_pdf_asaas.py --vol N

Outputs ~/Documents/BOOKS/asaas-al-taveel-vol-N.pdf
"""

import argparse
import pathlib
import sys

SOURCE = pathlib.Path.home() / "Documents" / "BOOKS" / "Asaas Al-Taveel.pdf"

# 0-indexed page slices [start, end) matching the physical PDF pages 1-368.
# Back matter (pages 369-416) excluded from all volumes.
VOLUMES = {
    1: {"pages": (0, 75),   "prophet": "Adam",               "page_range": "1-75"},
    2: {"pages": (75, 106),  "prophet": "Noah",               "page_range": "76-106"},
    3: {"pages": (106, 178), "prophet": "Abraham",            "page_range": "107-178"},
    4: {"pages": (178, 298), "prophet": "Moses",              "page_range": "179-298"},
    5: {"pages": (298, 314), "prophet": "Jesus",              "page_range": "299-314"},
    6: {"pages": (314, 368), "prophet": "Muhammad and Qaim",  "page_range": "315-368"},
}


def split(vol: int) -> None:
    if vol not in VOLUMES:
        print(f"ERROR: --vol must be 1-6, got {vol}", file=sys.stderr)
        sys.exit(1)

    if not SOURCE.exists():
        print(f"ERROR: source PDF not found: {SOURCE}", file=sys.stderr)
        sys.exit(1)

    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("ERROR: pypdf not installed. Run: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    info = VOLUMES[vol]
    start, end = info["pages"]
    out_path = SOURCE.parent / f"asaas-al-taveel-vol-{vol}.pdf"

    reader = PdfReader(SOURCE)
    writer = PdfWriter()
    for i in range(start, end):
        writer.add_page(reader.pages[i])

    with open(out_path, "wb") as fh:
        writer.write(fh)

    n_pages = end - start
    print(
        f"Vol {vol} ({info['prophet']}, pp {info['page_range']}): "
        f"{n_pages} pages -> {out_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vol", type=int, required=True, help="Volume number 1-6")
    args = parser.parse_args()
    split(args.vol)


if __name__ == "__main__":
    main()
