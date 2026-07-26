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
import os
import re
from pathlib import Path
from typing import Iterable

from _rules import ALLOWED_CATEGORIES, BUCKETS, bucket_for_profile

# Repo root resolution — MUST mirror getRepoRoot() in
# plan-dashboard/src/lib/content-paths.ts so the pipeline (writer) and the Astro
# site (reader) never resolve different content trees. Default is file-relative
# (deterministic, cwd-independent); an explicit PODCAST_FACTORY_ROOT override is
# honored identically on both sides.
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_REPO_ROOT = os.environ.get("PODCAST_FACTORY_ROOT")
REPO_ROOT = Path(_ENV_REPO_ROOT) if _ENV_REPO_ROOT else _DEFAULT_REPO_ROOT
CONTENT_ROOT = REPO_ROOT / "content"

# ── Multi-volume works (2026-06-09) ──────────────────────────────────────────
# A nested multi-volume "work" lives at content/<Bucket>/<work_slug>/ and is
# MARKED by a work.yml manifest. Its volumes are vol-NN/ subdirs, each a normal
# book dir. The COMPOSITE volume slug is "<work_slug>-<vol_dir>" (asaas + vol-02
# → asaas-vol-02). This module discovers volumes by the marker + glob WITHOUT
# parsing the yaml (no yaml dep, no circular import on _work_manifest) — the
# manifest CONTENTS are read by _work_manifest.py. When no work.yml exists
# anywhere, every function below is byte-identical to flat resolution.
WORK_MANIFEST_NAME = "work.yml"
# `[0-9]`, not `\d`. Python's `\d` is Unicode-aware and JavaScript's is ASCII-only,
# so `vol-٠١` matched here and not in content-paths.ts — the same dialect split that
# silently orphaned Composer edits through anchorKey until 2026-07-20. Volume dirs
# are minted by the pipeline as ASCII (`vol-01`), so pinning to ASCII costs nothing
# and makes both languages agree by construction rather than by coincidence.
# Pinned by plan-dashboard/scripts/lib/content-paths.fixtures.json.
_VOL_DIR_RE = re.compile(r"^vol-[0-9]+$")
_COMPOSITE_SLUG_RE = re.compile(r"^(?P<work>.+)-(?P<dir>vol-[0-9]+)$")


def is_work_parent(dir_: Path) -> bool:
    """True iff ``dir_`` is a multi-volume work parent (holds a work.yml marker)."""
    return (dir_ / WORK_MANIFEST_NAME).is_file()


def volume_dirs(work_dir: Path) -> list[Path]:
    """Sorted ``vol-NN`` subdirectories of a work parent (by name)."""
    if not work_dir.is_dir():
        return []
    return sorted(
        (c for c in work_dir.iterdir() if c.is_dir() and _VOL_DIR_RE.match(c.name)),
        key=lambda p: p.name,
    )


def work_rollup_status(work_dir: Path) -> str:
    """Roll a work's status up from its volumes: ``published`` only when ALL are."""
    vols = volume_dirs(work_dir)
    if not vols:
        return "draft"
    statuses = [status_of(v) for v in vols]
    if all(s == "published" for s in statuses):
        return "published"
    if all(s == "archived" for s in statuses):
        return "archived"
    return "draft"


# ── Standard per-book folder skeleton (2026-06-10) ──────────────────────────
# SINGLE source of truth for the subdirectories every book (or volume) dir gets
# at creation time. intake_book.py (flat + multi-volume), scaffold_book.py, and
# standardize_book_folders.py (retroactive migration) ALL consume this tuple —
# never define a folder list anywhere else. Extensibility-first: adding a
# pipeline surface = one entry here.
BOOK_SUBDIRS: tuple[str, ...] = (
    "_source",  # irreplaceable source inputs (tracked)
    "_system",  # pipeline state + scratch
    "_system/episode-drafts",
    "_system/scratchpad",
    "_system/source",
    "_system/source/text",
    "chapter-contracts",
    "chapters",
    "episodes",
    "m4a",  # NotebookLM audio drops (contents gitignored)
    "transcripts",  # Turboscribe/Azure transcripts
    "slide-decks",  # deck sources + framings + dropped deck PDFs
    "slide-decks/_manifests",  # slide→anchor manifests (tracked)
    "book",  # reading edition (book.md … book.pdf)
    "audits",
    "notebooklm",
)


def ensure_book_skeleton(book_dir: Path) -> None:
    """Create the standard subdirectory skeleton under ``book_dir``.

    Idempotent. Drops a ``.gitkeep`` in each leaf so empty folders survive git
    (audio/transcript CONTENTS stay gitignored; the keep-file is what's tracked).
    """
    book_dir = Path(book_dir)
    for sub in BOOK_SUBDIRS:
        d = book_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        keep = d / ".gitkeep"
        if not keep.exists() and not any(d.iterdir()):
            keep.touch()


def slug_of(path: Path) -> str:
    """Canonical slug for a content dir yielded by ``iter_content``/``find_content``.

    Returns the COMPOSITE slug for a volume dir (``<work_slug>-vol-NN``) and the
    plain dir name for a flat book or a work parent. Callers that need a stable,
    collision-free identity MUST use this instead of ``path.name`` (two works can
    both contain a ``vol-01``).
    """
    parent = path.parent
    if _VOL_DIR_RE.match(path.name) and is_work_parent(parent):
        return f"{parent.name}-{path.name}"
    return path.name


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
    "books": "Islamic",
    "lectures": "Islamic",
    "letters": "Islamic",
    "asbaaq": "Islamic",
    "interviews": "Islamic",
    "articles": "Islamic",
    "documents": "Islamic",
    "sites": "Guides",
    "explainers": "Guides",
}


def _validate_bucket(bucket: str) -> str:
    if bucket not in BUCKETS:
        raise ValueError(f"_paths: unknown bucket {bucket!r} (expected one of {BUCKETS})")
    return bucket


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
    stage: str | None = None,  # deprecated; accepted + ignored for back-compat
) -> Path:
    """Return the canonical directory for a piece of content: content/<Bucket>/<slug>.

    Does NOT check existence — use ``find_content()`` for the legacy-layout
    fallback. Prefer passing ``bucket=`` (or ``profile=``); ``category=`` is mapped
    to a bucket for transitional callers, and ``stage=`` is ignored (draft/published
    is now a status field, not a folder).
    """
    if not slug or "/" in slug:
        raise ValueError(f"_paths: invalid slug {slug!r}")
    b = _resolve_bucket(bucket=bucket, profile=profile, category=category)
    return CONTENT_ROOT / b / slug


def bucket_dir(bucket: str) -> Path:
    """Return content/<Bucket> for a known bucket."""
    return CONTENT_ROOT / _validate_bucket(bucket)


def drafts_root() -> Path:
    """DEPRECATED — legacy layout helper; zero callers as of 2026-06-10."""
    return DRAFTS_ROOT


def published_root() -> Path:
    """DEPRECATED — legacy layout helper; zero callers as of 2026-06-10."""
    return PUBLISHED_ROOT


def archive_root() -> Path:
    return ARCHIVE_ROOT


def category_root(category: str, *, stage: str = "drafts") -> Path:
    """DEPRECATED — legacy content/<stage>/<category>; zero callers as of 2026-06-10."""
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
    # Type-first (preferred). A bare slug that names a work PARENT (has work.yml)
    # resolves to the work dir with a rolled-up status; a flat book resolves as
    # before (byte-identical when no manifest exists).
    for b in BUCKETS:
        p = CONTENT_ROOT / b / slug
        if p.is_dir():
            if is_work_parent(p):
                return (work_rollup_status(p), b, p)
            return (status_of(p), b, p)
    # Composite volume slug: "<work>-vol-NN" → content/<B>/<work>/vol-NN, but ONLY
    # when <work> is a real work parent (has work.yml). A flat book ending in
    # "-vol-N" never reaches here — its own dir matched above.
    m = _COMPOSITE_SLUG_RE.match(slug)
    if m:
        work, vol = m.group("work"), m.group("dir")
        for b in BUCKETS:
            wp = CONTENT_ROOT / b / work
            vp = wp / vol
            if is_work_parent(wp) and vp.is_dir():
                return (status_of(vp), b, vp)
    # Legacy: drafts/<cat>/<slug>, then published/<cat>/<slug>.
    for st, st_root in (("drafts", DRAFTS_ROOT), ("published", PUBLISHED_ROOT)):
        for cat in ALLOWED_CATEGORIES:
            p = st_root / cat / slug
            if p.is_dir():
                return (st, cat, p)
    # Legacy: flat drafts/<slug>. BOOKS and LECTURES are legacy CONTAINERS, not
    # books — iter_content skips both when enumerating, and content-paths.ts guarded
    # both here while this side guarded only BOOKS. Aligned 2026-07-26; pinned by
    # plan-dashboard/scripts/lib/content-paths.fixtures.json.
    flat = DRAFTS_ROOT / slug
    if flat.is_dir() and slug not in ALLOWED_CATEGORIES and slug not in ("BOOKS", "LECTURES"):
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
    stage: str | None = None,  # deprecated alias for legacy callers
    category: str | None = None,  # deprecated (legacy layout filter)
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
            if child.resolve() in seen:
                continue
            seen.add(child.resolve())
            # A work parent is NOT itself a book — descend and yield its volumes
            # (each a normal book dir). Callers derive the composite slug via
            # slug_of(path). No-op when no work.yml exists → flat byte-identical.
            if is_work_parent(child):
                for vol in volume_dirs(child):
                    if vol.resolve() in seen:
                        continue
                    seen.add(vol.resolve())
                    yield (status_of(vol), b, vol)
                continue
            yield (status_of(child), b, child)

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
