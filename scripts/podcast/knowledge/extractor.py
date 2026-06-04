"""Extractor — phase 0h step 1.

# DEPRECATED — superseded by intelligence/extractor.py (Wave B DB-backed).
# No production callers. Retained for reference only; delete in a future cleanup.
# Note: knowledge/_atom_schemas.py is still live (imported by intelligence/extractor.py).

Reads audit-vetted chapter bundles from a book's `_system/episode-drafts/` and pulls
out atoms (Wave 1: Quran + hadith only). Writes a per-book scratch JSONL file with no
dedup. The Librarian handles dedup downstream.

Spec: `_workspace/plan/architecture.md` (Intelligence Layer section) and
      `_workspace/plan/refactor/plan.md` (Wave B).
Agent: `.github/agents/podcast-librarian.agent.md`

Status (2026-05-25): scaffold only. Wave 1 implementation pending.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractorResult:
    """Result of running the Extractor on one book."""
    scratch_path: Path
    atoms_extracted: dict[str, int]   # {"quran": N, "hadith": M}
    needs_review_count: int
    cost_usd: float


def extract_atoms_for_book(book_dir: Path) -> ExtractorResult:
    """Extract atoms from a book's audit-vetted chapters.

    Args:
        book_dir: `content/drafts/<slug>/` for the in-flight book.

    Returns:
        ExtractorResult with the scratch JSONL path and atom counts.

    Raises:
        FileNotFoundError: if the book directory or its episode-drafts are missing.
        RuntimeError: if the Extractor LLM call fails or atoms fail schema validation.
        CostCapExceeded: if cost exceeds R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD.

    Implementation contract (per spec §2.1):
        1. Verify `_system/orchestrator-state.json` shows phase 0g completed.
        2. For each `_system/episode-drafts/EP##-<slug>/`:
           - Read chapter source + 00-framing.md.
           - LLM call (Sonnet) with structured-output schema for {quran, hadith} atoms.
           - Validate each atom against the schema in `_atom_schemas.py`.
           - Tag atoms with confidence < 0.7 as `needs_review: true`.
        3. Write all atoms (no dedup) to
           `_system/knowledge-atoms-scratch.jsonl`.
        4. Track cumulative cost via `_cost_ledger.append_*` helpers.
        5. Halt with CostCapExceeded if cost > R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD.
    """
    raise NotImplementedError(
        "Wave 1 implementation pending. See _workspace/plan/architecture.md (Intelligence Layer section) + _workspace/plan/refactor/plan.md (Wave B)"
    )


def main() -> int:
    """CLI entry point: `python3 scripts/podcast/knowledge/extractor.py <slug>`."""
    raise NotImplementedError(
        "Wave 1 implementation pending. See _workspace/plan/architecture.md (Intelligence Layer section) + _workspace/plan/refactor/plan.md (Wave B)"
    )


if __name__ == "__main__":
    import sys
    sys.exit(main())
