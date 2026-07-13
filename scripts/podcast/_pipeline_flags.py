"""Feature-flag + knob readers for Book Pipeline v2.

Single source of truth for the ``book_pipeline_v2`` feature flag (default OFF)
and the two orthogonal book knobs — ``book_augmentation`` and ``book_voice`` —
that the unified book path reads from ``_system/series-config.yaml``.

Cohesion contract (the reason this module exists)
-------------------------------------------------
``book_pipeline_v2`` is the backbone that lets producers and consumers land in
any order without conflicting: with the flag **OFF** the pipeline reproduces
today's output byte-for-byte, and with it **ON** it exercises the new unified
path. Nothing in the legacy path may branch on these readers — they are
consumed ONLY inside code that is itself guarded by
``book_pipeline_v2_enabled(book_dir)``.

Knob-default map
----------------
The knob defaults are chosen so that flag ON + default config reproduces the
current two-route behaviour exactly:

  * ``deliverable_mode == translation_edition`` -> ``{none, faithful}``
    (the faithful translation edition — no augmentation, faithful voice)
  * legacy companion book (anything else)       -> ``{source_only, author_companion}``
    (the author-companion revoice with source-grounded enrichment)

An explicit ``book_augmentation`` / ``book_voice`` key in ``series-config.yaml``
overrides the default map. Invalid values fall back to the default map rather
than raising, so a typo can never harden into a silent behaviour change.

This module intentionally re-implements a tiny YAML reader instead of importing
``_translation_edition.read_series_config`` — that module pulls in the heavy
authoring stack at import time, and the flag readers must stay cheap enough to
call from anywhere (drivers, validators, tests) without side effects.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# ─── Flag + knob vocabulary (the ONLY place these string literals are defined) ──
FEATURE_FLAG_KEY = "book_pipeline_v2"
FEATURE_FLAG_ENV = "BOOK_PIPELINE_V2"

AUGMENTATION_KEY = "book_augmentation"
VOICE_KEY = "book_voice"

BOOK_AUGMENTATION_NONE = "none"
BOOK_AUGMENTATION_SOURCE_ONLY = "source_only"
_VALID_AUGMENTATION = frozenset({BOOK_AUGMENTATION_NONE, BOOK_AUGMENTATION_SOURCE_ONLY})

BOOK_VOICE_FAITHFUL = "faithful"
BOOK_VOICE_AUTHOR_COMPANION = "author_companion"
_VALID_VOICE = frozenset({BOOK_VOICE_FAITHFUL, BOOK_VOICE_AUTHOR_COMPANION})

_TRANSLATION_EDITION_MODE = "translation_edition"

_TRUTHY = frozenset({"1", "true", "yes", "on", "enabled"})
_FALSY = frozenset({"0", "false", "no", "off", "disabled", ""})


def _read_series_config(book_dir: Path) -> dict[str, Any]:
    """Load ``_system/series-config.yaml`` defensively (never raises)."""
    cfg_path = Path(book_dir) / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — a malformed config must never crash a reader
        return {}
    return data if isinstance(data, dict) else {}


def _coerce_bool(value: Any) -> bool | None:
    """Return True/False for a recognizable value, else None (unset/unknown)."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    token = str(value).strip().lower()
    if token in _TRUTHY:
        return True
    if token in _FALSY:
        return False
    return None


def book_pipeline_v2_enabled(book_dir: Path, cfg: dict[str, Any] | None = None) -> bool:
    """Whether the v2 unified book path is active for this book.

    Resolution order: the ``BOOK_PIPELINE_V2`` environment variable (a testing /
    CI convenience that lets both fixture books be exercised without editing each
    config) overrides the per-book ``book_pipeline_v2`` config key. Default OFF.
    """
    env_override = _coerce_bool(os.environ.get(FEATURE_FLAG_ENV))
    if env_override is not None:
        return env_override
    if cfg is None:
        cfg = _read_series_config(book_dir)
    return _coerce_bool(cfg.get(FEATURE_FLAG_KEY)) or False


def _default_knobs(cfg: dict[str, Any]) -> tuple[str, str]:
    """The zero-regression default map, keyed off the legacy route selector."""
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
    """Convenience bundle: the flag state plus both resolved knobs.

    Callers guarded by ``book_pipeline_v2_enabled`` use this to read the whole
    knob matrix in one config load.
    """
    cfg = _read_series_config(book_dir)
    return {
        "book_pipeline_v2": book_pipeline_v2_enabled(book_dir, cfg),
        "augmentation": book_augmentation(book_dir, cfg),
        "voice": book_voice(book_dir, cfg),
    }
