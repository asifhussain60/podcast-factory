"""_branching.py — branch-naming policy for the podcast pipeline.

Single source of truth for how content branches are named off `develop`.

POLICY (locked 2026-06-07, reintroducing category grouping by content bucket):

  Every piece of content is processed on ONE branch named ``<Bucket>/<slug>`` —
  the bucket is the content's top-level category folder (Islamic, Technical,
  Fiction, Guides), derived from its ``content_profile`` (NOT its legacy
  ``category`` tag). The entire pipeline runs on that branch, which merges back
  to develop after publish so develop ALWAYS holds the latest, holistic content.

  Branch naming:

      <Bucket>/<full-slug>   — e.g. `Islamic/ayyuhal-walad`,
                               `Fiction/journey-to-the-west-vol-1`,
                               `Technical/claude-code-training`

  The bucket is resolved by ``_paths.resolve_bucket`` — the SAME resolver the
  content-folder layout uses — so a branch's bucket can never drift from the
  folder bucket. Slugs are ALWAYS the full kebab-cased name. Never abbreviate.

  HISTORY:
   - Pre-2026-06-04 branches used a content-TYPE prefix — `book/<slug>`,
     `lecture/<slug>`. Retired 2026-06-04.
   - 2026-06-04 → 2026-06-07 used the BARE slug with no prefix.
   - 2026-06-07 reintroduced grouping, now by content BUCKET (this file). This
     is distinct from the old type prefixes: buckets come from content_profile.
   ``branch_prefix()`` is retained for back-compat but is no longer used in names.

Consumers:
  - scripts/podcast/orchestrate_book.py   — branch creation + state stamp
  - scripts/podcast/intake_book.py        — initial branch from develop
  - scripts/podcast/_progress.py          — state.json branch field
  - scripts/podcast/phases/*.py           — preflight / merge / scaffold / series_plan
  - infra/claude-agents/podcast-orchestrator.md — agent doc
  - CLAUDE.md, framework.md               — operator-facing policy doc
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import resolve_bucket  # noqa: E402

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


def branch_name(
    category: str | None,
    slug: str,
    *,
    profile: str | None = None,
    bucket: str | None = None,
) -> str:
    """Return the branch name ``<Bucket>/<slug>`` (bucket-grouped, 2026-06-07).

    The bucket is resolved from the most specific signal available, preferring
    ``content_profile`` over the legacy ``category`` tag (which does NOT reliably
    determine the bucket — e.g. a `books`-category item can be Islamic OR Fiction):

        bucket=  (explicit)  >  profile=  (content_profile)  >  category=  (legacy)

    Callers SHOULD pass ``profile=`` (the book's ``content_profile``) or
    ``bucket=`` when known; ``category`` alone falls back to a coarse map that
    defaults to Islamic.

    Slug must already be kebab-cased and is used verbatim — no validation or
    abbreviation. It must not itself contain '/'.
    """
    if not slug:
        raise ValueError("branch_name: slug must be non-empty")
    if "/" in slug:
        raise ValueError(f"branch_name: slug must not contain '/' (got {slug!r})")
    b = resolve_bucket(bucket=bucket, profile=profile, category=category)
    return f"{b}/{slug}"
