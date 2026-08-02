"""Book-knob readers for the unified book pipeline.

Single source of truth for the two orthogonal book knobs — ``book_augmentation``
and ``book_voice`` — that the unified book path reads from
``_system/series-config.yaml``.

Knob-default map
----------------
  * ``deliverable_mode == translation_edition`` -> ``{none, faithful}``
    (the faithful translation edition — no augmentation, faithful voice)
  * content_profile ``islamic_scholarly``       -> ``{source_only, faithful}``
    (the articulation route: faithful base + the REQ-BA de-calque pass, with
    source-grounded enrichment)
  * anything else                               -> ``{source_only, author_companion}``
    (the author-companion revoice with source-grounded enrichment)

The Islamic default was ``author_companion`` until 2026-07-31 (Asif). Two books
had already been moved off it by hand for the same reason, and the reason
generalises: with ``narrative_frame`` enforcing who narrates, the
author-companion prompt has little left to do that the frame does not already
fix — on ``the-master-and-the-disciple`` six of nine chapters came back 92-100%
identical to the faithful base and one byte-identical — while the fluency pass is
the one actually written for de-calque work, and the only route governed by a
written contract (``docs/standards/book-articulation.md``, REQ-BA-010..160). A
scholarly Islamic edition wants the articulated faithful translation by default;
a book that genuinely wants the companion re-voice can still say so explicitly.

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


def _default_knobs(book_dir: Path, cfg: dict[str, Any]) -> tuple[str, str]:
    """The default knob map, keyed off the deliverable mode and content profile.

    The profile is resolved through ``_content_profile.is_islamic_scholarly`` —
    the SAME resolver every other profile-gated behaviour in the pipeline uses —
    rather than read off ``cfg`` here. Reading the key directly would be a second,
    subtly different implementation of "is this an Islamic book": that resolver
    also treats an unrecognised profile as Islamic, and it is the shared answer,
    not this module's opinion, that must decide. It costs one small re-read of a
    file this module has usually just parsed; correctness is worth the read.

    Imported lazily for the reason in the module docstring — the knob readers are
    called from drivers, validators and tests, and must not pull anything heavy at
    import time. (``_content_profile`` is light, but the convention is what keeps
    it that way, and ``narrative_frame`` / ``autonomy`` below already follow it.)

    KNOWN DIVERGENCE, left deliberately: ``narrative_frame`` below reads
    ``content_profile`` straight off ``cfg``, so an ABSENT profile resolves there
    to ``external_narrator`` (no profile key -> no entry in the profile-default
    map) while it resolves HERE to Islamic. Not unified, because the frame is a
    SOURCE property and widening its default is a much larger behavioural change
    than a knob default — and no live book is affected: every book in the repo now
    declares its profile. Unify only with the frame rule's owner, not in passing.
    """
    mode = str(cfg.get("deliverable_mode") or "").strip()
    if mode == _TRANSLATION_EDITION_MODE:
        return BOOK_AUGMENTATION_NONE, BOOK_VOICE_FAITHFUL
    from _content_profile import is_islamic_scholarly

    if is_islamic_scholarly(Path(book_dir)):
        return BOOK_AUGMENTATION_SOURCE_ONLY, BOOK_VOICE_FAITHFUL
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
    return _default_knobs(book_dir, cfg)[0]


def book_voice(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """``faithful`` | ``author_companion`` — the voice knob (see module docstring)."""
    if cfg is None:
        cfg = _read_series_config(book_dir)
    explicit = str(cfg.get(VOICE_KEY) or "").strip().lower()
    if explicit and explicit not in _VALID_VOICE:
        _reject_unknown(VOICE_KEY, explicit, _VALID_VOICE)
    if explicit:
        return explicit
    return _default_knobs(book_dir, cfg)[1]


def book_visuals(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """``manual_only`` | ``pipeline`` — who may put a figure in the reading edition.

    ``manual_only`` means the pipeline never generates or places a visual: no
    illustration pass, no slide import, and nothing but the human's curated
    ``book/visual-layout.json`` (written by the Book Composer) can put a figure on
    a page. ``pipeline`` is the historical behaviour, where the illustrate and
    slide-import phases run and produce candidate assets.

    ``manual_only`` is the DEFAULT for every book (2026-07-31, Asif): no image
    reaches the PDF except by his hand in the Book Composer. Slide-deck PROMPTS
    are still authored — those are a NotebookLM deliverable and never touch the
    reading edition. The default used to follow the augmentation knob, which left
    translation editions on ``pipeline``, auto-injecting diagrams and imported
    NotebookLM decks into the PDF and halting the book lane until those decks were
    dropped. An explicit ``pipeline`` still opts a book back in.
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
    return BOOK_VISUALS_MANUAL_ONLY


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


BOOK_BRANCH_KEY = "enable_book_branch"


def book_branch_enabled(book_dir: Path) -> bool:
    """Is the reading-edition lane switched on for this book?

    Unlike every other knob this one lives in ``meta.yml`` under ``series:``, not
    in ``series-config.yaml`` — kept here anyway so there is ONE definition of how
    to read it. There used to be two, copied verbatim into ``phases/book_driver``
    and ``validate_book_ready``, and both were wrong the same way.

    ``series`` is overloaded across the corpus: in most books it is a config
    MAPPING (``series: {enable_book_branch: true}``), but in all six
    ``asaas-al-taveel`` volumes it is the series TITLE, a plain string. The old
    accessor was ``data.get("series", {}).get(...)``, which raises
    ``AttributeError`` on a string and was swallowed by a bare ``except`` — so
    those volumes could never enable the lane no matter what anyone wrote in their
    meta.yml, and the failure was indistinguishable from the flag being absent.
    Read the mapping shape when it IS a mapping, and answer False for the title
    shape rather than crashing on it.

    A translation edition is always enabled — the reading edition IS its
    deliverable, so there is no flag to forget.
    """
    book_dir = Path(book_dir)
    try:
        from _translation_edition import is_translation_edition

        if is_translation_edition(book_dir):
            return True
    except Exception:
        pass
    meta = book_dir / "meta.yml"
    if not meta.exists():
        return False
    try:
        data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
    except Exception:
        return False
    series = data.get("series") if isinstance(data, dict) else None
    if not isinstance(series, dict):
        return False
    return bool(series.get(BOOK_BRANCH_KEY, False))


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
