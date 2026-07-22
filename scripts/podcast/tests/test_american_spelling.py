"""Coverage for _american_spelling — one spelling standard across deliverables.

The defect this guards: a model drafts one chapter with "honour" and re-voices
the next with "honor", so a single edition ships both. The pass has to be
mechanical enough to trust on every compose and narrow enough that it never
touches Arabic, a transliterated term, or a machine fence.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _american_spelling import (  # noqa: E402
    ORTHOGRAPHY,
    USAGE,
    findings,
    to_american,
)


def test_the_our_family_loses_its_u() -> None:
    assert to_american("honour, colour, favour, labour, neighbour") == ("honor, color, favor, labor, neighbor")


def test_re_endings_become_er() -> None:
    assert to_american("the centre of the theatre") == "the center of the theater"


def test_ise_endings_become_ize() -> None:
    assert to_american("realise, recognised, organising") == ("realize, recognized, organizing")


def test_doubled_l_is_reduced_and_single_l_is_doubled() -> None:
    assert to_american("travelled, marvellous, fulfil, skilful") == ("traveled, marvelous, fulfill, skillful")


def test_the_silent_e_drops_from_judgement_and_acknowledgement() -> None:
    assert to_american("judgement, acknowledgement, abridgement") == ("judgment, acknowledgment, abridgment")


def test_capitalization_is_preserved() -> None:
    """Sentence-initial and shouted forms must not be flattened to lowercase."""
    assert to_american("Honour and HONOUR and honour") == "Honor and HONOR and honor"
    assert to_american("Travelling") == "Traveling"


def test_usage_tier_can_be_switched_off_independently() -> None:
    """Orthography is mechanical; toward/towards is a word choice, so it is
    separable — turning usage off must leave it exactly as written."""
    text = "He travelled towards the centre, amongst friends."
    assert to_american(text) == "He traveled toward the center, among friends."
    assert to_american(text, usage=False) == ("He traveled towards the center, amongst friends.")


def test_a_word_that_merely_contains_a_british_form_is_untouched() -> None:
    """Whole-word only: 'greyhound' is not 'grayhound', and a transliterated
    term that happens to embed a mapped string keeps its spelling."""
    assert to_american("greyhound") == "greyhound"
    assert to_american("centreboard") == "centreboard"


def test_arabic_script_is_never_touched() -> None:
    src = "the centre of البيت المعمور and its honour"
    assert to_american(src) == "the center of البيت المعمور and its honor"


def test_transliterated_terms_survive() -> None:
    """The substitutions are ASCII and whole-word, so a transliteration cannot
    be respelled into nonsense."""
    src = "Bayt al-Mamur, al-Imam al-Natiq, duat, tawil"
    assert to_american(src) == src


def test_fenced_blocks_are_skipped() -> None:
    """Machine fences carry pipeline data, not prose — leave them byte-identical."""
    src = "The colour here.\n```\ncolour: British\n```\nAnd the colour there."
    out = to_american(src)
    assert out.splitlines()[0] == "The color here."
    assert out.splitlines()[2] == "colour: British"  # inside the fence
    assert out.splitlines()[4] == "And the color there."


def test_idempotent() -> None:
    once = to_american("honour the centre whilst travelling towards it")
    assert to_american(once) == once


def test_findings_reports_without_mutating() -> None:
    src = "honour and honour and centre"
    assert findings(src) == {"honour": 2, "centre": 1}
    assert "honour" in src  # unchanged


def test_no_table_entry_is_a_no_op_or_a_cycle() -> None:
    """A key mapping to itself would be dead weight; a value that is also a key
    would make the pass non-idempotent."""
    for table in (ORTHOGRAPHY, USAGE):
        for british, american in table.items():
            assert british != american, f"{british} maps to itself"
            assert american not in table, f"{british} -> {american} is a cycle"


def test_empty_and_none_like_input() -> None:
    assert to_american("") == ""
