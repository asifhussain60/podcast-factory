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

An explicit ``book_augmentation`` / ``book_voice`` / ``book_visuals`` key in
``series-config.yaml`` overrides the default map. An UNRECOGNISED value RAISES
``ValueError`` (2026-07-21). It used to fall back to the default map, which was
the silent behaviour change that rule was meant to prevent: ``book_voice:
fathful`` on a book with no ``deliverable_mode`` defaults to ``author_companion``,
so a translation edition received a full author re-voice — hours of model time
and a different book at the end of it, with nothing saying why. Callers that must
not abort on a bad config catch the ValueError where they can report it; see
``phases/book_driver``.

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

VISUALS_KEY = "book_visuals"
BOOK_VISUALS_MANUAL_ONLY = "manual_only"
BOOK_VISUALS_PIPELINE = "pipeline"
_VALID_VISUALS = frozenset({BOOK_VISUALS_MANUAL_ONLY, BOOK_VISUALS_PIPELINE})

# Narrative frame — a property of the SOURCE, not of the delivery route. Kept
# beside the knobs because it is read from the same file, but deliberately NOT
# part of the knob-default map: no product choice may change who narrates.
NARRATIVE_FRAME_KEY = "narrative_frame"
NARRATOR_SUBJECT_KEY = "narrator_subject"
AUTONOMY_KEY = "autonomy"

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


def _reject_unknown(key: str, value: str, valid: frozenset[str]) -> None:
    """A knob value nobody recognises is a typo, and typos here change the product.

    ``book_voice: fathful`` used to fall through to the default map, so a
    translation edition quietly received a full author re-voice — hours of model
    time, a different book at the end of it, and nothing anywhere saying why. Each
    knob is two values wide; if a value is not one of them the config is wrong and
    the run should stop rather than guess which book was intended.
    """
    raise ValueError(
        f"_system/series-config.yaml: {key}: {value!r} is not a recognised value "
        f"({', '.join(sorted(valid))}). Fix the config — a knob typo silently "
        "changes which book the pipeline produces."
    )


def book_augmentation(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """``none`` | ``source_only`` — the augmentation knob (see module docstring)."""
    if cfg is None:
        cfg = _read_series_config(book_dir)
    explicit = str(cfg.get(AUGMENTATION_KEY) or "").strip().lower()
    if explicit and explicit not in _VALID_AUGMENTATION:
        _reject_unknown(AUGMENTATION_KEY, explicit, _VALID_AUGMENTATION)
    if explicit:
        return explicit
    return _default_knobs(cfg)[0]


def book_voice(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """``faithful`` | ``author_companion`` — the voice knob (see module docstring)."""
    if cfg is None:
        cfg = _read_series_config(book_dir)
    explicit = str(cfg.get(VOICE_KEY) or "").strip().lower()
    if explicit and explicit not in _VALID_VOICE:
        _reject_unknown(VOICE_KEY, explicit, _VALID_VOICE)
    if explicit:
        return explicit
    return _default_knobs(cfg)[1]


def book_visuals(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """``manual_only`` | ``pipeline`` — who may put a figure in the reading edition.

    ``manual_only`` means the pipeline never generates or places a visual: no
    illustration pass, no slide import, and nothing but the human's curated
    ``book/visual-layout.json`` (written by the Book Composer) can put a figure on
    a page. ``pipeline`` is the historical behaviour, where the illustrate and
    slide-import phases run and produce candidate assets.

    The default follows the augmentation knob: a companion edition
    (``source_only``) is a text deliverable whose visuals are curated by hand, so
    it defaults to ``manual_only``; every other book keeps ``pipeline`` so this
    change cannot silently alter an existing lane. An explicit key wins either way.
    """
    if cfg is None:
        cfg = _read_series_config(book_dir)
    explicit = str(cfg.get(VISUALS_KEY) or "").strip().lower()
    # Strict for the same reason its two siblings are: this value decides whether
    # the illustrate and slide-import phases run at all, so a typo here silently
    # produces candidate assets behind the curator's back, or silently stops
    # producing them.
    if explicit and explicit not in _VALID_VISUALS:
        _reject_unknown(VISUALS_KEY, explicit, _VALID_VISUALS)
    if explicit:
        return explicit
    if book_augmentation(book_dir, cfg) == BOOK_AUGMENTATION_SOURCE_ONLY:
        return BOOK_VISUALS_MANUAL_ONLY
    return BOOK_VISUALS_PIPELINE


def narrative_frame(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """Who narrates this book — see ``_rules.NARRATIVE_FRAMES``.

    Unlike the knobs above, this is NOT a product decision: it is a property of
    the SOURCE text, so it is deliberately independent of ``book_voice`` and
    ``deliverable_mode``. A book that opens as an anonymous transmitted report
    stays third-person whether it ships as a translation edition or a companion
    reading edition. An undeclared frame falls back to the content profile's
    default, which is conservative on purpose (see ``_rules``).
    """
    if cfg is None:
        cfg = _read_series_config(book_dir)
    from _rules import narrative_frame_for

    declared = str(cfg.get(NARRATIVE_FRAME_KEY) or "").strip().lower()
    profile = str(cfg.get("content_profile") or "").strip().lower()
    return narrative_frame_for(profile, declared or None)


def narrator_subject(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """The named narrator, required only by first-person participant frames."""
    if cfg is None:
        cfg = _read_series_config(book_dir)
    return str(cfg.get(NARRATOR_SUBJECT_KEY) or "").strip()


def autonomy(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """How far a started run drives before it stops — see ``_rules.AUTONOMY_LEVELS``.

    Absent or misspelled resolves to ``manual``, i.e. the behaviour every book had
    before this knob existed. Opting a book into autonomy is an act; failing to
    spell it correctly must never be one.
    """
    if cfg is None:
        cfg = _read_series_config(book_dir)
    from _autonomy import autonomy_level_for

    return autonomy_level_for(str(cfg.get(AUTONOMY_KEY) or "").strip().lower() or None)


def book_knobs(book_dir: Path) -> dict[str, Any]:
    """Convenience bundle: every resolved knob read in one config load."""
    cfg = _read_series_config(book_dir)
    return {
        "augmentation": book_augmentation(book_dir, cfg),
        "voice": book_voice(book_dir, cfg),
        "visuals": book_visuals(book_dir, cfg),
        "narrative_frame": narrative_frame(book_dir, cfg),
        "narrator_subject": narrator_subject(book_dir, cfg),
        "autonomy": autonomy(book_dir, cfg),
    }
