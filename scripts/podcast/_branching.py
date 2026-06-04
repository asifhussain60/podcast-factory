"""_branching.py — branch-naming policy for the podcast pipeline.

Single source of truth for how content branches are named off `develop`.

POLICY (locked 2026-06-04, reverting to a single-branch-per-item model):

  Every piece of content is processed on ONE branch named after its slug —
  no typed prefix. The entire pipeline runs on that branch, which merges back
  to develop after publish so develop ALWAYS holds the latest, holistic content.

  Branch naming:

      <full-slug>             — e.g. `ayyuhal-walad`, `kitab-al-riyad`

  Slugs are ALWAYS the full kebab-cased name. Never abbreviate.
  (Pre-2026-06-04 branches used a category prefix — `book/<slug>`, `lecture/<slug>`.
  `branch_prefix()` is retained for back-compat but is no longer used in names.)

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
    "asbaaq":     "sabaq",
    "sites":      "site",
    "explainers": "explainer",
}

# Fallback prefix when category is unknown, unset, or doesn't match the map.
# Intentionally generic — `draft/` keeps the branch trackable while signaling
# that classification is pending.
_FALLBACK_PREFIX = "draft"


def branch_prefix(category: str | None) -> str:  # deprecated (kept for back-compat)
    """Legacy category→prefix lookup. No longer used in branch names (2026-06-04)."""
    if not category:
        return _FALLBACK_PREFIX
    return _CATEGORY_TO_PREFIX.get(category.strip().lower(), _FALLBACK_PREFIX)


def branch_name(category: str | None, slug: str) -> str:
    """Return the branch name — the bare slug (one branch per item, 2026-06-04).

    The ``category`` arg is accepted for back-compat with existing callers but is
    ignored: branches are now named after the slug alone. Slug must already be
    kebab-cased and is used verbatim — no validation or abbreviation.
    """
    if not slug:
        raise ValueError("branch_name: slug must be non-empty")
    if "/" in slug:
        raise ValueError(f"branch_name: slug must not contain '/' (got {slug!r})")
    return slug
