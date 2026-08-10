# Rearticulation audit — "The Creator of the Thing and the No-Thing" (chapter key: `the creator of the thing and the no-thing`)

**Date:** 2026-08-10
**Verdict:** KEPT (second attempt succeeded; the prior attempt's revert — the most severe of the three, content loss AND scripture loss together — is resolved)

## Baseline (pre-run, machine-base translation still sitting in book.md)

- Word count: 3,049 (script recount over the chapter's lines) / 3,039 (engine's own base count for the window)
- Arabic-script runs (engine counter, regex over the chapter body): 26 — including الْأَوَّل (al-awwal), الْحَقُّ (al-haqq), الشِّرْك (al-shirk/associationism), the Quranic verse شَهِدَ ٱللَّهُ أَنَّهُۥ لَآ إِلَهَ إِلَّا هُوَ, and the terms إِبْدَاع, اَلْوُجُودُ, تَأْوِيل, تَشْبِه
- Speech-tag pattern: one paragraph per turn — "We say:", "The author of al-Mahsul said:", "And his saying:", each followed by its own paragraph, across eight numbered "Section of the Tenth Chapter" subheadings
- Enumeration: eight sections (First through Eighth Section of the Tenth Chapter), unchanged in count and order
- Signature images: religion as "a single person who gathers his parts together" with the ranked scholars standing in for "the senses that perceive things"; the three-way logical exhaustion (prior to / with / posterior to the intellect) used to disprove the "no-thing"; the pronoun هو (He) as the one expression that names God "without affirming an attribute or a plurality"; the associationism charge built from a close reading of "and no thing with Him"
- Prior failure (most severe of the three reverted chapters): `fluency-19: abridged re-voice (1174<1828 words)`, `P1 large length drop: 3046->1174 words (38% of source — possible content loss)`, `Arabic runs dropped (13<26)`, `Arabic script dropped (8 run(s))` — specifically الْأَوَّل (al-awwal), الْحَقُّ (al-haqq), and السلام (al-salam) among the eight dropped runs. book.md going into this run still held the raw, un-rearticulated machine-base translation (`base_words == output_words == 3046` in the fluency report — the tell that no adapted rewrite had ever been kept).

## Checked before running: no duplication defect

- Split the chapter into its 51 paragraphs and diffed them for repeats (the failure mode found in chapter 1). The only repeats are the eight short speech tags themselves ("We say:", "The author of al-Mahsul said:", "And his saying:") recurring naturally across eight sections of dialectical response — no duplicated argument paragraph, no repeated block. The chapter's density (a tight, technical proof against three exhaustive cases, argued twice more from different angles across sections 3-7) is real content, not padding or duplication — so the first attempt's 62% cut was content loss, not a legitimate compression of redundant source.

## What the second run did

- Ran `rearticulate_chapter.py kitab-al-riyad "the creator of the thing and the no-thing" --json`
- Result: `status: adapted`, `gates: []`, `windows: 1`, `windows_kept: 1`
- Output word count: 2,971 (about 98% of the 3,039-word base — a normal tightening, nowhere near the 60%-abridgement threshold that reverted the first attempt)
- Sidecar `_system/composer-edits.json` recorded the edit for chapter key `the creator of the thing and the no-thing`, `base_fingerprint: d7cbb2d81e766e5c`, `saved_at: 2026-08-10T15:16:25.552278+00:00`, matching the live `book/book.md` content exactly

## Judged against REQ-BA-*

- **REQ-BA-010/020 (lucid modern English):** Confirmed. Calqued, Arabic-mirroring constructions are gone — "when he exerted himself, and strove, and discharged the right of..." became "worked tirelessly in service of..."; "It is impossible that it be prior to the intellect, for..." became "It cannot be prior to the intellect. The intellect is..." — short declarative sentences replacing the source's long subordinate chains, without softening any step of the logical argument.
- **REQ-BA-040 (speech and quotation integrity):** Confirmed. Every "We say:", "The author of al-Mahsul said:", and "And his saying:" tag survived, same speaker, same boundary, same paragraph structure. The Quranic verse شَهِدَ ٱللَّهُ أَنَّهُۥ لَآ إِلَهَ إِلَّا هُوَ and its translation ("Allah bears witness that there is no god but He") are byte-for-byte identical to the source, still set off as a block quotation, still followed by the same close reading of why the text says "but He" rather than "but Allah."
- **REQ-BA-050 (signature images intact):** Confirmed. "Religion, through them, resembles a single person who holds all his parts together: they are to religion as the senses are to that person, perceiving things on its behalf" — the sense-organ image survives as an image, not flattened into an abstraction about "cooperation." The three-way logical exhaustion (prior to / simultaneous with / posterior to the intellect) that structures the chapter's central proof is intact step for step.
- **REQ-BA-060/127 (Arabic script untouched, none dropped):** Confirmed and re-verified independently — recounted Arabic runs in the new book.md text directly: **26 runs in, 26 runs out**, an exact match to the pre-run baseline, including all three runs the first attempt lost (الْأَوَّل, الْحَقُّ) — السلام itself does not occur inside this chapter's own line range (it belongs to the adjoining chapter 20, which is where the first attempt's window boundary apparently bled the loss from). This is the gate that reverted the first attempt twice over; it now passes clean by direct recount, not just by the engine's self-report.
- **REQ-BA-070 (no variant spellings/terms):** Confirmed. "The thing," "the no-thing," "the willed-thing (al-mashi')," "associationism," "the true existence," "origination" all render exactly as elsewhere in the book — no new spelling or synonym substitution introduced for any of these load-bearing technical terms.
- **REQ-BA-100 (never shorter than a rewording, one paragraph per speech turn):** Confirmed. 2,971 of 3,039 words (98%) — a rewording, not an abridgement. Paragraph-per-turn structure under each of the eight "Section of the Tenth Chapter" headings is unchanged.

## Where this leaves chapter 19

`book/book.md` now holds the rearticulated prose — modern, lucid English carrying the full eight-section proof against the "no-thing," with the same argument density as the source rather than the 62%-cut summary the first attempt produced — and `_system/composer-edits.json` carries the durable sidecar entry (`saved_at: 2026-08-10T15:16:25+00:00`) that a future re-compose will replay rather than regenerate. `_system/book-fluency-report.json` was re-stamped by the run (`status: "composer-edit"`, superseding the old `"reverted"` entry), so the live gate state now correctly reflects a clean pass. Two non-blocking `editorial_queries`/`comprehension_flags` were filed out of band per REQ-BA-160 (an ambiguous causal connective in the Fifth Section's discussion of the willed-thing, and a comprehension note on the divine-speech/ordinary-speech distinction in the Sixth Section) — these are informational notes for human review, not REQ-BA failures, and required no prose changes.
