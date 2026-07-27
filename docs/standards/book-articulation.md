# Book Articulation Standard (REQ-BA-*)

Canonical rule text for **rearticulation** — taking a stiff, word-for-word,
Arabic-calqued English chapter and rewriting it so it reads like a professionally
published book, without changing what it says. This is the contract behind the
Book Composer's **Rearticulate** action (`scripts/podcast/rearticulate_chapter.py`),
the `book-articulation` skill, and the `book-rearticulator` agent. Cite findings
by `REQ-BA-NNN`; never re-copy rule text elsewhere.

Grounding: the [Library of Arabic Literature *Handbook for Editor–Translators*](https://dhjhkxawhe8q4.cloudfront.net/library-of-arabic-literature-wp/assets/20240716170340/Handbook-v5-2024-02-28.pdf)
(NYU Press, 2022 — "LAL" below), the house style of the standard scholarly series
for exactly this kind of edition, adapted to this repo's existing conventions.
Where a repo convention already exists (honorifics, American spelling, Arabic
retention, narrative frame), the repo convention wins and is cited, not restated.

## Voice and register

- **REQ-BA-010 — Modern, lucid, simple English.** The target reader is a general
  reader, not a specialist. Every sentence must be understandable on first read.
  Prefer the plain word over the ornate one when both carry the meaning (LAL's
  stated goal: "modern, lucid English translations" for "a general audience").
  Simple never means casual: the register stays dignified and bookish — no
  contractions, no marketing tone, no podcast language.
- **REQ-BA-020 — De-calque, and restructure freely.** Never preserve Arabic
  word order, pronoun chains, or rhetorical scaffolding at the cost of English
  idiom. Sentence and paragraph grammar MAY be rebuilt — split, merged,
  reordered within a paragraph — whenever the meaning is untouched. "Old,
  broken, literal translation" constructions ("and so it was that he...", "the
  most X of them in Y and the most Z of them in W" chains) are exactly what this
  pass exists to fix.
- **REQ-BA-030 — Meaning is invariant.** Every teaching, argument, example,
  named person, citation, and enumerated list survives with its content intact.
  Nothing is added: no outside facts, no modern analogies, no doctrine from
  other books, no explanatory asides not present in the source (LAL 6.2.4
  forbids even bracketed interpolations in the translation). Nothing is
  dropped, summarized, or reinterpreted.

## The protected artifacts

- **REQ-BA-040 — Speeches and quotations are artifacts.** Direct speech, Quran
  verses, hadith, poetry, prayers, and quoted sayings keep their boundaries,
  their speakers, and their content. A speech tag is never added, removed, or
  re-pointed (enforced: `_narrative.py` speech-tag findings). Inside a quote,
  wording may be de-calqued for readability, but never paraphrased so that a
  point, image, or claim inside it disappears.
- **REQ-BA-050 — Imagery survives as imagery.** Metaphors, similes, and
  parables keep their concrete images: a wellspring stays a wellspring, a
  mirage a mirage, branches bearing fruit stay branches bearing fruit. Recast
  the grammar around an image; never replace the image with an abstraction
  ("preached effectively" for "struck the mark" is the canonical violation).
- **REQ-BA-060 — Arabic script is untouchable.** Arabic-script runs are
  preserved verbatim — never romanized away, never re-vowelled, never dropped
  (repo rule: `_narrative.py` Arabic-retention + supplied-diacritics findings).
  Transliteration sits beside script, never in place of it.

## Terminology and mechanics

- **REQ-BA-070 — One rendering per term, English where English serves.** Every
  technical term is rendered the same way on every occurrence, book-wide. Where
  an accepted English word exists, use it rather than a transliteration (LAL
  6.2.10 rule 15: Merriam-Webster spelling, no diacritics — "shaykh", "mufti").
  Follow the book's established spelling of a term, never introduce a variant.
- **REQ-BA-080 — No new parenthetical transliterations.** Do not add
  "(ḥujaj)"-style glosses to the prose (LAL 6.2.10 rule 20). Glosses already
  present in the text are kept as they are.
- **REQ-BA-090 — Honorifics compact and consistent.** Use the repo's compact
  forms exactly as the surrounding text does; never spell out long English
  honorific formulas repeatedly (repo rule, mirrors LAL 6.2.6 "be consistent").
- **REQ-BA-100 — Never shorter, one paragraph per speech turn.** Output length
  stays approximately the source length — rearticulation is a rewording, never
  an abridgement (enforced: the 60% gate reverts the window). Dialogue keeps a
  new paragraph per speech turn (LAL 6.2.2). Paragraph breaks may otherwise be
  re-drawn to serve the reading.
- **REQ-BA-110 — American spelling and book punctuation.** American English
  spelling per Merriam-Webster (repo rule: `_american_spelling.py`; LAL 6.2.1),
  the serial comma, and periods/commas inside closing quotes.
- **REQ-BA-120 — The narrative frame is binding.** WHO narrates comes from
  `_system/series-config.yaml` (`narrative_frame`), never from the prose in
  front of you. Grammatical person, one narrator per book, and enumeration
  survival are enforced by `_narrative.py` and gated by `book-challenger`
  Pass 3 (BK-N1–N7). Rearticulation runs inside those gates, never around them.
