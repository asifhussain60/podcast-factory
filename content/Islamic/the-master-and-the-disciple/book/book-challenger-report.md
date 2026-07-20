# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-20 13:05 EST (book_challenger_version 1.0)
**Scope:** whole-book
**Route:** augmented-companion (`deliverable_mode` unset)
**Content profile:** islamic_scholarly (full probe catalog)
**Declared narrative_frame:** transmitted_report (`_system/series-config.yaml`)
**book_voice:** faithful
**book_augmentation:** source_only
**Chapters reviewed:** 9 (preface + 8)
**Iterations:** 1 (of 5 max)
**Verdict (book-level):** BLOCKED

---

## Per-chapter verdicts

| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface — How to Read a Conversation Made of Doors | pass | pass | SHIP-READY (P2 only) |
| 1. The Persian Who Was Dead and Revived | pass | pass | SHIP-READY |
| 2. A Stranger in the City | **fail** (BK-P4) | pass | SHIP-WITH-CAUTION |
| 3. The Boy at the Door — Limits and Conditions | pass | pass | SHIP-READY |
| 4. How the World Was Made | pass | **fail** (BK-N7) | SHIP-WITH-CAUTION |
| 5. The World, the Hereafter, and the Speech of Parables | **fail** (BK-P4) | **fail** (BK-N7) | **BLOCKED** |
| 6. Three Layers of Knowledge | pass | pass | SHIP-READY |
| 7. The Five Shares and the Long Road to the Shaykh | pass | pass | SHIP-READY |
| 8. Homecoming, the Father, and the Debate with Abu Malik | **fail** (BK-P3) | **fail** (BK-N5) | **BLOCKED** |

## Whole-book passes

| Check | Result |
|---|---|
| BK-A1 voice consistency | **fail** (P1) — chapter 5 dialogue convention diverges from all other dialogue chapters |
| BK-A2 segmentation sanity | pass — ranges 8–1353 contiguous, zero gaps, source is 1353 lines, all 9 titles match `book-toc.json` |
| BK-A3 preface + TOC integrity | **fail** (P2) — preface title duplicated; `book-toc.json.voice` is stale |
| BK-A4 plain transliteration | pass — zero scholarly diacritics in Latin text |
| BK-A5 tradition fit | **fail** (P1) — enrichment woven in despite `source_only`; ch5 note imports later-Ismaili emanationist cosmology |
| BK-N3 frame consistency | **pass** — all nine sections narrate from the anonymous transmitter position |
| BK-N1 narrative person | pass — 0 violations (all first person is direct discourse or the transmitter's own `بلغنا` register) |
| BK-N2 speech attribution integrity | pass — VERIFIED: inverted-tag speaker multiset identical base→book in ch8 (Salih 64, He 23, They 18, he 8, they 1); 0 tag-word changes book-wide |
| BK-N4 Arabic script retention | pass — all 51 Arabic runs present, consonantal skeletons identical base→book |
| BK-N6 structural enumeration | pass — chapter 5 (a)–(g) survives complete (seven items, not six) |
| Seam integrity ch7 (3 windows) / ch8 (5–6 windows) | pass — 0 duplicated sentences ≥60 chars book-wide; part-file word sums equal whole-chunk word counts exactly (7258/7258 and 14384/14384) |
| Deterministic `_narrative.py` seeds | 0 findings, as reported — treated as "nothing cheap left", not as a pass |

---

## Findings

### BK1 · BK-P3 + BK-N5 · P0 · VERIFIED
- **Chapter:** 8 — Homecoming, the Father, and the Debate with Abu Malik
- **book.md:** line 1266 — `وَإِنَّهُ كُلَّ يَوْمٍ هُوَ فِي شَأْنٍ`
- **Source (OCR `_system/source/ocr/raw-extract.md`):** the phrase occurs EXACTLY ONCE in the whole scan, unvowelled, as `وإن الله كل يوم هو في شأن` (normalized `وإناللهكليومهوفيشأن`, OCR offset ~50909, near page marker 327).
- **Base chunk:** `book/_chunks/translation/bk-08.md` line 413 — same defective form, so the defect originates at the TRANSLATION stage, not the de-calque.
- **Why it fails:** three independent departures. (1) `الله` is dropped and `وَإِنَّهُ` substituted for `وَإِنَّ اللَّهَ` — the wording matches neither the OCR nor the mushaf (Q 55:29 is `كُلَّ يَوْمٍ هُوَ فِي شَأْنٍ`, with no prefix at all). (2) Full tashkeel is supplied on a run whose only source form is unvowelled — model-memory vowelling, the exact BK-N5 failure. (3) The book renders the SAME source phrase correctly at line 892 (`وإن الله كل يوم هو في شأن`, unvowelled, OCR-faithful), so the two occurrences of one phrase contradict each other inside one chapter. `_system/book-arabic-audit.json` mislabels this run `resolution: "ocr"` — the audit's own grounding claim is false.
- **Worker action:** replace line 1266 with the OCR form `وإن الله كل يوم هو في شأن`, unvowelled, matching line 892. Fix in `book/_chunks/translation/bk-08.md` line 413 first so a re-compose cannot reintroduce it. Separately, correct the arabic-audit resolver: it reported `ocr` for a run absent from the OCR.

### BK2 · BK-P4 · P0 · VERIFIED
- **Chapter:** 5 — The World, the Hereafter, and the Speech of Parables
- **book.md:** lines 460–472 — "> **Editorial note (source-grounded).** … the whole ordered succession of the celestial spheres has a stated purpose: to generate minerals, plants, animals, and human seed upon this terrestrial realm … the spiritual world was brought forth in a single instantaneous emanation from absolute non-existence, whereas this lower world is differentiated gradually."
- **Source:** absent. Not in `book/_chunks/translation/bk-05.md` (VERIFIED: `grep 'editorial:begin'` over all nine base chunks returns zero hits) and not in the assigned source range (lines 233–380).
- **Why it fails:** `_system/series-config.yaml` sets `book_augmentation: source_only`, which forbids outside-source material, yet `_system/book-augment-report.json` records `accepted: 2` and `_system/augment-used-ledger.json` lists fourteen consumed atoms. Worse, the injected cosmology CONTRADICTS the book's own: chapter 4 (lines 234–283) teaches creation from light through will → command → saying, producing seven things; this note substitutes a later Ismaili Neoplatonic scheme of instantaneous emanation from absolute non-existence plus sphere-driven generation. A reader is told, in the book's own voice, doctrine the author never taught.
- **Worker action:** re-compose with the augmenter genuinely disabled — the `source_only` setting is not being honoured by the augment step. Strip lines 460–472 and restore chapter 5 to its base chunk. Then fix the gate so `book_augmentation: source_only` hard-blocks `_book_augment` rather than being advisory.

### BK3 · BK-P4 + BK-A5 · P1 · VERIFIED
- **Chapter:** 2 — A Stranger in the City
- **book.md:** lines 97–108 — "> **Editorial note (source-grounded).** … The root of *Sharia* (sh-r-) means to open up a path — specifically the trodden way down to water."
- **Source:** absent from `book/_chunks/translation/bk-02.md` and from source lines 23–69. Traceable to atom `etymology:shr` in `_system/augment-used-ledger.json`.
- **Why it fails:** same `source_only` violation as BK2. It also attributes to the passage a term the passage never uses — the stranger's sermon speaks of "open highways of the pasture", never of *Sharia* — so the note asserts an authorial intent that is the augmenter's, not the author's. Additionally the root is malformed: "(sh-r-)" has lost its ʿayn (should be `شرع` / sh-r-ʿ), and the note discusses Arabic AS LETTERS while supplying no Arabic script at all.
- **Worker action:** strip lines 97–108 with BK2. If any etymological gloss is ever reinstated under a different config, it must carry the script `شرع (shar-ʿa)` per BK-N4 and must not claim the source uses the term.

### BK4 · BK-A1 + BK-N7 · P1 · VERIFIED
- **Chapter:** whole-book, anchored on 5
- **book.md:** chapter 5 (lines 284–473) renders dialogue unquoted — e.g. line 286 "The scholar said: As for this world, no one will ever truly reproach it…"; every other dialogue chapter quotes it — e.g. line 1156 "Salih said: \"Then what is the difference between the name and the named?\""
- **Measured split (unquoted / quoted speech tags):** ch2 0/19 · ch3 2/50 · **ch5 60/2** · ch6 1/46 · ch7 1/91 · ch8 2/139. Chapter 5 is the sole inversion. Identical in the base chunks, so this originates at the translation stage.
- **Why it fails:** BK-A1 — one book must not switch its dialogue convention mid-way; a reader crossing from chapter 4 into 5 into 6 meets three different presentations of the same Master–boy exchange. BK-N7 — the register shifts with it, chapter 5 reading as reported summary where its neighbours read as staged dialogue.
- **Worker action:** normalize chapter 5 to the majority convention (quoted direct speech) in `book/_chunks/translation/bk-05.md`, then re-compose. Do not touch the (a)–(g) enumeration while doing so.

### BK5 · BK-N7 · P1 · VERIFIED
- **Chapter:** 4 — How the World Was Made
- **book.md:** line 257 — "Then the **way** of creation in pairs went forth … Then this **way** extended into speech"; line 272 — "made it manifest through parables and through the **sunna**"
- **Source:** `book/_chunks/translation/bk-04.md` — "Then the **sunna** of creation in pairs went forth … Then this **sunna** extended into speech" and "made it manifest by parables and by the **sunna**"
- **Why it fails:** elegant variation on a technical term, the named BK-N7 defect. The base uses *sunna* four times book-wide; the composed book keeps two and silently renders two as "way" — both losses inside chapter 4, one of them fifteen lines above a retained "sunna". A reader cannot trace the term through the argument, and the chapter appears to distinguish "way" from "sunna" when the source uses one word.
- **Worker action:** restore *sunna* at both sites in chapter 4. Terminological consistency outranks synonym variety in this genre; the de-calque pass must be constrained from substituting English glosses for retained Arabic technical terms.

### BK6 · BK-P6 · P1 · VERIFIED
- **Chapter:** 8 — Homecoming, the Father, and the Debate with Abu Malik
- **book.md:** lines 1266, 1280, 1314, 1352, 1358, 1364 — six standalone Arabic scripture blocks set as bare body paragraphs, e.g. line 1358 `أَطِيعُوا اللَّهَ وَأَطِيعُوا الرَّسُولَ وَأُولِي الْأَمْرِ مِنكُمْ` with no `>` prefix.
- **Source:** inherited from `book/_chunks/translation/bk-08.md` lines 413, 427, 461, 499, 505, 511 (VERIFIED: all six `bq=False` there, while the six earlier Arabic runs in the same chunk are `bq=True`).
- **Why it fails:** the other 45 Arabic runs in the book carry the `>` blockquote, so the PDF sets scripture apart visually everywhere except the final stretch of the climactic debate, where six Quranic citations will render as ordinary prose. The convention breaks exactly where the argument leans hardest on citation. This clusters at the chapter-8 window tail (base part-05 holds four of the six), so it reads as a seam artifact even though no text was lost.
- **Worker action:** add the `>` prefix to all six in `bk-08.md` and re-compose. This is the one finding whose fix is purely mechanical.

### BK7 · BK-A3 · P2 · VERIFIED
- **Chapter:** preface — How to Read a Conversation Made of Doors
- **book.md:** lines 3–5 — `## How to Read a Conversation Made of Doors` immediately followed by a blank line and the body line `How to Read a Conversation Made of Doors`
- **Source:** `book/_chunks/translation/preface.md` line 1 carries the title as its first body line; the compose step emits the `## ` heading independently, so both survive.
- **Why it fails:** the title prints twice in the reading edition. This is the likely cause of the `BR-PAGE-FILL` P1s on pages 2–3 in `_system/book-render-checks.json` (149 and 394 chars against a 1683 median).
- **Secondary, same probe:** the preface does not orient a modern reader. It is a faithful rendering of the source's own opening (the believers' three thanks) under an editorial-sounding title; it never says who is speaking, to whom, or why the dialogue still matters. Note this is a design consequence of the correct 2026-07-20 decision to revert the preface to its faithful base — the anti-abridgement revert is NOT a defect, but it does leave the book with no orienting front matter.
- **Worker action:** strip the duplicate title line when emitting the preface chunk. Decide separately whether a genuine orienting preface is wanted; if so it must be additional front matter, not a rewrite of the source's opening.

### BK8 · BK-A3 · P2 · VERIFIED
- **Chapter:** n/a — configuration artifact
- **File:** `book/book-toc.json` line 3 — `"voice": "modern author first-person"`
- **Why it fails:** this contradicts the frame locked on 2026-07-20 (`narrative_frame: transmitted_report`, `book_voice: faithful`). It is stale, and it names the exact defect the relock was written to eliminate. Any future compose that reads `book-toc.json.voice` instead of `series-config.yaml` will reintroduce first-person narration book-wide.
- **Worker action:** update the field to `faithful / transmitted_report`, or delete it so `series-config.yaml` is unambiguously the single source of truth.

---

## Arabic verification detail (BK-P2 / BK-P3 / BK-N4 / BK-N5)

51 Arabic runs, all present, all consonantal skeletons identical between base chunks and `book.md`. One defect (BK1). Every other run confirmed:

- **OCR-grounded, 47 runs** — verified by normalized substring match against `_system/source/ocr/raw-extract.md` (diacritics and non-Arabic stripped).
- **Three runs flagged `unverified` by `_system/book-arabic-audit.json`** — I verified all three against the canonical mushaf and they are correct, so they are NOT findings: `فَلَا تَغُرَّنَّكُمُ الْحَيَاةُ الدُّنْيَا` (ch6 L558, Q 31:33 / 35:5), `فَمَنِ اضْطُرَّ غَيْرَ بَاغٍ وَلَا عَادٍ فَلَا إِثْمَ عَلَيْهِ` (ch7 L656, Q 2:173), `عَلَىٰ فَتْرَةٍ مِّنَ الرُّسُلِ` (ch8 L1314, Q 5:19). Their supplied vowelling is legitimate canonical anchoring, not BK-N5 model memory. Advisory only: the deterministic audit could not clear them itself.
- **`فَتَبَارَكَ الَّذِي جَعَلَ اللَّيْلَ وَالنَّهَارَ خِلْفَةً…` (ch2 L91)** — NOT a mis-citation. It echoes Q 25:62 (`وَهُوَ الَّذِي…`) but the book does not present it as scripture; it is the closing doxology of the stranger's own sermon and it is OCR-grounded, continuing into `وَصَلَّى اللَّهُ عَلَى مَنِ اخْتَارَهُ…`. Correctly left unattributed.
- **Quranic citations spot-verified against the mushaf and correct:** 12:4, 12:8, 12:43, 4:69, 7:179, 7:26, 2:173, 5:19, 11:113, 4:59, 9:123, 31:33/35:5, 42:11, 36:82.
- **BK-N4 letters-as-letters:** chapter 4 line 244 correctly keeps script beside its count — "From them is derived كُنْ, which is two letters, and فَيَكُونُ, which is five". No transliteration stands in for script anywhere in the book body. The sole violation is inside injected note BK3, which is being removed.

## Teaching + citation fidelity against the base chunks (BK-P1 / BK-P4)

The de-calque changed phrasing, not meaning, everywhere except the two injected notes. Evidence:

- **Numbers:** per-chapter numeral multisets are unchanged apart from the indefinite article "one" and one added "seven" in ch5, which I traced to a punctuation-only reflow of item (c) — every doctrinal count (seven, twelve, seventeen, eleven, five, three) is intact.
- **Named persons:** zero deltas. Salih, al-Bakhtari, Abu Malik, Ka'b al-Ahbar, Moses, Joseph, Jesus, Abraham, Ishmael, Isaac, Jacob, Jonah, Shu'ayb, Joshua, Elias, Talut, David, Solomon, Zechariah, John all survive with identical counts.
- **Speech tags:** 0 tag-changing hunks across all nine sections.
- **Highest-churn hunks read in full** (ch8 L1106, L1156, L1254): all synonym-level. One change is an improvement, not a defect — base "God is too **dear** for that" → book "God is too **exalted** for that", correcting a mistranslation of *jalla / taʿālā*.
- The 29 `said:` → `said,` conversions in ch8 are punctuation only; speaker identity is provably unchanged (see BK-N2 above).

## Process note for the caller (not a finding)

Your brief states every chapter was restored from its faithful base and then de-calqued once. The artifacts say otherwise, and this matters for reproducing the fix. `_system/book-fluency-report.json` (written 12:14:55, same second as `book.md`) reports `adapted: 0, reverted: 1` with all eight chapters `"status": "skipped", "windows": 0` — the fluency pass did no chapter work at all. What actually shipped is the output of `_system/book-voice-report.json` (11:44:38), which reports `revoiced: 9, reverted: 0` with ch7 at 3 windows and ch8 at 6 — the window counts you quoted come from the RE-VOICE stage, not the de-calque. The re-voice ran under the correct `transmitted_report` frame and did no narrative damage (Pass 3 is clean apart from BK5), but it is the stage that carried the augmenter's two notes into the text.

## Verified vs Inferred summary

| Finding | Severity | Basis |
|---|---|---|
| BK1 BK-P3 + BK-N5 | P0 | VERIFIED — OCR offset located, single occurrence, contradicted by L892 |
| BK2 BK-P4 | P0 | VERIFIED — absent from base chunks; augment ledger + report record the injection |
| BK3 BK-P4 + BK-A5 | P1 | VERIFIED — atom `etymology:shr` named in ledger |
| BK4 BK-A1 + BK-N7 | P1 | VERIFIED — counted per chapter, base and book |
| BK5 BK-N7 | P1 | VERIFIED — base/book term counts 4 vs 2 |
| BK6 BK-P6 | P1 | VERIFIED — six line numbers in book and base |
| BK7 BK-A3 | P2 | VERIFIED — lines 3–5; render-checks corroborate |
| BK8 BK-A3 | P2 | VERIFIED — field quoted from `book-toc.json` |

8 findings: 2 P0, 4 P1, 2 P2. All VERIFIED; none INFERRED.

## Ledger emission summary

8 records appended to `_learning/findings.jsonl` with `source: "book-challenger"`, `resolution: "flagged"`, deduped by signature.
