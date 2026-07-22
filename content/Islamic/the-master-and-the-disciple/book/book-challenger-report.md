# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-22 (book_challenger_version 1.0)
**Scope:** whole-book (post-RCA-001 full re-compose)
**Route:** translation-edition (pinned by compose path; `deliverable_mode` deliberately unset — see series-config comments)
**Content profile:** islamic_scholarly · **narrative_frame:** transmitted_report
**Chapters reviewed:** 8 (+ preface/introduction)
**Iterations:** 1 (of 5 max — all findings require Worker re-compose or Composer edits; no convergence possible without them)
**Verdict (book-level):** BLOCKED (4 × P0)

## Per-chapter verdicts
| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface / How to Read a Conversation Made of Doors | fail (BK1004) | pass | BLOCKED |
| 1. The Persian Who Was Dead and Revived | pass | fail (BK1001) | BLOCKED |
| 2. A Stranger in the City | pass | pass | SHIP-READY |
| 3. The Boy at the Door — Limits and Conditions | pass (note P1 BK1007) | pass | SHIP-WITH-CAUTION |
| 4. How the World Was Made | pass | pass | SHIP-READY |
| 5. The World, the Hereafter, and the Speech of Parables | fail (BK1002, BK1003, BK1008) | fail (BK1003) | BLOCKED |
| 6. Three Layers of Knowledge | pass (seam twin of BK1002) | pass | BLOCKED (shared seam) |
| 7. The Five Shares and the Long Road to the Shaykh | pass (note P1 BK1006) | pass | SHIP-WITH-CAUTION |
| 8. Homecoming, the Father, and the Debate with Abu Malik | pass | pass (P2s only) | SHIP-WITH-CAUTION (BK1005) |

## Whole-book passes
| Check | Result |
|---|---|
| BK-A1 voice consistency | FAIL — Master/scholar/teacher variation (BK1005) |
| BK-A2 segmentation sanity | pass w/ notes — ch2 renders source (27) from ch3's range (no dup); ch5 overruns into ch6 (the P0 seam); basmala dropped (P2); titles evocative; coverage otherwise complete (sampled per-paragraph sweep, 563 source paragraphs) |
| BK-A3 preface + TOC integrity | pass — 354-word intro accurate (Ja'far ibn Mansur al-Yaman / early Fatimid attribution correct); headings monotonic, match book-toc.json |
| BK-A4 plain transliteration | advisory (translation route) — intro diacritics vs plain body (BK1013) |
| BK-A5 tradition fit | pass on tradition (wisdom-corpus atoms are same Ismaili tradition); false PROVENANCE filed as BK1007 |
| BK-N3 frame consistency | pass — transmitted report, third person, all 8 chapters (sole intrusion is BK1001, model chatter) |
| BK-N4 Arabic-script retention | pass — script kept, translit beside script (كن (Kun)); all source Arabic blocks present |
| BK-N5 supplied diacritics | pass — Quran legitimately vowelled; non-Quran tracks scan; the سئَّة shadda rides OCR noise (bundled in BK1008) |
| BK-N6 enumeration survival | pass — ch5 (a)-(g) seven-sevens list SURVIVES AS LETTERED LIST; ch3 five conditions numbered; ch7 six qualities prose (matches source form); (94)(95)… section numbering correctly dropped as apparatus |
| BK-P3 sweep | 40+ Arabic blocks verified: every skeleton traced to OCR or canonical mushaf; zero consonantal corruption; deviations are vowel-level only (BK1008, BK1009) |
| Prose craft / de-calque | pass — articulation verified SUPERIOR to refined-english in sampled garbles: "Kab al-Ahbar"/"Abd al-Jabbar" recovered from "heel of the inks"/"mighty servant"; حجج الأوصياء correctly "proofs of the executors" against OCR where refined said "guardians"; jewel/counterfeit debate coherent. No study-guide scaffolding, no calque residue found at finding level |
| book-duplication-check.json | empty — cross-seam twin invisible to run-shape rule, as expected |
| Deterministic _narrative seeds | all empty (precision-tuned); manual findings stand |
| Composer edits (persian, five-shares, homecoming) | judged as edition text per contract; BK1001 lives INSIDE the ch1 edit body (`_system/composer-edits.json`) — fix via Composer, NOT re-compose |
| book-self-study.md | absent — BK-SS n/a |

## Findings (P0 → P1 → P2)

### BK1001 · BK-N1 (+BK-P6) · P0 · VERIFIED
- **Chapter:** 1 — The Persian Who Was Dead and Revived
- **book.md:** lines 29–31 — "إن أفضل الحسنات إحياء الأموات — I must keep this Arabic verbatim. / Let me produce the polished prose directly."
- **Why it fails:** Model process chatter shipped as the chapter's opening prose; first-person model voice under a transmitted_report frame. The chatter is inside the SAVED COMPOSER EDIT body itself (`composer-edits.json`, chapter_key "the persian…"), so a re-compose will faithfully replay it.
- **Worker action:** Edit in the Composer: delete lines 29–31 (the chapter's real opening is line 33 "As for the doctrines of the righteous…"; the hadith already appears properly at lines 37–39). Re-save so the sidecar edit body is clean.

### BK1002 · BK-P7 (+BK-P1) · P0 · VERIFIED
- **Chapter:** 5/6 seam
- **book.md:** ch5 lines 483–489 vs ch6 lines 507–513
- **Source:** lines 381–390, paragraphs (154)–(157)
- **Why it fails:** The (154)–(157) exchange is told twice across the seam. Clause map (per the earn-the-deletion rule): ch5's copy holds (154) the boy's pairs-question — MISSING from ch6, which opens with "I accept" answering a question never asked; ch5's (155) is off-source ("You have spoken truly. But whose pairs are they…" vs source "I accept. But are they pairs of a single kind?"); ch5's (157) truncates mid-hadith ("a knower, godly and firm in knowledge,"). Ch6's copy renders (155)–(157) faithfully plus the page-29 continuation ("one who has been taught… and another, a learner upon the way of salvation…"). Every source clause of (154)–(157) exists in ch6's copy EXCEPT (154).
- **Worker action:** MERGE, not blind delete: end ch5 at line 481 ("…which is its essence and its meaning."); open ch6 with the (154) question (take ch5 line 483's rendering, retagged to the unified teacher term per BK1005), followed by ch6's existing 507 onward. No source clause is lost by removing ch5 483–489 once (154) is moved.

### BK1003 · BK-N2 (+BK-P1) · P0 · VERIFIED
- **Chapter:** 5
- **book.md:** lines 443–449 — "The Master said: It is the time." / "The Master said: It is the time of the Will…"
- **Source:** lines 344–350 — (139) "It is time." (140) The boy said: "And what is time?" (141) "It is the time of the will…"
- **Why it fails:** The boy's turn (140) was dropped, leaving two consecutive Master tags — a speech removed relative to the source.
- **Worker action:** Restore the turn: `The boy said: "And what is time?"` between lines 447 and 449; fold the doubled tag.

### BK1004 · BK-P1 · P0 · VERIFIED
- **Chapter:** Preface ("The book's own opening")
- **book.md:** lines 21–25 — "he answered each in turn. / As for gratitude toward the Master… / As for gratitude toward the knowledge…"
- **Source:** line 13 — "as for thanking the work, it is to be patient with it and call to it."
- **Why it fails:** The third of the three counts of gratitude — the teaching the whole opening scene builds to — is absent, and the text explicitly promises all three.
- **Worker action:** Append: "As for gratitude toward the work, it is to be patient in it and to call others to it."

### BK1005 · BK-N7 (+BK-A1) · P1 · VERIFIED
- **Chapter:** whole book
- **book.md:** "The Master said" (chs 1–5) → "The scholar said" (chs 6–8) → "the teacher" (ch7 767–769); ch8: "The father said" (885, Composer edit) vs "The Shaykh said" (889, 893, 897) for the SAME speaker in one exchange, while "the Shaykh" also names ch7's greater Shaykh.
- **Why it fails:** One book, one rendering per figure — terminological consistency is the prose virtue of this genre; a reader cannot trace the protagonist teacher (or tell the boy's father from the greater Shaykh) across chapters.
- **Worker action:** Author decision, then global harmonization: pick ONE term for العالم (recommend "the Master" to match title + chs 1–5), and disambiguate the ch8 father (e.g., keep "the father"/"al-Bakhtari", reserving "the Shaykh" for ch7's elder — the ch8 editorial note can carry the source's shaykh usage). Ch7/ch8 carry Composer edits: harmonize via Composer.

### BK1006 · BK-P4 (+BK-P1) · P1 · VERIFIED
- **Chapter:** 7
- **book.md:** line 739 — "The scholar went on until he reached the boy's greater father"
- **Source:** OCR lines 985–986 — "فأراد أن يأخذ زاداً من عنده، فكره أن يقبل ذلك. ومضى حتى أتى والده الأكبر"
- **Why it fails:** والده الأكبر is the SCHOLAR'S own greater father — the book re-points the relationship to the boy, contradicting its own bridge note at 744 ("the Master's own elder father here"). Same paragraph loses the provision clause: the boy offers the scholar provisions and the scholar declines (refined-english garbled it; the book followed the garble instead of the OCR).
- **Worker action:** Via Composer (ch7 is edit-carrying): "…departed. The boy wished him to take provisions from his own store, but the scholar would not accept them. He went on until he reached his own greater father, and described the boy to him…"

### BK1007 · BK-P4 (+BK-A5-adjacent) · P1 · VERIFIED
- **Chapter:** 3 (lines 234–245) and 5 (lines 491–503) editorial notes
- **book.md:** "The book's own teaching elsewhere illuminates…" (ch3); "Elsewhere in this same teaching the soul so invoked is named plainly — the Commander of the Faithful calls the universal soul 'a divine force'…" (ch5)
- **Why it fails:** Both claims are FALSE provenance: the content comes from the wisdom corpus (doctrine:wisdom atoms — a different work; see book-augment-report.json), not from this book. Grep of the full source confirms neither teaching exists in it. Notes are fenced apparatus and tradition-compatible (no cross-tradition bleed), but a published edition may not label corpus material "the book's own teaching" / "this same teaching," nor stamp "(source-grounded)" on it.
- **Worker action:** Reword provenance in both notes ("A related teaching preserved in this tradition records…") or drop the two notes; fix the "(source-grounded)" label template for corpus-derived notes.

### BK1008 · BK-P3 · P1 · VERIFIED
- **Chapter:** 5
- **book.md:** line 357 — "فذلك سئَّة حدود وهي الحدّ السابع"
- **Source:** OCR line 479 carries the same noise; OCR line 482 has the correct "ستة حدود" three lines later; English (line 359) correctly reads "six limits."
- **Why it fails:** سئَّة is a non-word — an obvious OCR corruption of ستة transcribed into the shipped Arabic, shadda and all.
- **Worker action:** Correct to ستة in the Arabic block (both the same block's later occurrence is already correct in OCR — verify the whole slab while touching it).

### BK1009 · BK-P3 · P1 · VERIFIED
- **Chapter:** whole book (3 blocks)
- **book.md:** line 471 (Q 7:26) سَوْآتِكِمْ / وَرَيْشًا — canonical سَوْآتِكُمْ / وَرِيشًا (OCR line 589 carries the same misprint); line 1379 (Q 4:59) وَأَوْلِي — canonical وَأُولِي (OCR line 2036 same); line 557 (Q 28:76) مَا إِن — canonical مَا إِنَّ.
- **Why it fails:** Quranic verses carry scan-inherited vowel deviations. Consonantal skeletons all match the canonical mushaf (zero consonantal corruption book-wide), but per the locked canonical-first policy the mushaf outranks the scan for Quran — the printed edition's misprints are not authority for scripture.
- **Worker action:** Correct the three blocks to canonical vowelling from `fts_quran` (mirror.db). Elsewhere the book already corrects scan noise for Quran (e.g., فَتْرَةٍ vs OCR فَثْرَةٍ at line 1339; تَغُرَّنَّكُمُ vs OCR تَغْرَّتَكُمُ at 593) — these three are the stragglers.

### BK1010 · BK-P6 · P2 · VERIFIED
- **Chapter:** 8 · line 1213 — "Abu Malik said that they had learned this from God." Source (474) is direct speech ("They learned this from God."). Sole indirect-speech lapse in the book; restore direct form.

### BK1011 · BK-P4 · P2 · VERIFIED
- **Chapter:** 8 · line 1315 — un-tagged interpolation restating (518) with no source counterpart ("For whoever fell short of him could take no comfort in the description…"). Drop, or fold into the preceding tagged answer.

### BK1012 · BK-N7 · P2 · VERIFIED
- **Chapter:** 8 · line 1325 — "the moment We reasoned with you" — capital "We" inside Salih's own speech reads as the divine We; lowercase.

### BK1013 · BK-A4 · P2 (advisory) · VERIFIED
- Intro (lines 6–12) uses scholarly diacritics (Kitāb al-ʿĀlim wa-l-Ghulām, ẓāhir/bāṭin, taʾwīl, daʿwa) while the body uses plain forms (tawil, hujja, duat) — pick one register (plain, per the fold policy) or declare the intro exempt; nested gloss "the island (al-Jazira (الجزيرة))" line 43 deviates from the "(Tur, الطور)" pattern; honorifics عليه السلام (569) vs (ع) (577); Arabic sometimes bare lines (789, 875, 1287, 1303, 1339, 1375–1383) vs blockquoted elsewhere.

### BK1014 · BK-A2 · P2 · VERIFIED
- Source basmala (refined line 5, OCR page 1) appears nowhere in the edition front matter. Consider opening "The book's own opening" with it.

### BK1015 · BK-P2 · P2 · VERIFIED
- Chapter 5 Arabic slabs at 337 and 357 begin mid-sentence (357 opens with "، ") — splice artifacts of the Arabic-above-English windowing; trim to clause boundaries when re-composing the chapter.

## Verified vs Inferred summary
All 15 findings VERIFIED against book.md + refined-english.md + ocr/raw-extract.md + canonical mushaf (mirror.db fts_quran) + composer-edits.json + book-augment-report.json. Zero INFERRED.

## Ledger emission summary
15 records appended to `_learning/findings.jsonl` (source=book-challenger, BK-N1/BK-P7/BK-N2/BK-P1 P0 ×4; BK-N7/BK-P4×2/BK-P3×2 P1 ×5; P2 ×6). Dedup by signature within run.
