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


def source_language(book_dir: Path) -> str:
    """Return the book's declared source language, lowercased; 'en' by default.

    Read by `_book_voice_prompts._source_defect` to decide what the articulation
    pass is actually repairing: a translated source arrives calqued, while a book
    written in English is hard for entirely different reasons. Defaults to 'en'
    only when the field is absent AND the book declares no target language —
    a translation edition that forgot the field must not be told its Arabic
    source is already fluent English.
    """
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return "en"
    try:
        with cfg_path.open() as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return "en"
    declared = str(cfg.get("source_language") or "").strip().lower()
    if declared:
        return declared
    return "" if cfg.get("target_language") else "en"


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


def skip_podcast(book_dir: Path) -> bool:
    """True when THIS book's own series-config.yaml opts out of the podcast lane.

    `skip_podcast: true` is a PER-BOOK override, independent of the content-type
    registry's `ContentType.skip_per_chapter` (`_content_types.py`). The registry
    flag is keyed to profiles whose audio already exists and IS the deliverable
    (`islamic_session`, `audiobook`) — those also skip OCR and phonetics, because
    there is nothing to transcribe or predict the pronunciation of. This flag is
    for the opposite case: a book that still needs OCR + phonetics (the read-aloud
    narration still has to say Arabic terms correctly) but whose deliverable is
    chapters + read-aloud + slide-decks, never a two-host NotebookLM conversation.
    Deliberately does NOT touch `book_augmentation`/`book_voice` defaults in
    `_pipeline_flags.py` — those are keyed to "audio already exists", which is not
    true here; a `skip_podcast` book still gets the normal articulation/augmentation
    treatment for its reading edition.

    Asif, 2026-09-17 (isaf-al-talib): "I can see this happening again. Not all
    books should have to go down the podcast route." Defaults False — every
    existing book, with no field or an absent/falsy one, is unaffected.
    """
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return False
    try:
        with cfg_path.open() as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return False
    return bool(cfg.get("skip_podcast", False))
