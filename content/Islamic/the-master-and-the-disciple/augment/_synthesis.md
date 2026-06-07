# _synthesis — Master and the Disciple: ksessions augmentation

> Generated from KSESSIONS database (Group 12, 5 categories, 21 sessions).
> This file is the pipeline entry-point for the augment layer.

## Session → Chapter alignment guide

This table maps the 5 teaching sessions onto the book's thematic arc.
Use this during 0d (chapter design) to align chapter boundaries with session content.

| Session | Category | Sessions covered | Likely chapter(s) |
|---------|----------|-----------------|-------------------|
| 01 | True Sources Of Knowledge | 1-4 (Intro, Glorifying Allah, How To Seek, Allegiance) | Ch01–02 |
| 02 | Spiritual Symbols | 5-7 (Root Principles, Symbols Based On Roots, Worldly Symbols) | Ch02–03 |
| 03 | Knowledge vs Actions | 8-11 (Three Levels, Power vs Strength, Acting With Knowledge, Differences/Purifying) | Ch03–04 |
| 04 | Disciple Becomes Master | 12-16 (Rebirth, Returning Home, Ka'ab Al-Ahbaar, Abu Malik Debates Saleh, Description of Religion) | Ch04–05 |
| 05 | Unity & Justice | 17-21 (Who is Allah, Intermediaries, Unbroken Chain, Return To Allah) | Ch05–06 |

## How to use this augment in the V2 pipeline

- **Phase 0d (chapter design)**: read `_synthesis.md` + per-session files alongside
  `_system/source/text/refined-english.md` when deciding chapter boundaries
- **Phase 0e (enrichment)**: pass per-session file for the corresponding chapter(s)
  as supplemental context; filter `[TEACHING-CONTEXT]` blocks unless the episode
  explicitly uses contemporary analogy
- **[BOOK-CONTENT]** tags = safe for direct use in episode framing
- **[TEACHING-CONTEXT]** tags = use only if the episode format calls for
  contemporary bridge material; never attribute to Syedna Jaffer or the book

## Source paths

- Arabic source images: `_system/source/images/page_0001.png` … `page_0095.png`
- OCR Arabic extract: `_system/source/ocr/raw-extract.md`
- OCR English translation: `_system/source/ocr/translated-en.md`
- Curator refined English: `_system/source/text/refined-english.md`
- Stitched PDF: `_system/source/ocr/source-stitched.pdf`

---

## Session inventory

### 01 — True Sources Of Knowledge
- **1.** Introduction To The Book — we begin the story and learn the importance of gratitude and etiquette in seekin
- **2.** Glorifying Allah — the scholar glorifies Allah and explains his design in the creation of this univ
- **3.** How To Seek Knowledge — the master and the disciple discuss the proper etiquette of learning
- **4.** Allegiance To Imam — Syedna Jaffer explains the importance of the Allegiance, and the role it plays i

### 02 — Spiritual Symbols
- **5.** Root Principles — the scholar begins revealing the signs within creation with mathematical precisi
- **6.** Symbols Based On Root Principles — the scholar continues revealing the symbols pointing to the signs of Allah. He e
- **7.** Worldly Symbols Pointing to Spiritual Entities — the author explains that everything in creation (from the tiny dust mote to the 

### 03 — Knowledge Vs Actions
- **8.** Three Levels of knowledge — explains the three levels of knowledge and who are operating at each.
- **9.** Power vs Strength — He reveals the interpretations of the phrase there is no power nor strength exce
- **10.** Importance Of Acting With Knowledge — the scholar explains how action subsists through knowledge and vice versa. He al
- **11.** Differences In Opinions — (no description)
- **12.** Purifying Posessions — the master and disciple part ways. The young man's fate brings him in the presen

### 04 — Disciple Becomes Master
- **13.** Rebirth Of The Disciple — the young man finally meets the Sheikh who leads him to the fulfillment of his s
- **14.** Returning Home — the young man, after completing his training returns home and becomes a source o
- **15.** Ka'ab Al-Ahbaar — we are introduced to a new character named Abu Malik, who is a famous scholar we
- **16.** ABU MALIK Debates SALEH — Abu Malik reaches out to the disciple (SALEH), and they begin their debate in or
- **17.** Description Of Religion — Saleh compares knowledge to jewels and provides a beautiful description of true 

### 05 — Unity And Justice
- **18.** Who is Allah? — Saleh explains the unity of Allah being more than a combination of nouns and adj
- **19.** Intermediaries Of Allah — Saleh explains to Abu Malik the necessity of Allah's intermediaries who act as a
- **20.** The Unbroken Chain — we learn why the scholars (IMAM & DUAAT) of our time have gone into hiding
- **21.** Return To Allah — the story concludes with Saleh explaining the oppression committed against the f
