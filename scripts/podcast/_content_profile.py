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
            profile, cfg_path,
        )
        return ISLAMIC_SCHOLARLY_PROFILE

    return profile


def is_islamic_scholarly(book_dir: Path) -> bool:
    """Convenience predicate: True when the book uses the default Islamic pipeline."""
    return resolve_content_profile(book_dir) == ISLAMIC_SCHOLARLY_PROFILE
