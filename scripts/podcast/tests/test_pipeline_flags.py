from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _pipeline_flags import (
    BOOK_AUGMENTATION_NONE,
    BOOK_AUGMENTATION_SOURCE_ONLY,
    BOOK_VOICE_AUTHOR_COMPANION,
    BOOK_VOICE_FAITHFUL,
    book_augmentation,
    book_knobs,
    book_voice,
)


def _book(tmp_path: Path, config: str) -> Path:
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "series-config.yaml").write_text(config, encoding="utf-8")
    return bd


# ─── Default knob map ───────────────────────────────────────────────────────
def test_translation_edition_defaults_to_none_faithful(tmp_path: Path) -> None:
    bd = _book(tmp_path, "deliverable_mode: translation_edition\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_NONE
    assert book_voice(bd) == BOOK_VOICE_FAITHFUL


def test_legacy_companion_defaults_to_source_only_author_companion(tmp_path: Path) -> None:
    bd = _book(tmp_path, "series:\n  enable_book_branch: true\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_SOURCE_ONLY
    assert book_voice(bd) == BOOK_VOICE_AUTHOR_COMPANION


def test_empty_config_defaults_to_companion(tmp_path: Path) -> None:
    bd = _book(tmp_path, "\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_SOURCE_ONLY
    assert book_voice(bd) == BOOK_VOICE_AUTHOR_COMPANION


# ─── Explicit knobs override the default map ────────────────────────────────
def test_explicit_knobs_override_translation_default(tmp_path: Path) -> None:
    bd = _book(
        tmp_path,
        "deliverable_mode: translation_edition\nbook_augmentation: source_only\nbook_voice: author_companion\n",
    )
    assert book_augmentation(bd) == BOOK_AUGMENTATION_SOURCE_ONLY
    assert book_voice(bd) == BOOK_VOICE_AUTHOR_COMPANION


def test_an_unrecognised_knob_value_is_refused_not_defaulted(tmp_path: Path) -> None:
    """A typo must not choose the book for us.

    This used to fall back to the default map, which is the silent behaviour change
    it was meant to prevent: `book_voice: fathful` on a book with no
    `deliverable_mode` defaults to `author_companion`, so a translation edition
    received a full author re-voice — hours of model time and a different book at
    the end of it, with nothing anywhere saying why.
    """
    bd = _book(tmp_path, "deliverable_mode: translation_edition\nbook_augmentation: bogus\n")
    with pytest.raises(ValueError, match="book_augmentation"):
        book_augmentation(bd)

    bd2 = _book(tmp_path / "second", "book_voice: fathful\n")
    with pytest.raises(ValueError, match="book_voice"):
        book_voice(bd2)


def test_book_knobs_bundle(tmp_path: Path) -> None:
    bd = _book(tmp_path, "deliverable_mode: translation_edition\n")
    knobs = book_knobs(bd)
    assert knobs == {
        "augmentation": BOOK_AUGMENTATION_NONE,
        "voice": BOOK_VOICE_FAITHFUL,
        # A translation edition keeps the historical pipeline-visual behaviour;
        # only the companion path defaults to human-curated figures.
        "visuals": "pipeline",
        # The narrative frame is a SOURCE property, resolved independently of
        # every knob above — choosing a translation edition does not choose a
        # narrator. With no content_profile declared, the conservative default.
        "narrative_frame": "external_narrator",
        "narrator_subject": "",
        # Autonomy is opt-in per book. Absent means manual — every gate still
        # waits for --resume, exactly as it did before levels existed.
        "autonomy": "manual",
    }
