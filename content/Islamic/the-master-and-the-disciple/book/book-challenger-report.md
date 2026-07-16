# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-16 (book_challenger_version 1.0)
**Scope:** whole-book — v2 knob-matrix validation cell c5 (book_augmentation=none, book_voice=faithful)
**Content profile:** islamic_scholarly (full catalog)
**Route:** augmented-companion selector, judged at translation-route strictness per v2 knobs (no augmentation permitted; faithful voice, not author-first-person)
**Chapters reviewed:** 8
**Iterations:** 1 (of 5 max) — VALIDATION RUN, no re-compose triggered
**Verdict (book-level):** BLOCKED

Ground truth used: `_system/source/text/refined-english.md` (1,353 lines) + `_system/source/ocr/raw-extract.md` (page-aligned Arabic OCR, 1,917 Arabic chars — used as BK-P3 ground truth). Quranic verses verified against the canonical mushaf.

**Positive headline:** the composer demonstrably re-translated against the OCR Arabic wherever the refined English was garbled, and every checked correction is RIGHT: `ووجده ضالاً فهداه ووجده عائلاً فأغناه` (bk-1), `إمام قمت بحجته، حجة نصحت في أمانته، وميت تفضلت بحياته` (bk-7 "three goods" triad, OCR p.52), `وامر أباك بالإحسان إليهم` / `وعطف على هداهم ولي الله فيهم` (bk-8 ending, OCR p.94), `سيدنا محمد` and `القائد الغرّ المحجّلين` (doxology, OCR p.94 — script exact where the refined source wrongly said "leader of the Muhajirun"). All 16 Quranic quotations are consonantally canonical (7:26, 6:120, 16:60, 16:74, 12:4, 12:8, 12:43, 2:233, 28:76, 31:33, 89:24, 42:11 fragment, 55:29, 5:19, 11:113, 4:59, 9:123). BK-P3 passes with zero findings. No outside-source doctrine, no modern analogies, no invented citations anywhere — the two BK-P4 findings below are narrator connective tissue, not doctrine.

## Per-chapter verdicts
| Chapter | Pass 1 | Verdict |
|---|---|---|
| Preface (planned, absent) | fail (BK-P1 P0, BK-A3 P2) | BLOCKED |
| 1. The Persian Who Was Dead and Revived | pass | SHIP-READY |
| 2. A Stranger in the City | fail (BK-P6 seam dup) | SHIP-WITH-CAUTION |
| 3. The Boy at the Door — Limits and Conditions | fail (BK-P6 seam dup, shared with ch2) | SHIP-WITH-CAUTION |
| 4. How the World Was Made | pass | SHIP-READY |
| 5. The World, the Hereafter, and the Speech of Parables | pass (boundary drift noted at BK-A2) | SHIP-READY |
| 6. Three Layers of Knowledge | fail (BK-A2 boundary/title drift) | SHIP-WITH-CAUTION |
| 7. The Five Shares and the Long Road to the Shaykh | fail (BK-P6 dup x1, BK-P4 P2 bridge) | SHIP-WITH-CAUTION |
| 8. Homecoming, the Father, and the Debate with Abu Malik | fail (BK-P6 dup x2, BK-P4 P1 recap, BK-P2 epithet) | SHIP-WITH-CAUTION |

## Whole-book passes
| Check | Result |
|---|---|
| BK-A1 voice consistency | pass (faithful dignified translation voice throughout; one mode-shift noted as P2 under BK-P6) |
| BK-A2 segmentation sanity | FAIL — P1 (BK7: rendered boundaries drift from crosswalk/TOC ranges; ch6 title describes content delivered in ch5) |
| BK-A3 preface + TOC integrity | FAIL — P2 (BK9: planned preface absent; TOC voice field contradicts knob) |
| BK-A4 plain transliteration | pass (zero scholarly diacritics in book.md; refined source's ẓāhir/ḥujaj etc. correctly folded to zahir/hujaj) |
| BK-A5 tradition fit | pass / n-a (no enable_knowledge_augmenter in meta.yml; zero enrichment found; Ismaili imamate/cosmology doctrine is native to the source — meta.yml doctrinal_context confirms) |

## Findings (P0 → P1 → P2)

### BK1 · BK-P1 · P0 · VERIFIED
- **Chapter:** Preface (planned, absent)
- **book.md:** lines 1–3 — book opens `# The Master and the Disciple` then `## 1. The Persian Who Was Dead and Revived`; no preface exists
- **Source:** lines 8–13 (¶1–2, pp.1–2) — "As for thanking the Master, it is to obey him; as for thanking the knowledge, it is to act upon it and call to it; and as for thanking the work, it is to be patient with it and call to it." Plus the believers' framing question ("thanks on three counts") and the Master's "houses of the hearts / keys are remembrance: affliction, guidance, piety" teaching.
- **Why it fails:** book-toc.json assigns source lines 8–13 to a preface ("How to Read a Conversation Made of Doors", include=true) that was never rendered; the work's own opening teaching — the three-thanks doctrine that frames the entire narrative as an act of thanksgiving — is absent from the deliverable. Teaching lost.
- **Worker action:** re-compose must render ¶(1)–(2) either as the planned preface or as a prologue block before chapter 1.

### BK2 · BK-P6 · P1 · VERIFIED
- **Chapter:** 7 → seam into 8 (bk-7, The Five Shares and the Long Road to the Shaykh)
- **book.md:** lines 627–633 vs 635–637 — first pass: "Then they parted, and the scholar and the boy journeyed on until they drew near to the boy's city… 'My son, you have learned the counsel of the Shaykh, and there is no right guidance but in his word.'" then a SECOND farewell "When the time came to part, the two of them rose, shook hands, and embraced…"; second pass (635): "So the scholar and the boy went out together… 'O my son, I have understood the will of the Shaykh, and you have not…'"
- **Source:** lines 729–735 (¶300–302, pp.51–52) — the parting occurs ONCE: (300) farewell → "So the scholar and the boy went out…" → (301) "I have understood the will of the Shaykh, and you have not."
- **Why it fails:** chunk-seam double render of ¶(300)–(302); the first pass also inverts the meaning of (301) (attributes the understanding to the boy instead of the scholar), so the two renderings contradict each other and the farewell happens twice in sequence.
- **Worker action:** delete book.md lines 627–633 (keep the faithful 635–637 rendering).

### BK3 · BK-P6 · P1 · VERIFIED
- **Chapter:** 8 (Homecoming… Debate with Abu Malik)
- **book.md:** lines 719–733 vs 735–747 — ¶(343)–(350) rendered twice: first as "…rejecting the truth as false is the worst of wares… The humility returns to Allah…", then again as "What you have related, you have believed. But has not this one passed beyond the bounds of the liars and become two ignorant men gathered into one?… lying is the worst of wares… It was reverence to God…" including the king-petitioner parable twice.
- **Source:** lines 847–864 (¶343–350, pp.61–62) — the liar/ignorant + reverence-before-the-statement exchange occurs ONCE.
- **Why it fails:** double render with divergent terminology (takdhib "rejecting-as-false" vs kadhib "lying"); the reader cannot tell which the source says, and the dialectic repeats itself verbatim in structure.
- **Worker action:** keep one rendering (adjudicate takdhib vs kadhib against OCR p.61 Arabic) and delete the other.

### BK4 · BK-P6 · P1 · VERIFIED
- **Chapter:** 8
- **book.md:** lines 859 and 863 — Abu Malik's speech "You have dealt fairly and fulfilled the duty of the truth. As for the counterfeit… we have known it and made it known; so say of it whatever seems right to you." appears twice nearly verbatim, separated by the added recap at line 861.
- **Source:** line 1005 (¶409) — the speech occurs once.
- **Why it fails:** chunk-seam double render of ¶(409).
- **Worker action:** delete one copy (and the line-861 bridge, see BK5).

### BK5 · BK-P4 · P1 · VERIFIED
- **Chapter:** 8
- **book.md:** line 861 — "The talk between them had come round to the testing of true knowledge, which Salih likened to a precious jewel. The duty of the seeker, he had said, is to have the jewel assayed, so that its worth is made plain and the counterfeit, together with those who trade in it, is exposed."
- **Source:** lines 997–1005 (¶407–409) — no such recap paragraph exists.
- **Why it fails:** composer-added narrative recap with no source counterpart, inserted to smooth the BK4 duplication; under book_augmentation=none this is untraceable added content (non-doctrinal, hence P1 not P0).
- **Worker action:** delete with the BK4 duplicate.

### BK6 · BK-P6 · P1 · VERIFIED
- **Chapter:** 2 → 3 seam
- **book.md:** line 57 (end of ch2) vs line 61 (opening of ch3) — "Then his eyes brimmed over with tears, and he broke off his speech… Yet one man did follow after him out of the company—a youth…" rendered again as "His eyes brimmed over with tears, and he broke off his speech… He was followed by a youth."
- **Source:** line 70 (¶27) — occurs once, at the head of ch3's assigned range (70–200); ch2's range ends at 69.
- **Why it fails:** ch2 over-ran its assigned range and duplicated ¶(27), so the sermon's ending and the youth's introduction happen twice across the chapter break.
- **Worker action:** trim book.md lines 55–57's ¶(27) content from ch2 (or ch3's re-statement), keeping one rendering.

### BK7 · BK-A2 · P1 · VERIFIED
- **Chapter:** whole-book (acute at 1/2 and 5/6)
- **book.md:** ch1 lines 11–17 render ¶(6)–(7) (source lines 23–27, assigned to ch2); ch5 lines 317–339 render the three-layers-of-knowledge discussion and ¶(154)–(157) pairs dialogue (source lines ~381–387, assigned to ch6 — the crosswalk's ch6 source_excerpt "(154) Are not this world and the Hereafter a pair…" actually appears in book ch5 at line 333).
- **Source:** crosswalk/TOC ranges ch2=[23,69], ch6=[381,492].
- **Why it fails:** rendered chapter boundaries drift from the declared source_line_ranges; consequence: ch6's title "Three Layers of Knowledge" names content substantially delivered at the end of ch5, and the crosswalk no longer describes the rendered book — the crosswalk's audit value is compromised.
- **Worker action:** either move the boundary content to match the ranges, or regenerate book-toc.json + source-crosswalk.json ranges/excerpts from the rendered boundaries.

### BK8 · BK-P2 · P1 · VERIFIED
- **Chapter:** 8 (closing doxology)
- **book.md:** line 1127 — "the radiant, blaze-marked leader (القائد الغرّ المحجّلين)"
- **Source:** OCR p.94 — "إمام المتقين القائد الغرّ المحجَلين المحبوب من ربّ العالمين". Arabic script is EXACT against OCR (and correctly overrides refined-english.md line 1349's garbled "leader of the Muhajirun").
- **Why it fails:** the English translation misconstrues the idafa: القائد الغرّ المحجّلين means "the leader OF the radiant, blaze-marked ones" (the classical epithet of the wasi as leader of believers whose limbs shine from wudu); the book transfers the epithet from the followers to the leader. Downgraded to P1 because the referent (the wasi/Imam of the God-fearing) survives and the script is canonical; the mistranslation still alters a doxology in a religious text.
- **Worker action:** re-translate as "the leader of the radiant, blaze-marked ones" (or equivalent).

### BK9 · BK-A3 · P2 · VERIFIED
- **Chapter:** front matter
- **book.md:** lines 1–3 — no preface heading between the title and `## 1.`
- **Why it fails:** book-toc.json declares preface include=true, title "How to Read a Conversation Made of Doors"; none rendered (content loss is BK1; the structural TOC mismatch is this finding). Also book-toc.json `voice: "modern author first-person"` contradicts the series-config knob book_voice=faithful and the actual (correctly) faithful rendering — plan-artifact drift.
- **Worker action:** render the preface; regenerate book-toc.json voice field from the knob.

### BK10 · BK-P4 · P2 · VERIFIED
- **Chapter:** 7 and 8
- **book.md:** line 503 — "The scholar went on speaking of the great one to whom he would bring him:" (no source counterpart; bridges the source's p.43/44 page-break mid-sentence "whose palms are opened / with the light of Sinai"); line 1123 — "And so, the account continues, Abu Malik and his companions…" (source ¶556 reads simply "He said:").
- **Why it fails:** composer-added narrator connective tissue not present in the source; meaning-neutral and traceable to the narrative situation, hence advisory.
- **Worker action:** optional — replace with the source's plain "He said:" forms; at line 501–503 rejoin the broken sentence instead of bridging it.

### BK11 · BK-P6 · P2 · INFERRED
- **Chapter:** 8
- **book.md:** lines 987–1051 — the source's direct dialogue ¶(474)–(521) is converted to indirect reported speech ("Abu Malik said that men had learned this from God. Then Salih pressed him:… This, said Abu Malik, belongs to the foundations of justice.") then returns to direct quotation at 1049–1053.
- **Why it fails:** mid-chapter discourse-mode shift reads assembled rather than authored; content verified complete against ¶(474)–(507) paragraph-for-paragraph (no loss), hence advisory only.
- **Worker action:** optional — restore direct dialogue for the stretch.

### BK12 · BK-P6 · P2 · VERIFIED
- **Chapter:** 7
- **book.md:** line 501 — paragraph terminates mid-sentence on an em-dash: "…the one whose palms are opened —"
- **Why it fails:** mirrors the source page break instead of completing the sentence; in the rendered PDF this reads as a typographic fault.
- **Worker action:** rejoin with the line-503 continuation (see BK10).

## Verified vs Inferred summary
11 VERIFIED, 1 INFERRED (BK11). All Arabic-script blocks VERIFIED (Quran against mushaf; book-native Arabic against OCR raw-extract). No BK-P3 findings.

## Ledger emission summary
12 findings emitted to `_learning/findings.jsonl` with source=book-challenger, resolution=flagged.
