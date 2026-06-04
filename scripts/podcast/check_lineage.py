#!/usr/bin/env python3
"""check_lineage.py — staleness check for split-derivative chapter contracts.

Some chapters are SPLIT derivatives of a larger source chapter (Splitting
Policy is documented inline in `scripts/podcast/extract_chapter.py` —
formerly `content/podcast/.skill/handbook/extract-capability.md`, retired
2026-05-23). Each derivative's contract carries a `derived_from:` field
with a repo-relative path to the original source file. If that source is
later edited, the derivative becomes stale — its content reflects an
older version of the source.

This script compares the modification time of each `derived_from:` source
against the corresponding derivative chapter and flags any pair where the
source is newer.

Usage:
    python3 scripts/podcast/check_lineage.py
    python3 scripts/podcast/check_lineage.py --root <library-dir>

Exit codes:
    0 — every derivative is fresh (or there are no derivatives at all)
    1 — at least one derivative is stale, or a `derived_from:` path is broken

This script is read-only. The podcast-challenger agent invokes it as part of
Category G6 (derived-source staleness check).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from _paths import REPO_ROOT

DEFAULT_LIBRARY = REPO_ROOT / "content" / "drafts"

DERIVED_FROM_RE = re.compile(r"^derived_from:\s*(.+?)\s*$", re.MULTILINE)


def find_contracts(library_dir: Path) -> list[Path]:
    """Find every chapter-contracts/*.yml under library/<category>/<book>/."""
    out: list[Path] = []
    if not library_dir.exists():
        return out
    for category in sorted(library_dir.iterdir()):
        if not category.is_dir():
            continue
        for book in sorted(category.iterdir()):
            cdir = book / "chapter-contracts"
            if cdir.is_dir():
                out.extend(sorted(cdir.glob("*.yml")))
    return out


def parse_derived_from(contract_path: Path) -> str | None:
    """Extract the `derived_from:` value from a contract YAML.
    Returns None for null/missing values."""
    text = contract_path.read_text(encoding="utf-8")
    m = DERIVED_FROM_RE.search(text)
    if not m:
        return None
    val = m.group(1).strip()
    # Strip inline comments
    if "#" in val:
        val = val.split("#", 1)[0].strip()
    if val in ("null", "~", ""):
        return None
    # Strip surrounding quotes if present
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val


def find_chapter_for_contract(contract_path: Path) -> Path | None:
    """contract at <book>/chapter-contracts/<slug>.yml → chapter at
    <book>/chapters/ch??-<slug>.txt. Returns None if not found."""
    slug = contract_path.stem
    book_dir = contract_path.parent.parent
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.is_dir():
        return None
    for cand in chapters_dir.glob(f"ch*-{slug}.txt"):
        return cand
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--root", type=Path, default=None,
        help="Library root. Default: _workspace/",
    )
    args = ap.parse_args()
    library_dir = args.root or DEFAULT_LIBRARY
    contracts = find_contracts(library_dir)

    if not contracts:
        print(f"check_lineage: no contracts found under {library_dir} — nothing to check.")
        return 0

    derivatives = 0
    findings: list[str] = []
    for contract in contracts:
        df = parse_derived_from(contract)
        if df is None:
            continue
        derivatives += 1
        source = (REPO_ROOT / df).resolve()
        if not source.exists():
            findings.append(
                f"BROKEN_LINEAGE: contract {contract.relative_to(REPO_ROOT)}\n"
                f"    derived_from: {df}\n"
                f"    resolved to: {source}\n"
                f"    that path does not exist."
            )
            continue
        chapter = find_chapter_for_contract(contract)
        if chapter is None:
            findings.append(
                f"NO_CHAPTER: contract {contract.relative_to(REPO_ROOT)} has derived_from\n"
                f"    but its sibling chapter file is missing under "
                f"{contract.parent.parent / 'chapters'}."
            )
            continue
        source_mtime = source.stat().st_mtime
        chapter_mtime = chapter.stat().st_mtime
        if source_mtime > chapter_mtime:
            findings.append(
                f"STALE: {chapter.relative_to(REPO_ROOT)}\n"
                f"    derived_from {df}\n"
                f"    source is newer (mtime {source_mtime:.0f} > derivative mtime {chapter_mtime:.0f}).\n"
                f"    Either re-split from the new source, or accept the drift and re-touch\n"
                f"    the derivative to dismiss this warning."
            )

    if findings:
        print(f"check_lineage: {len(findings)} finding(s) across {derivatives} derivative(s)", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        return 1

    print(f"check_lineage: OK — {derivatives} derivative(s) checked, all fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
