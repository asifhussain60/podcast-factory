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
| [1. The Imamate, Pole of Religion](content/Islamic/degrees-of-excellence/chapters/ch01a-the-imamate-pole-and-foundation-of-religion.txt) | [EP01 — The Imamate, Pole of Religion](content/Islamic/degrees-of-excellence/episodes/EP01-the-imamate-pole-and-foundation-of-religion.txt) | Deep Dive | Long |
| [2. The Peak of Every Kind](content/Islamic/degrees-of-excellence/chapters/ch02b-degrees-of-excellence-the-peak-of-every-kind.txt) | [EP02 — The Peak of Every Kind](content/Islamic/degrees-of-excellence/episodes/EP02-degrees-of-excellence-the-peak-of-every-kind.txt) | Deep Dive | Long |
| [3. The Imam's Authority](content/Islamic/degrees-of-excellence/chapters/ch03c-the-imam-and-the-authority-over-sacred-law.txt) | [EP03 — The Imam's Authority](content/Islamic/degrees-of-excellence/episodes/EP03-the-imam-and-the-authority-over-sacred-law.txt) | Deep Dive | Long |
| [4. Worship and Law Without the Imam](content/Islamic/degrees-of-excellence/chapters/ch04d-worship-alms-and-war-void-without-the-imam.txt) | [EP04 — Worship and Law Without the Imam](content/Islamic/degrees-of-excellence/episodes/EP04-worship-alms-and-war-void-without-the-imam.txt) | Deep Dive | Long |
| [5. Prophets, Symbols, and the Caliphs](content/Islamic/degrees-of-excellence/chapters/ch05e-prophets-as-symbols-and-the-first-caliphs.txt) | [EP05 — Prophets, Symbols, and the Caliphs](content/Islamic/degrees-of-excellence/episodes/EP05-prophets-as-symbols-and-the-first-caliphs.txt) | Deep Dive | Long |
| [6. The Imam Who Mirrors God](content/Islamic/degrees-of-excellence/chapters/ch06f-the-virtues-of-ali-the-imam-who-mirrors-god.txt) | [EP06 — The Imam Who Mirrors God](content/Islamic/degrees-of-excellence/episodes/EP06-the-virtues-of-ali-the-imam-who-mirrors-god.txt) | Deep Dive | Long |

## 2 - Slide decks (NotebookLM -> Slide deck tool)

SLIDE DECK GENERATION (NotebookLM → Slide deck tool):
  For each chapter: open the slide notebook, choose the Slide deck tool,
  paste the framing file's contents BELOW its H1 into the Describe box,
  pick the Format + Length below, Generate, then download the PDF export
  and save it at the exact path in the last column.

| Chapter | Upload source | Describe-box paste | Format | Length | Save exported PDF as |
|---|---|---|---|---|---|
| ch01a | [ch01a-deck-the-imamate-pole-and-foundation-of-religion.txt](content/Islamic/degrees-of-excellence/slide-decks/ch01a-deck-the-imamate-pole-and-foundation-of-religion.txt) | [ch01a-framing-the-imamate-pole-and-foundation-of-religion.md](content/Islamic/degrees-of-excellence/slide-decks/ch01a-framing-the-imamate-pole-and-foundation-of-religion.md) | Detailed deck | Default | `content/Islamic/degrees-of-excellence/slide-decks/ch01a-the-imamate-pole-and-foundation-of-religion.pdf` |
| ch02b | [ch02b-deck-degrees-of-excellence-the-peak-of-every-kind.txt](content/Islamic/degrees-of-excellence/slide-decks/ch02b-deck-degrees-of-excellence-the-peak-of-every-kind.txt) | [ch02b-framing-degrees-of-excellence-the-peak-of-every-kind.md](content/Islamic/degrees-of-excellence/slide-decks/ch02b-framing-degrees-of-excellence-the-peak-of-every-kind.md) | Detailed deck | Default | `content/Islamic/degrees-of-excellence/slide-decks/ch02b-degrees-of-excellence-the-peak-of-every-kind.pdf` |
| ch03c | [ch03c-deck-the-imam-and-the-authority-over-sacred-law.txt](content/Islamic/degrees-of-excellence/slide-decks/ch03c-deck-the-imam-and-the-authority-over-sacred-law.txt) | [ch03c-framing-the-imam-and-the-authority-over-sacred-law.md](content/Islamic/degrees-of-excellence/slide-decks/ch03c-framing-the-imam-and-the-authority-over-sacred-law.md) | Detailed deck | Default | `content/Islamic/degrees-of-excellence/slide-decks/ch03c-the-imam-and-the-authority-over-sacred-law.pdf` |
| ch04d | [ch04d-deck-worship-alms-and-war-void-without-the-imam.txt](content/Islamic/degrees-of-excellence/slide-decks/ch04d-deck-worship-alms-and-war-void-without-the-imam.txt) | [ch04d-framing-worship-alms-and-war-void-without-the-imam.md](content/Islamic/degrees-of-excellence/slide-decks/ch04d-framing-worship-alms-and-war-void-without-the-imam.md) | Detailed deck | Default | `content/Islamic/degrees-of-excellence/slide-decks/ch04d-worship-alms-and-war-void-without-the-imam.pdf` |
| ch05e | [ch05e-deck-prophets-as-symbols-and-the-first-caliphs.txt](content/Islamic/degrees-of-excellence/slide-decks/ch05e-deck-prophets-as-symbols-and-the-first-caliphs.txt) | [ch05e-framing-prophets-as-symbols-and-the-first-caliphs.md](content/Islamic/degrees-of-excellence/slide-decks/ch05e-framing-prophets-as-symbols-and-the-first-caliphs.md) | Detailed deck | Default | `content/Islamic/degrees-of-excellence/slide-decks/ch05e-prophets-as-symbols-and-the-first-caliphs.pdf` |
| ch06f | [ch06f-deck-the-virtues-of-ali-the-imam-who-mirrors-god.txt](content/Islamic/degrees-of-excellence/slide-decks/ch06f-deck-the-virtues-of-ali-the-imam-who-mirrors-god.txt) | [ch06f-framing-the-virtues-of-ali-the-imam-who-mirrors-god.md](content/Islamic/degrees-of-excellence/slide-decks/ch06f-framing-the-virtues-of-ali-the-imam-who-mirrors-god.md) | Detailed deck | Default | `content/Islamic/degrees-of-excellence/slide-decks/ch06f-the-virtues-of-ali-the-imam-who-mirrors-god.pdf` |

  Decks dropped before `--resume` are imported automatically into the
  reading edition (0book-slide-import) — no further action needed.
  To exempt a chapter from the reading-edition weave, create an empty
  marker file: slide-decks/<ch>-<slug>.SKIP

## 3 - Drop-target checklist

- [ ] EP01 — The Imamate, Pole of Religion
      audio      -> m4a/ch01a-the-imamate-pole-and-foundation-of-religion.m4a
      transcript -> m4a/transcripts/ch01a-the-imamate-pole-and-foundation-of-religion.transcript.txt  (auto on --resume)
- [ ] EP02 — The Peak of Every Kind
      audio      -> m4a/ch02b-degrees-of-excellence-the-peak-of-every-kind.m4a
      transcript -> m4a/transcripts/ch02b-degrees-of-excellence-the-peak-of-every-kind.transcript.txt  (auto on --resume)
- [ ] EP03 — The Imam's Authority
      audio      -> m4a/ch03c-the-imam-and-the-authority-over-sacred-law.m4a
      transcript -> m4a/transcripts/ch03c-the-imam-and-the-authority-over-sacred-law.transcript.txt  (auto on --resume)
- [ ] EP04 — Worship and Law Without the Imam
      audio      -> m4a/ch04d-worship-alms-and-war-void-without-the-imam.m4a
      transcript -> m4a/transcripts/ch04d-worship-alms-and-war-void-without-the-imam.transcript.txt  (auto on --resume)
- [ ] EP05 — Prophets, Symbols, and the Caliphs
      audio      -> m4a/ch05e-prophets-as-symbols-and-the-first-caliphs.m4a
      transcript -> m4a/transcripts/ch05e-prophets-as-symbols-and-the-first-caliphs.transcript.txt  (auto on --resume)
- [ ] EP06 — The Imam Who Mirrors God
      audio      -> m4a/ch06f-the-virtues-of-ali-the-imam-who-mirrors-god.m4a
      transcript -> m4a/transcripts/ch06f-the-virtues-of-ali-the-imam-who-mirrors-god.transcript.txt  (auto on --resume)

## When every box above is checked

    python3 scripts/podcast/orchestrate_book.py --resume degrees-of-excellence

The orchestrator normalizes filenames, transcribes via Azure Speech, imports
any dropped slide PDFs, then publishes. If audio is still missing it re-halts
cleanly and rewrites this file — nothing is lost.
