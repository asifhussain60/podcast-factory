#!/usr/bin/env python3
"""WHO narrates and WHETHER the narration addresses anyone are two questions.

They were one question until 2026-08-11: the lecture-voice and navigation guards
keyed off grammatical PERSON, so every first-person book was assumed to be a
letter and both guards fell silent. That is right for *Ayyuhal Walad*, where the
address to the disciple IS the form, and wrong for a lecture transcribed into a
book — the speaker is genuinely "I", and every "you" and "notice this" is the room
he was standing in.

`first_person_expository` is the frame that separates them, and the tests below
are in three groups:

  * the new frame does what it says
  * the four older frames do EXACTLY what they did before (the Ayyuhal Walad pin)
  * the prompt and the guards agree about every frame, forever

The third group is the one that matters most. A rule stated to the model but not
policed is a suggestion; a rule policed but not stated reverts every window. The
contract test walks the whole registry, so a sixth frame cannot be added with the
two halves disagreeing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _narrative import lecture_voice_findings, navigation_findings  # noqa: E402
from _narrative_prompts import frame_prompt_directive  # noqa: E402
from _rules import NARRATIVE_FRAMES, addresses_reader_for, narrative_person_for  # noqa: E402

EXPOSITORY = "first_person_expository"

#: A rewrite that turns to the reader and directs a room.
ADDRESSED = "Now consider the word, and you will see how your own heart answers it."
#: The same thought, expounded.
EXPOUNDED = "The word answers the heart that receives it."
#: Apparatus locating the prose in the source's division scheme.
NAVIGATION = "This is the fourth chapter of the first gate of the first canopy."


# ---------------------------------------------------------------------------
# The new frame
# ---------------------------------------------------------------------------


def test_the_speaker_keeps_his_i_and_loses_his_room() -> None:
    """The whole point of the frame, in one assertion pair."""
    assert narrative_person_for(EXPOSITORY) == "first"
    assert addresses_reader_for(EXPOSITORY) is False


def test_the_directive_asks_for_first_person_and_for_no_audience() -> None:
    directive = frame_prompt_directive(EXPOSITORY)
    assert "FIRST PERSON" in directive
    assert "NO LECTURE VOICE" in directive
    assert "NO NAVIGATION APPARATUS" in directive


def test_the_directive_says_which_i_stays() -> None:
    """A model told only "do not address anybody" can read that as "drop the I".
    The instruction names the distinction rather than leaving it to be inferred."""
    directive = frame_prompt_directive(EXPOSITORY).lower()
    assert "keep your own" in directive
    assert "audience" in directive


def test_a_lecture_is_told_about_its_own_division_scheme() -> None:
    """A lecture's apparatus is its sessions, not canopies and gates."""
    directive = frame_prompt_directive(EXPOSITORY)
    assert "session" in directive.lower()


def test_the_guards_are_live_under_the_new_frame() -> None:
    assert lecture_voice_findings(EXPOUNDED, ADDRESSED, frame=EXPOSITORY)
    assert navigation_findings("A book.", NAVIGATION, frame=EXPOSITORY)


def test_the_guards_are_differential_not_absolute() -> None:
    """A transcript is SATURATED with address. An absolute check would revert
    every window before the pass could remove one, so only ADDING is a finding."""
    assert lecture_voice_findings(ADDRESSED, ADDRESSED, frame=EXPOSITORY) == []
    assert lecture_voice_findings(ADDRESSED, EXPOUNDED, frame=EXPOSITORY) == []


# ---------------------------------------------------------------------------
# The pin: nothing that worked before behaves differently
# ---------------------------------------------------------------------------


def test_ayyuhal_walad_is_untouched() -> None:
    """A letter to a disciple addresses him — that is the form, not a defect.
    Stripping the second person there would leave nothing on the page."""
    assert addresses_reader_for("first_person_author") is True
    assert lecture_voice_findings(EXPOUNDED, ADDRESSED, frame="first_person_author") == []
    assert navigation_findings("A book.", NAVIGATION, frame="first_person_author") == []
    assert "NO LECTURE VOICE" not in frame_prompt_directive("first_person_author")


@pytest.mark.parametrize("frame", ["transmitted_report", "external_narrator"])
def test_the_third_person_frames_still_carry_the_guards(frame: str) -> None:
    assert addresses_reader_for(frame) is False
    assert lecture_voice_findings(EXPOUNDED, ADDRESSED, frame=frame)
    assert navigation_findings("A book.", NAVIGATION, frame=frame)
    assert "NO LECTURE VOICE" in frame_prompt_directive(frame)


def test_an_unknown_frame_still_falls_back_rather_than_raising() -> None:
    """A typo in one book's config must not halt the pipeline."""
    assert addresses_reader_for("not-a-frame") is False
    assert narrative_person_for("not-a-frame") == "third"


# ---------------------------------------------------------------------------
# The contract, across the whole registry
# ---------------------------------------------------------------------------


def test_every_frame_decides_whether_it_addresses_a_reader() -> None:
    """Not defaulted. Adding a frame must be a decision about both questions."""
    for name, spec in NARRATIVE_FRAMES.items():
        assert "addresses_reader" in spec, f"{name} does not say whether it addresses a reader"
        assert isinstance(spec["addresses_reader"], bool)


@pytest.mark.parametrize("frame", sorted(NARRATIVE_FRAMES))
def test_the_prompt_and_the_gate_agree_about_this_frame(frame: str) -> None:
    """The one invariant this split exists to protect: a frame is ASKED for the
    prose its guards will accept. Stated-but-unpoliced is a suggestion;
    policed-but-unstated reverts every window and ships the base."""
    stated = "NO LECTURE VOICE" in frame_prompt_directive(frame)
    policed = bool(lecture_voice_findings(EXPOUNDED, ADDRESSED, frame=frame))
    assert stated == policed, f"{frame}: prompt says {stated}, gate says {policed}"


@pytest.mark.parametrize("frame", sorted(NARRATIVE_FRAMES))
def test_navigation_is_stated_exactly_where_it_is_policed(frame: str) -> None:
    stated = "NO NAVIGATION APPARATUS" in frame_prompt_directive(frame)
    policed = bool(navigation_findings("A book.", NAVIGATION, frame=frame))
    assert stated == policed, f"{frame}: prompt says {stated}, gate says {policed}"


@pytest.mark.parametrize("frame", sorted(NARRATIVE_FRAMES))
def test_speech_attribution_is_binding_under_every_frame(frame: str) -> None:
    """Whatever else changes, no frame may licence re-pointing a speech tag."""
    assert "speech tag" in frame_prompt_directive(frame).lower()
