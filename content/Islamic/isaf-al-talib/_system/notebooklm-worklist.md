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
| [1. Faith and Guardianship](content/Islamic/isaf-al-talib/chapters/ch01-foundations-of-faith-and-guardianship.txt) | EP01 — Faith and Guardianship | Deep Dive | Long |
| [2. Ranks and Communal Affection](content/Islamic/isaf-al-talib/chapters/ch02-ranks-loyalty-and-communal-affection.txt) | EP02 — Ranks and Communal Affection | Deep Dive | Long |
| [3. Purity Through Ablution](content/Islamic/isaf-al-talib/chapters/ch03-purity-through-ablution.txt) | EP03 — Purity Through Ablution | Deep Dive | Long |
| [4. Major Washing and Purity](content/Islamic/isaf-al-talib/chapters/ch04-major-washing-and-material-purity.txt) | EP04 — Major Washing and Purity | Deep Dive | Long |
| [5. Foods and Everyday Purity](content/Islamic/isaf-al-talib/chapters/ch05-foods-cleanliness-and-everyday-purity.txt) | EP05 — Foods and Everyday Purity | Deep Dive | Long |
| [6. Bodily Substances and Disavowal](content/Islamic/isaf-al-talib/chapters/ch06-bodily-substances-and-disavowal.txt) | EP06 — Bodily Substances and Disavowal | Deep Dive | Long |
| [7. Prayer and Sacred Times](content/Islamic/isaf-al-talib/chapters/ch07-prayer-virtue-and-sacred-times.txt) | EP07 — Prayer and Sacred Times | Deep Dive | Long |
| [8. Adhan and Iqama](content/Islamic/isaf-al-talib/chapters/ch08-adhan-and-iqama.txt) | EP08 — Adhan and Iqama | Debate | Long |
| [9. The Prayer Summons](content/Islamic/isaf-al-talib/chapters/ch09-the-form-of-the-prayer-summons.txt) | EP09 — The Prayer Summons | Debate | Long |
| [10. Mosques and Sacred Space](content/Islamic/isaf-al-talib/chapters/ch10-mosques-and-sacred-space.txt) | EP10 — Mosques and Sacred Space | Deep Dive | Long |
| [11. Imamate in Prayer](content/Islamic/isaf-al-talib/chapters/ch11-imamate-in-prayer.txt) | EP11 — Imamate in Prayer | Deep Dive | Long |
| [12. Shared Prayer](content/Islamic/isaf-al-talib/chapters/ch12-congregation-and-shared-prayer.txt) | EP12 — Shared Prayer | Deep Dive | Long |
| [13. Prayer's Living Edges](content/Islamic/isaf-al-talib/chapters/ch13-supplication-conduct-and-dress-in-prayer.txt) | EP13 — Prayer's Living Edges | Deep Dive | Long |
| [14. Friday, Eid, and Omission](content/Islamic/isaf-al-talib/chapters/ch14-friday-eid-and-prayer-corrections.txt) | EP14 — Friday, Eid, and Omission | Deep Dive | Long |
| [15. Unbroken Prayer and Early Formation](content/Islamic/isaf-al-talib/chapters/ch15-missed-rakahs-and-learning-prayer.txt) | EP15 — Unbroken Prayer and Early Formation | Deep Dive | Long |
| [16. The Traveller's Prayer](content/Islamic/isaf-al-talib/chapters/ch16-the-travellers-prayer.txt) | EP16 — The Traveller's Prayer | Deep Dive | Long |
| [17. Occasional Prayers and Free Devotion](content/Islamic/isaf-al-talib/chapters/ch17-special-prayers-and-voluntary-devotion.txt) | EP17 — Occasional Prayers and Free Devotion | Deep Dive | Long |
| [18. Visiting the Sick, Remembering Death](content/Islamic/isaf-al-talib/chapters/ch18-sickness-epidemic-and-remembering-death.txt) | EP18 — Visiting the Sick, Remembering Death | Deep Dive | Long |
| [19. Condolence, Washing, and Burial](content/Islamic/isaf-al-talib/chapters/ch19-condolence-mourning-and-burial.txt) | EP19 — Condolence, Washing, and Burial | Deep Dive | Long |
| [20. Zakat as Obligation and Intention](content/Islamic/isaf-al-talib/chapters/ch20-zakat-obligation-and-intention.txt) | EP20 — Zakat as Obligation and Intention | Deep Dive | Long |
| [21. Coin, Herd, Harvest, and Head](content/Islamic/isaf-al-talib/chapters/ch21-zakat-on-wealth-livestock-crops-and-fitr.txt) | EP21 — Coin, Herd, Harvest, and Head | Deep Dive | Long |
| [22. The Shield, the Name, the Count](content/Islamic/isaf-al-talib/chapters/ch22-the-obligation-and-meaning-of-fasting.txt) | EP22 — The Shield, the Name, the Count | Deep Dive | Long |
| [23. The Month That Cannot Shrink](content/Islamic/isaf-al-talib/chapters/ch23-fasting-duties-and-the-crescent-question.txt) | EP23 — The Month That Cannot Shrink | Debate | Long |
| [24. A Fast Begun Two Days Early](content/Islamic/isaf-al-talib/chapters/ch24-scripture-counted-days-and-the-complete-month.txt) | EP24 — A Fast Begun Two Days Early | Deep Dive | Long |
| [25. The Eye That Cannot Be Trusted](content/Islamic/isaf-al-talib/chapters/ch25-astronomy-calculation-and-religious-obligation.txt) | EP25 — The Eye That Cannot Be Trusted | Deep Dive | Long |
| [26. The Duty Nobody Holds Alone](content/Islamic/isaf-al-talib/chapters/ch26-two-sightings-and-higher-meaning.txt) | EP26 — The Duty Nobody Holds Alone | Deep Dive | Long |
| [27. The Figure in the Calendar](content/Islamic/isaf-al-talib/chapters/ch27-ramadan-foundation-and-obedient-knowledge.txt) | EP27 — The Figure in the Calendar | Deep Dive | Long |

## 2 - Slide decks (NotebookLM -> Slide deck tool)

SLIDE DECK GENERATION (NotebookLM → Slide deck tool):
  For each chapter: open the slide notebook, choose the Slide deck tool,
  paste the framing file's contents BELOW its H1 into the Describe box,
  pick the Format + Length below, Generate, then download the PDF export
  and save it at the exact path in the last column.

| Chapter | Upload source | Describe-box paste | Format | Length | Save exported PDF as |
|---|---|---|---|---|---|
| ch01 | [ch01-deck-foundations-of-faith-and-guardianship.txt](content/Islamic/isaf-al-talib/slide-decks/ch01-deck-foundations-of-faith-and-guardianship.txt) | [ch01-framing-foundations-of-faith-and-guardianship.md](content/Islamic/isaf-al-talib/slide-decks/ch01-framing-foundations-of-faith-and-guardianship.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch01-foundations-of-faith-and-guardianship.pdf` |
| ch02 | [ch02-deck-ranks-loyalty-and-communal-affection.txt](content/Islamic/isaf-al-talib/slide-decks/ch02-deck-ranks-loyalty-and-communal-affection.txt) | [ch02-framing-ranks-loyalty-and-communal-affection.md](content/Islamic/isaf-al-talib/slide-decks/ch02-framing-ranks-loyalty-and-communal-affection.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch02-ranks-loyalty-and-communal-affection.pdf` |
| ch03 | [ch03-deck-purity-through-ablution.txt](content/Islamic/isaf-al-talib/slide-decks/ch03-deck-purity-through-ablution.txt) | [ch03-framing-purity-through-ablution.md](content/Islamic/isaf-al-talib/slide-decks/ch03-framing-purity-through-ablution.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch03-purity-through-ablution.pdf` |
| ch04 | [ch04-deck-major-washing-and-material-purity.txt](content/Islamic/isaf-al-talib/slide-decks/ch04-deck-major-washing-and-material-purity.txt) | [ch04-framing-major-washing-and-material-purity.md](content/Islamic/isaf-al-talib/slide-decks/ch04-framing-major-washing-and-material-purity.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch04-major-washing-and-material-purity.pdf` |
| ch05 | [ch05-deck-foods-cleanliness-and-everyday-purity.txt](content/Islamic/isaf-al-talib/slide-decks/ch05-deck-foods-cleanliness-and-everyday-purity.txt) | [ch05-framing-foods-cleanliness-and-everyday-purity.md](content/Islamic/isaf-al-talib/slide-decks/ch05-framing-foods-cleanliness-and-everyday-purity.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch05-foods-cleanliness-and-everyday-purity.pdf` |
| ch06 | [ch06-deck-bodily-substances-and-disavowal.txt](content/Islamic/isaf-al-talib/slide-decks/ch06-deck-bodily-substances-and-disavowal.txt) | [ch06-framing-bodily-substances-and-disavowal.md](content/Islamic/isaf-al-talib/slide-decks/ch06-framing-bodily-substances-and-disavowal.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch06-bodily-substances-and-disavowal.pdf` |
| ch07 | [ch07-deck-prayer-virtue-and-sacred-times.txt](content/Islamic/isaf-al-talib/slide-decks/ch07-deck-prayer-virtue-and-sacred-times.txt) | [ch07-framing-prayer-virtue-and-sacred-times.md](content/Islamic/isaf-al-talib/slide-decks/ch07-framing-prayer-virtue-and-sacred-times.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch07-prayer-virtue-and-sacred-times.pdf` |
| ch08 | [ch08-deck-adhan-and-iqama.txt](content/Islamic/isaf-al-talib/slide-decks/ch08-deck-adhan-and-iqama.txt) | [ch08-framing-adhan-and-iqama.md](content/Islamic/isaf-al-talib/slide-decks/ch08-framing-adhan-and-iqama.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch08-adhan-and-iqama.pdf` |
| ch09 | [ch09-deck-the-form-of-the-prayer-summons.txt](content/Islamic/isaf-al-talib/slide-decks/ch09-deck-the-form-of-the-prayer-summons.txt) | [ch09-framing-the-form-of-the-prayer-summons.md](content/Islamic/isaf-al-talib/slide-decks/ch09-framing-the-form-of-the-prayer-summons.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch09-the-form-of-the-prayer-summons.pdf` |
| ch10 | [ch10-deck-mosques-and-sacred-space.txt](content/Islamic/isaf-al-talib/slide-decks/ch10-deck-mosques-and-sacred-space.txt) | [ch10-framing-mosques-and-sacred-space.md](content/Islamic/isaf-al-talib/slide-decks/ch10-framing-mosques-and-sacred-space.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch10-mosques-and-sacred-space.pdf` |
| ch11 | [ch11-deck-imamate-in-prayer.txt](content/Islamic/isaf-al-talib/slide-decks/ch11-deck-imamate-in-prayer.txt) | [ch11-framing-imamate-in-prayer.md](content/Islamic/isaf-al-talib/slide-decks/ch11-framing-imamate-in-prayer.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch11-imamate-in-prayer.pdf` |
| ch12 | [ch12-deck-congregation-and-shared-prayer.txt](content/Islamic/isaf-al-talib/slide-decks/ch12-deck-congregation-and-shared-prayer.txt) | [ch12-framing-congregation-and-shared-prayer.md](content/Islamic/isaf-al-talib/slide-decks/ch12-framing-congregation-and-shared-prayer.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch12-congregation-and-shared-prayer.pdf` |
| ch13 | [ch13-deck-supplication-conduct-and-dress-in-prayer.txt](content/Islamic/isaf-al-talib/slide-decks/ch13-deck-supplication-conduct-and-dress-in-prayer.txt) | [ch13-framing-supplication-conduct-and-dress-in-prayer.md](content/Islamic/isaf-al-talib/slide-decks/ch13-framing-supplication-conduct-and-dress-in-prayer.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch13-supplication-conduct-and-dress-in-prayer.pdf` |
| ch14 | [ch14-deck-friday-eid-and-prayer-corrections.txt](content/Islamic/isaf-al-talib/slide-decks/ch14-deck-friday-eid-and-prayer-corrections.txt) | [ch14-framing-friday-eid-and-prayer-corrections.md](content/Islamic/isaf-al-talib/slide-decks/ch14-framing-friday-eid-and-prayer-corrections.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch14-friday-eid-and-prayer-corrections.pdf` |
| ch15 | [ch15-deck-missed-rakahs-and-learning-prayer.txt](content/Islamic/isaf-al-talib/slide-decks/ch15-deck-missed-rakahs-and-learning-prayer.txt) | [ch15-framing-missed-rakahs-and-learning-prayer.md](content/Islamic/isaf-al-talib/slide-decks/ch15-framing-missed-rakahs-and-learning-prayer.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch15-missed-rakahs-and-learning-prayer.pdf` |
| ch16 | [ch16-deck-the-travellers-prayer.txt](content/Islamic/isaf-al-talib/slide-decks/ch16-deck-the-travellers-prayer.txt) | [ch16-framing-the-travellers-prayer.md](content/Islamic/isaf-al-talib/slide-decks/ch16-framing-the-travellers-prayer.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch16-the-travellers-prayer.pdf` |
| ch17 | [ch17-deck-special-prayers-and-voluntary-devotion.txt](content/Islamic/isaf-al-talib/slide-decks/ch17-deck-special-prayers-and-voluntary-devotion.txt) | [ch17-framing-special-prayers-and-voluntary-devotion.md](content/Islamic/isaf-al-talib/slide-decks/ch17-framing-special-prayers-and-voluntary-devotion.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch17-special-prayers-and-voluntary-devotion.pdf` |
| ch18 | [ch18-deck-sickness-epidemic-and-remembering-death.txt](content/Islamic/isaf-al-talib/slide-decks/ch18-deck-sickness-epidemic-and-remembering-death.txt) | [ch18-framing-sickness-epidemic-and-remembering-death.md](content/Islamic/isaf-al-talib/slide-decks/ch18-framing-sickness-epidemic-and-remembering-death.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch18-sickness-epidemic-and-remembering-death.pdf` |
| ch19 | [ch19-deck-condolence-mourning-and-burial.txt](content/Islamic/isaf-al-talib/slide-decks/ch19-deck-condolence-mourning-and-burial.txt) | [ch19-framing-condolence-mourning-and-burial.md](content/Islamic/isaf-al-talib/slide-decks/ch19-framing-condolence-mourning-and-burial.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch19-condolence-mourning-and-burial.pdf` |
| ch20 | [ch20-deck-zakat-obligation-and-intention.txt](content/Islamic/isaf-al-talib/slide-decks/ch20-deck-zakat-obligation-and-intention.txt) | [ch20-framing-zakat-obligation-and-intention.md](content/Islamic/isaf-al-talib/slide-decks/ch20-framing-zakat-obligation-and-intention.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch20-zakat-obligation-and-intention.pdf` |
| ch21 | [ch21-deck-zakat-on-wealth-livestock-crops-and-fitr.txt](content/Islamic/isaf-al-talib/slide-decks/ch21-deck-zakat-on-wealth-livestock-crops-and-fitr.txt) | [ch21-framing-zakat-on-wealth-livestock-crops-and-fitr.md](content/Islamic/isaf-al-talib/slide-decks/ch21-framing-zakat-on-wealth-livestock-crops-and-fitr.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch21-zakat-on-wealth-livestock-crops-and-fitr.pdf` |
| ch22 | [ch22-deck-the-obligation-and-meaning-of-fasting.txt](content/Islamic/isaf-al-talib/slide-decks/ch22-deck-the-obligation-and-meaning-of-fasting.txt) | [ch22-framing-the-obligation-and-meaning-of-fasting.md](content/Islamic/isaf-al-talib/slide-decks/ch22-framing-the-obligation-and-meaning-of-fasting.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch22-the-obligation-and-meaning-of-fasting.pdf` |
| ch23 | [ch23-deck-fasting-duties-and-the-crescent-question.txt](content/Islamic/isaf-al-talib/slide-decks/ch23-deck-fasting-duties-and-the-crescent-question.txt) | [ch23-framing-fasting-duties-and-the-crescent-question.md](content/Islamic/isaf-al-talib/slide-decks/ch23-framing-fasting-duties-and-the-crescent-question.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch23-fasting-duties-and-the-crescent-question.pdf` |
| ch24 | [ch24-deck-scripture-counted-days-and-the-complete-month.txt](content/Islamic/isaf-al-talib/slide-decks/ch24-deck-scripture-counted-days-and-the-complete-month.txt) | [ch24-framing-scripture-counted-days-and-the-complete-month.md](content/Islamic/isaf-al-talib/slide-decks/ch24-framing-scripture-counted-days-and-the-complete-month.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch24-scripture-counted-days-and-the-complete-month.pdf` |
| ch25 | [ch25-deck-astronomy-calculation-and-religious-obligation.txt](content/Islamic/isaf-al-talib/slide-decks/ch25-deck-astronomy-calculation-and-religious-obligation.txt) | [ch25-framing-astronomy-calculation-and-religious-obligation.md](content/Islamic/isaf-al-talib/slide-decks/ch25-framing-astronomy-calculation-and-religious-obligation.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch25-astronomy-calculation-and-religious-obligation.pdf` |
| ch26 | [ch26-deck-two-sightings-and-higher-meaning.txt](content/Islamic/isaf-al-talib/slide-decks/ch26-deck-two-sightings-and-higher-meaning.txt) | [ch26-framing-two-sightings-and-higher-meaning.md](content/Islamic/isaf-al-talib/slide-decks/ch26-framing-two-sightings-and-higher-meaning.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch26-two-sightings-and-higher-meaning.pdf` |
| ch27 | [ch27-deck-ramadan-foundation-and-obedient-knowledge.txt](content/Islamic/isaf-al-talib/slide-decks/ch27-deck-ramadan-foundation-and-obedient-knowledge.txt) | [ch27-framing-ramadan-foundation-and-obedient-knowledge.md](content/Islamic/isaf-al-talib/slide-decks/ch27-framing-ramadan-foundation-and-obedient-knowledge.md) | Detailed deck | Default | `content/Islamic/isaf-al-talib/slide-decks/ch27-ramadan-foundation-and-obedient-knowledge.pdf` |

  Decks dropped before `--resume` are imported automatically into the
  reading edition (0book-slide-import) — no further action needed.
  To exempt a chapter from the reading-edition weave, create an empty
  marker file: slide-decks/<ch>-<slug>.SKIP

## 3 - Drop-target checklist

- [ ] EP01 — Faith and Guardianship
      audio      -> m4a/ch01-foundations-of-faith-and-guardianship.m4a
      transcript -> m4a/transcripts/ch01-foundations-of-faith-and-guardianship.transcript.txt  (auto on --resume)
- [ ] EP02 — Ranks and Communal Affection
      audio      -> m4a/ch02-ranks-loyalty-and-communal-affection.m4a
      transcript -> m4a/transcripts/ch02-ranks-loyalty-and-communal-affection.transcript.txt  (auto on --resume)
- [ ] EP03 — Purity Through Ablution
      audio      -> m4a/ch03-purity-through-ablution.m4a
      transcript -> m4a/transcripts/ch03-purity-through-ablution.transcript.txt  (auto on --resume)
- [ ] EP04 — Major Washing and Purity
      audio      -> m4a/ch04-major-washing-and-material-purity.m4a
      transcript -> m4a/transcripts/ch04-major-washing-and-material-purity.transcript.txt  (auto on --resume)
- [ ] EP05 — Foods and Everyday Purity
      audio      -> m4a/ch05-foods-cleanliness-and-everyday-purity.m4a
      transcript -> m4a/transcripts/ch05-foods-cleanliness-and-everyday-purity.transcript.txt  (auto on --resume)
- [ ] EP06 — Bodily Substances and Disavowal
      audio      -> m4a/ch06-bodily-substances-and-disavowal.m4a
      transcript -> m4a/transcripts/ch06-bodily-substances-and-disavowal.transcript.txt  (auto on --resume)
- [ ] EP07 — Prayer and Sacred Times
      audio      -> m4a/ch07-prayer-virtue-and-sacred-times.m4a
      transcript -> m4a/transcripts/ch07-prayer-virtue-and-sacred-times.transcript.txt  (auto on --resume)
- [ ] EP08 — Adhan and Iqama
      audio      -> m4a/ch08-adhan-and-iqama.m4a
      transcript -> m4a/transcripts/ch08-adhan-and-iqama.transcript.txt  (auto on --resume)
- [ ] EP09 — The Prayer Summons
      audio      -> m4a/ch09-the-form-of-the-prayer-summons.m4a
      transcript -> m4a/transcripts/ch09-the-form-of-the-prayer-summons.transcript.txt  (auto on --resume)
- [ ] EP10 — Mosques and Sacred Space
      audio      -> m4a/ch10-mosques-and-sacred-space.m4a
      transcript -> m4a/transcripts/ch10-mosques-and-sacred-space.transcript.txt  (auto on --resume)
- [ ] EP11 — Imamate in Prayer
      audio      -> m4a/ch11-imamate-in-prayer.m4a
      transcript -> m4a/transcripts/ch11-imamate-in-prayer.transcript.txt  (auto on --resume)
- [ ] EP12 — Shared Prayer
      audio      -> m4a/ch12-congregation-and-shared-prayer.m4a
      transcript -> m4a/transcripts/ch12-congregation-and-shared-prayer.transcript.txt  (auto on --resume)
- [ ] EP13 — Prayer's Living Edges
      audio      -> m4a/ch13-supplication-conduct-and-dress-in-prayer.m4a
      transcript -> m4a/transcripts/ch13-supplication-conduct-and-dress-in-prayer.transcript.txt  (auto on --resume)
- [ ] EP14 — Friday, Eid, and Omission
      audio      -> m4a/ch14-friday-eid-and-prayer-corrections.m4a
      transcript -> m4a/transcripts/ch14-friday-eid-and-prayer-corrections.transcript.txt  (auto on --resume)
- [ ] EP15 — Unbroken Prayer and Early Formation
      audio      -> m4a/ch15-missed-rakahs-and-learning-prayer.m4a
      transcript -> m4a/transcripts/ch15-missed-rakahs-and-learning-prayer.transcript.txt  (auto on --resume)
- [ ] EP16 — The Traveller's Prayer
      audio      -> m4a/ch16-the-travellers-prayer.m4a
      transcript -> m4a/transcripts/ch16-the-travellers-prayer.transcript.txt  (auto on --resume)
- [ ] EP17 — Occasional Prayers and Free Devotion
      audio      -> m4a/ch17-special-prayers-and-voluntary-devotion.m4a
      transcript -> m4a/transcripts/ch17-special-prayers-and-voluntary-devotion.transcript.txt  (auto on --resume)
- [ ] EP18 — Visiting the Sick, Remembering Death
      audio      -> m4a/ch18-sickness-epidemic-and-remembering-death.m4a
      transcript -> m4a/transcripts/ch18-sickness-epidemic-and-remembering-death.transcript.txt  (auto on --resume)
- [ ] EP19 — Condolence, Washing, and Burial
      audio      -> m4a/ch19-condolence-mourning-and-burial.m4a
      transcript -> m4a/transcripts/ch19-condolence-mourning-and-burial.transcript.txt  (auto on --resume)
- [ ] EP20 — Zakat as Obligation and Intention
      audio      -> m4a/ch20-zakat-obligation-and-intention.m4a
      transcript -> m4a/transcripts/ch20-zakat-obligation-and-intention.transcript.txt  (auto on --resume)
- [ ] EP21 — Coin, Herd, Harvest, and Head
      audio      -> m4a/ch21-zakat-on-wealth-livestock-crops-and-fitr.m4a
      transcript -> m4a/transcripts/ch21-zakat-on-wealth-livestock-crops-and-fitr.transcript.txt  (auto on --resume)
- [ ] EP22 — The Shield, the Name, the Count
      audio      -> m4a/ch22-the-obligation-and-meaning-of-fasting.m4a
      transcript -> m4a/transcripts/ch22-the-obligation-and-meaning-of-fasting.transcript.txt  (auto on --resume)
- [ ] EP23 — The Month That Cannot Shrink
      audio      -> m4a/ch23-fasting-duties-and-the-crescent-question.m4a
      transcript -> m4a/transcripts/ch23-fasting-duties-and-the-crescent-question.transcript.txt  (auto on --resume)
- [ ] EP24 — A Fast Begun Two Days Early
      audio      -> m4a/ch24-scripture-counted-days-and-the-complete-month.m4a
      transcript -> m4a/transcripts/ch24-scripture-counted-days-and-the-complete-month.transcript.txt  (auto on --resume)
- [ ] EP25 — The Eye That Cannot Be Trusted
      audio      -> m4a/ch25-astronomy-calculation-and-religious-obligation.m4a
      transcript -> m4a/transcripts/ch25-astronomy-calculation-and-religious-obligation.transcript.txt  (auto on --resume)
- [ ] EP26 — The Duty Nobody Holds Alone
      audio      -> m4a/ch26-two-sightings-and-higher-meaning.m4a
      transcript -> m4a/transcripts/ch26-two-sightings-and-higher-meaning.transcript.txt  (auto on --resume)
- [ ] EP27 — The Figure in the Calendar
      audio      -> m4a/ch27-ramadan-foundation-and-obedient-knowledge.m4a
      transcript -> m4a/transcripts/ch27-ramadan-foundation-and-obedient-knowledge.transcript.txt  (auto on --resume)

## When every box above is checked

    python3 scripts/podcast/orchestrate_book.py --resume isaf-al-talib

The orchestrator normalizes filenames, transcribes via Azure Speech, imports
any dropped slide PDFs, then publishes. If audio is still missing it re-halts
cleanly and rewrites this file — nothing is lost.
