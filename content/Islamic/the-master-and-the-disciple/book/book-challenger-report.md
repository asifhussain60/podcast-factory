# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-22 (book_challenger_version 1.0)
**Scope:** whole-book (re-challenge after generator fixes 26a349b, 93fe1f4, 53ffdf9, 0b52991)
**Content profile:** islamic_scholarly
**Route:** augmented-companion knobs, translation-edition behaviour (`book_augmentation: source_only`, `book_voice: faithful`; `deliverable_mode` deliberately unset; route pinned by compose_book_v2 step 1)
**Declared narrative_frame:** transmitted_report
**Chapters reviewed:** 8 + preface
**Iterations:** 1 (of 5 max)
**Verdict (book-level):** SHIP-READY

## Method note

Re-challenge scope: word-level diff of current `book.md` against the challenger-converged approved
base (1b750a3) enumerates every delta. All 42 changed lines fall into exactly four sanctioned
categories — inline Arabic annotation, plain-transliteration fold, American spelling, and the
first-use honorific expansion. Zero prose sentences, zero speech tags, zero enumerations, and zero
Quranic/source blockquotes changed, so Pass 1 / Pass 2 fidelity is inherited from the converged base
and review effort concentrated on the changed lines plus a fresh Pass 3 and Arabic verification sweep.

## Resolution of the prior run's findings (all closed)

| Prior | Was | Now | Status |
|---|---|---|---|
| BK1 natiq plural script | `(natiq (النطقاء))` | line 374 `the speaker (الناطق)`; glossary `arabic_script: الناطق` | RESOLVED (generator) |
| BK2 Allah fired inside Abd Allah | line 779 `Abd Allah (الله)` | annotation removed; standalone `Allah (الله)` correctly re-fired at ch-7 first standalone use (line 841) — verified first-use-per-chapter across all 8 chapters | RESOLVED (span reservation) |
| BK3 Kab al-Ahbar doubled script | script twice in 8 chars | line 885 single `"Kab al-Ahbar" (كعب الأحبار)` | RESOLVED (idempotency window) |
| BK4 sh-r- root stub | third radical dropped | line 113 `*Sharia* (sh-r-')` restored | RESOLVED (fold exemption) |
| BK5 nested parentheses (12 sites) | `(natiq (النطقاء))` etc. | script REPLACES the romanization: `his gate (باب)` — zero nested parens remain book-wide | RESOLVED by 53ffdf9; residual editorial call noted as BK5 below |
| BK6 wasi with suffix | `وصيه` | `الوصي` (lines 13, 362; glossary fixed) | RESOLVED |
| BK7 draught→draft | sense destroyed | line 823 `his draught grew sweet` restored; exclusion in the American fold | RESOLVED |
| BK8 honorific mixing | bare `(ع)` under the annotation convention | first-use expansion: line 551 `Joseph (عليه السلام)` in full; later `(ع)` sites (559, 1255, 1273) abbreviate per the LOCKED convention (full on first use, abbreviation after); the plural formula's only occurrence (1255, عليهم السلام) is full | RESOLVED by convention (0b52991) — later (ع) sites deliberately NOT flagged |
| P2s: labelled; Arabic in bold/italic spans | — | `labeled` (line 15); scripts moved outside `**…**`/`*…*` spans (lines 9, 533, 537) | RESOLVED |

## Per-chapter verdicts
| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface — How to Read a Conversation Made of Doors | pass (inherited; Composer-edited — author's text) | pass | SHIP-READY |
| 1. The Persian Who Was Dead and Revived | pass | pass | SHIP-READY |
| 2. A Stranger in the City | pass | pass (sh-r-' restored) | SHIP-READY |
| 3. The Boy at the Door — Limits and Conditions | pass | pass | SHIP-READY |
| 4. How the World Was Made | pass | pass | SHIP-READY |
| 5. The World, the Hereafter, and the Speech of Parables | pass | pass (natiq singular) | SHIP-READY |
| 6. Three Layers of Knowledge | pass | pass | SHIP-READY |
| 7. The Five Shares and the Long Road to the Shaykh | pass | pass (Abd Allah healed; draught restored) | SHIP-READY |
| 8. Homecoming, the Father, and the Debate with Abu Malik | pass | pass (single Kab al-Ahbar script) | SHIP-READY |

## Whole-book passes
| Check | Result |
|---|---|
| BK-A1 voice consistency | pass (no prose changed vs converged base) |
| BK-A2 segmentation sanity | pass — TOC ranges 14–1353 contiguous, preface 8–13, source head 1–7 in front matter; crosswalk present and matches TOC exactly |
| BK-A3 preface + TOC integrity | pass — headings monotonic, match book-toc.json |
| BK-A4 plain transliteration | pass — zero scholarly diacritics in Latin text; apostrophe folds consistent (Jafar, dawa, Kab 2/2, Shuayb 2/2, Mamur); `sh-r-'` exempted by design |
| BK-A5 tradition fit | n/a — source_only, no enrichment atoms |
| BK-N1 narrative person | pass — transmitted_report throughout |
| BK-N2 speech attribution | pass — zero tag deltas vs converged base |
| BK-N3 frame consistency | pass — one narrator, all chapters |
| BK-N4 Arabic script retention | pass — 65 inline annotations, each glyph-checked against glossary; all scripts correct for their terms |
| BK-N5 supplied diacritics | pass — عُبيد الله damma is scan vowelling (raw-extract 1064); honorific formulae unvowelled; Quranic vowelling covered by the mushaf convention (see BK6 advisory) |
| BK-N6 enumeration | pass — no enumeration touched by the deltas |
| BK-N7 register/terminology | pass — no split renderings after folds |
| BK-P7 duplicated passage | pass — duplication-check findings empty; no prose changed since the manual ch7 merge review |
| Arabic audit | 23 canonical-mushaf / 30 ocr / 1 honorific / 0 unverified; 1 vowelling_review item disposed as BK6 below |
| Allah annotation placement | verified first-standalone-use-per-chapter: preface 23, ch1 45, ch2 65, ch3 130, ch4–5 none (chapters use "God"), ch6 497, ch7 841, ch8 875 — none earlier unannotated |

## Findings (P2 only — advisory, no verdict impact)

### BK1 · BK-P3 · P2 · VERIFIED (carry-over — open editorial call, unchanged)
- **Chapter:** 7 — The Five Shares and the Long Road to the Shaykh
- **book.md:** line 701 — `whose palms are opened with the light of Sinai (الطور)`
- **Why:** الطور is *al-Tur*; the English word beside it is "Sinai". Script correct for the term, mismatched to the word it annotates. Prefer `the Mount, al-Tur (الطور)`.

### BK2 · BK-P3 · P2 · VERIFIED (carry-over — open editorial call, unchanged)
- **Chapter:** 8 — lines 987, 1019 — `O Abu Salih (أبا صالح)`, `O Abu al-Khair (أبا الخير)`
- **Why:** Script is vocative accusative (correct Arabic after يا) beside nominative *Abu*. Contextually right, conventionally mismatched.

### BK3 · BK-P3 · P2 · VERIFIED (carry-over — open editorial call; shape changed with script-only annotations, issue persists)
- **Chapters:** preface (lines 5, 13), 5 (line 362)
- **book.md:** `his gate (باب)` vs `his successor (الوصي)`, `his summoners (الدعاة)`, `the twelve arguments (الحجج)`; `the Ismaili dawa (دعوة)` vs definite English
- **Why:** Definite article carried inconsistently across annotations. Normalize to citation form (الباب or bab throughout).

### BK4 · BK-P3 · P2 · VERIFIED (carry-over — open editorial call, unchanged)
- **Chapter:** 5 — line 462 — `O children of Adam (آدم), We have sent down…`
- **Why:** The annotation sits in the translation directly beneath the Quranic block that already reads `يَا بَنِي آدَمَ`, restating the same word unvowelled beside the vowelled mushaf form.

### BK5 · BK-N7 · P2 · VERIFIED (new state of the nested-parens editorial call)
- **Chapters:** preface (line 13), 5 (lines 354–374)
- **book.md:** `the speaking Imam (الإمام الناطق), his gate (باب), his successor (الوصي), his summoners (الدعاة)`
- **Why:** The 53ffdf9 resolution (script replaces romanization) eliminated all twelve nested-paren sites — verified zero remain book-wide — but as a side effect the terms *natiq, bab, wasi, duat, nuqaba, hujaj, tawil* no longer appear in Latin anywhere in the book. A reader who cannot read Arabic script can no longer NAME the book's core technical vocabulary, and the preface sentence introducing "a set of terms" now shows only glyphs. Where the romanization is itself the running text (*hawl*, *quwwa*, lines 533/537) it survives — so the alternative form `the gate (bab, باب)` remains available if Asif wants the names back. Open editorial call; no verdict impact.

### BK6 · BK-P3 · P2 · VERIFIED (new — verification-infrastructure advisory)
- **Chapter:** 7 — line 769 — `وَمَا يُلَقَّاهَا إِلَّا الَّذِينَ صَبَرُوا وَمَا يُلَقَّاهَا إِلَّا ذُو حَظٍّ عَظِيمٍ`
- **Source:** raw-extract line 1059 — `وما يُلقاها إلا الذين صبروا وما يُلقاها إلا ذو حظ عظيم` (scan, near-bare)
- **Why:** This IS canonical Quran (41:35) — verified against `mirror.db` (surah 41, ayat 35) by manual comparison; the harakat supplied are recitation-correct and the full vowelling is licensed by the book's stated convention ("where they are Quran they carry the vowelling of the mushaf"). But the book keeps the scan's standard (imla'i) rasm `يُلَقَّاهَا` where the Uthmani mushaf has `يُلَقَّىٰهَآ`, and `_arabic_coverage.normalize_arabic` does not fold `ىٰ`→`ا` — so `_mushaf.is_quranic` returns False and the audit lists this verse under `vowelling_review` on EVERY run, a recurring false positive that will erode trust in that review list. Worker action: extend the normalizer (or the defective-substring path) to equate alif-maqsura-with-dagger-alif with plain alif; advisory only, never a gate.

### BK7 · BK-A2 · P2 · VERIFIED (new — process staleness)
- **Artifacts:** `_system/book-arabic-audit.json`, `_system/book-duplication-check.json`
- **Why:** Both predate the last book.md commit (0b52991, honorific expansion) by ~2h50m. The only textual delta since their stamp is `(ع)`→`(عليه السلام)` at line 551 — manually verified benign (correct formula, unvowelled) — but the audit's honorific-formula count (1) no longer reflects the manuscript. Restamp on next compose/audit run.

## Verified vs Inferred summary
7 findings, all VERIFIED — against `book.md`, the approved base at 1b750a3, `_system/glossary.yml`,
`_system/source/ocr/raw-extract.md`, and `content/knowledge-base/mirror.db` (canonical mushaf,
consulted directly for Q 41:35, 2:233, 28:76, 12:4, 7:26). 0 INFERRED.

Arabic verification coverage: all 65 inline annotations glyph-checked against the glossary and, where
present in the scan, against raw-extract; all Quranic/source blockquotes byte-identical to the base
verified at 1b750a3 (fresh mushaf spot-checks passed modulo the imla'i-vs-Uthmani orthography
convention documented at BK6). Nothing passed silently: the single `vowelling_review` item is
disposed above with a canonical verification, not waved through.

## Ledger emission summary
7 records appended to `_learning/findings.jsonl` (source `book-challenger`, version 1.0,
resolution `flagged`): 0 × P0, 0 × P1, 7 × P2. No file under `book/` other than this report was
modified. Verdict: SHIP-READY — the four P0s and four P1s of the prior run are all resolved at the
generator; only advisory P2s remain, all open editorial calls or infrastructure notes.
