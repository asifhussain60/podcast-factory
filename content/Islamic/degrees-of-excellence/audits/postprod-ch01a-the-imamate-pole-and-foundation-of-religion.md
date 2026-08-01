---
postprod_version: 1.0
episode: EP01-the-imamate-pole-and-foundation-of-religion
chapter_ref: ch01a-the-imamate-pole-and-foundation-of-religion
archetype: scholarly-deep-dive
content_profile: islamic_scholarly / deep_dive / extended / traditional
verdict: BLOCKED
p0_count: 1
p1_count: 5
p2_count: 4
duration_min: 28.0
duration_target_min: 50-60
audited: 2026-08-01
---

# Postprod Audit — EP01-the-imamate-pole-and-foundation-of-religion

## Pairing
Audio `m4a/ch01a-the-imamate-pole-and-foundation-of-religion.m4a` (28.0 min) paired to `chapters/ch01a-the-imamate-pole-and-foundation-of-religion.txt` by exact stem match.
Transcript `m4a/transcripts/ch01a-the-imamate-pole-and-foundation-of-religion.transcript.txt` (5039 words), mirrored at `transcripts/EP01-the-imamate-pole-and-foundation-of-religion.transcript.txt`.
Confidence: exact. No inference required, no ambiguity.

## What held

The three central tensions the framing demanded are all surfaced by name — "the imam before the messenger," "a necessity conceded, then contested," "two witnesses, one verdict." The author's order is followed exactly. Every Quran reference the framing licensed appears (19:54, 2:124, 2:282, 41:53) and **no reference outside that list is invented**. Name discipline holds for the hard cases: Ja'far al-Sadiq is "the sixth imam," Rumi is "a poet," the first imam rotates correctly through "the father of imams" / "the commander of the faithful," and the reigning imam is never named. The spine is delivered three times. The closing question lands as written.

## Findings

### PR-PC-01 (P0) — "imamate" is never pronounced stably
Twelve of the thirteen times the book's central term is spoken it comes back garbled: `imit` (7), `emma` (2), `emmit`, `emmet`, `imminent`. The glossary sets `audio_phonetic: i-maa-mate`. Both spine deliveries are affected: *"The imit is the pole and foundation of religion, the office that never lapses while the messenger comes and goes."* The ASR resolves the bare word "imam" correctly throughout, which is what makes a transcription artifact unlikely as the whole explanation.
**Verify by ear before acting** — spot-check 00:04:30 and the closing spine.

### PR-PI-01 (P1) — Cold open, against an explicit "No cold open"
The episode begins *"I want you to imagine just for a moment that you are asked to build a house from the ground up."* No greeting, no book title, no author until roughly ninety seconds in. The framing's opening directive reads: "Open with a brief, warm welcome — name the book ... and its author, and preview ... No cold open." This is also the shape `FAUX_PROFUNDITY_OPENING_PATTERNS` exists to catch (the stock regex misses it only because of the inserted "just").

### PR-PE-02 (P1) — Six governing images where the framing allowed exactly three
Permitted: the pole/millstone, the religious stars, the two witnesses in court. All three are present — and so are the house-and-roof cold open, the cathedral with its buried course of stones, the ocean current and the wave (this one is in the source), and a counterfeit-currency riff that runs to *"No criminal enterprise spends time forging a $3 bill"* and *"minting fake coins out of lead."* The source supports the counterfeit idea in one sentence; the currency-crime elaboration is host-supplied modern idiom.

### PR-PC-03 (P1) — ta'wil rendered two different ways inside one episode
*"it is combined with its tie wheel. Its hidden inner interpretation."* Later the same episode says *"the tawil, the inner spiritual reality"* correctly. The framing sets `ta'wil: taa-WEEL`. A doctrinal term delivered inconsistently within a single episode.

### PR-PJ-01b (P1) — Framing scaffolding spoken aloud
*"And that establishes our very first governing image"* and *"our second governing image, the religious stars."* "Governing image" is the CUSTOMIZE prompt's own section label, not critical vocabulary the hosts would reach for. Every framing closes with "Do not read this prompt aloud."

### PR-PJ-05 (P1) — Self-referential and awe-performing register
*"Our mission in this exploration is to..."* (`DEEP_DIVE_SELF_REFERENCE_PATTERNS`), *"It's a massive paradigm shift,"* *"What is so fascinating here,"* *"It is a breathtaking way to begin a treatise,"* *"the truth becomes blindingly obvious."* The archetype's anti-pattern catalogue names "dropping the scholarly register mid-episode" explicitly; *"Oh man, that would be a complete nightmare"* and *"way bigger than that"* are the same failure.

### PR-PD-01 (P2) — Possible inversion of the reigning imam's anonymity
*"the author's reliance on the reigning master, the imam of the age, whom he names, but whose constant uninterrupted presence guarantees the foundation of the world."* The source says "the master of the age — the imam of his own day, **whom he will never name**." The trailing "but" only parses with the negation, so this is most likely a dropped word in transcription rather than a host error — **but if the audio really says "whom he names" it inverts a deliberate feature of Fatimid daawa practice and becomes P0.** Verify by ear.

### PR-PC-04 (P2) — qutb and the author's name
*"the first concept is KOTBB"* against the framing's `qutb: KOOTB`. The author's name is cut off mid-word: *"a remarkable treatise called Establishing the Imamat. Written by Al-Nah"*.

### PR-PB-02 (P2) — natiq/samit thinned to a single clause
The source has "every speaker-prophet stands as the visible peak of his cycle while the silent one beside him carries the inner meaning through," and names the natiq as "the seventh imam of his era." The episode keeps one clause — *"The keeper holds what the voice spoke"* — and drops the seventh-imam structure entirely. What remains is an ocean-current-and-wave image in which the imam *becomes* the messenger and subsides back, which reads as one office at two moments rather than two contemporaneous offices. See the book-level finding PR-PB-02.

### PR-PG-01 (P2) — Filler
"Exactly" / " exactly" x12, " Yeah," x4, "you know" recurring, in 5,039 words. `SURPRISE_DENY` lists "Exactly"; `FILLER_INTERJECTIONS` lists " Yeah,".

## Hallucination sweep — clean apart from the imagery
Every doctrinal claim traces to `chapters/ch01a-*.txt`. The three linked reasons, the two creations, the two witnesses, the Abraham ascent by stages, the thaqalayn hadith, the earth-never-empty saying, "my witness is every stone and every piece of clay" — all present in the source, none embellished. The only untraceable material is the imagery flagged under PR-PE-02.
