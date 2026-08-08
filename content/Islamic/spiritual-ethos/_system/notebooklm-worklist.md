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
| [1. Ali and the Prophet](content/Islamic/spiritual-ethos/chapters/ch01a-ali-and-the-prophet.txt) | [EP01 — Ali and the Prophet](content/Islamic/spiritual-ethos/episodes/EP01-ali-and-the-prophet.txt) | Deep Dive | Long |
| [2. Why Intellect, Not Reason](content/Islamic/spiritual-ethos/chapters/ch02b-why-intellect-not-reason.txt) | [EP02 — Why Intellect, Not Reason](content/Islamic/spiritual-ethos/episodes/EP02-why-intellect-not-reason.txt) | Deep Dive | Long |
| [3. Paradox and the Inner Struggle](content/Islamic/spiritual-ethos/chapters/ch03c-paradox-and-the-inner-struggle.txt) | [EP03 — Paradox and the Inner Struggle](content/Islamic/spiritual-ethos/episodes/EP03-paradox-and-the-inner-struggle.txt) | Deep Dive | Long |
| [4. Joy, Virtue, and the Hereafter](content/Islamic/spiritual-ethos/chapters/ch04d-joy-virtue-and-the-hereafter.txt) | [EP04 — Joy, Virtue, and the Hereafter](content/Islamic/spiritual-ethos/episodes/EP04-joy-virtue-and-the-hereafter.txt) | Deep Dive | Long |
| [5. The Sacred Conception of Justice](content/Islamic/spiritual-ethos/chapters/ch05a-the-sacred-conception-of-justice.txt) | [EP05 — The Sacred Conception of Justice](content/Islamic/spiritual-ethos/episodes/EP05-the-sacred-conception-of-justice.txt) | Deep Dive | Long |
| [6. Pride and Conscience](content/Islamic/spiritual-ethos/chapters/ch06b-pride-and-conscience.txt) | [EP06 — Pride and Conscience](content/Islamic/spiritual-ethos/episodes/EP06-pride-and-conscience.txt) | Deep Dive | Long |
| [7. Classes of Society and the Poor](content/Islamic/spiritual-ethos/chapters/ch07c-the-classes-of-society-and-the-poor.txt) | [EP07 — Classes of Society and the Poor](content/Islamic/spiritual-ethos/episodes/EP07-the-classes-of-society-and-the-poor.txt) | Deep Dive | Long |
| [8. Prayer as the Source of Justice](content/Islamic/spiritual-ethos/chapters/ch08d-prayer-as-the-source-of-justice.txt) | [EP08 — Prayer as the Source of Justice](content/Islamic/spiritual-ethos/episodes/EP08-prayer-as-the-source-of-justice.txt) | Deep Dive | Long |
| [9. Dhikr, the Polish for Hearts](content/Islamic/spiritual-ethos/chapters/ch09a-dhikr-the-polish-for-hearts.txt) | [EP09 — Dhikr, the Polish for Hearts](content/Islamic/spiritual-ethos/episodes/EP09-dhikr-the-polish-for-hearts.txt) | Deep Dive | Long |
| [10. The Veils That Do Not Veil](content/Islamic/spiritual-ethos/chapters/ch10b-the-veils-that-do-not-veil.txt) | [EP10 — The Veils That Do Not Veil](content/Islamic/spiritual-ethos/episodes/EP10-the-veils-that-do-not-veil.txt) | Deep Dive | Long |
| [11. Forgetting the Self, Becoming the Name](content/Islamic/spiritual-ethos/chapters/ch11c-forgetting-the-self-and-the-name.txt) | [EP11 — Forgetting the Self, Becoming the Name](content/Islamic/spiritual-ethos/episodes/EP11-forgetting-the-self-and-the-name.txt) | Deep Dive | Long |
| [12. The First Sermon of Nahj al-Balagha](content/Islamic/spiritual-ethos/chapters/ch12-the-first-sermon-of-nahj-al-balagha.txt) | [EP12 — The First Sermon of Nahj al-Balagha](content/Islamic/spiritual-ethos/episodes/EP12-the-first-sermon-of-nahj-al-balagha.txt) | Deep Dive | Long |
| [13. The Letter of Ali (ع) to Malik al-Ashtar](content/Islamic/spiritual-ethos/chapters/ch13-the-letter-of-ali-to-malik-al-ashtar.txt) | [EP13 — The Letter of Ali (ع) to Malik al-Ashtar](content/Islamic/spiritual-ethos/episodes/EP13-the-letter-of-ali-to-malik-al-ashtar.txt) | Deep Dive | Long |

## 2 - Slide decks (NotebookLM -> Slide deck tool)

SLIDE DECK GENERATION (NotebookLM → Slide deck tool):
  For each chapter: open the slide notebook, choose the Slide deck tool,
  paste the framing file's contents BELOW its H1 into the Describe box,
  pick the Format + Length below, Generate, then download the PDF export
  and save it at the exact path in the last column.

| Chapter | Upload source | Describe-box paste | Format | Length | Save exported PDF as |
|---|---|---|---|---|---|
| book | [book-deck-source.txt](content/Islamic/spiritual-ethos/slide-decks/book-deck-source.txt) | [book-framing.md](content/Islamic/spiritual-ethos/slide-decks/book-framing.md) | Detailed deck | Default | `content/Islamic/spiritual-ethos/slide-decks/book-deck.pdf` |

  Decks dropped before `--resume` are imported automatically into the
  reading edition (0book-slide-import) — no further action needed.
  To exempt a chapter from the reading-edition weave, create an empty
  marker file: slide-decks/<ch>-<slug>.SKIP

## 3 - Drop-target checklist

- [ ] EP01 — Ali and the Prophet
      audio      -> m4a/ch01a-ali-and-the-prophet.m4a
      transcript -> m4a/transcripts/ch01a-ali-and-the-prophet.transcript.txt  (auto on --resume)
- [ ] EP02 — Why Intellect, Not Reason
      audio      -> m4a/ch02b-why-intellect-not-reason.m4a
      transcript -> m4a/transcripts/ch02b-why-intellect-not-reason.transcript.txt  (auto on --resume)
- [ ] EP03 — Paradox and the Inner Struggle
      audio      -> m4a/ch03c-paradox-and-the-inner-struggle.m4a
      transcript -> m4a/transcripts/ch03c-paradox-and-the-inner-struggle.transcript.txt  (auto on --resume)
- [ ] EP04 — Joy, Virtue, and the Hereafter
      audio      -> m4a/ch04d-joy-virtue-and-the-hereafter.m4a
      transcript -> m4a/transcripts/ch04d-joy-virtue-and-the-hereafter.transcript.txt  (auto on --resume)
- [ ] EP05 — The Sacred Conception of Justice
      audio      -> m4a/ch05a-the-sacred-conception-of-justice.m4a
      transcript -> m4a/transcripts/ch05a-the-sacred-conception-of-justice.transcript.txt  (auto on --resume)
- [ ] EP06 — Pride and Conscience
      audio      -> m4a/ch06b-pride-and-conscience.m4a
      transcript -> m4a/transcripts/ch06b-pride-and-conscience.transcript.txt  (auto on --resume)
- [ ] EP07 — Classes of Society and the Poor
      audio      -> m4a/ch07c-the-classes-of-society-and-the-poor.m4a
      transcript -> m4a/transcripts/ch07c-the-classes-of-society-and-the-poor.transcript.txt  (auto on --resume)
- [ ] EP08 — Prayer as the Source of Justice
      audio      -> m4a/ch08d-prayer-as-the-source-of-justice.m4a
      transcript -> m4a/transcripts/ch08d-prayer-as-the-source-of-justice.transcript.txt  (auto on --resume)
- [ ] EP09 — Dhikr, the Polish for Hearts
      audio      -> m4a/ch09a-dhikr-the-polish-for-hearts.m4a
      transcript -> m4a/transcripts/ch09a-dhikr-the-polish-for-hearts.transcript.txt  (auto on --resume)
- [ ] EP10 — The Veils That Do Not Veil
      audio      -> m4a/ch10b-the-veils-that-do-not-veil.m4a
      transcript -> m4a/transcripts/ch10b-the-veils-that-do-not-veil.transcript.txt  (auto on --resume)
- [ ] EP11 — Forgetting the Self, Becoming the Name
      audio      -> m4a/ch11c-forgetting-the-self-and-the-name.m4a
      transcript -> m4a/transcripts/ch11c-forgetting-the-self-and-the-name.transcript.txt  (auto on --resume)
- [ ] EP12 — The First Sermon of Nahj al-Balagha
      audio      -> m4a/ch12-the-first-sermon-of-nahj-al-balagha.m4a
      transcript -> m4a/transcripts/ch12-the-first-sermon-of-nahj-al-balagha.transcript.txt  (auto on --resume)
- [ ] EP13 — The Letter of Ali (ع) to Malik al-Ashtar
      audio      -> m4a/ch13-the-letter-of-ali-to-malik-al-ashtar.m4a
      transcript -> m4a/transcripts/ch13-the-letter-of-ali-to-malik-al-ashtar.transcript.txt  (auto on --resume)

## When every box above is checked

    python3 scripts/podcast/orchestrate_book.py --resume spiritual-ethos

The orchestrator normalizes filenames, transcribes via Azure Speech, imports
any dropped slide PDFs, then publishes. If audio is still missing it re-halts
cleanly and rewrites this file — nothing is lost.
