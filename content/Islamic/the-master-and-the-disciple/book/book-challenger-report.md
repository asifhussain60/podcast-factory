# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-22 9:46 AM EST (book_challenger_version 1.0)
**Scope:** whole-book — FINAL convergence run (verification of the BK1/BK4/BK5 corrections + settlement of BK2/BK3/BK6)
**Content profile:** islamic_scholarly
**Route:** augmented-companion knobs, translation-edition behaviour (`book_augmentation: source_only`, `book_voice: faithful`)
**Declared narrative_frame:** transmitted_report
**Chapters reviewed:** 8 + preface
**Iterations:** 1 (of 5 max) — third full sweep today; prior sweeps 09:30 (SHIP-WITH-CAUTION) and morning (SHIP-READY pre-annotation)
**Verdict (book-level):** SHIP-READY

## Method note

Word-level diff of working-tree `book.md` against git HEAD (b0f7d02): **exactly three changed
lines** — 296, 567, 885 — each matching one declared correction, nothing else moved. One upstream
line changed in `refined-english.md` (the (181) paragraph, source line 447 area), mirroring the
BK1 fix. `composer-edits.json` diff: exactly three new entries appended. `book-arabic-audit.json`
diff: exactly the expected restamp (أولياء الله run removed, 58→57, canonical 25→24). Zero speech
tags, zero enumerations, zero blockquotes, zero Quranic text changed — confirmed deterministically:
`_narrative.frame_findings(HEAD, working-tree, frame=transmitted_report)` returns 0 findings, and
`ocr_vowelling_findings` returns 0. All unchanged text inherits Pass 1/2/3 verdicts from today's
two prior sweeps.

## Verification of the three corrections (all VERIFIED against the scan/glossary)

### BK1 — al-Khidr misreading (P1) — FIXED, verified against the scan
Line 567 now reads: "The seven green ears are causes between God and the guardians." The scan
(`_system/source/ocr/raw-extract.md` lines 724–726) reads
`والسبع السنبلات٦ الخضر أسباب بين الله وبين الأوصياء` — الخضر is the adjective *khudr* ("green",
modifying السنبلات), the predicate أسباب is indefinite plural "causes". The corrected sentence
matches the Arabic word-for-word, restores the plural predicate, and restores the sevenfold
parallelism (fat cows = causes of God; lean cows = the seven natiqs; green ears = causes; dry
ears = the guardians). The fabricated person al-Khidr is gone from `book.md` entirely (zero
matches for Khidr/خضر book-wide). The same correction was applied upstream:
`refined-english.md` (181) now reads "The seven green ears⁶ are causes between God and the
guardians [awliyāʾ]" — the root cause (Phase-0b translation misreading) is corrected at source,
so no future compose can re-inherit it. **RESOLVED.**

### BK4 — awliya fossil annotation (P2) — FIXED, glossary-exact
Line 296 now reads: "the friends of God (awliya, أولياء) are bound". The script matches the
curated glossary entry `awliyāʾ → أولياء` glyph-for-glyph; the teach-term introduction now
carries its Latin name in the standard `(name, script)` intro form (same shape as the preface's
al-Imam al-Natiq / bab intros); the Latin side is plain ASCII (BK-A4 pass). The Worker reports
the site byte-stable across two re-runs of the annotation pass (inside the derive loop) —
stability under future derivation is Worker-attested (not re-run here, since a re-run would
mutate `book.md`); the current bytes are VERIFIED correct. **RESOLVED.**

### BK5 — punctuation placement (P2) — FIXED
Line 885 now reads `"Kab al-Ahbar (كعب الأحبار)."` — period inside the closing quotation mark,
American convention, matching the edition's locked American-spelling standard. Script unchanged
and still scan-grounded. **RESOLVED.**

## Settlements (accepted by author authorization — recorded, not findings)

- **BK2 (al-Khidr glossary entry):** deliberately KEPT with empty `arabic_script`. It serves the
  PODCAST lane (ch07d's editorial "the figure traditionally identified as Khidr" — legitimate
  enrichment, not a misreading), and the empty script keeps it out of the book pass. Accepted.
- **BK3 (Hizb Allah romanization anchor):** `(*Hizb Allah*)` at line 244 stays — it is the
  author's gloss shape and the derive loop's re-derivation anchor. Accepted as convention.
- **BK6 (script-side definite-article mix):** bare باب vs articled الوصي/الدعاة/النقباء etc.
  follows curated citation forms in the glossary. Accepted as convention.

## Composer-edit sidecar (the durability check)

`_system/composer-edits.json` carries four entries; anchor keys all resolve against live
headings via `_book_edits.anchor_key` (no orphans):

| chapter_key | anchors to | body vs live |
|---|---|---|
| how to read a conversation made of doors (2026-07-21) | preface | pre-existing; body predates the approved annotation reshape — self-healing (replay → derive loop restyles), noted below |
| how the world was made (2026-07-22) | ch 4 | **byte-identical** (8,491 chars) |
| three layers of knowledge (2026-07-22) | ch 6 | **byte-identical** (18,401 chars) |
| homecoming, the father, and the debate with abu malik (2026-07-22) | ch 8 | **byte-identical** (77,183 chars) |

The three fix-carrying edits embed the corrected sentences (including the awliya annotation
reshape), so every correction survives a re-compose. **Observation, not a finding:** the
2026-07-21 preface edit's body carries the pre-reshape annotation forms
(`(الإمام) (*al-Imam al-Natiq (الإمام الناطق)*)` vs live `(al-Imam al-Natiq, الإمام الناطق)`).
This pre-dates today's work, was present at the 09:30 APPROVED sweep, and is self-correcting:
on a future re-compose the replayed body passes through the same annotation derive loop that
produced the live shape (verified idempotent by the Worker). Not new, not material — recorded
for continuity only.

## Sidecar freshness (VERIFIED current — recomputed in memory, not trusted from mtime)

- `book-arabic-audit.json`: recomputed via `audit_book_arabic` over current `book.md` bytes +
  OCR + knowledge base — **chapter lists byte-equal to the stored sidecar**; totals identical:
  57 runs = 24 canonical-mushaf + 32 ocr + 0 knowledge-base + 1 honorific-formula +
  **0 unverified**; `ocr_vowelling_findings` = 0 (no vowelling_review key, correctly absent).
- Canonical count 25→24 explained and expected: the removed parenthetical أولياء الله (a Quranic
  phrase, resolved canonical) gave way to bare أولياء, which at 6 Arabic letters sits below the
  audit's 8-letter run threshold (`_ARABIC_RUN_MIN_CHARS = 8`) and so does not register as a run
  at all — same as every other short annotation term (باب, الشيخ). The ocr total is unchanged at
  32. **No Quranic verse text was touched** — the delta is an annotation parenthetical, not a
  quotation block.
- `book-duplication-check.json`: recomputed via `duplicate_passage_findings` over current bytes —
  0 findings, matching the stored sidecar.

## Per-chapter verdicts
| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface — How to Read a Conversation Made of Doors | pass | pass | SHIP-READY |
| 1. The Persian Who Was Dead and Revived | pass | pass | SHIP-READY |
| 2. A Stranger in the City | pass | pass | SHIP-READY |
| 3. The Boy at the Door — Limits and Conditions | pass | pass (BK3 accepted) | SHIP-READY |
| 4. How the World Was Made | pass | pass (BK4 fixed, verified) | SHIP-READY |
| 5. The World, the Hereafter, and the Speech of Parables | pass | pass | SHIP-READY |
| 6. Three Layers of Knowledge | **pass (BK1 fixed, verified against scan)** | pass | SHIP-READY |
| 7. The Five Shares and the Long Road to the Shaykh | pass | pass | SHIP-READY |
| 8. Homecoming, the Father, and the Debate with Abu Malik | pass | pass (BK5 fixed) | SHIP-READY |

## Whole-book passes
| Check | Result |
|---|---|
| BK-A1 voice consistency | pass (three sentence-level deltas, register unchanged) |
| BK-A2 segmentation sanity | pass (TOC/crosswalk untouched) |
| BK-A3 preface + TOC integrity | pass — headings monotonic, match book-toc.json |
| BK-A4 plain transliteration | pass — "awliya" plain ASCII; zero Latin diacritics book-wide |
| BK-A5 tradition fit | n/a — source_only, no enrichment |
| BK-N1 narrative person | pass — frame_findings(HEAD→tree) = 0 |
| BK-N2 speech attribution | pass — zero tag deltas ("The Master said:" unchanged at 567) |
| BK-N3 frame consistency | pass — transmitted_report, one narrator |
| BK-N4 Arabic script retention | pass — أولياء retained with transliteration BESIDE the script |
| BK-N5 supplied diacritics | pass — ocr_vowelling_findings = 0; both changed scripts unvowelled |
| BK-N6 enumeration | pass — sevenfold structure RESTORED by the BK1 fix |
| BK-N7 register/terminology | pass — "causes" now consistent across all four limbs of the dream |
| BK-P7 duplicated passage | pass — 0 findings, recomputed over current bytes |

## Findings

None open. 0 × P0, 0 × P1, 0 × P2. Three prior findings RESOLVED (BK1, BK4, BK5 — all fixes
verified against the scan/glossary/convention); three prior advisories ACCEPTED as conventions
by author authorization (BK2, BK3, BK6). No new material findings; the preface composer-edit
staleness is a pre-existing, self-healing observation recorded above.

## Verified vs Inferred summary

All six dispositions VERIFIED against concrete evidence: the OCR scan (green-ears passage,
lines 724–726), `refined-english.md` (181), `glossary.yml` (awliyāʾ/أولياء, al-Khidr entries),
word-level git diffs of all four changed files, byte-comparison of composer-edit bodies vs live
chapter bodies, in-memory recomputation of both audit sidecars, and deterministic
`_narrative` seeds. One Worker-attested claim noted as such (annotation-pass byte-stability at
the awliya site across future re-derivations); current bytes independently VERIFIED.

## Ledger emission summary

6 records appended to `_learning/findings.jsonl` (source `book-challenger`, version 1.0):
3 × `resolved` (BK1/BK4/BK5 signatures), 3 × `accepted-convention` (BK2/BK3/BK6 signatures).

**Verdict: SHIP-READY.** Every delta since HEAD is one of the three declared corrections (plus
the awliya annotation reshape they required); the al-Khidr fabrication is corrected at both the
edition and its source ground truth and verified word-for-word against the Arabic scan; all
corrections are durably recorded in the Composer sidecar and survive re-compose; both audit
sidecars describe the current bytes exactly. No open findings at any severity.
