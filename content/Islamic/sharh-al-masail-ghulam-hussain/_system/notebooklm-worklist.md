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
| [1. Lawful Earning and the Table](content/Islamic/sharh-al-masail-ghulam-hussain/chapters/ch01-earning-and-the-manners-of-the-table.txt) | [EP01 — Lawful Earning and the Table](content/Islamic/sharh-al-masail-ghulam-hussain/episodes/EP01-earning-and-the-manners-of-the-table.txt) | Deep Dive | Long |
| [2. Sale, Debt, and the Trust](content/Islamic/sharh-al-masail-ghulam-hussain/chapters/ch02-sale-debt-and-the-contracts-of-trade.txt) | [EP02 — Sale, Debt, and the Trust](content/Islamic/sharh-al-masail-ghulam-hussain/episodes/EP02-sale-debt-and-the-contracts-of-trade.txt) | Deep Dive | Long |
| [3. Pledge, Shared Wall, and Marriage](content/Islamic/sharh-al-masail-ghulam-hussain/chapters/ch03-the-pledge-and-the-call-to-marry.txt) | [EP03 — Pledge, Shared Wall, and Marriage](content/Islamic/sharh-al-masail-ghulam-hussain/episodes/EP03-the-pledge-and-the-call-to-marry.txt) | Deep Dive | Long |
| [4. The Marriage Contract and Its Bonds](content/Islamic/sharh-al-masail-ghulam-hussain/chapters/ch04-the-marriage-contract-and-its-bonds.txt) | [EP04 — The Marriage Contract and Its Bonds](content/Islamic/sharh-al-masail-ghulam-hussain/episodes/EP04-the-marriage-contract-and-its-bonds.txt) | Deep Dive | Long |
| [5. Maintenance, Dissolution, and Inheritance](content/Islamic/sharh-al-masail-ghulam-hussain/chapters/ch05-maintenance-dissolution-and-inheritance.txt) | [EP05 — Maintenance, Dissolution, and Inheritance](content/Islamic/sharh-al-masail-ghulam-hussain/episodes/EP05-maintenance-dissolution-and-inheritance.txt) | Deep Dive | Long |

## 2 - Slide decks (NotebookLM -> Slide deck tool)

SLIDE DECK GENERATION (NotebookLM → Slide deck tool):
  For each chapter: open the slide notebook, choose the Slide deck tool,
  paste the framing file's contents BELOW its H1 into the Describe box,
  pick the Format + Length below, Generate, then download the PDF export
  and save it at the exact path in the last column.

| Chapter | Upload source | Describe-box paste | Format | Length | Save exported PDF as |
|---|---|---|---|---|---|
| book | [book-deck-source.txt](content/Islamic/sharh-al-masail-ghulam-hussain/slide-decks/book-deck-source.txt) | [book-framing.md](content/Islamic/sharh-al-masail-ghulam-hussain/slide-decks/book-framing.md) | Detailed deck | Default | `content/Islamic/sharh-al-masail-ghulam-hussain/slide-decks/book-deck.pdf` |

  Decks dropped before `--resume` are imported automatically into the
  reading edition (0book-slide-import) — no further action needed.
  To exempt a chapter from the reading-edition weave, create an empty
  marker file: slide-decks/<ch>-<slug>.SKIP

## 3 - Drop-target checklist

- [ ] EP01 — Lawful Earning and the Table
      audio      -> m4a/ch01-earning-and-the-manners-of-the-table.m4a
      transcript -> m4a/transcripts/ch01-earning-and-the-manners-of-the-table.transcript.txt  (auto on --resume)
- [ ] EP02 — Sale, Debt, and the Trust
      audio      -> m4a/ch02-sale-debt-and-the-contracts-of-trade.m4a
      transcript -> m4a/transcripts/ch02-sale-debt-and-the-contracts-of-trade.transcript.txt  (auto on --resume)
- [ ] EP03 — Pledge, Shared Wall, and Marriage
      audio      -> m4a/ch03-the-pledge-and-the-call-to-marry.m4a
      transcript -> m4a/transcripts/ch03-the-pledge-and-the-call-to-marry.transcript.txt  (auto on --resume)
- [ ] EP04 — The Marriage Contract and Its Bonds
      audio      -> m4a/ch04-the-marriage-contract-and-its-bonds.m4a
      transcript -> m4a/transcripts/ch04-the-marriage-contract-and-its-bonds.transcript.txt  (auto on --resume)
- [ ] EP05 — Maintenance, Dissolution, and Inheritance
      audio      -> m4a/ch05-maintenance-dissolution-and-inheritance.m4a
      transcript -> m4a/transcripts/ch05-maintenance-dissolution-and-inheritance.transcript.txt  (auto on --resume)

## When every box above is checked

    python3 scripts/podcast/orchestrate_book.py --resume sharh-al-masail-ghulam-hussain

The orchestrator normalizes filenames, transcribes via Azure Speech, imports
any dropped slide PDFs, then publishes. If audio is still missing it re-halts
cleanly and rewrites this file — nothing is lost.
