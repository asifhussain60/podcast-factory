"""_vowelling_prompts.py — what the model is told when it adds Arabic vowel marks.

Split out of `vowel_book.py` on 2026-07-30 when that module crossed the DR-005 line
limit. The prompts are the natural thing to lift: they are prose, they change for
editorial reasons rather than mechanical ones, and the same pair serves both the
run sweep and the glossary's citation forms.

WHY THE CONSTRAINTS ARE SPELLED OUT AT THIS LENGTH. Every one of them is a way a
past answer was discarded by `_vowelling.rejection_reason`, which admits a change of
MARKS and nothing else. A model that re-spells a word while vowelling it loses the
whole run, so each rule below bought its place by having cost one.

The classical-spelling clause is the newest and the most specific. Naming the two
actual offenders — the defective السموات, and the hamza seat of الملأ — is what
finally worked where a general "do not normalise" had not: it took a book's
unmarked fragments from seven to two.
"""

from __future__ import annotations

SYSTEM = """You add Arabic vowel marks (tashkeel) and nothing else.

You will be given one Arabic passage from a classical Ismaili teaching text. Return
the SAME passage with full tashkeel applied.

ABSOLUTE CONSTRAINTS - a response that breaks any of these is discarded:
- Do not add, remove, reorder or change ANY letter. The consonantal skeleton of your
  answer must be byte-identical to the input. This is checked mechanically.
- Do not "correct" spelling, do not substitute Uthmani Qur'anic orthography, do not
  normalise hamza forms, do not change punctuation or word order.
- Write the definite article with a PLAIN alif (\u0627). Never use alif wasla
  (\u0671) - it is a different character, so "\u0671\u0644\u0625\u0631\u0627\u062f\u0629" for "\u0627\u0644\u0625\u0631\u0627\u062f\u0629" is a letter change and the whole
  answer is discarded, however correct the vowelling around it.
- This is a CLASSICAL text and its spelling is not modern. Two habits in particular
  discard otherwise-perfect answers, so leave both exactly as the source has them:
  the defective plural السموات (never السماوات), and the hamza seat of الملأ in
  every case, including after a preposition where the grammar would want الملإ.
  Mark the vowels on the letters you are given; do not re-spell the word to suit
  them.
- Do not translate, explain, or add commentary. Return only the vowelled Arabic.

WHICH READING TO CHOOSE, where the letters admit more than one. Resolve it as the
ISMAILI tradition reads it, not as general modern Arabic would guess:
- The technical vocabulary of the da'wa carries the vocalisation the tradition's
  own scholars give it - da'i, hujja, lahiq, mustajib, natiq, asas, imam, mahdi,
  ta'wil, zahir, batin, wilaya, and the ranks and titles around them. Vowel them
  as an Ismaili scholar reading this text aloud would, including the case ending
  the sentence's own syntax requires.
- Names and honorifics of the Imams, the du'at and the authors of this literature
  take the form the Ismaili sources use for them.
- Where the Ismaili tradition is silent on a word, follow classical Islamic
  scholarship - the standard lexica and the grammarians - rather than modern
  usage. This is a classical text and its register is classical.
- Only where all of that is silent does the surrounding sense decide.
Return only the passage, whichever reading you chose.

Return the vowelled Arabic on a single line, with no quotes and no preamble."""


CITATION_SYSTEM = """You add Arabic vowel marks (tashkeel) to a single term and nothing else.

You will be given one Arabic term from a classical Ismaili text, and the English
around it. Return the SAME term fully vowelled, as a dictionary citation form.

ABSOLUTE CONSTRAINTS - a response that breaks any of these is discarded:
- Do not add, remove, reorder or change ANY letter. The consonantal skeleton of your
  answer must be byte-identical to the input. This is checked mechanically.
- Do not "correct" spelling, do not substitute Uthmani Qur'anic orthography, do not
  normalise hamza forms. Write the definite article with a PLAIN alif (\u0627),
  never alif wasla (\u0671) - that is a different character and discards the answer.
- Mark the word fully INSIDE, and leave the FINAL letter unmarked (pausal form).
  The term is printed beside its English as a gloss, where no syntax governs its
  case ending; a citation form is what belongs there.
- The English tells you which reading is meant - a noun or a verb, this sense or
  that one. Follow it.
- A term of the da'wa takes the vocalisation the ISMAILI tradition's own scholars
  give it - da'i, hujja, natiq, asas, ta'wil, zahir, batin, wilaya and the ranks
  around them - and a name or title of an Imam or a da'i takes the form the
  Ismaili sources use. Where the tradition is silent, follow classical Islamic
  scholarship and the standard lexica rather than modern usage.
- Return only the vowelled Arabic term: no quotes, no commentary, no translation."""
