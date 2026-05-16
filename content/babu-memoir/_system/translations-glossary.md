# Translations Glossary

Canonical English translations for the non-English words and phrases the memoir uses.

This file is the single source of truth. When the delta report flags a translation change in any chapter, update the entry here first, then apply the new form across every chapter in which the word appears. The form recorded here overrides everything else.

Reminder of the rule (also in voice-fingerprint and craft-techniques): single words never get a parenthetical gloss. Multi-word phrases or full sentences do. ABD is the named exception, glossed as "slave" because the meaning is the point.

Format: WORD or PHRASE | CANONICAL TRANSLATION | chapters where it appears

---

## Family Terms

| Term | Canonical Translation | Appears In |
|------|----------------------|------------|
| Baba | my father | Intro, Ch01-Man, Ch02-Love, Ch03-Marriage |
| Amma | my mother | Ch01-Man, Ch02-Love, Ch03-Marriage |
| Nana | maternal grandfather | Ch02-Love, Ch03-Marriage |
| Nani | maternal grandmother | Ch02-Love |
| Afifa Khala | Aunt Afifa | Ch02-Love, Ch03-Marriage |

## Islamic / Religious Terms

| Term | Canonical Translation | Appears In |
|------|----------------------|------------|
| Allah | God | Intro, Ch01-Man, Ch02-Love, Ch03-Marriage |
| Allah's | God's | Ch02-Love, Ch03-Marriage |
| Ali (AS) | AS — peace be upon him | Ch01-Man, Ch02-Love, Ch03-Marriage (first use in each chapter only) |
| ayah | verse | Ch02-Love |
| abd | servant/devotee | Ch02-Love |
| halal | permitted | Ch02-Love |
| haram | forbidden | Ch02-Love |
| majlis (Moharram) | a Shia Islamic commemorative gathering | Ch02-Love |
| nikah | Islamic marriage contract | Ch03-Marriage |

## Cultural / Other Terms

| Term | Canonical Translation | Appears In |
|------|----------------------|------------|
| Dr. Sahab | Doctor, sir | Ch02-Love |
| biryani | a spiced rice dish | Ch03-Marriage |

---

## Podcast Pronunciation Lexicon

Phonetic spellings used by the `/podcast` skill when generating NotebookLM-ready output. These are pronunciation-friendly transcriptions — the podcast removes non-Latin script entirely and uses these spellings so text-to-speech produces consistent audio across episodes.

The podcast skill reads this section on every run, projects only the terms that appear in a given source into that source's `03-pronunciation.md` guide, and proposes new terms via the staging file `06-library-proposals.md` (never edits this file directly). To apply proposals: `/podcast apply <source-slug>`.

Memoir chapters continue to use the canonical translations in the sections above. This section is podcast-specific.

Format: PHONETIC | MEANING | MEMOIR EQUIVALENT (if any) | LANGUAGE FAMILY

| Phonetic | Meaning | Memoir equivalent | Language family |
|---|---|---|---|
| Allaah | God | Allah | Arabic |
| Muhammad | the Prophet of Islam | — | Arabic |
| Ali | the first Imam in Shia/Ismaili tradition | Ali (AS) | Arabic |
| Sharee-ah | revealed law / outward path of practice | — | Arabic |
| Ta'wil | esoteric / disciplined interpretation | — | Arabic |
| Wilaayah | spiritual authority, guardianship | — | Arabic |
| Hujjah | the proof; a senior rank in the Ismaili da'wah | — | Arabic |
| Natiq | the speaking Prophet who reveals outward law | — | Arabic |
| Da'i | summoner; teacher in the Ismaili da'wah | — | Arabic |
| Imam | spiritual guide; in Shia tradition, the rightful leader of the community | — | Arabic |
| Shaykh | elder, teacher, master | — | Arabic |

### Devotional phrases

| Phonetic | Meaning |
|---|---|
| Innaa lil-laahi wa innaa ilayhi raaji-oon | Indeed we belong to God, and to Him we return |

### Bootstrap note

The eleven terms above plus the devotional phrase were seeded on 2026-05-16 when the `/podcast` skill was first installed. Subsequent additions arrive via podcast runs and the `/podcast apply` command, each carrying a provenance footer naming the source work and section.

---

## Revision History

Changes to this glossary are made automatically when the delta script detects that Asif
has changed a parenthetical translation in any chapter. The old form is struck out and
the new canonical form is recorded here with a note of which chapter the change was
detected in.

Podcast lexicon additions are committed by the `/podcast apply <slug>` command and tagged with the source-slug in the commit message.

<!-- REVISION LOG — append entries below this line -->

2026-05-16 — Podcast Pronunciation Lexicon section seeded with 11 terms + 1 devotional phrase as part of `/podcast` skill installation. No memoir chapter content affected.
