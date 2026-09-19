"""The span definition behind finalize gate G14 (R-ARABIC-INTEGRITY).

`arabic_integrity` fingerprints every Arabic span before the first model touches a book and re-checks after each
pass; ANY span that changed, vanished or appeared without sanction fails the run. Everything depends on three small
pure functions agreeing about what a "span" is, so they are pinned here: a change to one silently changes what the
gate can see.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import arabic_integrity as ai  # noqa: E402

VERSE = "وَمِمَّا رَزَقْنَاهُمْ يُنفِقُونَ"
BISMILLAH = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"


def test_a_multi_word_verse_is_one_span_not_one_per_word():
    assert ai.extract_spans(f"He recited {VERSE} and was silent.") == [VERSE]


def test_two_separate_quotations_are_two_spans():
    spans = ai.extract_spans(f"First {VERSE}. Later {BISMILLAH}.")
    assert spans == [VERSE, BISMILLAH]


def test_english_only_text_has_no_spans():
    assert ai.extract_spans("No Arabic here at all.") == []


def test_a_lone_arabic_letter_is_not_a_protected_span():
    assert ai.extract_spans("the letter ھ is illustrative") == []


def test_arabic_punctuation_glues_words_into_one_span_and_english_ends_it():
    """Pinned as it behaves: the span keeps a TRAILING Arabic semicolon (the comment in `extract_spans` says trailing
    glue must not leak; it does). Harmless to the gate — snapshot and verify use this same definition — but it means
    a span's identity includes its closing punctuation, which is worth knowing before changing it."""
    spans = ai.extract_spans("قال، ثم سكت؛ and English")
    assert len(spans) == 1 and spans[0].startswith("قال") and "and" not in spans[0] and "English" not in spans[0]


def test_extraction_is_stable_across_an_inline_marker_wrapper():
    assert ai.extract_spans(f"⟪ar:{VERSE}⟫") == [VERSE]


def test_normalisation_is_nfc_and_ignores_directional_marks():
    decomposed = unicodedata.normalize("NFD", VERSE)
    assert ai.normalize_arabic_span(decomposed) == unicodedata.normalize("NFC", VERSE)
    assert ai.normalize_arabic_span("‏" + VERSE + "‎") == ai.normalize_arabic_span(VERSE)


def test_vowel_marks_are_part_of_a_spans_identity_but_not_of_its_skeleton():
    bare = "".join(c for c in VERSE if unicodedata.category(c) != "Mn")
    assert ai.normalize_arabic_span(VERSE) != ai.normalize_arabic_span(bare), "a re-vowelled span is a different span"
    assert ai.skeleton(VERSE) == bare, "the skeleton is the same letters with every vowel mark removed"


def test_the_hash_is_deterministic_and_distinguishes_a_changed_vowel():
    changed = VERSE.replace("َ", "ُ", 1)
    assert ai._hash(ai.normalize_arabic_span(VERSE)) == ai._hash(ai.normalize_arabic_span(VERSE))
    assert ai._hash(ai.normalize_arabic_span(VERSE)) != ai._hash(ai.normalize_arabic_span(changed))
