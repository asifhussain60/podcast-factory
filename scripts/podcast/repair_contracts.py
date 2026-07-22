#!/usr/bin/env python3
"""repair_contracts.py — deterministically conform chapter contracts to the gate schema.

The Phase-0d contract gate (_contract_validation.py) refuses contracts whose
LLM-written fields drifted from the schema: a prose `angle` instead of a
VALID_ANGLES enum, an invented `source_type`, a `chapter_ref` that holds the
source-chapter number instead of the chapter file stem, or an over-long title.

The chapter *content* is fine when this fires — only the per-chapter `.yml`
metadata is malformed — so this repair fixes ONLY those fields in place,
deterministically (no LLM), validating against the validator's own enums so it
can never drift from the gate. Idempotent: a conforming contract is untouched.

Reusable so the heartbeat / watchdog can auto-repair on a contract-gate failure:
    python3 scripts/podcast/repair_contracts.py <slug> [--dry-run]
Exit 0 = all contracts now conform (or already did); 2 = book/contracts missing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import yaml
from _contract_validation import VALID_ANGLES, VALID_SOURCE_TYPES
from _paths import find_content


class _IndentDumper(yaml.SafeDumper):
    """Indent block sequences UNDER their key (`key:\\n  - item`), which the
    pipeline's minimal loader (_extract_yaml.load_yaml) requires — pyyaml's
    default dedents them (`key:\\n- item`) and the loader can't parse that."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def _dump_contract(data: dict) -> str:
    # width huge so long one-line prose fields never wrap (the loader reads only
    # single-line quoted scalars; a wrapped value would break parsing).
    return yaml.dump(
        data,
        Dumper=_IndentDumper,
        sort_keys=False,
        allow_unicode=True,
        width=1_000_000,
        default_flow_style=False,
    )


# Defaults chosen for faithful Islamic-scholarly exposition (the Kunooz/KaR family):
# deep-dive teaching, audio-lecture source. Both are members of the validator enums.
DEFAULT_ANGLE = "faithful_exposition"
DEFAULT_SOURCE_TYPE = "lecture"
TITLE_MAX = 60
TITLE_MINOR = {"and", "the", "of", "a", "an", "in", "on", "to", "for", "at", "by", "or"}


def _humanize_slug(slug: str) -> str:
    """`the-cycle-and-the-practical-frame` -> `The Cycle and the Practical Frame`."""
    words = [w for w in slug.split("-") if w]
    out = []
    for i, w in enumerate(words):
        out.append(w if (i > 0 and w in TITLE_MINOR) else w[:1].upper() + w[1:])
    title = " ".join(out)
    return title[:TITLE_MAX].rstrip()


def _chapter_stem_for(book_dir: Path, contract_slug: str) -> str | None:
    """Find chapters/ch<NN>[x]-<slug>.txt (or <slug>.txt) and return its stem."""
    chdir = book_dir / "chapters"
    if not chdir.is_dir():
        return None
    for p in sorted(chdir.glob("*.txt")):
        stem = p.stem
        if stem == contract_slug or stem.split("-", 1)[-1] == contract_slug or stem.endswith(f"-{contract_slug}"):
            return stem
    return None


def repair_contracts(slug: str, *, dry_run: bool = False) -> int:
    hit = find_content(slug)
    if not hit:
        print(f"repair_contracts: book {slug!r} not found", file=sys.stderr)
        return 2
    return repair_contracts_in_dir(Path(hit[2]), dry_run=dry_run)


def repair_contracts_in_dir(book_dir: Path, *, dry_run: bool = False, log=print) -> int:
    """Conform every chapter-contracts/*.yml under book_dir to the gate schema.
    Book-dir entry so the Phase-0d gate can auto-repair before validating."""
    book_dir = Path(book_dir)
    cdir = book_dir / "chapter-contracts"
    contracts = sorted(cdir.glob("*.yml")) if cdir.is_dir() else []
    if not contracts:
        log(f"  repair_contracts: no contracts under {cdir} — nothing to repair")
        return 0

    total_changed = 0
    for y in contracts:
        data = yaml.safe_load(y.read_text(encoding="utf-8")) or {}
        changes: list[str] = []

        # 1. chapter_ref must equal the chapter file stem (source number lives in
        #    source_chapter_ref, which we leave alone).
        stem = _chapter_stem_for(book_dir, y.stem)
        if stem and str(data.get("chapter_ref") or "").strip() != stem:
            if "source_chapter_ref" not in data and str(data.get("chapter_ref") or "").isdigit():
                data["source_chapter_ref"] = data.get("chapter_ref")
            data["chapter_ref"] = stem
            changes.append(f"chapter_ref -> {stem}")

        # 2. angle must be a VALID_ANGLES enum; preserve the prose as angle_note.
        angle = str(data.get("angle") or "").strip()
        if angle not in VALID_ANGLES:
            if angle and len(angle) > 3:
                data["angle_note"] = angle  # keep the editorial description
            data["angle"] = DEFAULT_ANGLE
            changes.append(f"angle -> {DEFAULT_ANGLE}")

        # 3. source_type must be a VALID_SOURCE_TYPES enum.
        if str(data.get("source_type") or "").strip() not in VALID_SOURCE_TYPES:
            data["source_type"] = DEFAULT_SOURCE_TYPE
            changes.append(f"source_type -> {DEFAULT_SOURCE_TYPE}")

        # 4. title must be <= 60 chars (INVARIANT 6); derive a concise one from the slug.
        title = str(data.get("title") or "").strip()
        if not title or len(title) > TITLE_MAX:
            new_title = _humanize_slug(y.stem)
            data["title"] = new_title
            changes.append(f"title -> {new_title!r}")

        if changes:
            total_changed += 1
            log(f"  {y.name}: {'; '.join(changes)}")
        # Always re-emit through the loader-compatible dumper so the on-disk format
        # is guaranteed parseable by _extract_yaml.load_yaml (indented block lists,
        # no line-wrapping). Idempotent: re-running produces identical bytes.
        if not dry_run:
            y.write_text(_dump_contract(data), encoding="utf-8")

    verb = "would fix" if dry_run else "fixed"
    log(f"==> repair_contracts: {verb} {total_changed}/{len(contracts)} contract(s) in {book_dir.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    return repair_contracts(a.slug, dry_run=a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
