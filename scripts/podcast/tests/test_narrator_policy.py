"""Who may be quoted when a book is augmented.

Asif: "Do not augment with quotations from Abu Bakar, Umar, Uthman, Ayesha.
Only quotes of the Ahl-e-Bait, Imam Ali, Ismail bin Muhammad, and their
followers are approved."

These tests pin the precise scope: an ATTRIBUTION is blocked, a mere MENTION of
the same name in doctrinal prose is not — the corpus has a real example of the
latter (a historical passage naming Abu Bakr and Umar as adversaries) that must
survive untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _narrator_policy import (  # noqa: E402
    atom_narrator,
    disallowed_narrator,
    filter_atoms,
)


def quote_atom(speaker: str, text: str = "text") -> dict:
    return {"id": f"quote:{speaker}", "type": "quote", "body": {"speaker": speaker, "text_en": text}}


def hadith_atom(narrator: str | None, text: str = "text") -> dict:
    return {"id": "hadith:x", "type": "hadith", "body": {"narrator": narrator, "text_en": text}}


# ─── name matching ────────────────────────────────────────────────────────────
def test_each_named_companion_is_caught_by_common_spelling_variants() -> None:
    assert disallowed_narrator("Abu Bakr") == "Abu Bakr"
    assert disallowed_narrator("Abu Bakar") == "Abu Bakr"
    assert disallowed_narrator("Umar ibn al-Khattab") == "Umar"
    assert disallowed_narrator("Janab Umar") == "Umar"
    assert disallowed_narrator("Omar") == "Umar"
    assert disallowed_narrator("Uthman ibn Affan") == "Uthman"
    assert disallowed_narrator("Usman") == "Uthman"
    assert disallowed_narrator("Aisha") == "Aisha"
    assert disallowed_narrator("Ayesha") == "Aisha"
    assert disallowed_narrator("A'isha bint Abi Bakr") == "Aisha"


def test_approved_speakers_are_never_flagged() -> None:
    for name in (
        "Imam Ali",
        "Mawla Ali",
        "Sayyidna Ali",
        "The Commander of the Faithful",
        "Imam al-Sadiq",
        "Mawlana Ja'far al-Sadiq",
        "Sayyidna Isma'il",
        "Ghazali",
        "The Prophet Muhammad",
        "Allah",
        "The scholar",
        "The disciple",
        "Salih",
    ):
        assert disallowed_narrator(name) is None, name


def test_a_bare_substring_does_not_false_positive() -> None:
    """The rule matches whole names, not letters that merely appear inside another."""
    assert disallowed_narrator("Umarah al-Yamani") is None
    assert disallowed_narrator("Maryam") is None


def test_empty_or_missing_speaker_is_never_flagged() -> None:
    assert disallowed_narrator("") is None
    assert disallowed_narrator(None) is None


# ─── attribution field extraction ────────────────────────────────────────────
def test_quote_atoms_are_read_from_speaker() -> None:
    assert atom_narrator(quote_atom("Umar ibn al-Khattab")) == "Umar ibn al-Khattab"


def test_hadith_atoms_are_read_from_narrator() -> None:
    assert atom_narrator(hadith_atom("Imam Ali")) == "Imam Ali"


def test_a_null_narrator_is_the_empty_string_not_a_crash() -> None:
    assert atom_narrator(hadith_atom(None)) == ""


def test_doctrine_and_quran_atoms_carry_no_attribution_field() -> None:
    """A passage mentioning a name in prose is not a QUOTATION from that person."""
    doctrine = {"id": "doctrine:x", "type": "doctrine", "body": {"text_en": "Abu Bakr and Umar and Ali ibn Abi Talib"}}
    assert atom_narrator(doctrine) == ""
    assert disallowed_narrator(atom_narrator(doctrine)) is None


# ─── the filter, on the real shape of failure found in this corpus ──────────
def test_the_three_umar_attributed_quotes_actually_in_this_corpus_are_excluded() -> None:
    """The real hits found when this policy was built: two Umar-attributed
    quotes praising Ali, one Umar bay'ah quote. Attribution rules on WHO is
    quoted, not on whether the content itself is friendly to Ali."""
    atoms = [
        quote_atom("Janab Umar", "I give bay'ah."),
        quote_atom("Umar ibn al-Khattab", "Had it not been for 'Ali, 'Umar would have perished."),
        quote_atom("Imam Ali", "an approved quote"),
    ]
    kept, excluded = filter_atoms(atoms)
    assert [a["body"]["speaker"] for a in kept] == ["Imam Ali"]
    assert {e["matched"] for e in excluded} == {"Umar"}


def test_a_doctrinal_passage_merely_naming_the_four_companions_is_kept() -> None:
    """Real atom this corpus carries: a historical passage grouping Abu Bakr and
    Umar with Ali as figures of the era. Not a quotation FROM them — must survive."""
    doctrine = {
        "id": "doctrine:wisdom:1:20:6",
        "type": "doctrine",
        "body": {"text_en": "adversaries against Abu Bakr and Umar and Ali ibn Abi Talib"},
    }
    kept, excluded = filter_atoms([doctrine])
    assert kept == [doctrine]
    assert excluded == []


def test_hadith_with_no_recorded_narrator_is_kept() -> None:
    atoms = [hadith_atom(None, "a hadith with no narrator on file")]
    kept, excluded = filter_atoms(atoms)
    assert kept == atoms
    assert excluded == []


def test_excluded_entries_carry_enough_to_explain_themselves() -> None:
    _, excluded = filter_atoms([quote_atom("Aisha")])
    assert excluded[0]["matched"] == "Aisha"
    assert excluded[0]["speaker"] == "Aisha"
    assert excluded[0]["id"]
