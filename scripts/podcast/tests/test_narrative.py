"""Deterministic narrative-frame guards.

Every case here is drawn from a defect that actually shipped on
`the-master-and-the-disciple` (2026-07-19/20) and passed every gate in place at
the time. The negative cases matter as much as the positive ones: these checks
revert prose when they fire, so a false positive costs a chapter.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _narrative import (  # noqa: E402
    arabic_retention_findings,
    enumeration_findings,
    frame_findings,
    narrative_person_findings,
    speech_tag_findings,
    supplied_diacritics_findings,
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
def test_vowelling_an_unvowelled_source_run_is_flagged() -> None:
    base = "من حيث يشاء الله"
    candidate = "مِنْ حَيْثُ يَشَاءُ اللهُ"
    findings = supplied_diacritics_findings(base, candidate)
    assert findings and "diacritics supplied" in findings[0]


def test_carrying_source_vowelling_through_is_allowed() -> None:
    base = "كُنْ فَيَكُونُ"
    assert supplied_diacritics_findings(base, base) == []


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


def test_repeated_run_vowelled_elsewhere_is_not_a_supplied_diacritic() -> None:
    # `الله` appears bare in prose and vowelled in a scripture block in the same
    # chapter. Keeping only the last source form made a chapter compared against
    # ITSELF report fabricated vowelling.
    base = "He said الله in the prose.\n\n> وَبَانَ اللهُ في الآية\n\nand الله again."
    assert supplied_diacritics_findings(base, base) == []


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
