# Shared Arabic / Islamic Pronunciation Reference

Canonical, skill-agnostic reference for every Arabic or Islamic term that appears
anywhere in this repository. Read by the `/journal` and `/podcast` skills, by the
`podcast-challenger` agent, and by any future skill that touches Arabic content.

This folder is the **single source of truth**. Per-book pronunciation overrides
(e.g., `content/podcast/<book>/_system/pronunciation.md`) and per-source lexicons
(e.g., `_system/source/text/_lexicon.md`) supplement this reference but never
contradict it. When they conflict, this folder wins.

---

## What lives here

| File | Purpose | Mandatory readers |
|------|---------|-------------------|
| [01-tts-pronunciation-key.md](01-tts-pronunciation-key.md) | Engineering rules for shaping any Arabic respelling so text-to-speech engines (NotebookLM, ElevenLabs, OpenAI TTS) read it correctly. Long-vowel rule, gemination, liaison, ASCII-only, anti-patterns. | podcast (every run), podcast-challenger, anyone authoring a `00-framing.md` pronunciation block |
| [02-quran-letter-phonetics.md](02-quran-letter-phonetics.md) | Classical-Arabic letter-by-letter phonetic guide. The 28 Arabic letters named in Latin (alif, baa, taa…) with their classical sound, recommended ASCII respelling, and engine-reliability notes. Underpins every respelling decision. | podcast (every run before authoring or refining a chapter that contains Arabic), podcast-challenger Loop C1 |
| [03-arabic-english-manifest.md](03-arabic-english-manifest.md) | Latin-only Arabic → English → TTS-tuned phonetic lookup. Format: `aoozu \| I seek protection \| a-OO-thoo`. No Arabic script. Covers honorifics, devotional phrases, Quranic openers, theology, ritual, lifecycle, and named figures. | podcast (every authoring or refinement pass), journal (when an Arabic term first appears in a chapter and needs an English gloss decision per `translations-glossary.md`) |
| [04-common-term-substitutions.md](04-common-term-substitutions.md) | Substitution policy: when to translate common Arabic terms into English instead of keeping the Arabic. Context-driven: `nafs` becomes "soul" / "lower soul" / "irascible soul" based on what surrounds it; `shaytan` becomes "Satan"; etc. | podcast (every authoring pass, before declaring a chapter ready), journal (every refinement pass that touches Arabic vocabulary) |
| [05-name-alias-policy.md](05-name-alias-policy.md) | Long-name → short-alias policy. Full name on first chapter-occurrence; short alias (Ghazali, Haatim, Shaqeeq, Junaid) thereafter. ~30 canonical aliases for Imams, Sufi tradition, hadith collectors, Ismaili figures. Reduces listener fatigue from repeated long honorific-laden names. | podcast (every chapter authoring + framing pass — chapter applies the alias, framing tells NotebookLM hosts the same rule), journal (when a new long name first appears in memoir) |

---

## Hard rule: no Arabic script in shared docs

Files in this folder use **Latin / ASCII only**. Arabic letters are identified
by their canonical name in Latin (alif, baa, taa, thaa, jeem, Haa, khaa…). This
keeps the reference usable by every TTS engine and by any human reader without
Arabic literacy. Per-book lexicons (`_lexicon.md`) may carry Arabic script for
verification, but this folder does not.

---

## How skills wire to this folder

### Podcast skill (every run)

1. Read all four files in this folder as part of the Session Start Protocol
   (`skills-staging/podcast/SKILL.md` §1) BEFORE reading the book-specific
   pronunciation file.
2. During Phase 0c (Arabic Phonetic Transcription Pass), every respelling
   decision must conform to `01-tts-pronunciation-key.md` rules and use
   `02-quran-letter-phonetics.md` for letter-by-letter calls.
3. During Phase 0d/0e (chapter design + enrichment), any Arabic term added must
   be checked against `03-arabic-english-manifest.md`. If the manifest carries a
   phonetic, use it verbatim. If absent, draft one per the key, then add it to
   both the book's `_phonetics.md` AND propose it for inclusion here.
4. During the Phase 4 quality gate, `04-common-term-substitutions.md` is the
   authority: any Arabic term in the substitution table that has NOT been
   replaced with its English form (or kept Arabic with a documented justification
   in the framing's pronunciation hooks) is a P1 finding.

### Journal skill (every refinement that touches Arabic)

1. When the delta report (`auto_delta.py`) flags an Arabic translation change in
   any chapter, the entry in `content/babu-memoir/_system/translations-glossary.md`
   is updated first. The shared manifest here is the authority for the canonical
   English gloss.
2. The journal skill applies `04-common-term-substitutions.md` policy when
   deciding whether a single Arabic term in a memoir chapter should be glossed,
   substituted, or left untouched. Memoir voice is the override — Asif's
   established choices in chapters that have shipped are protected.

### Podcast-challenger agent

1. Loop C1 (phonetic coverage) cross-checks every Arabic term in a chapter
   against `03-arabic-english-manifest.md` first, then against the book's
   `_lexicon.md`. A term that appears in neither is a P0 finding.
2. Loop C2 (lexicon parity) verifies that any phonetic introduced in a chapter
   matches the manifest spelling exactly. A drift (e.g., `Sunnah` →
   `SOON-nuh` in one chapter, `Sun-nuh` in another) is a P1 finding.
3. A new Loop C4 check verifies `04-common-term-substitutions.md` compliance:
   any flagged term still in Arabic form without a documented justification is
   a P1 finding.

---

## Adding a new term

When a chapter or memoir entry introduces an Arabic term that is not in this
folder:

1. **Draft the phonetic** per `01-tts-pronunciation-key.md` and the relevant
   letter sounds in `02-quran-letter-phonetics.md`.
2. **Decide context** — does the term belong in honorifics, devotional phrases,
   theology, ritual, lifecycle, or named figures? Add it to the matching table
   in `03-arabic-english-manifest.md`.
3. **Decide substitution** — does the term have a clean English equivalent that
   should usually replace it? If yes, add it to `04-common-term-substitutions.md`
   with the context guidance.
4. **Cascade**:
   - Podcast: also add to the book's `_phonetics.md` and `_lexicon.md`.
   - Journal: also add to `content/babu-memoir/_system/translations-glossary.md`
     in the matching section.
5. **Commit** the manifest update in the same commit as the chapter or memoir
   change that introduced the term, so future readers see the lineage.

---

## Provenance

Seeded on 2026-05-17 from the root-level `arabic-islamic-pronunciation-key.md`
(which has been removed) plus prior content in
`content/babu-memoir/_system/translations-glossary.md` (Podcast Pronunciation
Lexicon section) and `content/podcast/ayyuhal-walad/_system/pronunciation.md`.
