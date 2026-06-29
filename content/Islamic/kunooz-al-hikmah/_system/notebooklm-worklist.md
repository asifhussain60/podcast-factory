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
| [1. Family of Light](content/Islamic/kunooz-al-hikmah/chapters/ch01a-family-of-light.txt) | [EP01 — Family of Light](content/Islamic/kunooz-al-hikmah/episodes/EP01-family-of-light.txt) | Deep Dive | Long |
| [2. Named Duat and the Discipline of Concealment](content/Islamic/kunooz-al-hikmah/chapters/ch02b-named-duat-and-concealment.txt) | [EP02 — Named Duat and the Discipline of Concealment](content/Islamic/kunooz-al-hikmah/episodes/EP02-named-duat-and-concealment.txt) | Deep Dive | Long |
| [3. The Two Foundational Questions](content/Islamic/kunooz-al-hikmah/chapters/ch03-two-foundational-questions.txt) | [EP03 — The Two Foundational Questions](content/Islamic/kunooz-al-hikmah/episodes/EP03-two-foundational-questions.txt) | Deep Dive | Long |
| [4. The Heart Beneath the House, and the Early Lectures](content/Islamic/kunooz-al-hikmah/chapters/ch04a-heart-shahadah-and-early-lectures.txt) | [EP04 — The Heart Beneath the House, and the Early Lectures](content/Islamic/kunooz-al-hikmah/episodes/EP04-heart-shahadah-and-early-lectures.txt) | Deep Dive | Long |
| [5. The Later Lectures, and the End of the Book](content/Islamic/kunooz-al-hikmah/chapters/ch05b-later-lectures-and-the-end-of-book.txt) | [EP05 — The Later Lectures, and the End of the Book](content/Islamic/kunooz-al-hikmah/episodes/EP05-later-lectures-and-the-end-of-book.txt) | Deep Dive | Long |
| [6. The Author's Posture, and the Line That Carries Him](content/Islamic/kunooz-al-hikmah/chapters/ch06a-authors-posture-and-the-line.txt) | [EP06 — The Author's Posture, and the Line That Carries Him](content/Islamic/kunooz-al-hikmah/episodes/EP06-authors-posture-and-the-line.txt) | Deep Dive | Long |
| [7. The Cycle, the Litany, and the Practical Frame](content/Islamic/kunooz-al-hikmah/chapters/ch07b-the-cycle-and-the-practical-frame.txt) | [EP07 — The Cycle, the Litany, and the Practical Frame](content/Islamic/kunooz-al-hikmah/episodes/EP07-the-cycle-and-the-practical-frame.txt) | Deep Dive | Long |
| [8. The Cycles, the Cave, and the Precision of Return](content/Islamic/kunooz-al-hikmah/chapters/ch08a-lectures-six-seven-eight-continued.txt) | [EP08 — The Cycles, the Cave, and the Precision of Return](content/Islamic/kunooz-al-hikmah/episodes/EP08-lectures-six-seven-eight-continued.txt) | Deep Dive | Long |
| [9. Lectures Nine Ten Eleven Continued](content/Islamic/kunooz-al-hikmah/chapters/ch09b-lectures-nine-ten-eleven-continued.txt) | [EP09 — Lectures Nine Ten Eleven Continued](content/Islamic/kunooz-al-hikmah/episodes/EP09-lectures-nine-ten-eleven-continued.txt) | Deep Dive | Long |
| [10. Lectures Twelve Fourteen Fifteen Continued](content/Islamic/kunooz-al-hikmah/chapters/ch10c-lectures-twelve-fourteen-fifteen-continued.txt) | [EP10 — Lectures Twelve Fourteen Fifteen Continued](content/Islamic/kunooz-al-hikmah/episodes/EP10-lectures-twelve-fourteen-fifteen-continued.txt) | Deep Dive | Long |
| [11. Living Context and the Whole Structure](content/Islamic/kunooz-al-hikmah/chapters/ch11-living-context-and-the-whole-structure.txt) | [EP11 — Living Context and the Whole Structure](content/Islamic/kunooz-al-hikmah/episodes/EP11-living-context-and-the-whole-structure.txt) | Deep Dive | Long |
| [12. Particular Doctrines Drawn Out](content/Islamic/kunooz-al-hikmah/chapters/ch12-particular-doctrines-drawn-out.txt) | [EP12 — Particular Doctrines Drawn Out](content/Islamic/kunooz-al-hikmah/episodes/EP12-particular-doctrines-drawn-out.txt) | Deep Dive | Long |
| [13. Doctrinal Synthesis and Supplementary](content/Islamic/kunooz-al-hikmah/chapters/ch13-doctrinal-synthesis-and-supplementary.txt) | [EP13 — Doctrinal Synthesis and Supplementary](content/Islamic/kunooz-al-hikmah/episodes/EP13-doctrinal-synthesis-and-supplementary.txt) | Deep Dive | Long |

## 3 - Drop-target checklist

- [ ] EP01 — Family of Light
      audio      -> m4a/ch01a-family-of-light.m4a
      transcript -> m4a/transcripts/ch01a-family-of-light.transcript.txt  (auto on --resume)
- [ ] EP02 — Named Duat and the Discipline of Concealment
      audio      -> m4a/ch02b-named-duat-and-concealment.m4a
      transcript -> m4a/transcripts/ch02b-named-duat-and-concealment.transcript.txt  (auto on --resume)
- [ ] EP03 — The Two Foundational Questions
      audio      -> m4a/ch03-two-foundational-questions.m4a
      transcript -> m4a/transcripts/ch03-two-foundational-questions.transcript.txt  (auto on --resume)
- [ ] EP04 — The Heart Beneath the House, and the Early Lectures
      audio      -> m4a/ch04a-heart-shahadah-and-early-lectures.m4a
      transcript -> m4a/transcripts/ch04a-heart-shahadah-and-early-lectures.transcript.txt  (auto on --resume)
- [ ] EP05 — The Later Lectures, and the End of the Book
      audio      -> m4a/ch05b-later-lectures-and-the-end-of-book.m4a
      transcript -> m4a/transcripts/ch05b-later-lectures-and-the-end-of-book.transcript.txt  (auto on --resume)
- [ ] EP06 — The Author's Posture, and the Line That Carries Him
      audio      -> m4a/ch06a-authors-posture-and-the-line.m4a
      transcript -> m4a/transcripts/ch06a-authors-posture-and-the-line.transcript.txt  (auto on --resume)
- [ ] EP07 — The Cycle, the Litany, and the Practical Frame
      audio      -> m4a/ch07b-the-cycle-and-the-practical-frame.m4a
      transcript -> m4a/transcripts/ch07b-the-cycle-and-the-practical-frame.transcript.txt  (auto on --resume)
- [ ] EP08 — The Cycles, the Cave, and the Precision of Return
      audio      -> m4a/ch08a-lectures-six-seven-eight-continued.m4a
      transcript -> m4a/transcripts/ch08a-lectures-six-seven-eight-continued.transcript.txt  (auto on --resume)
- [ ] EP09 — Lectures Nine Ten Eleven Continued
      audio      -> m4a/ch09b-lectures-nine-ten-eleven-continued.m4a
      transcript -> m4a/transcripts/ch09b-lectures-nine-ten-eleven-continued.transcript.txt  (auto on --resume)
- [ ] EP10 — Lectures Twelve Fourteen Fifteen Continued
      audio      -> m4a/ch10c-lectures-twelve-fourteen-fifteen-continued.m4a
      transcript -> m4a/transcripts/ch10c-lectures-twelve-fourteen-fifteen-continued.transcript.txt  (auto on --resume)
- [ ] EP11 — Living Context and the Whole Structure
      audio      -> m4a/ch11-living-context-and-the-whole-structure.m4a
      transcript -> m4a/transcripts/ch11-living-context-and-the-whole-structure.transcript.txt  (auto on --resume)
- [ ] EP12 — Particular Doctrines Drawn Out
      audio      -> m4a/ch12-particular-doctrines-drawn-out.m4a
      transcript -> m4a/transcripts/ch12-particular-doctrines-drawn-out.transcript.txt  (auto on --resume)
- [ ] EP13 — Doctrinal Synthesis and Supplementary
      audio      -> m4a/ch13-doctrinal-synthesis-and-supplementary.m4a
      transcript -> m4a/transcripts/ch13-doctrinal-synthesis-and-supplementary.transcript.txt  (auto on --resume)

## When every box above is checked

    python3 scripts/podcast/orchestrate_book.py --resume kunooz-al-hikmah

The orchestrator normalizes filenames, transcribes via Azure Speech, imports
any dropped slide PDFs, then publishes. If audio is still missing it re-halts
cleanly and rewrites this file — nothing is lost.
