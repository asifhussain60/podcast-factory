"""_paths.py — canonical filesystem path resolver for podcast-factory content.

Single source of truth for mapping content → directory. All other scripts MUST
call into this module instead of building paths from string literals like
``content/drafts/<slug>/``. This is the seam that lets the on-disk layout evolve
without search-and-replace through 20+ scripts.

LAYOUT (type-first, locked 2026-06-04):

    content/
      Islamic/<slug>/          ← scholarly religious texts
      Technical/<slug>/        ← developer / engineering material
      Fiction/<slug>/          ← stories
      Guides/<slug>/           ← plain-language general-audience content
      _system/                 ← cross-cutting pipeline plumbing
        shared/                  (was content/_shared)
        archive/<date>/<slug>/   (soft-deletes; was content/_archive)
        knowledge-base/
        podcast/
        catalog/                 (was content/published/_meta + archetypes)

The top-level **bucket** is the content TYPE and derives from a book's
``content_profile`` (see _rules.bucket_for_profile). Draft-vs-published is no
longer a folder — it is a ``status`` field in each book's
``_system/orchestrator-state.json`` (default ``draft``), read via status_of().

LEGACY (pre-2026-06-04): content lived at ``content/drafts/<category>/<slug>/``
and ``content/published/<category>/<slug>/`` (and older flat / BOOKS variants).
``find_content()`` / ``iter_content()`` still resolve those so a partial
migration cannot silently break readers. New writes ALWAYS use the type-first
layout. Back-compat: ``content_dir()`` still accepts the old ``stage=`` /
``category=`` kwargs and maps them onto a bucket, so existing callers keep working.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from _rules import ALLOWED_CATEGORIES, BUCKETS, bucket_for_profile

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_ROOT = REPO_ROOT / "content"

# Type-first plumbing root (2026-06-04).
SYSTEM_ROOT = CONTENT_ROOT / "_system"

# Shared/archive resolve to the new _system location once it exists, else the
# legacy top-level folders — so the resolver is correct before AND after the move.
_NEW_SHARED = SYSTEM_ROOT / "shared"
_NEW_ARCHIVE = SYSTEM_ROOT / "archive"
_LEGACY_SHARED = CONTENT_ROOT / "_shared"
_LEGACY_ARCHIVE = CONTENT_ROOT / "_archive"
SHARED_ROOT = _NEW_SHARED if _NEW_SHARED.is_dir() else _LEGACY_SHARED
ARCHIVE_ROOT = _NEW_ARCHIVE if _NEW_ARCHIVE.is_dir() else _LEGACY_ARCHIVE

# Legacy stage roots — fallback resolution only; never a write target for new content.
DRAFTS_ROOT = CONTENT_ROOT / "drafts"
PUBLISHED_ROOT = CONTENT_ROOT / "published"

# Deprecated; retained so old importers don't crash.
STAGES = ("drafts", "published")
STATUSES = ("draft", "published", "archived")

# Legacy category → bucket, for back-compat callers that still pass a category.
# The authoritative bucket comes from a book's content_profile; this table only
# serves transitional callers (scaffold/preflight) that pass category=.
_CATEGORY_TO_BUCKET: dict[str, str] = {
    "books": "Islamic", "lectures": "Islamic", "letters": "Islamic",
    "asbaaq": "Islamic", "interviews": "Islamic", "articles": "Islamic",
    "documents": "Islamic", "sites": "Guides", "explainers": "Guides",
}


def _validate_bucket(bucket: str) -> str:
    if bucket not in BUCKETS:
        raise ValueError(f"_paths: unknown bucket {bucket!r} (expected one of {BUCKETS})")
    return bucket


def _validate_slug(slug: str) -> str:
    """Accept a flat slug (``<name>``) or a one-level NESTED slug (``<parent>/<vol>``).

    Nested slugs let a multi-volume work live under a parent container
    (``content/Islamic/asaas-al-taveel/vol-01``) while every flat book is
    unchanged. Rejects empty, absolute, trailing-slash, traversal, or deeper-
    than-one-level paths so a slug can never escape its bucket.
    """
    if not slug or slug.startswith("/") or slug.endswith("/") or "\\" in slug:
        raise ValueError(f"_paths: invalid slug {slug!r}")
    parts = slug.split("/")
    if len(parts) > 2 or any(p in ("", "..", ".") for p in parts):
        raise ValueError(f"_paths: invalid slug {slug!r}")
    return slug


def _is_book_dir(p: Path) -> bool:
    """True if ``p`` is a processable book (has pipeline state), not a parent container.

    A nested-volume parent (``asaas-al-taveel/`` holding ``vol-01`` … ``vol-06``)
    carries neither a ``_system/`` plumbing dir nor a ``meta.yml`` at its own level,
    so the discovery scan descends into it instead of treating it as a book.
    """
    return (p / "_system").is_dir() or (p / "meta.yml").is_file()


def slug_of(path: Path) -> str:
    """Flat, filename-safe slug for a content dir.

    A flat book is its folder name (``kitab-al-riyad``). A NESTED volume folds the
    container into the slug as ``<container>-<leaf>`` (``asaas-al-taveel`` + ``vol-01``
    -> ``asaas-al-taveel-vol-01``) so the slug never contains ``/`` — it stays safe
    as a chapter-file / lock / contract filename component across the pipeline,
    while the folder on disk stays a clean ``vol-01``.
    """
    rp = path.resolve()
    for b in BUCKETS:
        try:
            parts = rp.relative_to((CONTENT_ROOT / b).resolve()).parts
        except ValueError:
            continue
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return f"{parts[0]}-{parts[1]}"
        return "-".join(parts)
    return path.name


def resolve_bucket(*, bucket: str | None, profile: str | None, category: str | None) -> str:
    """Pick the bucket from the most specific signal available. Defaults to Islamic.

    Resolution order (most → least specific): explicit ``bucket`` > ``content_profile``
    (via ``bucket_for_profile``) > legacy ``category`` (via ``_CATEGORY_TO_BUCKET``).
    Public so branch-naming (_branching.py) and the path layout share one resolver —
    folder bucket and branch bucket can never drift.
    """
    if bucket:
        return _validate_bucket(bucket)
    if profile:
        return bucket_for_profile(profile)
    if category:
        return _CATEGORY_TO_BUCKET.get(category.strip().lower(), "Islamic")
    return "Islamic"


# Back-compat alias for internal callers that used the private name.
_resolve_bucket = resolve_bucket


def status_of(book_dir: Path) -> str:
    """Read the publication status from a book's orchestrator-state.json.

    Returns ``draft`` when the file or field is absent — the safe default that
    keeps un-flagged content out of the published catalog.
    """
    state = book_dir / "_system" / "orchestrator-state.json"
    if not state.is_file():
        return "draft"
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except Exception:
        return "draft"
    s = data.get("status")
    return s if s in STATUSES else "draft"


def content_dir(
    slug: str,
    *,
    bucket: str | None = None,
    profile: str | None = None,
    category: str | None = None,
    stage: str | None = None,   # deprecated; accepted + ignored for back-compat
) -> Path:
    """Return the canonical directory for a piece of content: content/<Bucket>/<slug>.

    Does NOT check existence — use ``find_content()`` for the legacy-layout
    fallback. Prefer passing ``bucket=`` (or ``profile=``); ``category=`` is mapped
    to a bucket for transitional callers, and ``stage=`` is ignored (draft/published
    is now a status field, not a folder).
    """
    _validate_slug(slug)
    b = _resolve_bucket(bucket=bucket, profile=profile, category=category)
    return CONTENT_ROOT / b / slug


def bucket_dir(bucket: str) -> Path:
    """Return content/<Bucket> for a known bucket."""
    return CONTENT_ROOT / _validate_bucket(bucket)


def drafts_root() -> Path:        # deprecated (legacy layout)
    return DRAFTS_ROOT


def published_root() -> Path:     # deprecated (legacy layout)
    return PUBLISHED_ROOT


def archive_root() -> Path:
    return ARCHIVE_ROOT


def category_root(category: str, *, stage: str = "drafts") -> Path:  # deprecated
    """Legacy: content/<stage>/<category>. Retained for transitional callers."""
    root = PUBLISHED_ROOT if stage == "published" else DRAFTS_ROOT
    return root / category


def find_content(slug: str) -> tuple[str, str, Path] | None:
    """Locate ``slug`` on disk.

    Returns ``(status_or_stage, bucket_or_category, path)`` for the first match,
    or ``None``. Search order: type-first layout (``content/<Bucket>/<slug>``,
    first element is the book's ``status``), then legacy fallbacks
    (``drafts/<cat>``, ``published/<cat>``, flat ``drafts/<slug>``,
    ``drafts/BOOKS/<slug>`` — first element is the legacy ``stage``).
    """
    # Type-first (preferred): a flat book directly under the bucket.
    for b in BUCKETS:
        p = CONTENT_ROOT / b / slug
        if _is_book_dir(p):
            return (status_of(p), b, p)
    # Nested volume: a flat slug ``<container>-<leaf>`` maps to a book at
    # ``<bucket>/<container>/<leaf>``. Descend one level into parent containers
    # and match by the same ``<container>-<leaf>`` rule slug_of() emits.
    for b in BUCKETS:
        b_root = CONTENT_ROOT / b
        if not b_root.is_dir():
            continue
        for container in sorted(b_root.iterdir()):
            if (not container.is_dir() or container.name.startswith(("_", "."))
                    or _is_book_dir(container)):
                continue
            for leaf in sorted(container.iterdir()):
                if (leaf.is_dir() and not leaf.name.startswith(("_", "."))
                        and _is_book_dir(leaf)
                        and f"{container.name}-{leaf.name}" == slug):
                    return (status_of(leaf), b, leaf)
    # Legacy: drafts/<cat>/<slug>, then published/<cat>/<slug>.
    for st, st_root in (("drafts", DRAFTS_ROOT), ("published", PUBLISHED_ROOT)):
        for cat in ALLOWED_CATEGORIES:
            p = st_root / cat / slug
            if p.is_dir():
                return (st, cat, p)
    # Legacy: flat drafts/<slug>.
    flat = DRAFTS_ROOT / slug
    if flat.is_dir() and slug not in ALLOWED_CATEGORIES and slug != "BOOKS":
        return ("drafts", "books", flat)
    # Legacy: nested orphan drafts/BOOKS/<slug>.
    nested = DRAFTS_ROOT / "BOOKS" / slug
    if nested.is_dir():
        return ("drafts", "books", nested)
    return None


def resolve_content(slug: str) -> Path:
    """Return the content directory for ``slug``, bucket-agnostic.

    Uses ``find_content()`` when the directory exists; otherwise falls back to the
    canonical type-first path (Islamic bucket) for write-time resolution.
    """
    found = find_content(slug)
    return found[2] if found else content_dir(slug)


def iter_content(
    *,
    bucket: str | None = None,
    stage: str | None = None,      # deprecated alias for legacy callers
    category: str | None = None,   # deprecated (legacy layout filter)
) -> Iterable[tuple[str, str, Path]]:
    """Yield every ``(status_or_stage, bucket_or_category, dir)`` on disk.

    Honors the type-first layout AND the legacy drafts/published layout so a
    partial migration still surfaces everything. Skips hidden / ``_``-prefixed dirs.
    The ``stage`` kwarg is accepted for back-compat but ignored for the type-first
    scan (status is per-book, not a tree).
    """
    seen: set[Path] = set()
    buckets = (bucket,) if bucket else BUCKETS

    # Type-first.
    for b in buckets:
        b_root = CONTENT_ROOT / b
        if not b_root.is_dir():
            continue
        for child in sorted(b_root.iterdir()):
            if not child.is_dir() or child.name.startswith(("_", ".")):
                continue
            if _is_book_dir(child):
                if child.resolve() in seen:
                    continue
                seen.add(child.resolve())
                yield (status_of(child), b, child)
                continue
            # Parent container (e.g. a multi-volume work): descend one level and
            # yield each nested volume book. Flat books never reach this branch.
            for sub in sorted(child.iterdir()):
                if not sub.is_dir() or sub.name.startswith(("_", ".")):
                    continue
                if not _is_book_dir(sub):
                    continue
                if sub.resolve() in seen:
                    continue
                seen.add(sub.resolve())
                yield (status_of(sub), b, sub)

    # Legacy fallback (only when not filtering to a specific new bucket).
    if bucket:
        return
    stages = (stage,) if stage else STAGES
    cats = (category,) if category else ALLOWED_CATEGORIES
    for st in stages:
        st_root = PUBLISHED_ROOT if st == "published" else DRAFTS_ROOT
        if not st_root.is_dir():
            continue
        for cat in cats:
            cat_dir = st_root / cat
            if not cat_dir.is_dir():
                continue
            for child in sorted(cat_dir.iterdir()):
                if not child.is_dir() or child.name.startswith(("_", ".")):
                    continue
                if child.resolve() in seen:
                    continue
                seen.add(child.resolve())
                yield (st, cat, child)
        # Legacy flat drafts/<slug>.
        if st == "drafts" and category in (None, "books"):
            for child in sorted(st_root.iterdir()):
                if not child.is_dir():
                    continue
                if child.name in ALLOWED_CATEGORIES or child.name == "BOOKS":
                    continue
                if child.name.startswith(("_", ".")):
                    continue
                if child.resolve() in seen:
                    continue
                seen.add(child.resolve())
                yield (st, "books", child)


def relative_to_repo(path: Path) -> str:
    """Return ``path`` as a forward-slash POSIX string relative to repo root."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
