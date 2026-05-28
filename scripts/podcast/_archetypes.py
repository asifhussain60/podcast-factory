"""_archetypes.py — Archetype registry loader and resolver for podcast-factory.

Archetypes live on disk at::

    content/_shared/archetypes/<slug>/
        spec.yml          # required — machine-readable doctrine
        exemplar.md       # required — illustrative episode structure
        anti-patterns.md  # required — challenger denial catalog

This module reads those files, validates them, and provides the single
resolution function used by the pipeline and the challenger when deciding
which authoring doctrine applies to a book.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml  # PyYAML
except ImportError:  # pragma: no cover
    _yaml = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
_ARCHETYPES_ROOT = _REPO_ROOT / "content" / "_shared" / "archetypes"

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Archetype:
    slug: str
    display_name: str
    genre_tags: list[str]
    genre_signals: list[str]
    required_fields: list[str]
    authoring_doctrine: dict[str, Any]
    challenger_categories_active: list[str]
    anti_patterns_summary: list[str]
    # raw file contents (for DB snapshot and challenger reference)
    spec_yml_text: str
    exemplar_md_text: str
    anti_patterns_md_text: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_spec(spec_text: str, slug: str) -> dict[str, Any]:
    """Parse spec.yml text into a dict.

    Falls back to minimal regex parsing when PyYAML is unavailable so the
    module remains importable in environments without optional deps.
    """
    if _yaml is not None:
        data: dict[str, Any] = _yaml.safe_load(spec_text) or {}
        return data
    # Minimal fallback: extract only scalar top-level keys.
    data = {}
    for line in spec_text.splitlines():
        m = re.match(r'^(\w[\w_-]*):\s*(.+)$', line)
        if m:
            data[m.group(1)] = m.group(2).strip()
    return data


def _load_one(archetype_dir: Path) -> Archetype:
    slug = archetype_dir.name
    spec_path = archetype_dir / "spec.yml"
    exemplar_path = archetype_dir / "exemplar.md"
    anti_path = archetype_dir / "anti-patterns.md"

    missing = [p.name for p in (spec_path, exemplar_path, anti_path) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"_archetypes: {slug} is missing required files: {', '.join(missing)}"
        )

    spec_text = spec_path.read_text(encoding="utf-8")
    exemplar_text = exemplar_path.read_text(encoding="utf-8")
    anti_text = anti_path.read_text(encoding="utf-8")

    spec = _parse_spec(spec_text, slug)

    return Archetype(
        slug=slug,
        display_name=spec.get("display_name", slug),
        genre_tags=list(spec.get("genre_tags") or []),
        genre_signals=list((spec.get("genre_signals") or {}).values()
                           if isinstance(spec.get("genre_signals"), dict)
                           else (spec.get("genre_signals") or [])),
        required_fields=list(spec.get("required_fields") or []),
        authoring_doctrine=dict(spec.get("authoring_doctrine") or {}),
        challenger_categories_active=list(
            spec.get("challenger_categories_active") or []
        ),
        anti_patterns_summary=list(spec.get("anti_patterns_summary") or []),
        spec_yml_text=spec_text,
        exemplar_md_text=exemplar_text,
        anti_patterns_md_text=anti_text,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_cache: dict[str, Archetype] = {}


def load_archetype(slug: str) -> Archetype:
    """Load and return the named archetype, caching after the first load.

    Raises ``FileNotFoundError`` if the archetype directory or any of its
    required files do not exist.
    """
    if slug in _cache:
        return _cache[slug]
    archetype_dir = _ARCHETYPES_ROOT / slug
    if not archetype_dir.is_dir():
        raise FileNotFoundError(
            f"_archetypes: no archetype directory at {archetype_dir}"
        )
    archetype = _load_one(archetype_dir)
    _cache[slug] = archetype
    return archetype


def list_archetypes() -> list[str]:
    """Return the slugs of all archetype directories present on disk."""
    if not _ARCHETYPES_ROOT.is_dir():
        return []
    return sorted(
        d.name
        for d in _ARCHETYPES_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")
    )


_KNOWN_ARCHETYPE_IDS: dict[str, str] = {
    # Maps common meta.yml values → canonical slug.
    "scholarly-deep-dive": "scholarly-deep-dive",
    "scholarly_deep_dive": "scholarly-deep-dive",
    "play-novel": "play-novel",
    "play_novel": "play-novel",
    "lecture-series": "lecture-series",
    "lecture_series": "lecture-series",
    "aphorism-collection": "aphorism-collection",
    "aphorism_collection": "aphorism-collection",
    "narrative-prose": "narrative-prose",
    "narrative_prose": "narrative-prose",
    "encyclopedic-epistolary": "encyclopedic-epistolary",
    "encyclopedic_epistolary": "encyclopedic-epistolary",
    "socratic-dialogue": "socratic-dialogue",
    "socratic_dialogue": "socratic-dialogue",
}


def build_exemplar_vector(archetype_slug: str) -> list[float]:
    """Compute a bigram-frequency vector from an archetype's exemplar text.

    Reads ``content/_shared/archetypes/<slug>/exemplar.md``, tokenises into
    bigrams, and returns a list of frequencies sorted descending.  The result
    is saved alongside the exemplar as ``exemplar_vector.json`` for fast
    reloads.  Calling this again overwrites the cached file.
    """
    import json
    archetype_dir = _ARCHETYPES_ROOT / archetype_slug
    exemplar_path = archetype_dir / "exemplar.md"
    if not exemplar_path.exists():
        raise FileNotFoundError(f"exemplar.md not found for archetype {archetype_slug!r}")

    text = exemplar_path.read_text(encoding="utf-8").lower()
    tokens = text.split()
    counts: dict[str, int] = {}
    for i in range(len(tokens) - 1):
        bg = tokens[i] + "_" + tokens[i + 1]
        counts[bg] = counts.get(bg, 0) + 1

    vector = sorted(counts.values(), reverse=True)
    out_path = archetype_dir / "exemplar_vector.json"
    out_path.write_text(json.dumps(vector), encoding="utf-8")
    return vector


def load_exemplar_vector(archetype_slug: str) -> list[float] | None:
    """Load a pre-built exemplar vector from disk, or return None if absent.

    Callers should pass the result to ``_quality.score()`` as
    ``voice_exemplar_vector``.  Returns ``None`` (rather than raising) when
    the vector has not yet been built so the scorer can fall back gracefully.
    """
    import json
    vec_path = _ARCHETYPES_ROOT / archetype_slug / "exemplar_vector.json"
    if not vec_path.exists():
        return None
    return json.loads(vec_path.read_text(encoding="utf-8"))


def resolve_archetype_for_book(meta: dict[str, Any]) -> Archetype | None:
    """Resolve and return the archetype for a book given its meta dict.

    Reads ``meta["archetype_id"]`` (or ``meta["archetype"]``) and maps it to
    a canonical slug. Returns ``None`` if no archetype is set or if the
    declared archetype is not found on disk (logs a warning rather than
    raising so the pipeline can continue in degraded mode).
    """
    raw = meta.get("archetype_id") or meta.get("archetype") or ""
    if not raw:
        return None
    slug = _KNOWN_ARCHETYPE_IDS.get(str(raw).strip().lower(), str(raw).strip().lower())
    try:
        return load_archetype(slug)
    except FileNotFoundError:
        import warnings
        warnings.warn(
            f"_archetypes: archetype {slug!r} declared in meta but not found on disk; "
            "continuing without archetype doctrine.",
            stacklevel=2,
        )
        return None
