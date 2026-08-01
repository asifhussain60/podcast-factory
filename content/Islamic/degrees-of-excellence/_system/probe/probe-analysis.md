# Pronunciation probe — run 1 analysis

- **Book:** degrees-of-excellence
- **Audio:** `m4a/How_medieval_Arabic_words_defined_cosmic_order.m4a` (5:06, NotebookLM, Shorter)
- **Transcript:** `_system/probe/EP00-pronunciation-probe/probe.transcript.txt` (Azure Speech)
- **Verdict:** PRONUNCIATION-PARTIAL
- `probe_analyst_version: 1.0`

## The run did not do what it was asked

The bundle listed 39 numbered terms and instructed the hosts to walk them in
order. NotebookLM ignored the structure and produced an ordinary themed Deep
Dive — "how a handful of specific Arabic words didn't just describe history, but
they actively shaped it" — naming **9 of the 39 terms**. Thirty were never
spoken, so nothing can be concluded about them.

This is a defect in the probe's design, not in the book. A NotebookLM Audio
Overview conversationalises its source; handing it a list of instructions
addressed to the hosts produced a discussion ABOUT a glossary rather than a
reading OF one. The Shorter length compounded it: 39 terms in five minutes is
seven seconds each, and the model spent its budget on theme instead.

The framing also carries no deny-list, so the surprise-noise the episode
framings ban leaked straight in — the run opens "Oh, wow. Right." and calls
itself a "Dip Dive".

## What the 9 spoken terms show

The sample is small, but one-sided enough to act on.

| # | Term | Intended | Heard | Form | Verdict |
|---|---|---|---|---|---|
| 2 | al-Kirmani | `al-Kirmani` | "Al-Kirmani" | plain | **correct** |
| 16 | tawhid | `tow-HEED` | "toheed" | respelling | **correct** |
| 23 | tashbih | `tash-BEEH` | "Tashbieh" / "Tashbee" | respelling | **correct** (2nd truncated) |
| 1 | al-Naysaburi | `an-nay-saa-BOO-ree` | "Ani Saburi" / "Aizab Uri" | respelling | **mangled**, two ways |
| 13 | vicegerent | `vice-JEER-uhnt` | "vice jeer hunt" / "the vice version" | respelling | **mangled** |
| 18 | walaya | `wa-LAA-ya` | "wa la ya" / "wa la a" | respelling | **mangled** |
| 22 | sais | `SAA-is` | "a SAA, is" | respelling | **mangled** |
| 24 | khutba | `KHUT-bah` | "KHU Tiba" | respelling | **mangled** |
| 35 | nur al-imama | `NOOR al-i-MAA-ma` | "NO or Ali Masma" | respelling | **mangled** |

Two words nobody instructed came out perfect: **Imam**, said many times, and
**Khalifa**. Both are ordinary loanwords the voice model already knows.

### The pattern is about shape, not about respelling as such

Six of the seven failures split at the hyphens and read the pieces as separate
words — "wa la ya", "KHU Tiba", "vice jeer hunt". The two respellings that
survived, `tow-HEED` and `tash-BEEH`, are two syllables with no internal article
and no capitalised fragment that could stand alone as an English word.

So the 2026-07-18 finding recorded in `term_render.py` — that this TTS reads
hyphen-CAPS respellings literally — is **confirmed on this book, for anything
longer than two syllables**. The 41 overrides written on 2026-08-01 are mostly
of the failing shape: `AHL az-ZAH-hir`, `DAA-i-rat ad-DEEN`, `BAYT al-MAAL`,
`NOOR al-i-MAA-ma`.

It also confirms the build's new loanword warning: `imam` was already perfect
unaided, and the override table respells it to `i-MAAM`.

## Nothing was written to the ledger

Deliberate. A `respell` verdict records `confirmed @ the corrected form`, and no
corrected form has been heard yet — writing one now would put a guess into the
cross-book library under the one status that is supposed to mean "a human heard
this come out right". Thirty terms have no evidence at all.

The library's value is that a hit means somebody listened. Run 2 earns the
entries.

## What run 2 must change

1. **Force coverage.** The source becomes a glossary the hosts read, not a list
   of instructions they discuss, and the framing states the exact count and
   forbids thematic digression.
2. **Give it room.** Shorter cannot hold 39 terms. Either raise the length or
   split into batches of ~15 — a batch that fits is worth more than a full list
   that gets skimmed.
3. **Carry the deny-list**, so the probe is not itself teaching the hosts the
   surprise-noise habits the episode framings spend words banning.
4. **Lead with plain transliteration.** Given the evidence, run 2 should test
   the ladder's own default against the respellings, rather than testing 39
   respellings of a shape already shown to fail.
