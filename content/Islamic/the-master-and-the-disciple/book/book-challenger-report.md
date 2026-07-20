# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-20 16:05 EST (book_challenger_version 1.0)
**Scope:** whole-book
**Content profile:** islamic_scholarly
**Route:** augmented companion (`series-config.yaml` carries no `deliverable_mode`; `book_augmentation: source_only` = source-grounded augmentation ON, `book_voice: faithful`). `_system/translation-edition-manifest.json` records `mode: translation_edition, augmentation: forbidden`, so the stricter faithfulness posture was applied to everything outside the two labelled editorial notes.
**Declared narrative_frame:** `transmitted_report` (third person outside direct discourse)
**Chapters reviewed:** 8 + preface
**Iterations:** 1 (of 5 max)
**Verdict (book-level):** BLOCKED

> This run SUPERSEDES the 2026-07-20 13:16 EST report in every particular. None of
> BK1-BK11 from that run were carried forward. Every item below was re-derived from
> `book/book.md` at commit 8a9c1e7 (working tree clean), `_system/source/ocr/raw-extract.md`,
> `content/knowledge-base/mirror.db` (`fts_quran`), and `book/_chunks/translation/`.

---

## Repair confirmations — the eleven prior findings, re-verified

| Prior | Check | Status on current text | Evidence |
|---|---|---|---|
| BK1-BK3 | BK-N5 supplied diacritics, 3 non-Quranic runs | **FIXED** | book.md 188 `فإنه من عمل لله بما يعلم…`, 841 `ولكن المؤمن ينظر بنور الله`, 1279 `شهد فلان وهو عدل من العدول` — all three now bare, matching `raw-extract.md` 255 / 1189 / 1923-1924. `_narrative.ocr_vowelling_findings` returns empty on all 9 sections. |
| BK4 | BK-N7 one term, two renderings | **FIXED (with residue)** | `The scholar said` = 0 occurrences; `The Master said` = 112; `The Shaykh said` = 13. The Shaykh of ch7 remains a distinct character. Residue at two lines — see BK4 below. |
| BK5 | BK-A1 ch5 quoting convention | **FIXED (with residue)** | ch5 is now 58 quoted / 2 unquoted speech tags, in line with ch3 (50/2), ch7 (87/1), ch8 (124/1). Residue at 316-322 — see BK5 below. |
| BK6 | BK-P4 false internal cross-reference | **FIXED** | The ch5 note (458-471) now cites "the chapter on how the world was made", which exists (ch4, book.md 232). Every claim it makes — three words will/command/saying, seven letters of *kun fa-yakun*, pairs apparent/inward, body-and-soul — is verified present at book.md 234-240, 242, 278. No "sphere", "emanation" or "mineral" doctrine remains anywhere in the note. |
| BK9 | BK-P6 five-vs-seven enumeration | **FIXED** | Note 464-465 now lists all seven: "air, water, light, darkness, food, clothing, and marriage", matching book.md 298 exactly. |
| BK7 | BK-A3 duplicated preface heading | **FIXED** | Line 3 is the sole heading; line 5 opens the body ("We have been informed that…"). The orientation half of BK7 is still open — see BK7 below. |
| BK10 | BK-A3 stale `voice` field | **FIXED** | `book-toc.json:1` → `"voice": "transmitted report, third person"`, matching `narrative_frame: transmitted_report`. |
| BK8 | BK-A4 broken sh-r root | **FIXED** | book.md 99 reads `The root of *Sharia* (sh-r-')` — three radicals, with `'` for ʿayn, the same plain-transliteration convention the book uses at `du'at` (340) and `ta'wil` (344). |
| BK11 | BK-P6 duplicated English gloss | **FIXED** | book.md 839-843: lead-in now ends "none knows the unseen but Allah." and the gloss under the Arabic reads "But the believer sees by the light of Allah." — no repetition. |
| — | "Sharia" spelling | **CONFIRMED single spelling** | 6 occurrences (99, 336, 1079, 1085, 1089, 1093), all `Sharia`. Zero variants. Full Latin-diacritic sweep of the whole file returns **zero** non-ASCII letters outside Arabic script and typographic dashes/quotes — BK-A4 clean. |

---

## Per-chapter verdicts

| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface — How to Read a Conversation Made of Doors | pass | pass | SHIP-READY (P2 only) |
| 1. The Persian Who Was Dead and Revived | pass | pass | SHIP-READY |
| 2. A Stranger in the City | pass | **fail** (BK-N5) | **BLOCKED** |
| 3. The Boy at the Door — Limits and Conditions | pass | pass | SHIP-READY |
| 4. How the World Was Made | pass | pass | SHIP-READY |
| 5. The World, the Hereafter, and the Speech of Parables | **fail** (BK-P6) | pass | SHIP-WITH-CAUTION |
| 6. Three Layers of Knowledge | pass | pass | SHIP-READY |
| 7. The Five Shares and the Long Road to the Shaykh | **fail** (BK-P1, BK-P4) | **fail** (BK-N7) | **BLOCKED** |
| 8. Homecoming, the Father, and the Debate with Abu Malik | pass | **fail** (BK-N7) | SHIP-WITH-CAUTION |

## Whole-book passes

| Check | Result |
|---|---|
| BK-P1 no-teaching-lost | **fail** — two sentences of §302 absent from chapter 7 (BK11); all other sections clean, ratios 0.98-1.25, proper-noun diff resolves to rendering choices |
| BK-P2 verbatim-quote survival | pass — `arabic_retention_findings` empty in all 9 sections; every one of the 30 Arabic display runs carries an English gloss within 4 lines |
| BK-P3 Arabic-script accuracy | pass — 22 canonical-mushaf, 28 OCR-grounded, 1 honorific; all Quranic runs independently re-matched against `fts_quran` |
| BK-A1 voice consistency | **fail** — speech-tag punctuation and dialogue style split by chapter (BK3), plus two local breaks (BK5, BK8) |
| BK-A2 segmentation sanity | pass — TOC covers source lines 8-1353 contiguously with no gap; titles evocative, none clause-lifted |
| BK-A3 preface + TOC integrity | **fail (P2)** — heading sequence matches `book-toc.json` and the duplicate is gone, but the preface still does not orient a modern reader |
| BK-A4 plain transliteration | pass — zero scholarly diacritics in Latin text anywhere in the file |
| BK-A5 tradition fit | pass — 13 `doctrine:wisdom:*` atoms + `etymology:shr` in `_system/augment-used-ledger.json`, all Ismaili/al-Anwaar corpus, matched to Ja'far b. Mansur al-Yaman |
| BK-N1 narrative person | pass — `narrative_person_findings` clean on all 9 sections under `transmitted_report` |
| BK-N2 speech attribution integrity | pass (with a caution folded into BK6) — `speech_tag_findings` empty book vs base; no tag added to an untagged paragraph, none re-pointed |
| BK-N3 frame consistency | pass — one anonymous transmitter throughout; `The narrator said` x4 (ch3, ch7), `The author said` once at 1391 (the source's own colophon), no chapter narrated by a character |
| BK-N4 Arabic script retention | pass — no Arabic run in the base is absent from the book; `كُنْ`/`فَيَكُونُ` discussed as letters keep the script (242) |
| BK-N5 supplied diacritics | **fail** — one run, book.md 89 (BK1) |
| BK-N6 enumeration preserved | pass — ch5 (a)-(g) survives 7/7; the five shares (675) and six qualities (827) intact |
| BK-N7 register + terminological consistency | **fail** — BK4, BK6, BK9 |
| Seam integrity ch7 (3 windows) | **fail** — window-2/window-3 overlap printed twice (BK2) |
| Seam integrity ch8 (5 windows) | pass — all four joins verified non-overlapping against `_chunks/translation/bk-08-part-0N.md` |

### Where the book is MORE faithful than `refined-english.md`

Recorded so a future run does not "restore" them. In each case `book.md` follows the Arabic scan and the refined English was wrong.

| book.md | refined-english.md | OCR / correct reading |
|---|---|---|
| 1161 "you have carried us away from the first meaning" | §459 "you have departed from the meaning of the Qur'an" | `raw-extract.md:1709` — `لقد خرجت بنا عن المعنى` (no Qur'an in the Arabic) |
| 1077 "a distressed man came to you" | §414 "a man came to you — Maqrub" | `مكروب` = distressed; the refined text read a descriptor as a proper name |
| 1393 "the radiant leader of the bright-marked" | §558 "the leader of the Muhajirun" | `قائد الغر المحجلين` — the book's reading is correct |

---

## Findings (P0 -> P1 -> P2)

### BK1 · BK-N5 · P0 · VERIFIED
- **Chapter:** 2 — A Stranger in the City
- **book.md:** 89 — `فَتَبَارَكَ الَّذِي جَعَلَ اللَّيْلَ وَالنَّهَارَ خِلْفَةً لِمَنْ أَرَادَ أَنْ يَذَّكَّرَ أَوْ أَرَادَ شُكُورًا، وَصَلَّى اللَّهُ عَلَى مَنِ اخْتَارَهُ مِنْ عِبَادِهِ وَجَعَلَهُ لِلْعَالَمِينَ نَذِيرًا.`
- **Source:** `_system/source/ocr/raw-extract.md` 103-105 — `فتبارك الذي جعل الليل والنهار` / `خلفة لمن أراد أن يذكّر أو أراد شكورًا، وصلى الله على من اختاره من٧` / `عباده وجعله للعالمين نذيراً.`
- **Why it fails:** the scan carries this run essentially bare — three marks in twenty-three words (`يذكّر`, `شكورًا`, `نذيراً`) — and the book prints full tashkeel throughout. The middle of the run is Quran 25:62 verbatim and its vowelling is canonical and legitimate; the opening `فَتَبَارَكَ` and the nine-word closing doxology `وَصَلَّى اللَّهُ عَلَى مَنِ اخْتَارَهُ مِنْ عِبَادِهِ وَجَعَلَهُ` are the author's own sermon words, and their vowel marks were written from model memory, not carried from the scan. This is the same defect class as the repaired BK1-BK3, at a site the earlier sweep did not reach. It was introduced at the TRANSLATION stage (`book/_chunks/translation/bk-02.md:43` already carries it fully vowelled), which is why `ocr_vowelling_findings` stays silent: that helper only judges a run whose skeleton sits inside the concatenation of the scan's *unvowelled* spans, and this scan span is itself lightly vowelled.
- **Worker action:** strip tashkeel from `فتبارك` and from everything after `شكورًا،`, leaving the Q 25:62 core vowelled. Do not touch any run the audit resolves `canonical-mushaf`.

### BK2 · BK-P4 · P0 · VERIFIED
- **Chapter:** 7 — The Five Shares and the Long Road to the Shaykh
- **book.md:** 815-819 and 821-825 — 815 `Then the two rose, clasped hands, and embraced, each bidding the other farewell… The Master and the boy set out and traveled on until they drew near the boy's own city, where his father was.` / 821 `Then they stood, clasped hands, and embraced, and each gave his friend farewell… Then they went their separate ways.` / 823 `So the Master and the boy set out together, and when they had come near to the boy's own city…`
- **Source:** `_system/source/text/refined-english.md` 731-737 (§300-302) — the embrace, the departure, the sitting down off the road, and the counsel about the father occur **once**. `raw-extract.md` confirms a single occurrence.
- **Why it fails:** the parting from the Shaykh, the journey to the boy's city, the sitting down off the road and the Master's counsel about the father are all printed **twice**, in two different wordings, five paragraphs apart. This is the chapter-7 windowing overlap: `_chunks/translation/bk-07-part-02.md` ends with these beats and `bk-07-part-03.md` re-narrates them as its opening context, and the two windows were concatenated without de-duplication. A reader of the printed edition sees the two men say goodbye twice.
- **CORRECTION (2026-07-20 16:40, on coordinator challenge):** the first draft of this finding said the second telling was the faithful one and the first could be deleted wholesale. **That was wrong.** A clause-by-clause comparison against `raw-extract.md` 1146-1165 (§300-302) shows the two tellings are each faithful in different places, so neither can be cut whole. The first telling alone carries `لا يملك نفسه من العبرة` ("unable to hold back his tears"), `رأي والدي بالاستتار في بعض هذه البادية` ("my own father's counsel … keep hidden somewhere in this open country" — the second telling misreads this as "honor your father's mind by keeping some of these matters veiled"), `ويسكن عنا بأسه` ("his anger toward us may subside" — the second telling loses the anger), and the opening of `واعلم يا بنيي أن الله قد فتح لك بأهون سعيك`. The second telling alone carries §301's `ولا تعرف` ("and you have not") and the whole close of §302 (`وعليك بحفظ أمانتك` onward). The correct repair is a merge, not a deletion — see BK11.
- **Worker action:** replace book.md 815-825 with the single merged passage set out in the hand-off note; do not delete either telling wholesale.

### BK3 · BK-A1 · P1 · VERIFIED
- **Chapter:** whole book
- **book.md:** 49 `They said, "Who are you, young man…"` (ch2) vs 118 `The boy said: "The absence of any excuse has frightened me…"` (ch3) vs 1349 `"You have spoken the truth, O Abu Malik," said Salih.` (ch8)
- **Why it fails:** three different typographic conventions for the same dialogue form, distributed by chapter rather than by any property of the text. Comma-before-quotation dominates chapters 2 (16 vs 2) and 6 (46 vs 0); colon-before-quotation dominates chapters 3 (50 vs 1), 5 (58 vs 2) and 7 (95 vs 0); chapter 8 mixes both (130 colon, 43 comma) and additionally introduces 71 quote-first inverted tags, clustered at lines 1290-1390, where chapters 1-7 have five between them. A reader crossing from chapter 5 to chapter 6, and again into the last stretch of chapter 8, meets what reads as a different book's typesetting. This is the running style-anchor failing per window, not per chapter.
- **Worker action:** pick one convention — the colon form is the book's plurality and suits the catechetical register — and normalise every speech tag in all nine sections, including the inverted tags in chapter 8's final window.

### BK4 · BK-N7 · P1 · VERIFIED
- **Chapter:** 7 — The Five Shares and the Long Road to the Shaykh
- **book.md:** 723 — `the two set out together until they reached the greater scholar` / 727 — `They remained with the scholar for a time, until the boy's affair was completed`
- **Source:** `refined-english.md` 626 (§256) "until they reached the greater scholar"; 634 (§259) "they stayed with the master for some time"
- **Why it fails:** the BK4 repair normalised `العالم` to "the Master" 112 times, but two references to the SAME class of figure survive as "scholar". Within five lines the reader meets "the greater scholar" (723), "the scholar" (727), "The shaykh who was master of that house" (727, the host — lowercase), "the Master" (729, 735) and "the Shaykh" (739, the great initiator). Five labels for three men, and the only thing separating the host from the initiator is the capital S on *Shaykh*, twelve lines apart. The source is itself loose here; a reading edition is where that gets resolved, not reproduced.
- **Worker action:** render `العالم الأكبر` consistently with the book's own choice — "the greater Master" or "the elder Master" — carry it to 727, and give the host a fixed non-*shaykh* designation ("the master of the house") so the capitalised *Shaykh* names exactly one man.

### BK5 · BK-P6 · P1 · VERIFIED
- **Chapter:** 5 — The World, the Hereafter, and the Speech of Parables
- **book.md:** 316-322 — `The Master said: "What is the reward of the one who brought you out from the narrowness of poverty into the breadth of ease?` / `He said: Thanks and praise."` / `The Master said: "And what is the reward…of knowledge?` / `He said: Obedience and action."`
- **Source:** `refined-english.md` 261-267 (§101-104) — four separate untagged turns, two questions and two answers.
- **Why it fails:** the Master's opening quotation mark is closed only at the end of the boy's reply, so on the printed page the boy's answers sit **inside** the Master's speech. The tags themselves are correct and untouched (BK-N2 passes), but the punctuation attributes "Thanks and praise" and "Obedience and action" to the wrong speaker for any reader who follows quotation marks. It is the last surviving pocket of the ch5 convention break that BK5 repaired everywhere else.
- **Worker action:** close the Master's quotation at each question mark and quote the boy's two replies in their own right.

### BK6 · BK-N7 · P1 · VERIFIED
- **Chapter:** 8 — Homecoming, the Father, and the Debate with Abu Malik
- **book.md:** 1291 — `Salih pressed the point further.` / 1297 — `Abu Malik conceded the ground.` / 1307 — `"Then what has shut us out of that justice?" Salih pressed.`
- **Source:** `refined-english.md` 1261 (§519) `Salih said to him`; 1267 (§522) `Abu Malik said`; 1269 (§523) `Salih said to him`
- **Why it fails:** three bare `قال` tags have been replaced with narratorial verdicts on how the debate is going. Under `transmitted_report` the narrator conveys and does not adjudicate; "conceded the ground" tells the reader who is winning, which is precisely the judgment the source leaves to him. The speaker attribution is correct in all three, so this is not BK-N2, but it is the translator becoming visible in the one chapter the book builds to. Introduced at the translation stage (`_chunks/translation/bk-08-part-05.md` carries the same wording), which is why the deterministic tag check is clean.
- **Worker action:** return the three to plain attribution ("Salih said", "Abu Malik said").

### BK7 · BK-A3 · P2 · VERIFIED
- **Chapter:** preface — How to Read a Conversation Made of Doors
- **book.md:** 5-27 — `We have been informed that some groups among the believers, and a number of the preachers of religion, came to a Master among them…`
- **Source:** `refined-english.md` 8-13
- **Why it fails:** the preface is a translation of the source's own opening paragraphs, so the reading edition opens with source material under a title that promises orientation. It never tells a modern reader who Ja'far b. Mansur al-Yaman was, who the two speakers are, what an anonymous transmitted report is, or why a tenth-century Fatimid dialogue still matters. The translator's introduction remains the edition's missing apparatus.
- **Worker action:** author a genuine reader-facing preface and let the translated §1-3 stand as the book's own opening chapter or as an appendix.

### BK8 · BK-A1 · P2 · VERIFIED
- **Chapter:** 2 — A Stranger in the City
- **book.md:** 85-87 — 85 opens `Then he said: "He who created the creation by His power…` and ends `…the keepers of the Word, the noble scribes,`; 87 begins `a trust which they discharge…` with no re-opening quotation mark and ends `…to seek knowledge and sufficiency.` with none closing.
- **Why it fails:** the sermon's quotation is opened and never closed. The book's own convention elsewhere (1163, 1257, 1355) re-opens every continuation paragraph with `"`. Here a reader is left inside an unterminated quotation across two long paragraphs and a display block.
- **Worker action:** re-open 87 with `"` and close the sermon before the blockquote at 89, or close it at the end of 87.

### BK9 · BK-N7 · P2 · VERIFIED
- **Chapter:** 8 — Homecoming, the Father, and the Debate with Abu Malik
- **book.md:** 857 — `"Name them," said the Shaykh. "What are the two?"` / 861, 865 — `The Shaykh said:` / `The Shaykh's heart was rent by his son's words.`
- **Source:** `refined-english.md` 768-776 (§314, §316, §318) — the source calls al-Bakhtari `الشيخ` here.
- **Why it fails:** the capitalised title *the Shaykh* denotes the boy's father al-Bakhtari at 857-865 and the great initiator of chapter 7 at 739-811, roughly fifty lines apart with no disambiguation. The source licenses it — both men are `الشيخ` — but a reading edition inherits the ambiguity into a context where chapter 7's Shaykh has just spoken at length. Only the surrounding narration at 849-853 ("Then his father came in upon him, angry") keeps the reader straight.
- **Worker action:** render al-Bakhtari as "his father" or "the old man" in these tags, or add a one-line editorial gloss at the chapter opening.

### BK10 · BK-P3 · P2 · VERIFIED (tooling, not a book defect)
- **Chapter:** 6 — Three Layers of Knowledge
- **book.md:** 557 — `فَلَا تَغُرَّنَّكُمُ الْحَيَاةُ الدُّنْيَا`
- **Source:** `content/knowledge-base/mirror.db` `fts_quran` — Q 31:33 and Q 35:5, `فَلَا تَغُرَّنَّكُمُ ٱلْحَيَوٰةُ ٱلدُّنْيَا`
- **Why it fails:** `_system/book-arabic-audit.json` reports this run `unverified` — the single unverified run in the whole book. It is canonical Quran; `_mushaf.is_quranic` misses it because the book sets Quran in modern imla'i (`الْحَيَاةُ`) while the table stores Uthmani (`ٱلْحَيَوٰةُ`), and the skeleton normaliser does not fold `حياة`/`حيوة`. Verified canonical by direct query during this sweep. The imla'i choice is applied consistently across the book and is a legitimate editorial decision. Recorded so no future run "repairs" a correct verse, and so the discriminator can be extended.
- **Worker action:** none on `book.md`. Extend the `_mushaf` skeleton fold to cover the Uthmani waw-alif spellings (`حيوة`/`حياة`, `الصلوة`/`الصلاة`, `زكوة`/`زكاة`).

### BK11 · BK-P1 · P0 · VERIFIED
- **Chapter:** 7 — The Five Shares and the Long Road to the Shaykh
- **book.md:** 819 ends `…what He has opened for none before you.` and 825 runs `…his solitude has become a fright to him. So you must guard the trust your father laid upon you…`
- **Source:** `_system/source/ocr/raw-extract.md` 1158-1163 (§302) — `واعلم، يا بنيّ، أن الله قد فتح لك بأهون سعيك ما لم أظن أنك بالغه إلا بعد مدّة. وقد أحسن الله إليك، فأحسن إلى نفسك، وأكرم من أكرمك الله به. فقد حسن ظننا بك وعظم رجاؤنا فيك.`
- **Why it fails:** the chapter-7 duplication was concealing a real omission. Two source sentences — "God has been good to you, so be good to yourself, and honor the one through whom God has honored you" and "our opinion of you has been good and our hope in you great" — are absent from **both** tellings, so they are absent from the book. A third, `ما لم أظن أنك بالغه إلا بعد مدّة` ("what I did not think you would attain except after a long while"), survives only as the mistranslation "what He has opened for none before you" at the end of 819. The per-chapter word ratio missed this because the duplicate inflated chapter 7 to 1.08.
- **Worker action:** restore the two omitted sentences and correct the third inside the merged passage, at their source position — between `…the loneliness has distressed him.` and `So you must guard the trust…`.

---

## Verified vs Inferred summary

| | Count |
|---|---|
| VERIFIED (concrete evidence in the files) | 11 |
| INFERRED (heuristic judgment) | 0 |

Every finding cites a `book.md` line, and every fidelity finding cites the OCR scan line, the refined-source paragraph, or the mushaf reference it was checked against. No finding rests on model recall of Arabic.

## Ledger emission summary

10 records appended to `_learning/findings.jsonl` with `source: "book-challenger"`, ids BK1-BK10, all `resolution: "flagged"`, deduped within the run by signature.

## Verdict

**BLOCKED** — three P0 records. BK1 (supplied vowelling on the non-Quranic parts of the chapter-2 sermon close) and BK2 (the chapter-7 farewell episode printed twice from an undeduplicated window overlap). Clearing both moves the book to SHIP-WITH-CAUTION on four P1s — BK3 speech-tag convention split, BK4 residual "scholar" labels, BK5 chapter-5 quotation-mark mis-attribution, BK6 interpretive speech tags in chapter 8 — of which BK3 and BK4 are mechanical and BK5/BK6 are small enough to fix by hand through the Book Composer. Both P0s are narrow, deterministic repairs; neither needs a re-compose of the whole book.
