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


def test_islamic_scholarly_defaults_to_source_only_faithful(tmp_path: Path) -> None:
    """The Islamic default is the ARTICULATION route (Asif, 2026-07-31).

    Was `author_companion` until then. With `narrative_frame` enforcing who
    narrates, the companion re-voice had little left to do the frame does not
    already do, while the fluency pass is the one written for de-calque work and
    the only route with a written contract (REQ-BA-*).
    """
    bd = _book(tmp_path, "content_profile: islamic_scholarly\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_SOURCE_ONLY
    assert book_voice(bd) == BOOK_VOICE_FAITHFUL


def test_undeclared_profile_follows_the_shared_resolver_to_islamic(tmp_path: Path) -> None:
    """An absent `content_profile` reads as Islamic — deliberately, not by accident.

    `_content_profile.resolve_content_profile` is the ONE answer to "what is this
    book", and it has always treated an undeclared profile as `islamic_scholarly`
    so that books predating the field kept working. The knob default asks that
    resolver rather than reading the key itself, so this case cannot drift away
    from every other profile-gated behaviour in the pipeline.
    """
    bd = _book(tmp_path, "series:\n  enable_book_branch: true\n")
    assert book_voice(bd) == BOOK_VOICE_FAITHFUL


def test_empty_config_defaults_to_faithful(tmp_path: Path) -> None:
    bd = _book(tmp_path, "\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_SOURCE_ONLY
    assert book_voice(bd) == BOOK_VOICE_FAITHFUL


@pytest.mark.parametrize("profile", ["fiction", "technical", "consumer_explainer", "general_nonfiction"])
def test_non_islamic_profiles_keep_the_companion_default(tmp_path: Path, profile: str) -> None:
    """The 2026-07-31 change is scoped to Islamic content and nothing else."""
    bd = _book(tmp_path / profile, f"content_profile: {profile}\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_SOURCE_ONLY
    assert book_voice(bd) == BOOK_VOICE_AUTHOR_COMPANION


def test_translation_edition_wins_over_the_profile(tmp_path: Path) -> None:
    """Mode is checked before profile, so the two Mukhtasar volumes are untouched.

    They declare `deliverable_mode: translation_edition` AND are Islamic; the mode
    branch must keep returning `none` for augmentation, not the profile's
    `source_only`, or a published edition would silently gain an augment pass.
    """
    bd = _book(tmp_path, "content_profile: islamic_scholarly\ndeliverable_mode: translation_edition\n")
    assert book_augmentation(bd) == BOOK_AUGMENTATION_NONE
    assert book_voice(bd) == BOOK_VOICE_FAITHFUL


def test_an_islamic_book_can_still_ask_for_the_companion_voice(tmp_path: Path) -> None:
    """An explicit knob always beats the default map — that is the whole point of pinning."""
    bd = _book(tmp_path, "content_profile: islamic_scholarly\nbook_voice: author_companion\n")
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
        # EVERY book defaults to human-curated figures (2026-07-31): no image
        # reaches the PDF except by hand in the Book Composer. A translation
        # edition used to fall through to "pipeline" and auto-inject.
        "visuals": "manual_only",
        # The narrative frame is a SOURCE property, resolved independently of
        # every knob above — choosing a translation edition does not choose a
        # narrator. With no content_profile declared, the conservative default.
        "narrative_frame": "external_narrator",
        "narrator_subject": "",
        # Autonomy is opt-in per book. Absent means manual — every gate still
        # waits for --resume, exactly as it did before levels existed.
        "autonomy": "manual",
    }


# ─── enable_book_branch: the meta.yml flag, and the shape trap ──────────────
from _pipeline_flags import book_branch_enabled  # noqa: E402


def _meta_book(tmp_path: Path, meta: str) -> Path:
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True, exist_ok=True)
    (bd / "meta.yml").write_text(meta, encoding="utf-8")
    return bd


def test_the_flag_is_read_from_a_series_mapping(tmp_path: Path) -> None:
    bd = _meta_book(tmp_path, "series:\n  enable_book_branch: true\n")
    assert book_branch_enabled(bd) is True


def test_an_absent_flag_leaves_the_lane_off(tmp_path: Path) -> None:
    bd = _meta_book(tmp_path, "series:\n  enable_knowledge_augmenter: true\n")
    assert book_branch_enabled(bd) is False


def test_a_series_that_is_a_TITLE_STRING_answers_instead_of_crashing(tmp_path: Path) -> None:
    # The trap. `series` is a config mapping in most books but the series TITLE
    # in all six asaas-al-taveel volumes. The old accessor,
    # `data.get("series", {}).get(...)`, raises AttributeError on a string and
    # was swallowed by a bare `except` — indistinguishable from "flag absent",
    # so those volumes could never enable the lane whatever their meta.yml said.
    bd = _meta_book(tmp_path, "series: Asas al-Taweel\n")
    assert book_branch_enabled(bd) is False


def test_a_missing_meta_leaves_the_lane_off(tmp_path: Path) -> None:
    bd = tmp_path / "nothing"
    (bd / "_system").mkdir(parents=True)
    assert book_branch_enabled(bd) is False


def test_unparseable_meta_leaves_the_lane_off(tmp_path: Path) -> None:
    bd = _meta_book(tmp_path, "series: [unclosed\n")
    assert book_branch_enabled(bd) is False


def test_the_two_callers_delegate_rather_than_re_deriving(tmp_path: Path) -> None:
    # This check existed twice, copied verbatim, and both copies carried the
    # string-shape bug. One definition, two thin delegates.
    for rel in ("phases/book_driver.py", "validate_book_ready.py"):
        text = (SCRIPT_DIR / rel).read_text(encoding="utf-8")
        assert "book_branch_enabled" in text, rel
        assert 'get("series", {})' not in text, f"{rel} re-derives the series lookup"
