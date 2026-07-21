# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-21 (book_challenger_version 1.0)
**Scope:** whole-book (delta-focused against approved base 1b750a3)
**Content profile:** islamic_scholarly
**Route:** augmented-companion knobs, translation-edition behaviour (`book_augmentation: source_only`, `book_voice: faithful`; `deliverable_mode` deliberately unset)
**Declared narrative_frame:** transmitted_report
**Chapters reviewed:** 8 + preface
**Iterations:** 1 (of 5 max)
**Verdict (book-level):** BLOCKED

## Method note

Current `book.md` (62a3cf2) differs from the challenger-converged, publication-reviewed base
(1b750a3) by exactly 42 lines. Everything outside those 42 lines is byte-identical to the approved
manuscript, so Pass 1 / Pass 2 fidelity properties are inherited; review effort was concentrated on
the three deterministic passes (transliteration fold, inline Arabic, American spelling) plus a full
Pass 3 re-run.

## Per-chapter verdicts
| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface — How to Read a Conversation Made of Doors | pass | fail (BK-P3 sh-r-, nested parens) | BLOCKED |
| 1. The Persian Who Was Dead and Revived | pass | pass | SHIP-READY |
| 2. A Stranger in the City | pass | fail (BK-P3 sh-r- root) | BLOCKED |
| 3. The Boy at the Door — Limits and Conditions | pass | pass | SHIP-READY |
| 4. How the World Was Made | pass | pass | SHIP-READY |
| 5. The World, the Hereafter, and the Speech of Parables | pass | fail (BK-P3 natiq) | BLOCKED |
| 6. Three Layers of Knowledge | pass | pass | SHIP-READY |
| 7. The Five Shares and the Long Road to the Shaykh | pass | fail (BK-P3 Abd Allah split; draught) | BLOCKED |
| 8. Homecoming, the Father, and the Debate with Abu Malik | pass | fail (BK-P3 duplicated Kab al-Ahbar) | BLOCKED |

## Whole-book passes
| Check | Result |
|---|---|
| BK-A1 voice consistency | pass (unchanged from approved base) |
| BK-A2 segmentation sanity | pass (8 chapters, contiguous source ranges 14–1353, no gaps) |
| BK-A3 preface + TOC integrity | pass (headings monotonic, match book-toc.json) |
| BK-A4 plain transliteration | pass on diacritics; P2 residue (`labelled`; Arabic inside italic/bold spans) |
| BK-A5 tradition fit | n/a — no enrichment atoms woven (source_only) |
| BK-N3 frame consistency | pass — transmitted_report throughout; deterministic frame_findings = 0 |
| BK-P7 duplicated passage | pass — `_system/book-duplication-check.json` empty; manual sweep clean |
| Deterministic Pass 3 (`_narrative.py`) | frame 0 / speech-tag 0 / arabic-retention 0 / supplied-diacritics 0 / enumeration 0 |
| Terminological consistency after fold | pass — no split renderings, no collisions (Sharia 6/6, Shuayb 2/2, Salih 92/92, Kab vs Kabir distinct) |
| Quranic + source Arabic blockquotes | untouched by all three passes (verified by diff + arabic_retention_findings) |

## Findings

### BK1 · BK-P3 · P0 · VERIFIED
- **Chapter:** 5 — The World, the Hereafter, and the Speech of Parables
- **book.md:** line 374 — `"They are the causes between God and the speaker (natiq (النطقاء)), and they are His."`
- **Source:** `_system/source/ocr/raw-extract.md` line 509 — `تلك أسباب بين الله وبين النطقاء، وهي له`
- **Why it fails:** النطقاء is the definite PLURAL (*al-nutaqa*); the transliteration it sits beside is the singular *natiq*, and the English is singular "the speaker". The script does not correspond to the term it annotates. Root cause is the glossary entry itself (`_system/glossary.yml`: `nāṭiq → النطقاء`), so it would propagate on any re-run.
- **Worker action:** Correct the glossary `arabic_script` to `الناطق` for the singular entry (or re-render the English as plural to match the source's النطقاء and annotate `nutaqa (النطقاء)`), then re-apply the inline pass.

### BK2 · BK-P3 · P0 · VERIFIED
- **Chapter:** 7 — The Five Shares and the Long Road to the Shaykh
- **book.md:** line 779 — `The boy said: "I am free, son of Abd Allah (الله)."`
- **Source:** raw-extract line 1064 — `قال: عُبيد الله ابن عبد الله`
- **Why it fails:** The "Allah" glossary entry fired on the *Allah* inside the proper name *Abd Allah*, splitting the name and annotating half of it. Four lines earlier (775) the same name is correctly annotated `Abd Allah (عبد الله)`, so the book now carries two different scripts for one name inside one chapter.
- **Worker action:** Suppress the standalone `Allah → الله` match when it falls inside a multi-word name already in the glossary (`Abd Allah`, `Ubayd Allah`); drop the annotation at 779 entirely (the name's first mention in the chapter is already annotated).

### BK3 · BK-P3 · P0 · VERIFIED
- **Chapter:** 8 — Homecoming, the Father, and the Debate with Abu Malik
- **book.md:** line 885 — `... their religion, "Kab al-Ahbar (كعب الأحبار)" (كعب الأحبار). Among them he was a man of standing ...`
- **Why it fails:** The Arabic was already present in the approved base as a trailing parenthetical; the inline pass added a second copy inside the quoted epithet. The printed page will show the same Arabic twice in eight characters.
- **Worker action:** Teach the inline pass to skip a term whose Arabic already appears within the same sentence, and delete one of the two copies here (keep the one inside the quoted epithet, drop the trailing pair).

### BK4 · BK-P3 · P0 · VERIFIED
- **Chapter:** 2 — A Stranger in the City (editorial note)
- **book.md:** line 114 — `> sense of the word for sacred law itself. The root of *Sharia* (sh-r-) means to open up a path`
- **Base (1b750a3):** `The root of *Sharia* (sh-r-') means to open up a path`
- **Why it fails:** The transliteration fold dropped the apostrophe that was standing for the third radical **ʿayn**. What was a correct trilateral root citation (sh-r-ʿ) is now a two-letter stub with a dangling hyphen, and the etymological claim the note makes is no longer true as printed. The apostrophe-drop rule is right for names and terms; it must not apply inside a root citation.
- **Worker action:** Restore the third radical. Preferred form given the book's own new convention: `The root of *Sharia* (ش ر ع)` — Arabic letters, no Latin apostrophe needed. Add a fold exemption for `X-Y-Z'` root patterns.

### BK5 · BK-P6 · P1 · VERIFIED
- **Chapters:** preface (line 13) and 5 (lines 354, 358, 362, 366, 374)
- **book.md:** line 13 — `the speaking Imam (الإمام) (*al-Imam al-Natiq (الإمام الناطق)*), his gate (*bab (باب)*), his successor (*wasi (وصيه)*), his summoners (*duat (الدعاة)*)`
- **Why it fails:** Twelve sites where the annotation landed inside an existing parenthetical, producing parentheses nested one inside another — `(natiq (النطقاء))`, `(bab (باب))`, `(hujaj (الحجج))`, `(tawil (التأويل))`, `(nuqaba (النقباء))`, `(duat (الدعاة))`. Line 13 and line 354 additionally give the script for *Imam* twice in a single clause (`الإمام` then `الإمام الناطق`). This is the book's most doctrinally important vocabulary passage and it now reads as machine output.
- **Worker action:** When the anchor is already inside `(...)`, set the script off with a comma or an em-dash instead of a second paren pair — `the gate (bab, باب)` — and suppress the standalone term when a compound containing it is annotated in the same clause.

### BK6 · BK-P3 · P1 · VERIFIED
- **Chapters:** preface (line 13), 5 (line 362)
- **book.md:** `his successor (*wasi (وصيه)*)`
- **Why it fails:** وصيه carries the pronominal suffix ـه ("HIS wasi"); the transliteration beside it is the bare *wasi*. Glossary-sourced (`waṣī → وصيه`), so it will recur.
- **Worker action:** Set the glossary `arabic_script` to the citation form `وصي` (or `الوصي`), matching how `bab`, `hujaj`, `nuqaba` are handled.

### BK7 · BK-P1 · P1 · VERIFIED
- **Chapter:** 7 — The Five Shares and the Long Road to the Shaykh
- **book.md:** line 231 — `his way became clear and his draft grew sweet, and he came to know his Lord`
- **Base (1b750a3):** `his way became clear and his draught grew sweet`
- **Why it fails:** The American-spelling pass converted *draught* (a drink drawn from a spring — the water imagery that runs from the preface's "watering-places" through this sentence) into *draft*, which in American English reads as a preliminary document. The sentence's sense is destroyed.
- **Worker action:** Restore `draught`, or re-word to `his drink grew sweet`. Add `draught` to the American-fold exclusion list (the beverage/drawing sense has no safe American substitute here).

### BK8 · BK-N7 · P1 · VERIFIED
- **Chapter:** 8 — lines 1255, 1273 (and 551, 559)
- **book.md:** `So it was revealed to Lot (ع) by the hand of Abraham (ع)` / `no messenger after Moses (ع)` / `Ishmael and Isaac (عليهم السلام)`
- **Why it fails:** These six honorific abbreviations are inherited from the approved base and were correct when the book had only ten parenthetical Arabic items. The inline pass has now established, across 68 sites, the convention *English/transliteration (its Arabic)*. Under that convention `Joseph (ع)` reads as though ع were the Arabic for Joseph. The book also mixes the abbreviation `(ع)` with the spelled-out `(عليهم السلام)` for the same function — an elegant-variation defect in exactly the place terminological consistency matters.
- **Worker action:** Pick one form and apply it uniformly. Recommended: spell out `(عليه السلام)` / `(عليهم السلام)` everywhere, so the reader never sees a bare letter in a slot the rest of the book uses for a term's script.

### BK9–BK14 · P2 · advisory (no verdict impact)
- **BK-P3, line 701** — `the light of Sinai (الطور)`: الطور is *al-Tur*, transliterated as **Tur** at line 45. The script is correct for the term but does not correspond to the English word it sits beside. Prefer `the light of the Mount, al-Tur (الطور)`.
- **BK-P3, lines 987, 1019** — `O Abu Salih (أبا صالح)`, `O Abu al-Khair (أبا الخير)`: the script is the vocative accusative (correct Arabic after يا) while the transliteration is nominative *Abu*. Contextually right, conventionally mismatched.
- **BK-P3, line 358 et al.** — inconsistent definite article: `nuqaba (النقباء)` and `duat (الدعاة)` carry `al-` in the script but not the transliteration, while `bab (باب)` and `Imam (الإمام)` go the other way. Normalize to citation form.
- **BK-A4, lines 9, 533, 537** — Arabic script placed inside `**bold**` (`**The Shaykh (الشيخ)**`) and `*italic*` (`*hawl (الحول)*`) spans. Arabic has no italic; renderers synthesize an oblique. Move the script outside the emphasis markers.
- **BK-P3, line 462** — `O children of Adam (آدم)` sits in the English translation directly beneath the Quranic block that already reads `يَا بَنِي آدَمَ`, restating the same word unvowelled next to the vowelled mushaf form.
- **BK-A4, line 15** — `labelled` survived the American-spelling fold (should be `labeled`).

## Verified vs Inferred summary
14 findings, all VERIFIED against `book.md`, the approved base at 1b750a3, `_system/glossary.yml`, and `_system/source/ocr/raw-extract.md`. 0 INFERRED.

Arabic verification coverage: all 68 inline annotations checked glyph-by-glyph against their glossary
`arabic_script` field and, where the term appears in the scan, against `raw-extract.md`. All Quranic
and source blockquote Arabic is byte-identical to the approved base (no re-verification required; it
was verified at that commit, resolution ladder canonical-mushaf/ocr, 0 unverified in
`_system/book-arabic-audit.json`). `عُبيد الله` at line 775 carries a damma — CONFIRMED as scan
vowelling (raw-extract line 1064), not model-supplied. BK-N5 clean.

## Ledger emission summary
14 records appended to `_learning/findings.jsonl` (source `book-challenger`, version 1.0,
resolution `flagged`): 4 × P0, 4 × P1, 6 × P2. No file under `book/` other than this report was modified.
