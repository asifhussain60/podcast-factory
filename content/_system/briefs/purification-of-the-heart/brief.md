# Purification of the Heart

A commission for the podcast factory, written from the Intake form on 2026-08-31T13:49:19.542Z. Nothing has been created yet — this document is the brief, not the book.

- **Folder name:** `purification-of-the-heart`
- **Shelf:** Sessions
- **Branch it will run on:** `Sessions/purification-of-the-heart`
- **Brief folder:** `/Users/asifhussain/PROJECTS/podcast-factory/content/_system/briefs/purification-of-the-heart`

## The source files

- **01-purification-of-the-heart.mp3** — Source recording
  - `/Users/asifhussain/PROJECTS/podcast-factory/content/Sessions/purification-of-the-heart/source/01-purification-of-the-heart.mp3`
- **02-purification-of-the-heart.mp3** — Source recording
  - `/Users/asifhussain/PROJECTS/podcast-factory/content/Sessions/purification-of-the-heart/source/02-purification-of-the-heart.mp3`
- **01-purification-of-the-heart.vtt** — Timestamped transcript
  - `/Users/asifhussain/PROJECTS/podcast-factory/content/Sessions/purification-of-the-heart/transcripts/01-purification-of-the-heart.vtt`
- **02-purification-of-the-heart.vtt** — Timestamped transcript
  - `/Users/asifhussain/PROJECTS/podcast-factory/content/Sessions/purification-of-the-heart/transcripts/02-purification-of-the-heart.vtt`

These are copies kept with the brief, so the paths above stay valid. The staging area they were uploaded to is swept after a day.

## The work

| Decision | Answer | As the pipeline reads it |
|---|---|---|
| Title | Purification of the Heart | `title: Purification of the Heart` |
| English title | Purification of the Heart | `title_english: Purification of the Heart` |
| Author | Sheikh Hamza Yusuf | `author: Sheikh Hamza Yusuf` |
| Folder name | Purification of the heart | `slug: purification-of-the-heart` |
| Pipeline profile | Islamic session | `content_profile: islamic_session` |
| Legacy category tag | Lectures | `category: lectures` |
| What kind of content is this | Islamic | — |
| Where it came from | A recorded talk or session | `source_medium: audio_lecture` |
| Study track | Theology | `study_track: theology` |

## The source

| Decision | Answer | As the pipeline reads it |
|---|---|---|
| Source language | English (en) | `source_language: en` |
| One volume of a larger work | No | — |
| Putting the Arabic back | Check the recording | `arabic_restoration: audio_grounded` |
| How exact the transcript is | Verbatim | `source_fidelity: verbatim` |

## The chapters

| Decision | Answer | As the pipeline reads it |
|---|---|---|
| How the chapters are decided | Follow the book's own chapter list | `chapter_segmentation: from_source_toc` |

## The edition

| Decision | Answer | As the pipeline reads it |
|---|---|---|
| Who narrates it | first-person author addressing the reader | `narrative_frame: first_person_author` |
| Voice of the edition | Faithful | `book_voice: faithful` |
| Produce a reading edition (PDF) | Yes | `enable_book_branch: true` |
| Produce slide decks | Yes | `enable_slide_decks: true` |
| Decks per | Per chapter | `slide_deck_mode: per-chapter` |
| What may be added | None | `book_augmentation: none` |
| Figures | Manual only | `book_visuals: manual_only` |
| How far it may run unattended | stop at every gate | `autonomy: manual` |

## The podcast

| Decision | Answer | As the pipeline reads it |
|---|---|---|
| Depth of the material | General | `content_level: general` |
| Density | Medium | `density: medium` |

## Chapters, in order (24)

1. Love of the World
2. Envy
3. Blameworthy Modesty
4. Fantasizing
5. Fear of Poverty
6. Ostentation
7. Relying on Other Than God
8. Displeasure with the Divine Decree
9. Seeking Reputation
10. False Hopes
11. Negative Thoughts
12. Vanity
13. Fraud
14. Anger
15. Heedlessness
16. Rancor
17. Boasting & Arrogance
18. Displeasure with Blame
19. Antipathy Toward Death
20. Obliviousness to Blessings
21. Derision
22. Comprehensive Treatment for the Heart
23. Beneficial Actions for Purifying the Heart
24. The Root of All Diseases of the Heart

## How this will be processed

Worked out from the answers above, in the order the steps run. These are the instructions, not a summary of them.

- This is a recorded session, not a text being adapted. The recording is the work. Its prose is PROOFREAD only -- spelling, punctuation, paragraph breaks, and words the transcriber dropped -- and never rewritten, re-voiced, summarised or enriched. A pass that starts improving the wording is reverted to the raw transcription.
- The sessions teach through a published work chapter by chapter. Cut the chapters where that book does and keep its own chapter names. A recording is NOT one chapter: a single sitting may cover several, and the count follows the book rather than the audio.
- There are 24 chapters, named in the list of chapters that accompanies this. Use those names exactly. Do not invent chapter titles, and do not merge two of them into one chapter or split one into two.
- Restore the Arabic the transcriber wrote out phonetically -- Qur'an, hadith, poetry and quotations -- back into Arabic script. Qur'anic runs are set from the canonical mushaf's own wording, never from a reconstruction. Where the text alone is ambiguous, check that moment of the recording to settle what was actually said.
- All Arabic carries its diacritics. There is no unvowelled Arabic in the finished edition.
- Qur'an, hadith, poetry and quotations are set in their own styled blocks, not run into the surrounding prose.
- NO podcast is generated. There are no episodes, no NotebookLM upload bundle and no synthesised voices -- the audio already exists and is the lecture itself.
- Produce a slide deck for each chapter.

## Still to settle

Claude fills this in when reviewing the brief: anything above that looks wrong for this source, anything the form could not ask, and the questions worth answering before the pipeline runs.
