#!/usr/bin/env python3
"""Batch slide convergence runner for asaas-al-taveel vol-01."""
import sys

from _paths import resolve_content

BOOK_DIR = resolve_content("asaas-al-taveel-vol-01")
SLUGS = [
    "what-ismaili-interpretation-is",
    "the-call-to-inner-meaning",
    "the-four-limits-of-the-shahada",
    "adam-the-tree-and-iblis-pact",
    "two-parties-and-the-line-to-noah",
]

from _slide_convergence import run_slide_convergence

for slug in SLUGS:
    print(f"\n=== {slug} ===", flush=True)
    try:
        result = run_slide_convergence(BOOK_DIR, slug)
        print(f"  verdict={result.verdict} iterations={result.iterations}", flush=True)
        if result.output_paths:
            for p in result.output_paths:
                print(f"  -> {p}", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)

print("\nDone.", flush=True)
