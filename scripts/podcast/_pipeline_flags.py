"""Book-knob readers for the unified book pipeline.

Single source of truth for the two orthogonal book knobs — ``book_augmentation``
and ``book_voice`` — that the unified book path reads from
``_system/series-config.yaml``.

Knob-default map
----------------
The knob defaults are chosen so that default config reproduces each deliverable's
established behaviour:

  * ``deliverable_mode == translation_edition`` -> ``{none, faithful}``
    (the faithful translation edition — no augmentation, faithful voice)
  * companion book (anything else)              -> ``{source_only, author_companion}``
    (the author-companion revoice with source-grounded enrichment)

An explicit ``book_augmentation`` / ``book_voice`` key in ``series-config.yaml``
overrides the default map. Invalid values fall back to the default map rather
than raising, so a typo can never harden into a silent behaviour change.

This module intentionally re-implements a tiny YAML reader instead of importing
``_translation_edition.read_series_config`` — that module pulls in the heavy
authoring stack at import time, and the knob readers must stay cheap enough to
call from anywhere (drivers, validators, tests) without side effects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# ─── Knob vocabulary (the ONLY place these string literals are defined) ─────────
AUGMENTATION_KEY = "book_augmentation"
VOICE_KEY = "book_voice"

BOOK_AUGMENTATION_NONE = "none"
BOOK_AUGMENTATION_SOURCE_ONLY = "source_only"
_VALID_AUGMENTATION = frozenset({BOOK_AUGMENTATION_NONE, BOOK_AUGMENTATION_SOURCE_ONLY})

BOOK_VOICE_FAITHFUL = "faithful"
BOOK_VOICE_AUTHOR_COMPANION = "author_companion"
_VALID_VOICE = frozenset({BOOK_VOICE_FAITHFUL, BOOK_VOICE_AUTHOR_COMPANION})

_TRANSLATION_EDITION_MODE = "translation_edition"


def _read_series_config(book_dir: Path) -> dict[str, Any]:
    """Load ``_system/series-config.yaml`` defensively (never raises)."""
    cfg_path = Path(book_dir) / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _default_knobs(cfg: dict[str, Any]) -> tuple[str, str]:
    """The default knob map, keyed off the deliverable mode."""
    mode = str(cfg.get("deliverable_mode") or "").strip()
    if mode == _TRANSLATION_EDITION_MODE:
        return BOOK_AUGMENTATION_NONE, BOOK_VOICE_FAITHFUL
    return BOOK_AUGMENTATION_SOURCE_ONLY, BOOK_VOICE_AUTHOR_COMPANION


def book_augmentation(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """``none`` | ``source_only`` — the augmentation knob (see module docstring)."""
    if cfg is None:
        cfg = _read_series_config(book_dir)
    explicit = str(cfg.get(AUGMENTATION_KEY) or "").strip().lower()
    if explicit in _VALID_AUGMENTATION:
        return explicit
    return _default_knobs(cfg)[0]


def book_voice(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """``faithful`` | ``author_companion`` — the voice knob (see module docstring)."""
    if cfg is None:
        cfg = _read_series_config(book_dir)
    explicit = str(cfg.get(VOICE_KEY) or "").strip().lower()
    if explicit in _VALID_VOICE:
        return explicit
    return _default_knobs(cfg)[1]


def book_knobs(book_dir: Path) -> dict[str, Any]:
    """Convenience bundle: both resolved knobs read in one config load."""
    cfg = _read_series_config(book_dir)
    return {
        "augmentation": book_augmentation(book_dir, cfg),
        "voice": book_voice(book_dir, cfg),
    }
