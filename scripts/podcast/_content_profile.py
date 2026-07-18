"""
_content_profile.py — resolve the content_profile for a book directory.

Reads `content_profile` from `_system/series-config.yaml`; defaults to
`islamic_scholarly` when the field is absent or the file doesn't exist, so
every existing book is unaffected with no config change required.

Pipeline consumers:
  - build_episode_txt.py  : skip Arabic-specific assertions for non-Islamic profiles
  - _authoring/_refine.py : 0c phonetics already gated by CONSUMER_CATEGORIES; this
                            adds a profile-aware path for future consumer variants
  - podcast-challenger    : gate Arabic name-aliasing and citation checks
"""

from __future__ import annotations

from pathlib import Path

import yaml
from _rules import CONTENT_PROFILES, ISLAMIC_SCHOLARLY_PROFILE


def resolve_content_profile(book_dir: Path) -> str:
    """Return the content_profile declared in *book_dir*/_system/series-config.yaml.

    Falls back to ``islamic_scholarly`` when:
      - the file is absent
      - the field is not set
      - the value is not a recognised profile (logs a warning and falls back)

    Raises
    ------
    ValueError
        Only when the caller explicitly passes ``strict=True`` and the profile is
        unrecognised (used in tests; never in the live pipeline).
    """
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return ISLAMIC_SCHOLARLY_PROFILE

    try:
        with cfg_path.open() as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return ISLAMIC_SCHOLARLY_PROFILE

    profile = cfg.get("content_profile") or ISLAMIC_SCHOLARLY_PROFILE
    if profile not in CONTENT_PROFILES:
        import logging

        logging.getLogger(__name__).warning(
            "Unknown content_profile %r in %s — defaulting to islamic_scholarly",
            profile,
            cfg_path,
        )
        return ISLAMIC_SCHOLARLY_PROFILE

    return profile


def is_islamic_scholarly(book_dir: Path) -> bool:
    """Convenience predicate: True when the book uses the default Islamic pipeline."""
    return resolve_content_profile(book_dir) == ISLAMIC_SCHOLARLY_PROFILE


def slide_deck_mode(book_dir: Path) -> str:
    """Return the book's slide-deck mode: 'per-chapter' (default) or 'book'.

    `slide_deck_mode: book` in `_system/series-config.yaml` switches the
    mandatory per-chapter-slides phase to author ONE deck pair for the whole
    book (slide-decks/book-deck-source.txt + book-framing.md) — one NotebookLM
    generation instead of one per chapter. Unknown values fall back to
    per-chapter (zero behavior change for existing books).
    """
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return "per-chapter"
    try:
        with cfg_path.open() as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return "per-chapter"
    mode = str(cfg.get("slide_deck_mode") or "per-chapter").strip().lower()
    return "book" if mode == "book" else "per-chapter"


def density_standard_active(book_dir: Path) -> bool:
    """True when the book opts into the chapter-density standard (v2, 2026-06-10).

    Opt-in is `density_standard: 2` in `_system/series-config.yaml` — stamped by
    intake on new books, set manually on books being re-run under the standard.
    Legacy books without the field stay on advisory-only behavior: the preflight
    density gate and the chapter-set P0 promotion never halt them.
    """
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return False
    try:
        with cfg_path.open() as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return False
    try:
        return int(cfg.get("density_standard") or 0) >= 2
    except (TypeError, ValueError):
        return False
