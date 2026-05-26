"""Librarian — phase 0h step 2.

Takes the Extractor's scratch JSONL, walks each atom against the canonical library,
and writes back: merged library files + a human-readable merge report + (if any)
conflicts to `content/knowledge-base/_conflicts/pending-review.jsonl`.

Pure Python — no LLM calls. Wave 1: exact-match dedup on canonical ID.

Spec: `_workspace/plan/architecture.md` (Intelligence Layer section) and
      `_workspace/plan/refactor/plan.md` (Wave B).
Agent: `.github/agents/podcast-librarian.agent.md`

Status (2026-05-25): scaffold only. Wave 1 implementation pending.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MergeReport:
    """Per-book Librarian outcome."""
    atoms_new:      dict[str, int] = field(default_factory=dict)   # by type
    atoms_merged:   dict[str, int] = field(default_factory=dict)   # by type
    atoms_conflict: dict[str, int] = field(default_factory=dict)   # by type
    conflict_count: int = 0
    conflict_file:  Path | None = None
    report_md_path: Path | None = None


def merge_into_library(book_dir: Path, scratch_path: Path) -> MergeReport:
    """Merge a book's scratch atoms into the canonical knowledge library.

    Args:
        book_dir: `content/drafts/<slug>/` for the in-flight book.
        scratch_path: path to `_system/knowledge-atoms-scratch.jsonl`.

    Returns:
        MergeReport summarizing merge outcomes; conflict_count > 0 means halt.

    Implementation contract (per spec §2.2, §5):
        1. Load existing `content/knowledge-base/{quran,hadith}.jsonl` into dict
           keyed by atom id.
        2. For each scratch atom, classify against the canonical library:
           - NEW (id not in library)        → append to library with full envelope
           - KNOWN, identical body          → merge into `sources[]`
           - KNOWN, different text variant  → add to `variants[]`, NOT a conflict
           - KNOWN, true contradiction      → append to _conflicts/pending-review.jsonl
             (differing `text_ar`, differing hadith `grade`, differing `narrator`)
        3. Write back updated library JSONL files (atomic, lockfile-guarded).
        4. Write human-readable summary to
           `_system/knowledge-merge-report.md`.
        5. Update `content/knowledge-base/_index/stats.json` with new counts.
        6. If conflicts exist, return MergeReport with conflict_count > 0 — caller
           halts the phase.

    Never auto-merges conflicts; never modifies atoms that already exist in the
    canonical library beyond adding sources/variants.
    """
    raise NotImplementedError(
        "Wave 1 implementation pending. See _workspace/plan/architecture.md (Intelligence Layer) + _workspace/plan/refactor/plan.md (Wave B)"
    )


def main() -> int:
    """CLI entry point: `python3 scripts/podcast/knowledge/librarian.py <slug>`."""
    raise NotImplementedError(
        "Wave 1 implementation pending. See _workspace/plan/architecture.md (Intelligence Layer) + _workspace/plan/refactor/plan.md (Wave B)"
    )


if __name__ == "__main__":
    import sys
    sys.exit(main())
