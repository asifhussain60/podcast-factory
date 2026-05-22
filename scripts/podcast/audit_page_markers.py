#!/usr/bin/env python3
"""audit_page_markers.py — Audit `<!-- page N -->` marker preservation across Phase 0b.

Acceptance row: P22.markers.audit-tool (acceptance-criteria.md §P22.markers).

Compares page-marker sets between Phase 0a output (`raw-extract.md`) and Phase 0b
output (`refined-english.md`). Exits 0 when the sets match 1:1; exits non-zero
with a per-window breakdown table when they don't — surfacing exactly which
chunked refinement windows stripped, hallucinated, or duplicated markers.

Designed for two use cases:

1.  Operator-facing audit after a Phase 0b run:
        python3 scripts/podcast/audit_page_markers.py --book asaas-al-taveel

    Exits 0 if Phase 0b preserved every page marker; non-zero with a remediation
    table if it didn't. The remediation table maps each defective window to its
    input page range so the operator knows exactly which windows to re-run.

2.  Pre-flight check before downstream phases (0c phonetic, 0d segmentation,
    0e enrichment) that depend on page-marker anchoring. Wire into orchestrator
    Phase 0c entry-point: refuse to advance if Phase 0b output is mis-anchored.

Origin: asaas-al-taveel Phase 0b post-mortem 2026-05-20. 58 of 416 page anchors
stripped across 7 of 49 chunked refinement windows. Body content preserved;
metadata loss only. Without this audit tool, the defect would have only been
discoverable post-hoc by manual sampling.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PAGE_MARKER_RE = re.compile(r"<!-- page (\d+) -->")


@dataclass(frozen=True)
class WindowAudit:
    """One row of the per-window audit table."""

    name: str             # e.g. "win-003"
    in_pages: list[int]   # page numbers found in win-NNN.in.md
    out_pages: list[int]  # page numbers found in win-NNN.out.md
    delta: int            # len(in_pages) - len(out_pages); positive = pages lost

    @property
    def is_clean(self) -> bool:
        return self.in_pages == self.out_pages

    @property
    def lost_pages(self) -> list[int]:
        out_set = set(self.out_pages)
        return [p for p in self.in_pages if p not in out_set]

    @property
    def hallucinated_pages(self) -> list[int]:
        in_set = set(self.in_pages)
        return [p for p in self.out_pages if p not in in_set]


def extract_page_markers(text: str) -> list[int]:
    """Return the ordered list of page numbers from `<!-- page N -->` markers."""
    return [int(m.group(1)) for m in PAGE_MARKER_RE.finditer(text)]


def audit_top_level(
    raw_extract: Path,
    refined_english: Path,
) -> tuple[list[int], list[int], list[int], list[int]]:
    """Compare top-level raw vs refined page-marker sets.

    Returns (raw_markers, refined_markers, lost, hallucinated).
    """
    raw_text = raw_extract.read_text(encoding="utf-8")
    refined_text = refined_english.read_text(encoding="utf-8")
    raw_markers = extract_page_markers(raw_text)
    refined_markers = extract_page_markers(refined_text)
    raw_set = set(raw_markers)
    refined_set = set(refined_markers)
    lost = sorted(raw_set - refined_set)
    hallucinated = sorted(refined_set - raw_set)
    return raw_markers, refined_markers, lost, hallucinated


def audit_windows(chunks_dir: Path) -> list[WindowAudit]:
    """Audit each `_chunks/0b/win-NNN.{in,out}.md` pair."""
    audits: list[WindowAudit] = []
    if not chunks_dir.exists():
        return audits
    in_files = sorted(chunks_dir.glob("win-*.in.md"))
    for in_path in in_files:
        name = in_path.name.removesuffix(".in.md")
        out_path = chunks_dir / f"{name}.out.md"
        in_pages = extract_page_markers(in_path.read_text(encoding="utf-8"))
        if out_path.exists():
            out_pages = extract_page_markers(out_path.read_text(encoding="utf-8"))
        else:
            out_pages = []
        audits.append(
            WindowAudit(
                name=name,
                in_pages=in_pages,
                out_pages=out_pages,
                delta=len(in_pages) - len(out_pages),
            )
        )
    return audits


def render_top_level(
    raw_markers: list[int],
    refined_markers: list[int],
    lost: list[int],
    hallucinated: list[int],
) -> str:
    """Human-readable top-level audit."""
    raw_count = len(raw_markers)
    refined_count = len(refined_markers)
    lines = [
        "Top-level page-marker audit",
        "===========================",
        f"  raw-extract.md     : {raw_count} markers ({_summarize_range(raw_markers)})",
        f"  refined-english.md : {refined_count} markers ({_summarize_range(refined_markers)})",
        f"  net delta          : {raw_count - refined_count:+d}",
        "",
    ]
    if lost:
        lines.append(f"LOST  ({len(lost)} pages absent from refined): {_summarize_ranges(lost)}")
    if hallucinated:
        lines.append(
            f"HALLUCINATED  ({len(hallucinated)} pages in refined but not in raw): "
            f"{_summarize_ranges(hallucinated)}"
        )
    if not lost and not hallucinated:
        lines.append("✓ All page markers preserved.")
    return "\n".join(lines)


def render_window_audit(audits: list[WindowAudit]) -> str:
    """Per-window breakdown — only shows windows with non-clean output."""
    defective = [a for a in audits if not a.is_clean]
    if not defective:
        return "Per-window audit: all windows clean.\n"
    lines = [
        "",
        "Per-window audit (defective windows only)",
        "=========================================",
        f"{'window':<10} {'in':>4} {'out':>4} {'delta':>6}  {'pages affected'}",
        f"{'-' * 10} {'-' * 4:>4} {'-' * 4:>4} {'-' * 6:>6}  {'-' * 30}",
    ]
    for a in defective:
        affected_parts: list[str] = []
        if a.lost_pages:
            affected_parts.append(f"lost {_summarize_ranges(a.lost_pages)}")
        if a.hallucinated_pages:
            affected_parts.append(f"halluc {_summarize_ranges(a.hallucinated_pages)}")
        affected = "; ".join(affected_parts) or "(reordered)"
        lines.append(
            f"{a.name:<10} {len(a.in_pages):>4d} {len(a.out_pages):>4d} {a.delta:>+6d}  {affected}"
        )
    lines.append("")
    lines.append(f"Defective windows: {len(defective)} / {len(audits)}")
    return "\n".join(lines)


def _summarize_range(pages: Iterable[int]) -> str:
    pages = list(pages)
    if not pages:
        return "empty"
    return f"{min(pages)}–{max(pages)}"


def _summarize_ranges(pages: Iterable[int]) -> str:
    """Compress a sorted page list to range notation: [1,2,3,7,8] → '1-3, 7-8'."""
    pages = sorted(set(pages))
    if not pages:
        return ""
    parts: list[str] = []
    start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
            continue
        parts.append(f"{start}" if start == prev else f"{start}-{prev}")
        start = prev = p
    parts.append(f"{start}" if start == prev else f"{start}-{prev}")
    return ", ".join(parts)


def _resolve_book_dir(book_slug: str, category: str) -> Path:
    """Find the book directory anchored at the repo root."""
    here = Path(__file__).resolve()
    repo_root = here.parents[2]  # scripts/podcast/audit_page_markers.py → repo
    book_dir = repo_root / "_workspace" / category / book_slug
    if not book_dir.exists():
        raise SystemExit(f"book directory not found: {book_dir}")
    return book_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Phase 0b page-marker preservation. Exits 0 if every "
            "<!-- page N --> marker in raw-extract.md is present in "
            "refined-english.md (and no hallucinated markers); exits non-zero "
            "with a per-window breakdown on mismatch."
        ),
        epilog=(
            "Example: python3 scripts/podcast/audit_page_markers.py "
            "--book asaas-al-taveel"
        ),
    )
    parser.add_argument("--book", required=True, help="book slug (e.g. asaas-al-taveel)")
    parser.add_argument(
        "--category",
        default="books",
        choices=["books", "articles", "documents", "lectures", "interviews", "letters"],
        help="library subdirectory (default: books)",
    )
    parser.add_argument(
        "--skip-window-audit",
        action="store_true",
        help="skip per-window breakdown (only check top-level raw vs refined)",
    )
    args = parser.parse_args(argv)

    book_dir = _resolve_book_dir(args.book, args.category)
    text_dir = book_dir / "_system" / "source" / "text"
    raw_extract = text_dir / "raw-extract.md"
    refined_english = text_dir / "refined-english.md"

    if not raw_extract.exists():
        print(f"ERROR: {raw_extract} not found (Phase 0a not complete?)", file=sys.stderr)
        return 2
    if not refined_english.exists():
        print(f"ERROR: {refined_english} not found (Phase 0b not complete?)", file=sys.stderr)
        return 2

    raw_markers, refined_markers, lost, hallucinated = audit_top_level(
        raw_extract, refined_english
    )

    # Also check that within-refined, no marker is repeated (would indicate a
    # cross-window stitching duplication).
    refined_counter = Counter(refined_markers)
    repeated = sorted(p for p, n in refined_counter.items() if n > 1)

    print(render_top_level(raw_markers, refined_markers, lost, hallucinated))
    if repeated:
        print(
            f"\nREPEATED  ({len(repeated)} pages appear >1 time in refined): "
            f"{_summarize_ranges(repeated)}"
        )

    if not args.skip_window_audit:
        chunks_dir = text_dir / "_chunks" / "0b"
        window_audits = audit_windows(chunks_dir)
        if window_audits:
            print(render_window_audit(window_audits))

    clean = not lost and not hallucinated and not repeated
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
