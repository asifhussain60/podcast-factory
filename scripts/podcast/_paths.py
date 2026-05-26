"""_paths.py — canonical filesystem path resolver for podcast-factory content.

Single source of truth for mapping (stage, category, slug) → directory. All
other scripts MUST call into this module instead of building paths from
string literals like ``content/drafts/<slug>/``. This is the seam that lets
the on-disk layout evolve without search-and-replace through 20+ scripts.

LAYOUT (locked 2026-05-26):

    content/
      drafts/
        books/<slug>/
        lectures/<slug>/
        asbaaq/<slug>/
        ... (other categories from _rules.ALLOWED_CATEGORIES)
      published/
        books/<slug>/
        lectures/<slug>/
        asbaaq/<slug>/
        ...
      _shared/
      _archive/<date>/<slug>/   (soft-deletes land here, recoverable)

The category subfolder always matches the singular/plural form used in
``_rules.ALLOWED_CATEGORIES`` (plural: ``books``, ``lectures``, ``asbaaq``).

LEGACY (pre-2026-05-26): some content lived flat at ``content/drafts/<slug>/``
or in an orphan nested tree ``content/drafts/BOOKS/<slug>/``. ``find_content()``
will fall back to those if the canonical path is missing, so a partial
migration cannot silently break readers. New writes ALWAYS use the canonical
layout.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from _rules import ALLOWED_CATEGORIES

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_ROOT = REPO_ROOT / "content"
DRAFTS_ROOT = CONTENT_ROOT / "drafts"
PUBLISHED_ROOT = CONTENT_ROOT / "published"
SHARED_ROOT = CONTENT_ROOT / "_shared"
ARCHIVE_ROOT = CONTENT_ROOT / "_archive"

STAGES = ("drafts", "published")


def _stage_root(stage: str) -> Path:
    if stage == "drafts":
        return DRAFTS_ROOT
    if stage == "published":
        return PUBLISHED_ROOT
    raise ValueError(f"_paths: unknown stage {stage!r} (expected one of {STAGES})")


def _validate_category(category: str) -> str:
    cat = (category or "").strip().lower()
    if cat not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"_paths: unknown category {category!r} "
            f"(expected one of {ALLOWED_CATEGORIES})"
        )
    return cat


def content_dir(slug: str, *, stage: str = "drafts", category: str = "books") -> Path:
    """Return the canonical directory for a piece of content.

    Does NOT check that the directory exists — call ``find_content()`` if
    you need to handle the legacy-layout fallback. Use this for writes and
    for newly-created content where the canonical path is what you want.
    """
    if not slug or "/" in slug:
        raise ValueError(f"_paths: invalid slug {slug!r}")
    return _stage_root(stage) / _validate_category(category) / slug


def drafts_root() -> Path:
    return DRAFTS_ROOT


def published_root() -> Path:
    return PUBLISHED_ROOT


def archive_root() -> Path:
    return ARCHIVE_ROOT


def category_root(category: str, *, stage: str = "drafts") -> Path:
    """Return the directory that holds all <stage>/<category>/* slugs."""
    return _stage_root(stage) / _validate_category(category)


def find_content(slug: str) -> tuple[str, str, Path] | None:
    """Locate ``slug`` across all (stage, category) combinations.

    Returns ``(stage, category, path)`` for the first matching directory,
    or ``None`` if not found. Search order: canonical first
    (drafts/<cat>/<slug>, published/<cat>/<slug>), then legacy fallbacks
    (drafts/<slug>, drafts/BOOKS/<slug>).
    """
    # Canonical (preferred): drafts/<cat>/<slug>, then published/<cat>/<slug>
    for stage in STAGES:
        for cat in ALLOWED_CATEGORIES:
            p = _stage_root(stage) / cat / slug
            if p.is_dir():
                return (stage, cat, p)
    # Legacy: flat drafts/<slug>
    flat = DRAFTS_ROOT / slug
    if flat.is_dir() and slug not in ALLOWED_CATEGORIES and slug != "BOOKS":
        return ("drafts", "books", flat)
    # Legacy: nested orphan drafts/BOOKS/<slug>
    nested = DRAFTS_ROOT / "BOOKS" / slug
    if nested.is_dir():
        return ("drafts", "books", nested)
    return None


def iter_content(
    *,
    stage: str | None = None,
    category: str | None = None,
) -> Iterable[tuple[str, str, Path]]:
    """Yield every (stage, category, dir) currently on disk.

    Honors the canonical layout AND the legacy flat layout (so a partial
    migration still surfaces everything). Skips hidden directories and
    skips slug names that collide with category names.
    """
    stages = (stage,) if stage else STAGES
    cats = (category,) if category else ALLOWED_CATEGORIES
    seen: set[Path] = set()

    for st in stages:
        st_root = _stage_root(st)
        if not st_root.is_dir():
            continue
        # Canonical: <stage>/<cat>/<slug>
        for cat in cats:
            cat_dir = st_root / cat
            if not cat_dir.is_dir():
                continue
            for child in sorted(cat_dir.iterdir()):
                if not child.is_dir() or child.name.startswith("_") or child.name.startswith("."):
                    continue
                if child.resolve() in seen:
                    continue
                seen.add(child.resolve())
                yield (st, cat, child)
        # Legacy: <stage>/<slug> (flat books only)
        if st == "drafts" and (category in (None, "books")):
            for child in sorted(st_root.iterdir()):
                if not child.is_dir():
                    continue
                if child.name in ALLOWED_CATEGORIES or child.name == "BOOKS":
                    continue
                if child.name.startswith("_") or child.name.startswith("."):
                    continue
                if child.resolve() in seen:
                    continue
                seen.add(child.resolve())
                yield (st, "books", child)


def relative_to_repo(path: Path) -> str:
    """Return ``path`` as a forward-slash POSIX string relative to repo root.

    Useful for runtime-prefix stamping into orchestrator-state.json and for
    log messages, where consistent string form matters across platforms.
    """
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
