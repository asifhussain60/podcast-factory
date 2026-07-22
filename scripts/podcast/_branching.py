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
from _paths import resolve_bucket


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


def branch_for_work(
    volume_or_work_slug: str,
    *,
    profile: str | None = None,
    bucket: str | None = None,
    category: str | None = None,
) -> str:
    """Return the SINGLE branch for a multi-volume work, given any of its slugs.

    Q1 decision: ONE work = ONE branch. A composite volume slug
    (``asaas-vol-02``) maps to the same branch as the bare work slug
    (``asaas``) — ``Islamic/asaas``. A flat single book (no manifest) maps to its
    own ``<Bucket>/<slug>`` branch unchanged: ``work_slug_of`` returns None for it,
    so this degenerates to ``branch_name(slug)``.

    The branch is grouped under the work's BUCKET (same resolver as the folder
    layout), so branch bucket can never drift from folder bucket.
    """
    # Local import to avoid a module-load cycle (_work_manifest imports _paths,
    # _paths is imported here at module top; _branching is only imported lazily
    # by callers, never by _paths).
    from _work_manifest import work_slug_of

    work = work_slug_of(volume_or_work_slug) or volume_or_work_slug
    return branch_name(category, work, profile=profile, bucket=bucket)
