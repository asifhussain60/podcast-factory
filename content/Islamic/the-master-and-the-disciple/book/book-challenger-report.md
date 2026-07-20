# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-20 9:41 AM EST (book_challenger_version 1.0)
**Route:** augmented-companion (no `deliverable_mode: translation_edition`; `book_augmentation: source_only`, `book_voice: author_companion`)
**Content profile:** islamic_scholarly (full probe catalog)
**Scope:** per-chapter bk-07 — "The Five Shares and the Long Road to the Shaykh" (book.md lines 594-846)
**Chapters reviewed:** 1
**Iterations:** 1 (of 5 max)
**Verdict (chapter-level):** BLOCKED

## Ground truth used

| Artifact | Role in this run |
|---|---|
| `book/_chunks/translation/bk-07.md` (7,258 w) | faithful base — primary fidelity reference |
| `book/_chunks/translation/bk-07-part-0{1,2,3}.md` | the three re-voice windows; byte-exact concatenation == bk-07.md (VERIFIED). Seams fall at base lines 86 and 223. |
| `_system/source/text/refined-english.md` lines 493-762 | numbered source (paras 232-311) |
| `_system/source/ocr/raw-extract.md` | page-aligned OCR ground truth (Arabic + English) |
| `_system/book-voice-report.json` | ch7 `status: adapted`, 3 windows, 3 kept, 0 gates, 0 warnings |
| `_system/book-arabic-audit.json` | ch7: 5 Arabic runs, 1 flagged `unverified` |

## Per-chapter verdicts
| Chapter | Pass 1 | Verdict |
|---|---|---|
| 7. The Five Shares and the Long Road to the Shaykh | fail (BK-P1, BK-P4) | BLOCKED |

## Probe results — chapter 7

| ID | Probe | Result |
|---|---|---|
| BK-P1 | No-teaching-lost | **FAIL** — one source segment (para 302 tail) absent from both renditions; see BK2. Otherwise clean: 125 content paragraphs vs base 126 (net -1 = the seam-1 merge, no dropped paragraph); largest re-voice edit hunk is 8 words; all doctrinal term counts preserved (Allah 13/13, Shaykh 22->23, zakat 9/9, imam 1/1). |
| BK-P2 | Verbatim-quote survival | pass — all 5 Arabic blocks survive **byte-identically** with their English rendering beneath. |
| BK-P3 | Arabic-script accuracy | **pass — VERIFIED**. See table below. |
| BK-P4 | Faithfulness-against-addition | **FAIL** — duplicated source passage (BK1); minor inherited source-drift (BK5). No invented doctrine, no outside enrichment, no new named authority. |
| BK-P5 | Voice fidelity | fail (P1) — chapter did not convert to the configured `author_companion` first-person frame; see BK3. One orphaned narrator-announcement; see BK4. |
| BK-P6 | Prose craft | pass — no study-guide scaffolding, no enumerated-lesson drift, no podcast filler, no meta-commentary. Sentence-level re-voice is genuinely better prose than the base (looser clause rhythm, em-dash asides, "you can see that yourself"). |

### BK-P3 verification detail (headline duty)

| # | Arabic in ch7 | Canonical identification | Status |
|---|---|---|---|
| 1 | لَهُمْ قُلُوبٌ لَا يَفْقَهُونَ بِهَا … | Qur'an 7:179 | VERIFIED canonical (consonantal skeleton exact) |
| 2 | وَمَن يُطِعِ اللَّهَ وَالرَّسُولَ … ذَلِكَ الْفَضْلُ مِنَ اللَّهِ | Qur'an 4:69-70 | VERIFIED canonical |
| 3 | فَمَنِ اضْطُرَّ غَيْرَ بَاغٍ وَلَا عَادٍ فَلَا إِثْمَ عَلَيْهِ | Qur'an 2:173 | VERIFIED canonical. The deterministic audit marks this `unverified` only because it has no OCR match; canonical recall confirms it exactly. **Not a finding.** |
| 4 | وَمَا يُلَقَّاهَا إِلَّا الَّذِينَ صَبَرُوا … | Qur'an 41:35 | VERIFIED canonical |
| 5 | وَلَكِنَّ الْمُؤْمِنَ يَنْظُرُ بِنُورِ اللَّهِ | reported saying | VERIFIED against OCR ground truth — the string `ينظر بنور الله` is present in `_system/source/ocr/raw-extract.md`. Source-preserved, not model-supplied. |

No Arabic was added, dropped, re-vowelled, or altered by the re-voice pass. **BK-P3 is clean.**

### Seam integrity (the new windowing risk)

| Seam | Base position | Finding |
|---|---|---|
| Seam 1 | base line 86, between "…whose palms are opened" and "with the light of Sinai." | **Healed.** The base carried a mid-sentence paragraph break here (inherited from the source's page break at OCR line 967). The re-voice joined the two halves into one continuous paragraph at book.md line 679. Net -1 paragraph, no content loss. Positive outcome. |
| Seam 2 | base line 223, between "…what He has opened for none before you." and "Then they stood and clasped hands…" | **Sits exactly on a pre-existing duplication boundary.** Window 2 ended with rendition A of source paras 300-302; window 3 opened with rendition B of the same paras. Neither window could see the other, so the duplicate survived unchallenged. See BK1. |
| Voice/tense continuity | — | pass. Third-person attribution density is uniform across all three windows (W1: 14 "The scholar said" / 15 "The boy said"; W2: 12/19; W3: 3/3). No register shift, no dropped transition, no fresh-chapter opening mid-chapter. |
| Repetition scan | — | 12-gram duplicate-detection over the whole chapter returns exactly one duplicated run — the BK1 passage. The only other echo ("the people of this world are ranked in classes within their world", lines 614 and 620) is the source's own question-then-answer rhetorical pickup, present identically in the base. |

## Whole-book passes
| Check | Result |
|---|---|
| BK-A1 voice consistency | **fail (P1)** — see BK3 |
| BK-A2 segmentation sanity | pass (ch7 range 493-762 is contiguous with ch6 and ch8; title is evocative and matches the chapter's content) |
| BK-A3 preface + TOC integrity | pass (preface present and orienting; `## ` sequence 1-8 monotonic and matches `book-toc.json`) |
| BK-A4 plain transliteration | pass — **zero** scholarly-diacritic characters anywhere in `book.md` |
| BK-A5 tradition fit | n/a — `book_augmentation: source_only`; no enrichment atoms woven in; nothing cross-tradition detected |

---

## Findings (P0 -> P1 -> P2)

### BK1 · BK-P4 (with BK-P1) · P0 · VERIFIED
- **Chapter:** bk-07 — The Five Shares and the Long Road to the Shaykh
- **book.md:** lines 812-816 (rendition A) and lines 818-822 (rendition B)
- **Source:** `refined-english.md` lines 729-741 = paras (300)(301)(302); corroborated by `_system/source/ocr/raw-extract.md` lines 1146-1157 — **each occurs exactly once**
- **Rendition A, line 816 (truncated, quotation never closed):**
  > When they had sat down, the scholar said: "My son, you know your father's state and his enmity toward the people of this way … Know, my son, that God has opened for you, by the lightest of your striving, what He has opened for none before you.
- **Rendition B, line 822:**
  > When they had sat down, the scholar said: "My son, I know your father, and I know his enmity toward the people of this affair. And to that there has now been added your going out with me and your long absence from him …"
- **Why it fails:** the farewell-to-the-Shaykh, the journey to the boy's city, the "sit with me off the road" instruction, and the scholar's counsel about the father are each rendered **twice, in different words**, back to back (lines 812/818, 814/820, 816/822). A reader meets the same scene twice. Rendition A's speech is additionally truncated mid-thought with an unclosed `"`.
- **Attribution (important):** this duplication is **pre-existing in the faithful base** `bk-07.md` (lines 219-222 vs 223-229) and was **not** introduced by the 2026-07-19 re-voice. But the window split landed at base line 223 — precisely between the two renditions — so neither window's model call could see both copies, and the pass had no chance to collapse them. Verified independently: the concatenation of the three part files is byte-identical to `bk-07.md`.
- **Worker action:** fix at the base, not the re-voice. Regenerate `book/_chunks/translation/bk-07.md` for source paras (300)-(302) so the scene renders **once**, preferring rendition B's fuller text (it carries the "six qualities" lead-in intact) and folding in whatever rendition A holds that B lacks. Then re-run the re-voice. Additionally: make the windower refuse a seam that falls inside a detected repeated-passage span, or add a whole-chapter duplicate-passage gate after the windows are stitched — a per-window gate structurally cannot catch this class.

### BK2 · BK-P1 · P0 · VERIFIED
- **Chapter:** bk-07
- **book.md:** absent — searched the whole file for "full-grown", "be good to yourself", "honored you through", "thought well of you", "hope in you": zero hits
- **Source:** `refined-english.md` line 735-737, para (302); OCR `raw-extract.md` line 1157 + page 52
  > … Allah has opened to you the least of your aspirations even before you suppose yourself to be a full-grown man, until a stretch of time has passed. And Allah has been good to you, so be good to yourself, and honor the one Allah has honored you through. We have thought well of you, and our hope in you has been great.
- **Nearest surviving text (line 816):** "Know, my son, that God has opened for you, by the lightest of your striving, what He has opened for none before you." — this compresses the first clause and drops the rest.
- **Why it fails:** a complete teaching — the charge to be good to oneself and to honour the one through whom God honoured you, plus the master's declared good opinion and hope — is present in the source and in the OCR but appears in neither rendition of the passage. Because rendition A is truncated and rendition B skips straight to "So you must guard the trust your father laid upon you", the material falls into the gap between the two duplicates.
- **Attribution:** base-inherited (also absent from `bk-07.md`), not caused by the re-voice.
- **Worker action:** restore para (302) in full when regenerating the base chunk under BK1 — this is the same repair.

### BK3 · BK-A1 (with BK-P5) · P1 · VERIFIED
- **Chapter:** bk-07 (whole chapter, all three windows)
- **book.md:** lines 596-846 throughout; e.g. line 598
  > The scholar said: "As for the creation of bodies, it is various — you can see that yourself in the difference of tongues and colors."
- **Contrast, chapter 6 (line 480):**
  > I accepted that too, and I opened it out for him. In every pair the outward is a name and the inward is an attribute…
- **Contrast, chapter 8 (line 850):**
  > My father stood over me, and what passed between us that day was as raw as anything I have set into this book.
- **Why it fails:** `series-config.yaml` sets `book_voice: author_companion`, and chapters 5, 6, and 8 speak in the modern author's first person (the scholar as "I"). Chapter 7 remains third-person reportage. Measured across the book:

  | Chapter | "The scholar/Master/Shaykh said" | "The boy said" | first-person narration ("I said/told/asked/answered") |
  |---|---|---|---|
  | 5 | 0 | 10 | 30 |
  | 6 | 0 | 0 | 23 |
  | **7** | **40** | **37** | **0** |
  | 8 | 1 | 0 | 53 |

  The 2026-07-19 pass polished chapter 7's *sentences* (looser rhythm, em-dashes, contractions of clause structure) but never performed the *person conversion*. Reading 5 -> 6 -> 7 -> 8 in sequence, chapter 7 reads as a different hand. Chapter 3 shares this defect (27/23/0) — out of scope for this run but flagged for the same repair.
- **Worker action:** re-run the author-companion re-voice on chapter 7 with the person-conversion instruction made explicit and gated (e.g. fail a window whose output retains more than N third-person "The X said:" attribution tags when `book_voice: author_companion`). The current window gate passed with 0 warnings, which means the gate does not test for the frame at all. Do this **after** BK1/BK2 are repaired at the base, so the re-voice runs on a clean chunk.

### BK4 · BK-P5 · P2 · VERIFIED
- **Chapter:** bk-07
- **book.md:** line 674
  > Let me tell you how the scholar's heart was moved for the boy, once he saw how the jewel hidden within him had come clear…
- **Base:** `bk-07.md` line 79
  > The narrator said: The scholar's heart was moved for the boy when he saw how the jewel within him had come clear…
- **Source:** `refined-english.md` line 572, para (232) — "The narrator said: The scholar's heart was moved on the boy's behalf…"
- **Why it fails:** the re-voice replaced the narrator tag with a narrator-announcement ("Let me tell you how…"). In chapters 5/6/8 that would be in-voice; in chapter 7 there is no established "I", so this is the single first-person intrusion in an otherwise third-person chapter and its speaker is unidentifiable. Advisory only; it resolves automatically if BK3 is repaired.
- **Worker action:** none independently — subsumed by the BK3 re-voice.

### BK5 · BK-P4 · P2 · VERIFIED
- **Chapter:** bk-07
- **book.md:** line 679 — "in whose hand are the keys of **the gardens** and the landmarks of the kingdom"
- **Source/OCR:** `raw-extract.md` line 967 — "in whose hand is the keys of **heaven** and the landmarks of the kingdom"; `refined-english.md` line 578 — "the keys of the **heavens**"
- **Why it fails:** a noun in a doctrinal formula about the one holding the keys drifted from *heavens* to *gardens*. Also in this family: para (279) "I am newborn to you, **and you nurture me**" renders as "Then I am newly born to you. **Name me.**" (line 768), and para (274)'s ownership question is recast. All three are **base-inherited** — present verbatim in `bk-07.md` lines 165/167/177 — and none were introduced by the re-voice. Checked and cleared: "and he gestured with his hand toward the scholar who had called him" (line 770) IS source-grounded (OCR line 1073 "…his hand to the world. / who called him.") and is **not** an invention.
- **Worker action:** correct "gardens" -> "heavens" and restore "and you nurture me" when the base chunk is regenerated under BK1.

---

## What the re-voice pass got right (no findings)

- **No abridgement.** 7,589 words out of a 7,258-word base; 125 content paragraphs against 126, the single difference being the seam-1 merge. The failure mode that caused the earlier revert did not recur.
- **No invention.** A word-level diff of the full chapter against the base yields 487 edit hunks, of which exactly **two** exceed 8 words, and both are pure rephrasings ("the ease of its asking" -> "for how easy they were to ask for"). No teaching, ruling, named authority, citation, or doctrine was added.
- **No reattribution.** Every "The scholar said" / "The boy said" / "The Shaykh said" turn keeps its original speaker.
- **Scripture untouched.** All five Arabic blocks byte-identical to base; English renderings intact beneath each.
- **Terminology stable.** Allah 13/13, zakat+alms 9/9, imam 1/1, Shaykh 22->23 (the added instance is the chapter title). Zero diacritic leaks book-wide.
- **Seam 1 improved on the base** by repairing a mid-sentence paragraph break.

## Verified vs Inferred summary

All five findings are **VERIFIED** — each cites concrete evidence in `book.md`, `bk-07.md`, `refined-english.md`, and/or `_system/source/ocr/raw-extract.md`. No INFERRED findings were raised.

## Verdict

Two P0 findings remain -> **BLOCKED**.

Both P0s are **inherited from the faithful base chunk, not created by the 2026-07-19 windowed re-voice**. The re-voice itself is clean on fidelity, Arabic, and craft; its one substantive defect is the P1 voice-frame miss (BK3). The repair order is: (1) regenerate `bk-07.md` for source paras (300)-(302) to de-duplicate and restore the missing para (302) tail; (2) re-run the author-companion re-voice on chapter 7 with a person-conversion gate; (3) re-challenge.

## Ledger emission summary

5 records emitted to `_learning/findings.jsonl` with `source: book-challenger`, `resolution: flagged`.
