"""Deterministic narrative-frame guards.

Every case here is drawn from a defect that actually shipped on
`the-master-and-the-disciple` (2026-07-19/20) and passed every gate in place at
the time. The negative cases matter as much as the positive ones: these checks
revert prose when they fire, so a false positive costs a chapter.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _narrative import (  # noqa: E402
    arabic_retention_findings,
    enumeration_findings,
    frame_findings,
    frame_prompt_directive,
    lecture_voice_counts,
    lecture_voice_findings,
    narrative_person_findings,
    speech_tag_findings,
)
from _rules import narrative_frame_for, narrative_person_for  # noqa: E402


# ─── Frame registry ─────────────────────────────────────────────────────────
def test_declared_frame_wins_over_profile_default() -> None:
    assert narrative_frame_for("islamic_scholarly", "first_person_author") == "first_person_author"


def test_profile_default_applies_when_undeclared() -> None:
    assert narrative_frame_for("islamic_scholarly", None) == "transmitted_report"
    assert narrative_frame_for("fiction", None) == "external_narrator"


def test_unknown_declared_frame_falls_back_rather_than_raising() -> None:
    # A typo in one book's config must not halt the pipeline.
    assert narrative_frame_for("islamic_scholarly", "nonsense") == "transmitted_report"


def test_person_resolves_from_frame() -> None:
    assert narrative_person_for("transmitted_report") == "third"
    assert narrative_person_for("participant_narrator") == "first"


# ─── Narrative person ───────────────────────────────────────────────────────
# The live chapter-4 defect: the disciple became the narrator.
_CH4_DEFECT = "My Master opened the matter at the root of it all — the first of the causes."
# The live chapter-5 defect: the Master became the narrator, in the same book.
_CH5_DEFECT = "The boy came to me and said: This world holds a great multitude."
_CH5_DEFECT_B = "And I said to him: As for this world, no one will ever truly reproach it."


def test_participant_narration_fails_a_transmitted_report_frame() -> None:
    for text in (_CH4_DEFECT, _CH5_DEFECT, _CH5_DEFECT_B):
        findings = narrative_person_findings(text, "transmitted_report")
        assert findings, text
        assert "transmitted_report" in findings[0]


def test_source_narration_passes_the_same_frame() -> None:
    clean = (
        "The Master began with the first of the causes of the manifest order.\n\n"
        "The boy said: This world holds a great multitude.\n\n"
        "The scholar said: As for this world, no one will ever truly reproach it."
    )
    assert narrative_person_findings(clean, "transmitted_report") == []


def test_first_person_inside_quoted_speech_is_not_flagged() -> None:
    # First person belongs here under EVERY frame — a character speaking. If this
    # ever fires, the check reverts legitimate prose across the whole corpus.
    speech = (
        'The scholar said: "I say to you that the world was set up upon seven things, '
        'and I have told you of them already, and my own teacher told me the same."'
    )
    assert narrative_person_findings(speech, "transmitted_report") == []


def test_first_person_frame_flags_third_person_self_report() -> None:
    text = "Salih said to him that the matter was otherwise."
    findings = narrative_person_findings(text, "participant_narrator", narrator_subject="Salih")
    assert findings and "third person" in findings[0]


def test_first_person_frame_passes_its_own_narration() -> None:
    text = "My father stood over me, and what passed between us was as raw as anything here."
    assert narrative_person_findings(text, "participant_narrator", narrator_subject="Salih") == []


# ─── Speech attribution ─────────────────────────────────────────────────────
def test_inserted_speech_tag_is_flagged() -> None:
    # The chapter-8 P0, reduced: the source paragraph carried no tag.
    base = (
        'I said to him: "The originators were three."\n\n"This is the nation of the Magi, clinging to its rebellion."'
    )
    candidate = 'I said to him: "The originators were three."\n\n"This is the nation of the Magi," he said, "clinging to its rebellion."'
    findings = speech_tag_findings(base, candidate)
    assert findings and "cut into a quotation" in findings[0]


def test_closing_a_quotation_before_a_head_tag_is_not_interior() -> None:
    # A head attribution in the NEXT paragraph is an ordinary attribution, however
    # the paragraph before it ended. Matching across the blank line made adding
    # quotation marks to an unquoted chapter look like 58 inserted interior tags.
    base = "The Master said: As for this world, no one reproaches it.\n\nThe boy said: You have spoken truly."
    candidate = 'The Master said: "As for this world, no one reproaches it."\n\nThe boy said: "You have spoken truly."'
    assert speech_tag_findings(base, candidate) == []


def test_rewording_a_tag_is_allowed() -> None:
    base = "The scholar said: As for this world, no one reproaches it."
    candidate = "The scholar replied: As for this world, no one truly reproaches it."
    assert speech_tag_findings(base, candidate) == []


# ─── Trailing tag vs interrupting tag (2026-07-31) ──────────────────────────
# The check could not tell them apart, because the pattern stopped at the verb.
# A source in the head-tag style has a base count of zero, so the first natural
# de-calque of a line of dialogue tripped a P0 and reverted the window: on
# `ayyuhal-walad` that killed chapter 1, then killed chapter 3 twice and aborted
# a 27-minute compose. The rule was always the INTERRUPTING shape — the pattern
# now requires the quotation to re-open after the tag, which is what "interior"
# has meant in this module's own comments since it was written.
def test_a_trailing_tag_is_not_an_inserted_tag() -> None:
    """`"Y," X replied.` is ordinary English — and is what REQ-BA-020 asks for.

    Turning `X replied: "Y"` into `"Y," X replied.` moves no attribution: the
    speaker is named, the tag is terminated, nothing follows it to re-point.
    """
    base = 'Shaykh Hatim replied: "Thirty-three years!"'
    for candidate in (
        '"Thirty-three years," Hatim replied.',
        '"Thirty-three years," he replied.',
        '"Thirty-three years," he replied. Then he fell silent.',
    ):
        assert speech_tag_findings(base, candidate) == [], candidate


def test_a_trailing_tag_before_another_speaker_is_not_flagged() -> None:
    """A whole exchange de-calqued at once must not read as an insertion."""
    base = 'Shaykh Shafeeq asked: "How long have you been with me?"\n\nHatim replied: "Thirty-three years."'
    candidate = '"How long have you been with me?" Shafeeq asked.\n\n"Thirty-three years," Hatim replied. Shafeeq said: "Bravo."'
    assert speech_tag_findings(base, candidate) == []


def test_a_full_stop_ends_the_attribution() -> None:
    """`X said. "..."` is two sentences with a terminated tag, not an interruption.

    Deliberately narrower than `X said, "..."`: the comma form cuts a tag INTO one
    utterance, which is the shape that re-points speech. This one names its speaker
    and closes. The semantic BK-N2 pass still reads it against the source — this
    check is only the cheap seed.
    """
    base = '"I have gained eight benefits from you."'
    candidate = '"I have gained eight benefits," he replied. "That is enough for me."'
    assert speech_tag_findings(base, candidate) == []


@pytest.mark.parametrize(
    "candidate",
    [
        '"This is the nation of the Magi," he said, "clinging to its rebellion."',
        '"This is the nation of the Magi," he said: "clinging to its rebellion."',
        '"This is the nation of the Magi," he said "clinging to its rebellion."',
        '"This is the nation of the Magi," Salih said, "clinging to its rebellion."',
        "“This is the nation of the Magi,” he said, “clinging to its rebellion.”",
    ],
)
def test_the_interrupting_shape_is_still_caught(candidate: str) -> None:
    """Narrowing must not blind the gate to the defect it exists for."""
    base = '"This is the nation of the Magi, clinging to its rebellion."'
    findings = speech_tag_findings(base, candidate)
    assert findings and "cut into a quotation" in findings[0], candidate


# ─── Arabic retention ───────────────────────────────────────────────────────
def test_transliterating_arabic_away_is_flagged() -> None:
    base = "From them is derived كُنْ, which is two letters, and فَيَكُونُ, which is five."
    candidate = "From them is derived kun, which is two letters, and fa-yakun, which is five."
    findings = arabic_retention_findings(base, candidate)
    assert findings and "Arabic script dropped" in findings[0]


def test_transliteration_beside_the_script_passes() -> None:
    base = "From them is derived كُنْ, which is two letters, and فَيَكُونُ, which is five."
    candidate = "From them is derived كُنْ (kun), which is two letters, and فَيَكُونُ (fa-yakun), which is five."
    assert arabic_retention_findings(base, candidate) == []


def test_swapping_one_quotation_for_another_is_caught_though_the_count_holds() -> None:
    base = "He said لَيْسَ كَمِثْلِهِ شَيْءٌ and then كُنْ فَيَكُونُ."
    candidate = "He said لَيْسَ كَمِثْلِهِ شَيْءٌ and then إِنَّا لِلَّهِ."
    assert arabic_retention_findings(base, candidate)  # count is 2 either way


# ─── Supplied diacritics ────────────────────────────────────────────────────
# The two tests that lived here pinned `supplied_diacritics_findings`, deleted on
# 2026-07-29 with the rule it enforced: Arabic in these editions always carries
# its vowel marks now, so "the rewrite added marks the source lacked" describes
# the intended outcome. What replaces the guard is the marks-only gate in
# `_vowelling.rejection_reason` (pinned by tests/test_vowelling.py against shared
# fixtures) plus `arabic_retention_findings` below, which still refuses a rewrite
# that moves a LETTER.
def test_vowelling_a_run_is_not_a_retention_failure() -> None:
    """Marking a run must stay invisible to the guard that survived."""
    base = "من حيث يشاء الله وما شاء الله كان"
    vowelled = "مِنْ حَيْثُ يَشَاءُ اللهُ وَمَا شَاءَ اللهُ كَانَ"
    assert arabic_retention_findings(base, vowelled) == []


# ─── Enumeration ────────────────────────────────────────────────────────────
_ENUMERATED = (
    "(a) The heavens are seven.\n\n"
    "(b) The earths are seven.\n\n"
    "(c) The light has seven days.\n\n"
    "(d) The darkness is the seven nights.\n\n"
    "(e) The vessels are seven.\n\n"
    "(f) The blessings rest upon seven."
)


def test_dissolving_an_enumeration_into_prose_is_flagged() -> None:
    dissolved = (
        "The heavens, to begin with, are seven. The earths, likewise, are seven. "
        "The light has seven days. The darkness is the seven nights. The vessels, "
        "too, are seven, and the blessings rest upon seven."
    )
    findings = enumeration_findings(_ENUMERATED, dissolved)
    assert findings and "enumeration lost" in findings[0]


def test_preserved_enumeration_passes() -> None:
    assert enumeration_findings(_ENUMERATED, _ENUMERATED) == []


def test_unenumerated_source_is_not_policed() -> None:
    prose = "The heavens are seven and the earths are seven."
    assert enumeration_findings(prose, prose) == []


# Eight consecutive numbered SECTIONS, each a full prose paragraph — the shape
# of a scholarly transcription's per-paragraph numbering, not an argument list.
_SECTION_PARA = (
    "the Master said to them that the matter to which he had called them was "
    "the one he honored, and he asked that Allah be with His servants and "
    "complete it for them and ennoble those who answered Him in every affair "
    "of theirs, first and last, outward and inward, early and late alike."
)
_SECTION_NUMBERED = "\n\n".join(f"({n}) {_SECTION_PARA}" for n in range(1, 9))


def test_section_numbering_apparatus_is_exempt() -> None:
    translated = "\n\n".join(_SECTION_PARA for _ in range(8))
    assert enumeration_findings(_SECTION_NUMBERED, translated) == []


def test_mid_book_section_run_starting_above_one_is_exempt() -> None:
    # A chapter slice is a WINDOW into the numbered source: its run starts
    # above 1 ("(3) (4) (5)"), which no argument list ever does. This is the
    # exact shape that blocked the RCA-001 recovery compose on bk-01.
    base = "\n\n".join(f"({n}) {_SECTION_PARA}" for n in (3, 4, 5))
    translated = "\n\n".join(_SECTION_PARA for _ in range(3))
    assert enumeration_findings(base, translated) == []


def test_short_numbered_list_starting_at_one_stays_policed() -> None:
    base = "1. Rely upon Allah.\n\n2. Speak with a considered ruling.\n\n3. Do not fall into anger."
    dissolved = "Rely upon Allah, speak with a considered ruling, and do not fall into anger."
    findings = enumeration_findings(base, dissolved)
    assert findings and "enumeration lost" in findings[0]


def test_real_list_inside_numbered_sections_stays_policed() -> None:
    base = _SECTION_NUMBERED + "\n\n" + _ENUMERATED
    dissolved = "\n\n".join(_SECTION_PARA for _ in range(8)) + (
        "\n\nThe heavens are seven, the earths are seven, the light has seven "
        "days, the darkness is the seven nights, the vessels are seven, and "
        "the blessings rest upon seven."
    )
    findings = enumeration_findings(base, dissolved)
    assert findings and "enumeration lost" in findings[0]


# ─── Combined wiring ────────────────────────────────────────────────────────
def test_frame_findings_composes_every_guard() -> None:
    base = "The scholar said: From them is derived كُنْ.\n\n(a) One.\n\n(b) Two.\n\n(c) Three."
    candidate = "The boy came to me and said: From them is derived kun. One, two, and three."
    findings = frame_findings(base, candidate, frame="transmitted_report")
    joined = " | ".join(findings)
    assert "first-person narration" in joined
    assert "Arabic script dropped" in joined
    assert "enumeration lost" in joined


def test_frame_findings_clean_on_a_faithful_rewrite() -> None:
    base = "The scholar said: From them is derived كُنْ, which is two letters."
    candidate = "The scholar said: From them is derived كُنْ (kun), which is two letters."
    assert frame_findings(base, candidate, frame="transmitted_report") == []


def test_rewording_an_opening_attribution_is_not_an_insertion() -> None:
    # A de-calque pass legitimately reshapes an opening attribution. Gating the
    # whole-chapter tag count treated that as an insertion and reverted a real
    # chapter on the first live run. Only tags cut INTO a quotation are gated.
    base = "Certain groups came to a Master among them and spoke as men speak."
    candidate = "Certain groups came to a Master among them and said to him as men speak."
    assert speech_tag_findings(base, candidate) == []


# ─── Precision regressions (found by sweeping the real base, 2026-07-20) ─────
def test_vocative_address_inside_speech_is_not_narration() -> None:
    # "my son" spoken BY the Master TO the boy. Six of the eight live base
    # chapters open a continuation paragraph this way; a bare "my <relation>"
    # match reverted them all. Only subject position is a frame violation.
    for vocative in (
        "My son, you have heard the charge of the Shaykh, and there is no guidance but his words.",
        "my father, I have not disobeyed you in what you taught me.",
    ):
        assert narrative_person_findings(vocative, "transmitted_report") == [], vocative


def test_relationship_in_subject_position_is_still_narration() -> None:
    for subject in (
        "My father stood over me, and what passed between us was raw.",
        "My Master opened the matter at the root of it all.",
    ):
        assert narrative_person_findings(subject, "transmitted_report"), subject


def test_real_base_chapters_are_self_consistent() -> None:
    """Every shipped faithful chapter, compared against itself, must be clean.

    This is the guard that caught both precision bugs above. If it ever fails,
    the checks have started reverting correct prose across the whole corpus.
    """
    chunks = sorted(
        Path(__file__)
        .resolve()
        .parents[3]
        .glob("content/*/the-master-and-the-disciple/book/_chunks/translation/bk-*.md")
    )
    chunks = [c for c in chunks if "-part-" not in c.stem]
    if not chunks:  # the sample book is not present in every checkout
        return
    for chunk in chunks:
        text = chunk.read_text(encoding="utf-8")
        assert frame_findings(text, text, frame="transmitted_report") == [], chunk.stem


# ─── Lecture voice (R-NO-LECTURE-VOICE, 2026-08-03) ─────────────────────────
# `al-anwaar-al-lateefah` is transcribed from spoken lectures. Converting it to a
# transmitted report removed every "I" and left the lecturer intact, because the
# tells are not first person and no person check can see them.
LECTURE = (
    "Hold the word in mind for a moment, because the image inside it matters. "
    "Do not pass over that phrase lightly, and you should expect nothing else "
    "from these pages. Consider the grammar, because it sharpens the claim."
)
BOOK = (
    "The word carries an image worth holding. The phrase is not to be passed over "
    "lightly, and the book does no more than it promises. The grammar sharpens the claim."
)


def test_lecture_voice_counts_separate_address_from_stage_directions() -> None:
    address, stage = lecture_voice_counts(LECTURE)
    assert address == 1  # "you"
    assert stage == 3  # Hold / Do not pass / Consider
    assert lecture_voice_counts(BOOK) == (0, 0)


def test_articulating_a_lecture_into_a_book_is_never_flagged() -> None:
    """The direction this check exists to permit."""
    assert lecture_voice_findings(LECTURE, BOOK, frame="transmitted_report") == []


def test_adding_lecture_voice_to_a_third_person_book_is_flagged() -> None:
    findings = lecture_voice_findings(BOOK, LECTURE, frame="transmitted_report")
    assert len(findings) == 2
    assert any("addresses the reader" in f for f in findings)
    assert any("stage directions" in f for f in findings)


def test_first_person_frames_are_silent() -> None:
    """*Ayyuhal Walad* is a letter to a disciple — the address IS the form."""
    for frame in ("first_person_author", "participant_narrator"):
        assert lecture_voice_findings(BOOK, LECTURE, frame=frame) == [], frame


def test_quoted_speech_and_block_quotations_are_not_narration() -> None:
    """A character saying "consider what you have said" is dialogue, not a lecture."""
    dialogue = (
        'The Master replied: "Consider what you have said, and hold your judgment. '
        'Do not accept a thing by mere imitation, or your certainty will fail you."'
    )
    assert lecture_voice_counts(dialogue) == (0, 0)
    quoted_verse = "> “And remember your Lord when you forget.”\n\nThe verse closes the section."
    assert lecture_voice_counts(quoted_verse) == (0, 0)


def test_the_directive_states_the_rule_the_gate_enforces() -> None:
    """A gate whose prompt never asks for the behaviour just reverts every window."""
    directive = frame_prompt_directive("transmitted_report")
    assert "NO LECTURE VOICE" in directive
    for forbidden in ("consider", "notice", "imagine"):
        assert forbidden in directive
    # And it must not leak into the frames where addressing the reader is correct.
    assert "NO LECTURE VOICE" not in frame_prompt_directive("first_person_author")


def test_lecture_voice_joins_the_frame_findings_wiring() -> None:
    assert any("lecture voice" in f for f in frame_findings(BOOK, LECTURE, frame="transmitted_report"))
