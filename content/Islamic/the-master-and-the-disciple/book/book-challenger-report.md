# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-20 13:16 EST (book_challenger_version 1.0)
**Scope:** whole-book
**Content profile:** islamic_scholarly
**Route:** augmented companion (`book_augmentation: source_only` = augmentation ON, source-grounded; `book_voice: faithful`)
**Declared narrative_frame:** `transmitted_report` (third person outside direct discourse)
**Chapters reviewed:** 8 + preface
**Iterations:** 1 (of 5 max)
**Verdict (book-level):** BLOCKED

> This run SUPERSEDES the pre-repair report previously on disk. None of that run's findings
> were carried forward; every item below was re-derived from the current `book.md`,
> the OCR scan, the canonical mushaf, and the base translation chunks.

---

## Route note — a correction carried into this run

`book_augmentation: source_only` means source-grounded augmentation is **ON** (`none` = off).
The two `Editorial note (source-grounded)` blocks (book.md 97-108, 460-471) are therefore
**legitimate output of this route**, not a violation of any no-outside-augmentation rule.
They are judged here on accuracy and tradition fit only. Their grounding atoms are recorded in
`_system/augment-used-ledger.json` (13 `doctrine:wisdom:*` atoms + `etymology:shr`), all from the
al-Anwaar al-Lateefah / Ismaili corpus — tradition-appropriate to Ja'far b. Mansur al-Yaman.
**BK-A5 tradition fit: PASS.**

---

## Requested repair confirmations

### 1. Chapter 8 Arabic at book.md 1266 — the dropped-divine-name claim was WRONG. CONTRADICTED.

The scan carries **both** forms, at two different sites, and the book renders each at its own
site with a matching English gloss. Asif's reading is correct; the earlier finding is withdrawn.

| Site | book.md | Arabic | Gloss | OCR ground truth |
|---|---|---|---|---|
| Abu Malik's defence | 892 | `وإن الله كل يوم هو في شأن` | "Indeed, every day He is engaged in some matter." | **raw-extract.md:1306** (page 58) — `الله فيهم وإرادته منهم، ولو اجتهدوا، وإن الله كل يوم هو " في شأن.` |
| Salih's rebuttal | 1266 | `وإنه كل يوم هو في شأن` | "And truly, every day He is engaged in some affair." | **raw-extract.md:1903-1904** (page 84) — `والخالق أولى بالخلق والأمر ١٢ وإنه كل يوم هو ١٣` / `في شأن١٤، ولا ينكر فعله ولو بعث في كل يوم نذيراً.` |

The English immediately above each block also tracks its own scan line: 892's lead-in renders
OCR 1304-1306 ("nor will the creation ever reach the end of Allah's decree in them and His will
for them, however hard they strive"); 1266's lead-in renders OCR 1901-1904 ("The Creator is
foremost over the creation and over the command… even were He to send a warner every day").
Neither run is vowelled, matching the bare scan. **Repair (a) fabricated vowelling: fixed and
verified. Claim (b) dropped divine name: not a defect — no finding raised.**

### 2. Arabic blockquote consistency — CONFIRMED book-wide.

51 lines of `book.md` contain Arabic. **43 are display runs and all 43 carry the `>` blockquote.**
The 8 that do not are inline glosses inside running prose, which is the correct treatment:
`حزب الله` (232), `كُنْ`/`فَيَكُونُ` discussed AS LETTERS (244), `أولياء الله` (280),
`كعب الأحبار` (870), and the honorific `(ع)` / `(عليهم السلام)` (534, 542, 1240, 1258).
Zero display runs remain unfenced, including the six at the end of chapter 8.

### 3. `sunna` in chapter 4 — CONFIRMED consistent; but the SAME defect is live elsewhere.

Chapter 4 renders `السنة` as *sunna* at all three occurrences (book.md 258 x2, 272), matching the
base chunk `bk-04.md` (3 x `sunna`, 0 x `way`). OCR sites 354-355 and 413 are all covered.

The book-wide sweep, however, found a **larger instance of the same defect on the book's central
character** — see finding BK4 below. It is inherited from the base translation stage, not
introduced by the de-calque pass.

---

## Per-chapter verdicts

| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface — How to Read a Conversation Made of Doors | pass | pass | SHIP-READY (P2 only) |
| 1. The Persian Who Was Dead and Revived | pass | pass | SHIP-READY |
| 2. A Stranger in the City | pass | pass | SHIP-READY (P2 only) |
| 3. The Boy at the Door — Limits and Conditions | pass | **fail** (BK-N5, BK-N7) | BLOCKED |
| 4. How the World Was Made | pass | pass | SHIP-READY |
| 5. The World, the Hereafter, and the Speech of Parables | **fail** (BK-P4) | **fail** (BK-N7) | SHIP-WITH-CAUTION |
| 6. Three Layers of Knowledge | pass | **fail** (BK-N5) | BLOCKED |
| 7. The Five Shares and the Long Road to the Shaykh | pass | **fail** (BK-N7) | SHIP-WITH-CAUTION |
| 8. Homecoming, the Father, and the Debate with Abu Malik | pass | **fail** (BK-N5, BK-N7) | BLOCKED |

## Whole-book passes

| Check | Result |
|---|---|
| BK-A1 voice consistency | **fail** — ch5 quoting convention diverges (BK5) |
| BK-A2 segmentation sanity | pass — TOC ranges 8-1353 contiguous, no gaps, titles evocative |
| BK-A3 preface + TOC integrity | **fail (P2)** — duplicated heading line, no reader orientation, stale `voice` field |
| BK-A4 plain transliteration | pass — zero scholarly-diacritic leaks in Latin text (one broken root, BK8) |
| BK-A5 tradition fit | pass — enrichment atoms are Ismaili corpus, matched to an Ismaili source |
| BK-N1 narrative person | pass — deterministic clean on all 9 sections; no first-person narration outside quoted speech |
| BK-N2 speech attribution integrity | pass — interior-tag gate clean; ch8 speaker alternation matches source (ratio 0.88, zero swap opcodes) |
| BK-N3 frame consistency | pass — one transmitted narrator throughout; `The narrator said` used identically in ch3/6/7 |
| BK-N4 Arabic script retention | pass — set-difference of Arabic skeletons book vs base = empty in all 9 sections |
| BK-N5 supplied diacritics | **fail** — 3 non-Quranic runs vowelled beyond the scan (BK1-BK3) |
| BK-N6 enumeration preserved | pass — ch5 lettered series (a)-(g) survives 7/7 |
| BK-N7 register + terminological consistency | **fail** — one Arabic term, two English renderings (BK4) |
| Seam integrity ch7 (3 windows) | pass |
| Seam integrity ch8 (5 windows) | pass |
| Teaching + citation fidelity vs `_chunks/translation/` | pass — no named person, Arabic run, or citation added or dropped in any chapter |

### Seam detail

Joined paragraph counts equal the sum of the window paragraph counts exactly in both chapters
(ch7 126 = 126 across 3 windows; ch8 271 = 271 across 5 windows) — no material duplicated or
dropped at any join. The only repeated paragraphs in ch8 are the legitimate short affirmations
(`He said: "Yes."` x4, `He said: "Allah."`), each at its own point in the catechism.
The ch7 window-1/2 boundary falls mid-sentence in the base (`…whose palms are opened` /
`with the light of Sinai`); the composed book heals it into one sentence at line 684. Verified.

### Chapter-7 seam bonus: the book is MORE faithful than the refined source

At book.md 684 the book reads "keys of the **gardens**"; `refined-english.md:578` reads
"keys of the heavens". OCR `raw-extract.md:967` has `من بيده مفاتيح الجنان ومعالم الملكوت` —
*al-jinan*, the gardens. The book is right and the refined English was wrong. Same pattern at
book.md 1226: the refined source reads "the **seven** creations of the unseen" (¶492) where OCR
1807 has `ولم يبيّنوا من ٧ الخلق بالغيب` — the `٧` is a footnote marker, not the numeral. The
book's "the hidden things among creation" is the correct reading. Neither is a finding; both are
recorded because a future run must not "restore" them.

### Arabic provenance ledger

36 audited runs (`_system/book-arabic-audit.json`): 16 canonical-mushaf, 34 OCR-grounded, 1
honorific formula. Every Quranic run was independently re-verified against `fts_quran` in
`content/knowledge-base/mirror.db` during this sweep, including the five the automatic
discriminator missed — those misses are **orthographic, not textual**: the book sets Quran in
modern imla'i script while the mushaf table stores Uthmani, so substring matching fails on
`الْحَيَاةُ` vs `ٱلْحَيَوٰةُ`, `قَاتِلُوا` vs `قَٰتِلُوا`, `بَقَرَاتٍ` vs `بَقَرَٰتٍ`, `آتَيْنَاهُ` vs `وَءَاتَيْنَٰهُ`.
Targeted root queries confirm all five: **Q 31:33 / 35:5, Q 9:123, Q 12:4, Q 12:43, Q 28:76**.
The imla'i choice is consistently applied and is a legitimate editorial decision — no finding.
Three verses (Q 12:4, Q 12:43, Q 31:33) are supplied Arabic for verses the source cites in prose
only; that is the augmented route working as designed, and all three are canonical. **BK-P3
passes for every Quranic run in the book.**

---

## Findings (P0 → P1 → P2)

### BK1-BK3 · BK-N5 · P0 · VERIFIED
- **Chapter:** 3 (The Boy at the Door), 6 (Three Layers of Knowledge), 8 (Homecoming / Abu Malik)
- **book.md:** 190 — `فإنَّه مَن عمِلَ للهِ بما يعلم، هداه اللهُ إلى ما لا يعلم.`
  **Source:** `_system/source/ocr/raw-extract.md:255` — `والعمل من ذلك بما تعلم. فإنه من عمل لله بما يعلم، هداه الله إلى ما لا١` (bare)
- **book.md:** 842 — `وَلَكِنَّ الْمُؤْمِنَ يَنْظُرُ بِنُورِ اللَّهِ`
  **Source:** `raw-extract.md:1189` — `الله، ولكن المؤمن ينظر بنور الله٢. وأما الزيادة…` (bare)
- **book.md:** 1280 — `شَهِدَ فُلَانٌ وَهُوَ عَدْلٌ مِنَ الْعُدُولِ`
  **Source:** `raw-extract.md:1923-1924` — `(٥١٤) قال: بلى عدل١ٌ كما يقال "شهد فلان وهو عدل من` / `العدول".` (bare)
- **Why it fails:** all three are the source's OWN reported sayings, not Quran; the scan carries
  them unvowelled and the book supplies full tashkeel. Vowel marks written from model memory onto
  a reported saying are fabricated scripture, which is the one defect this book cannot ship with.
  The vowelling happens to be grammatically correct in all three cases, so no doctrine is altered —
  but its provenance is the model, not the scan.
- **Not a finding:** the fourth entry on `vowelling_review`, `فَيَكُونُ` (book.md 244), is the
  Quranic word of Q 2:117 discussed as letters; its vowelling is canonical. The discriminator
  missed it only because the standalone token is below the mushaf-match length floor.
- **Worker action:** strip tashkeel from these three runs so they match the scan. Do NOT touch
  the vowelling on any run resolved `canonical-mushaf`.

### BK4 · BK-N7 · P1 · VERIFIED
- **Chapter:** book-wide — preface + 1-4 vs 5-8
- **book.md:** 122 — `The Master said: "God did not create men already scholars…"` / 310 — `The scholar said: This world, and all that I have described to you of it, is an apparent standing over an inward.`
- **Source:** `_system/source/ocr/raw-extract.md` — `قال العالم` x109 (one invariant tag); `refined-english.md` — "The scholar said" x108 vs "The Master said" x3
- **Why it fails:** one Arabic term for the book's title character is given two English renderings
  split cleanly by chapter — "the Master" 37x in the preface and chapters 1-4 (27 of them speech
  tags in ch3), "the scholar" 125x in chapters 5-8 (84 speech tags). Chapter 3's own source range
  has 25 "The scholar said" against 2 "The Master said", so the book overrode its own source in
  one direction there and in the other direction later. A reader tracking the cast then meets
  three names for two men, because chapter 7 correctly introduces the genuinely distinct
  `الشيخ` / "the Shaykh". Inherited from the base translation chunks (`bk-03.md` vs
  `bk-05..08.md`), so it predates the de-calque pass.
- **Worker action:** pick ONE rendering for `العالم` and apply it to every speech tag and every
  narrative reference in all nine sections. "the Master" matches the book's own title; whichever
  is chosen, `الشيخ` must stay distinct as "the Shaykh".

### BK5 · BK-A1 · P1 · VERIFIED
- **Chapter:** 5 (The World, the Hereafter, and the Speech of Parables)
- **book.md:** 286 — `The boy said: This world, in which so vast a creation was set down, holds a great multitude…`
- **Why it fails:** chapter 5 sets 60 of its 62 speech attributions WITHOUT quotation marks
  (`The scholar said: …`), while chapters 2, 3, 6, 7 and 8 quote speech almost universally
  (19 / 50 / 46 / 91 / 138 quoted vs 0 / 2 / 2 / 2 / 3 unquoted). One chapter in nine uses a
  different typographic convention for the same dialogue form. This is the running style-anchor
  failing at exactly the chapter that also switches "Master" to "scholar" (BK4), so a reader hits
  both breaks at the same page.
- **Worker action:** re-compose ch5 to the book's dominant convention — quoted direct speech.

### BK6 · BK-P4 · P1 · VERIFIED
- **Chapter:** 5 (The World, the Hereafter, and the Speech of Parables)
- **book.md:** 462-465 — `…sits atop a wider cosmology this book elsewhere sets out. There, the whole ordered succession of the celestial spheres has a stated purpose: to generate minerals, plants, animals, and human seed upon this terrestrial realm, each sphere exerting its influence in its appointed turn.`
- **Source:** no source range — the tokens "sphere(s)" and "emanation" appear in `book.md` ONLY
  inside this editorial note (lines 464, 465, 470); the sole other "sphere" hits (378) are the
  ring-and-egg cosmography, and "minerals" (330) is the parable of gold, silver and gem.
- **Why it fails:** the note makes a false INTERNAL cross-reference. The celestial-sphere doctrine
  is real and correctly sourced (`doctrine:wisdom:*` atoms in the augment ledger, tradition-
  appropriate — BK-A5 passes), but it is not in this book, and a reader of the published edition
  will go looking for it and not find it. The material is admissible; the attribution is not.
- **Worker action:** re-word to attribute the cosmology to the wider corpus, as the note's own
  later sentence already does correctly ("The same corpus also marks a contrast…").

### BK7 · BK-A3 · P2 · VERIFIED
- **Chapter:** preface — How to Read a Conversation Made of Doors
- **book.md:** 3-5 — `## How to Read a Conversation Made of Doors` / (blank) / `How to Read a Conversation Made of Doors`
- **Why it fails:** the heading is repeated verbatim as the first body paragraph — a visible
  double title on the opening page of the PDF. Separately, the preface body (lines 7-29) is a
  translation of source ¶1-3 (`refined-english.md` 8-13) rather than an orientation: it never
  tells a modern reader who is speaking, to whom, or why the text still matters.
- **Worker action:** delete the duplicated line; author a genuine reader-facing preface (the
  translator's introduction already logged as missing apparatus for this edition).

### BK8 · BK-A4 · P2 · VERIFIED
- **Chapter:** 2 (A Stranger in the City)
- **book.md:** 102 — `The root of *Sharia* (sh-r-) means to open up a path`
- **Why it fails:** the sentence names a three-consonant root and prints two letters. The
  transliteration fold stripped the `ʿayn` and left `sh-r-` dangling, so the note contradicts
  itself in print. Correct form: `sh-r-'` (ش ر ع).
- **Worker action:** render the third radical in the plain-transliteration scheme rather than
  letting the diacritic fold delete it.

### BK9 · BK-P6 · P2 · VERIFIED
- **Chapter:** 5 (The World, the Hereafter, and the Speech of Parables)
- **book.md:** 466-467 — `So the seven-fold blessings the chapter lists (air, water, light, food, marriage) are not ends closing upon themselves…`
- **Source:** `book.md:300` — `(f) The blessings of this world rest upon seven: air, water, light, darkness, food, clothing, and marriage.`
- **Why it fails:** the note calls the list seven-fold and then parenthetically enumerates five,
  silently dropping darkness and clothing — the two the chapter spends its next sentences
  explaining. A reader counts and finds the note wrong about the page it sits on.
- **Worker action:** list all seven, or drop the parenthesis.

### BK10 · BK-A3 · P2 · VERIFIED
- **Chapter:** whole book (metadata)
- **File:** `book/book-toc.json:3` — `"voice": "modern author first-person"`
- **Why it fails:** contradicts `_system/series-config.yaml` (`narrative_frame: transmitted_report`,
  `book_voice: faithful`). The prose is correct; the metadata is stale from the pre-2026-07-20
  configuration and is exactly the kind of field a future re-compose could read back as authority,
  re-introducing the first-person defect this book was repaired for.
- **Worker action:** update the field to match the resolved frame, or remove it.

### BK11 · BK-P6 · P2 · VERIFIED
- **Chapter:** 6 (Three Layers of Knowledge)
- **book.md:** 840-844 — `…Yet the believer sees by the light of Allah.` / `> وَلَكِنَّ الْمُؤْمِنَ يَنْظُرُ بِنُورِ اللَّهِ` / `> But the believer sees by the light of Allah.`
- **Why it fails:** the English sentence is printed twice, once as the lead-in and once as the
  gloss under the Arabic, three lines apart. Cosmetic, but visible on the page.
- **Worker action:** drop the lead-in clause or the gloss.

---

## Verified vs Inferred summary

| | Count |
|---|---|
| VERIFIED (concrete evidence in the files) | 11 |
| INFERRED (heuristic judgment) | 0 |

Every finding cites a `book.md` line range plus, where the probe requires it, the exact OCR scan
line or mushaf reference it was checked against. No finding rests on model recall of Arabic.

## Ledger emission summary

11 records appended to `_learning/findings.jsonl` with `source: "book-challenger"`,
ids BK1-BK11, all `resolution: "flagged"`. Deduped within the run by signature.

## Verdict

**BLOCKED** — three P0 records (BK1-BK3, supplied diacritics on three non-Quranic runs). Clearing BK1-BK3 alone
moves the book to SHIP-WITH-CAUTION on the three P1s (BK4 terminological split, BK5 chapter-5
quoting convention, BK6 false internal cross-reference), each of which carries an author judgment
call and should be escalated rather than re-run blind.
