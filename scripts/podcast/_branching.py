"""_branching.py — branch-naming policy for the podcast pipeline.

Single source of truth for how content branches are named off `develop`.

POLICY (locked 2026-05-24, reversing the 2026-05-23 single-branch model):

  Every new piece of content is processed on its own typed branch off
  develop. The branch is created at intake time and merged back to develop
  ONLY after publish completes. The prefix is determined by the content's
  `category` field (see _rules.ALLOWED_CATEGORIES).

  Branch naming:

      book/<full-slug>        — for books
      doc/<full-slug>         — for documents
      lecture/<full-slug>     — for audio lectures
      article/<full-slug>     — for articles
      letter/<full-slug>      — for letters
      interview/<full-slug>   — for interviews
      draft/<full-slug>       — fallback when category is unknown/unset

  Slugs are ALWAYS the full kebab-cased name. Never abbreviate.
  Example: `book/kitab-al-riyad`, NEVER `book/KaR`.

Consumers:
  - scripts/podcast/orchestrate_book.py   — branch creation + state stamp
  - scripts/podcast/intake_book.py        — initial branch from develop
  - scripts/podcast/_progress.py          — state.json branch field
  - infra/claude-agents/podcast-orchestrator.md — agent doc
  - CLAUDE.md, framework.md               — operator-facing policy doc
"""
from __future__ import annotations

# Category → branch-prefix map. Keys must mirror _rules.ALLOWED_CATEGORIES;
# values are the singular form used in branch names.
_CATEGORY_TO_PREFIX = {
    "books":      "book",
    "documents":  "doc",
    "lectures":   "lecture",
    "articles":   "article",
    "letters":    "letter",
    "interviews": "interview",
}

# Fallback prefix when category is unknown, unset, or doesn't match the map.
# Intentionally generic — `draft/` keeps the branch trackable while signaling
# that classification is pending.
_FALLBACK_PREFIX = "draft"


def branch_prefix(category: str | None) -> str:
    """Return the branch prefix for a category. Unknown/missing → 'draft'."""
    if not category:
        return _FALLBACK_PREFIX
    return _CATEGORY_TO_PREFIX.get(category.strip().lower(), _FALLBACK_PREFIX)


def branch_name(category: str | None, slug: str) -> str:
    """Return the full branch name '<prefix>/<slug>'.

    Slug must already be kebab-cased and is used verbatim — this function
    does NOT validate or abbreviate. Pass the full slug always.
    """
    if not slug:
        raise ValueError("branch_name: slug must be non-empty")
    if "/" in slug:
        raise ValueError(f"branch_name: slug must not contain '/' (got {slug!r})")
    return f"{branch_prefix(category)}/{slug}"
