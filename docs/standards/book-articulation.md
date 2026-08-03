# Book Articulation Standard (REQ-BA-*)

Canonical rule text for **articulation** — taking a stiff, word-for-word,
Arabic-calqued English chapter and rewriting it so it reads like a professionally
published book, without changing what it says.

**This is the DEFAULT acceptable standard for the reading edition of an Islamic
scholarly book (Asif, 2026-07-31), not an opt-in.** It used to apply only to
books declaring `deliverable_mode: translation_edition`; anything else defaulted
to `book_voice: author_companion`, a re-voice with far more latitude and no
written contract at all. `_pipeline_flags._default_knobs` now returns
`{source_only, faithful}` for `content_profile: islamic_scholarly`, so
`0book-fluency` — the pass this standard governs — runs by default. The reference
edition is `the-master-and-the-disciple`. A book that genuinely wants the
companion re-voice must now say so explicitly.

It is the contract behind **both** rewrite routes: `0book-fluency`
(`scripts/podcast/_book_voice.py` / `_book_voice_prompts.py`), which runs
automatically at compose time over every book on the faithful voice, and the Book
Composer's **Rearticulate** action (`scripts/podcast/rearticulate_chapter.py`),
which reruns one chapter on demand. Both call the same prompt builder
(`_book_voice_prompts.py::_articulation_prompt`) so the automatic pass and the
on-demand tool cannot drift apart. Also referenced by the `book-articulation`
skill and the `book-rearticulator` agent.

**Verified, not merely instructed.** `book-challenger` check **BK-P8**
(articulation conformance) judges a composed book against the rules below that no
other `BK-*` check covers — REQ-BA-010, -020, -050, -080, -100, -140 — on every
book whose `book_voice` resolves to `faithful`. The remaining rules are already
gated elsewhere and are NOT re-checked by BK-P8; see the check's own scope note.
Cite findings by `REQ-BA-NNN`; never re-copy rule text elsewhere.

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
- **REQ-BA-125 — A book addresses nobody (R-NO-LECTURE-VOICE).** Under a
  third-person frame the narration never turns to the reader and never directs
  an audience. Out: "you"/"your" in narration, stage-direction imperatives
  (consider, notice, note, observe, recall, remember, imagine, picture, hold,
  look, mark, listen), and commentary about the discourse itself ("this is the
  heart of it", "before we go on", "as we shall see"). Every such move is
  RECAST into exposition — "Hold that frame, and step now inside it" becomes
  "Within that frame stands…" — never deleted, because it carries a thought.
  UNTOUCHED inside quoted speech, verses, hadith, prayers and block
  quotations: there one person addresses another, which every frame keeps.
  Silent under a first-person frame — *Ayyuhal Walad* is a letter to a
  disciple, where the address IS the form. Instructed by
  `_narrative.frame_prompt_directive` and guarded DIFFERENTIALLY by
  `_narrative.lecture_voice_findings` (a pass may not ADD lecture voice), so a
  lecture-derived source can be improved rather than reverted wholesale.
  Added 2026-08-03: `al-anwaar-al-lateefah` is transcribed from spoken
  lectures, and converting it to a transmitted report changed every "I" while
  leaving every "Do not pass over that phrase lightly" exactly where the
  speaker put it. It passed REQ-BA-120 on every paragraph and read nothing
  like the edition printed beside it.

## Rhetorical judgment and out-of-band notes

- **REQ-BA-130 — Meaningful repetition survives; mechanical repetition may be
  condensed.** Classical Arabic repetition used for rhythm, emphasis, or
  deliberate parallelism is preserved in refined form — a passage that says "he
  obeyed where they disobeyed, preserved what they squandered, and fulfilled
  the responsibility they neglected" keeps that structure. Repetition that
  reads as redundant only because it was carried over literally, with no
  rhetorical work left for it to do in English, may be condensed — but only
  where doing so drops no idea and weakens no emphasis the source intends.
- **REQ-BA-140 — Divine-pronoun capitalization follows the passage.** If the
  text already capitalizes pronouns referring to God ("He", "His", "Him"),
  keep doing so consistently; if it uses lowercase, keep that instead. Never
  introduce a new capitalization convention partway through a passage.
- **REQ-BA-150 — Dialogue-tag wording may vary; attribution may not.** A
  repetitive tag's wording may be varied ("he replied", "he asked" for "the
  boy said") as long as the speaker stays unambiguous. This does not loosen
  REQ-BA-040: no tag is added, removed, or re-pointed to a different speaker.
- **REQ-BA-160 — Ambiguity, comprehension risk, and terminology drift are
  reported out of band, never written into the prose.** If a passage is
  genuinely ambiguous, may confuse a modern reader without help this pass is
  not authorized to add, or uses a term worth standardizing book-wide, do not
  insert a bracketed note, a parenthetical aside, or explanatory context into
  the chapter itself (REQ-BA-030 already forbids added content — this is not
  an exception to it). Instead, append ONE trailing block after the chapter
  prose, in exactly this form, and nothing else:

  ```
  ===ARTICULATION-NOTES===
  AMBIGUITY: <what is unclear, in one sentence>
  COMPREHENSION: <what a modern reader may stumble on, in one sentence>
  TERMINOLOGY: <term> — <what rendering should be standardized>
  ===END-NOTES===
  ```

  Omit the block entirely when there is nothing to report. The pipeline strips
  this block before anything reaches `book.md` (`_book_voice.py`
  `_extract_articulation_notes`) and files each line into that chapter's pass
  record for human review — never auto-applied, never inline. A block that
  survives extraction is a defect, not a feature: it reverts the window
  (`revoice_gates`). Comprehension gaps that genuinely need a fix stay
  `book-publication-reviewer`'s job (its comprehension-bridges loop), not this
  pass's.
