# NotebookLM worklist

Single source for the manual NotebookLM round-trips. Work top to bottom.
The pipeline auto-normalizes + transcribes dropped audio and auto-imports
dropped slide PDFs the moment you re-run the resume command at the bottom —
no separate CLI steps, no filename fixing.

## 1 - Audio (NotebookLM -> Audio Overview)

Per row: click the CHAPTER cell to open the SOURCE to upload, and the EPISODE
cell to open the FRAMING to paste into NotebookLM's Customize box. Download each
generated .m4a and drop it anywhere under `m4a/` — filenames do not matter.

| Chapters | Episodes | Deep dive or debate | Length |
|---|---|---|---|
| [1. Trust and the Science of Realities](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch01a-the-trust-and-the-science-of-realities.txt) | [EP01 — Trust and the Science of Realities](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP01-the-trust-and-the-science-of-realities.txt) | Deep Dive | Long |
| [2. The Unknowable Originator](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch02b-the-unknowable-originator-and-the-first-intellect.txt) | [EP02 — The Unknowable Originator](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP02-the-unknowable-originator-and-the-first-intellect.txt) | Deep Dive | Long |
| [3. Naming the Unnameable](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch03c-naming-the-unnameable.txt) | [EP03 — Naming the Unnameable](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP03-naming-the-unnameable.txt) | Deep Dive | Long |
| [4. What Tawhid Really Is](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch04a-what-tawhid-really-is.txt) | [EP04 — What Tawhid Really Is](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP04-what-tawhid-really-is.txt) | Deep Dive | Long |
| [5. The Two Gnoses and the Mukathir](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch05b-outer-and-inner-gnosis-and-the-mukathir.txt) | [EP05 — The Two Gnoses and the Mukathir](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP05-outer-and-inner-gnosis-and-the-mukathir.txt) | Deep Dive | Long |
| [6. The Mukathir, House of Allah](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch06c-the-refined-mukathir-house-of-allah.txt) | [EP06 — The Mukathir, House of Allah](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP06-the-refined-mukathir-house-of-allah.txt) | Deep Dive | Long |
| [7. Ascent, Decline, and a God](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch07d-ascent-decline-and-the-birth-of-a-god.txt) | [EP07 — Ascent, Decline, and a God](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP07-ascent-decline-and-the-birth-of-a-god.txt) | Deep Dive | Long |
| [8. The Ladder of Tawhid](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch08e-the-ladder-of-tawhid.txt) | [EP08 — The Ladder of Tawhid](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP08-the-ladder-of-tawhid.txt) | Deep Dive | Long |
| [9. Origination From Nothing](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch09f-origination-from-nothing.txt) | [EP09 — Origination From Nothing](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP09-origination-from-nothing.txt) | Deep Dive | Long |
| [10. Equal but Not Infallible](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch10g-equal-but-not-infallible.txt) | [EP10 — Equal but Not Infallible](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP10-equal-but-not-infallible.txt) | Deep Dive | Long |
| [11. The Word and the Greatest Name](content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch11h-the-word-of-allah-and-the-greatest-name.txt) | [EP11 — The Word and the Greatest Name](content/Islamic/al-anwaar-al-lateefah/vol-01/episodes/EP11-the-word-of-allah-and-the-greatest-name.txt) | Deep Dive | Long |

## 2 - Slide decks (NotebookLM -> Slide deck tool)

SLIDE DECK GENERATION (NotebookLM → Slide deck tool):
  For each chapter: open the slide notebook, choose the Slide deck tool,
  paste the framing file's contents BELOW its H1 into the Describe box,
  pick the Format + Length below, Generate, then download the PDF export
  and save it at the exact path in the last column.

| Chapter | Upload source | Describe-box paste | Format | Length | Save exported PDF as |
|---|---|---|---|---|---|
| ch01a | [ch01a-deck-the-trust-and-the-science-of-realities.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch01a-deck-the-trust-and-the-science-of-realities.txt) | [ch01a-framing-the-trust-and-the-science-of-realities.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch01a-framing-the-trust-and-the-science-of-realities.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch01a-the-trust-and-the-science-of-realities.pdf` |
| ch02b | [ch02b-deck-the-unknowable-originator-and-the-first-intellect.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch02b-deck-the-unknowable-originator-and-the-first-intellect.txt) | [ch02b-framing-the-unknowable-originator-and-the-first-intellect.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch02b-framing-the-unknowable-originator-and-the-first-intellect.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch02b-the-unknowable-originator-and-the-first-intellect.pdf` |
| ch03c | [ch03c-deck-naming-the-unnameable.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch03c-deck-naming-the-unnameable.txt) | [ch03c-framing-naming-the-unnameable.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch03c-framing-naming-the-unnameable.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch03c-naming-the-unnameable.pdf` |
| ch04a | [ch04a-deck-what-tawhid-really-is.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch04a-deck-what-tawhid-really-is.txt) | [ch04a-framing-what-tawhid-really-is.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch04a-framing-what-tawhid-really-is.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch04a-what-tawhid-really-is.pdf` |
| ch05b | [ch05b-deck-outer-and-inner-gnosis-and-the-mukathir.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch05b-deck-outer-and-inner-gnosis-and-the-mukathir.txt) | [ch05b-framing-outer-and-inner-gnosis-and-the-mukathir.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch05b-framing-outer-and-inner-gnosis-and-the-mukathir.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch05b-outer-and-inner-gnosis-and-the-mukathir.pdf` |
| ch06c | [ch06c-deck-the-refined-mukathir-house-of-allah.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch06c-deck-the-refined-mukathir-house-of-allah.txt) | [ch06c-framing-the-refined-mukathir-house-of-allah.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch06c-framing-the-refined-mukathir-house-of-allah.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch06c-the-refined-mukathir-house-of-allah.pdf` |
| ch07d | [ch07d-deck-ascent-decline-and-the-birth-of-a-god.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch07d-deck-ascent-decline-and-the-birth-of-a-god.txt) | [ch07d-framing-ascent-decline-and-the-birth-of-a-god.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch07d-framing-ascent-decline-and-the-birth-of-a-god.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch07d-ascent-decline-and-the-birth-of-a-god.pdf` |
| ch08e | [ch08e-deck-the-ladder-of-tawhid.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch08e-deck-the-ladder-of-tawhid.txt) | [ch08e-framing-the-ladder-of-tawhid.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch08e-framing-the-ladder-of-tawhid.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch08e-the-ladder-of-tawhid.pdf` |
| ch09f | [ch09f-deck-origination-from-nothing.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch09f-deck-origination-from-nothing.txt) | [ch09f-framing-origination-from-nothing.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch09f-framing-origination-from-nothing.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch09f-origination-from-nothing.pdf` |
| ch10g | [ch10g-deck-equal-but-not-infallible.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch10g-deck-equal-but-not-infallible.txt) | [ch10g-framing-equal-but-not-infallible.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch10g-framing-equal-but-not-infallible.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch10g-equal-but-not-infallible.pdf` |
| ch11h | [ch11h-deck-the-word-of-allah-and-the-greatest-name.txt](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch11h-deck-the-word-of-allah-and-the-greatest-name.txt) | [ch11h-framing-the-word-of-allah-and-the-greatest-name.md](content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch11h-framing-the-word-of-allah-and-the-greatest-name.md) | Detailed deck | Default | `content/Islamic/al-anwaar-al-lateefah/vol-01/slide-decks/ch11h-the-word-of-allah-and-the-greatest-name.pdf` |

  Decks dropped before `--resume` are imported automatically into the
  reading edition (0book-slide-import) — no further action needed.
  To exempt a chapter from the reading-edition weave, create an empty
  marker file: slide-decks/<ch>-<slug>.SKIP

## 3 - Drop-target checklist

- [ ] EP01 — Trust and the Science of Realities
      audio      -> m4a/ch01a-the-trust-and-the-science-of-realities.m4a
      transcript -> m4a/transcripts/ch01a-the-trust-and-the-science-of-realities.transcript.txt  (auto on --resume)
- [ ] EP02 — The Unknowable Originator
      audio      -> m4a/ch02b-the-unknowable-originator-and-the-first-intellect.m4a
      transcript -> m4a/transcripts/ch02b-the-unknowable-originator-and-the-first-intellect.transcript.txt  (auto on --resume)
- [ ] EP03 — Naming the Unnameable
      audio      -> m4a/ch03c-naming-the-unnameable.m4a
      transcript -> m4a/transcripts/ch03c-naming-the-unnameable.transcript.txt  (auto on --resume)
- [ ] EP04 — What Tawhid Really Is
      audio      -> m4a/ch04a-what-tawhid-really-is.m4a
      transcript -> m4a/transcripts/ch04a-what-tawhid-really-is.transcript.txt  (auto on --resume)
- [ ] EP05 — The Two Gnoses and the Mukathir
      audio      -> m4a/ch05b-outer-and-inner-gnosis-and-the-mukathir.m4a
      transcript -> m4a/transcripts/ch05b-outer-and-inner-gnosis-and-the-mukathir.transcript.txt  (auto on --resume)
- [ ] EP06 — The Mukathir, House of Allah
      audio      -> m4a/ch06c-the-refined-mukathir-house-of-allah.m4a
      transcript -> m4a/transcripts/ch06c-the-refined-mukathir-house-of-allah.transcript.txt  (auto on --resume)
- [ ] EP07 — Ascent, Decline, and a God
      audio      -> m4a/ch07d-ascent-decline-and-the-birth-of-a-god.m4a
      transcript -> m4a/transcripts/ch07d-ascent-decline-and-the-birth-of-a-god.transcript.txt  (auto on --resume)
- [ ] EP08 — The Ladder of Tawhid
      audio      -> m4a/ch08e-the-ladder-of-tawhid.m4a
      transcript -> m4a/transcripts/ch08e-the-ladder-of-tawhid.transcript.txt  (auto on --resume)
- [ ] EP09 — Origination From Nothing
      audio      -> m4a/ch09f-origination-from-nothing.m4a
      transcript -> m4a/transcripts/ch09f-origination-from-nothing.transcript.txt  (auto on --resume)
- [ ] EP10 — Equal but Not Infallible
      audio      -> m4a/ch10g-equal-but-not-infallible.m4a
      transcript -> m4a/transcripts/ch10g-equal-but-not-infallible.transcript.txt  (auto on --resume)
- [ ] EP11 — The Word and the Greatest Name
      audio      -> m4a/ch11h-the-word-of-allah-and-the-greatest-name.m4a
      transcript -> m4a/transcripts/ch11h-the-word-of-allah-and-the-greatest-name.transcript.txt  (auto on --resume)

## When every box above is checked

    python3 scripts/podcast/orchestrate_book.py --resume al-anwaar-al-lateefah-vol-01

The orchestrator normalizes filenames, transcribes via Azure Speech, imports
any dropped slide PDFs, then publishes. If audio is still missing it re-halts
cleanly and rewrites this file — nothing is lost.
