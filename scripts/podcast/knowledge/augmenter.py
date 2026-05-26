"""Augmenter — stateless query helper for future-book prompts.

Reads from `content/knowledge-base/{quran,hadith}.jsonl` and returns prompt-ready
prior-treatment context for injection into other phases of future books.

Not a phase. Called as a function from inside other phases:
- `0e` enrichment prompt    (light: 200 tokens)
- `per-chapter` authoring   (medium: 500 tokens)
- `0g` audit (challenger)   (heavy: 800 tokens)

Spec: `_workspace/plan/intelligence-pipeline-wave1-spec.md` §2.3, §6
Agent: `.github/agents/podcast-librarian.agent.md`

Status (2026-05-25): scaffold only. Wave 1 implementation pending.
"""
from __future__ import annotations

from pathlib import Path


def augment_for_chapter(
    book_slug: str,
    chapter_id: str,
    chapter_text: str,
    *,
    types: tuple[str, ...] = ("quran", "hadith"),
    max_atoms: int = 5,
    max_tokens: int = 800,
) -> str:
    """Return a prompt-ready string of prior atoms relevant to this chapter.

    Wave 1 selection: regex-scans `chapter_text` for canonical citations
    (e.g. "Quran 2:255", "Bukhari 1234"), looks them up in the library, returns
    formatted context. No semantic ranking.

    Default-disabled per spec §2.3: returns empty string immediately if the
    book's series-config has `enable_knowledge_augmenter` unset or false.
    Operator flips per-book during A/B rollout. Default flips only after the
    Gate I A/B acceptance check (spec §11.I) passes on at least one book pair.

    Args:
        book_slug: slug of the CURRENT book (excluded from "prior" treatments).
        chapter_id: chapter identifier (e.g. "ch01-prologue").
        chapter_text: raw chapter text to scan for citations.
        types: atom types to consider (Wave 1: only quran + hadith available).
        max_atoms: top-K cap (default 5 per R_KNOWLEDGE_AUGMENT_MAX_ATOMS).
        max_tokens: token-budget cap (default 800 per R_KNOWLEDGE_AUGMENT_MAX_TOKENS).

    Returns:
        Formatted prompt string per spec §6.2; empty string if no matches.
        Always returns within max_tokens budget (truncate cleanly at atom boundary).

    Implementation contract (per spec §2.3, §6):
        1. Load library shards for requested types.
        2. Regex-scan chapter_text using citation patterns from
           `_citation_patterns.py` (Wave 1 deliverable).
        3. Look up matched canonical IDs in the library.
        4. Filter out atoms whose only `source` is `book_slug` (no self-citation).
        5. Sort by citation-count desc; take top max_atoms.
        6. Format per spec §6.2 template.
        7. Truncate at atom boundary if total tokens > max_tokens.
    """
    raise NotImplementedError(
        "Wave 1 implementation pending. See _workspace/plan/intelligence-pipeline-wave1-spec.md"
    )


def lookup_atom(atom_id: str, library_root: Path | None = None) -> dict | None:
    """Lookup a single atom by canonical id. Returns None if not in library."""
    raise NotImplementedError(
        "Wave 1 implementation pending."
    )
