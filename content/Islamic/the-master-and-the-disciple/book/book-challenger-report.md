# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-22 09:30 EST (book_challenger_version 1.0)
**Scope:** whole-book (re-challenge after annotation policy 40cc2ef — one deliberate change: `_book_inline_arabic.apply_inline_arabic` under per-term `annotation_class`, plus sidecar restamp)
**Content profile:** islamic_scholarly
**Route:** augmented-companion knobs, translation-edition behaviour (`book_augmentation: source_only`, `book_voice: faithful`)
**Declared narrative_frame:** transmitted_report
**Chapters reviewed:** 8 + preface
**Iterations:** 1 (of 5 max)
**Verdict (book-level):** SHIP-WITH-CAUTION

## Method note

Word-level diff of working-tree `book.md` against the last committed state (HEAD, last touched
0b52991): 31 changed lines, 31 insertions / 31 deletions, every hunk an annotation add / remove /
reshape. **Zero prose sentences, zero speech tags, zero enumerations, zero blockquotes, zero Quranic
text, zero honorifics changed.** Pass 1 / Pass 2 / Pass 3 fidelity is therefore inherited from the
morning's SHIP-READY run for all unchanged text; review concentrated on (a) the 31 changed lines,
(b) glyph-verification of all 30 surviving Arabic parentheticals, (c) the R-ARABIC-SCRIPT-RETAINED
judgment call, (d) the four prior P2 dispositions, (e) sidecar freshness — plus one source-grounded
spot-check that surfaced a NEW upstream P1 (BK1) in text this change did not touch.

## The annotation change itself: CLEAN

- 65 → 30 Arabic parentheticals (24 term annotations + 6 honorific formulae), matching the approved
  policy. All familiar-class removals (Allah ×7, Adam ×3, Islam ×2, Imam ×2, sunna ×2, Sharia ×2,
  zakat ×2, Shaykh, Sinai, Shuayb, Talut) and silent-class removals (quwwa, al-Kabir) verified as
  policy, not defects. No double spaces, no orphaned punctuation (one advisory, BK5).
- **Glyph verification:** all 24 surviving term annotations match the curated glossary
  `arabic_script` glyph-for-glyph, except the pre-existing fossil at line 296 (BK4). Honorific
  formulae excluded by design. Zero scholarly diacritics in Latin text (BK-A4 pass).
- **Teach-class introductions:** al-Imam al-Natiq / bab / wasi / duat introduced `(name, script)` at
  preface line 13; nuqaba (358), tawil (362), hujaj (366), natiq (374) at first use; dawa (5),
  hawl (533), alif (1137) script-appended at first prose use. Every later mention (`(*bab*)`,
  `(*wasi*)`, `(*duat*)`, `(*al-Imam al-Natiq*)`) OCCURS AFTER its introduction — ordering verified.
- **Name-class:** Salih / al-Bakhtari / Abu Malik carry script in the front-matter cast list (line 9);
  Ja'far ibn Mansur al-Yaman (5), Tur + Bayt al-Mamur (45), Ubayd Allah + Abd Allah (775, damma is
  scan vowelling), Kab al-Ahbar (885), Abu Salih (987), Abu al-Khair (1019) — all at true first
  mention, all glossary-exact.
- **R-ARABIC-SCRIPT-RETAINED judgment:** NO surviving site violates the rule outright. Every term
  the book teaches and names in Latin carries script at exactly one introduction (or in an adjacent
  quotation block); teach terms with no introduction (batin, zahir, Kun, Taqiyya, hujja, ta'zir, dai)
  never appear in romanized form anywhere in the prose — their concepts are translated — so nothing
  was removed from them. The one-introduction-per-term interpretation is satisfied. Two gaps noted:
  awliya's introduction is script-only with no Latin name (BK4), and al-Khidr has no script at all —
  which investigation shows is not an annotation gap but a translation misreading (BK1).

## Resolution of the four prior P2 advisories

| Prior | Site | Now | Status |
|---|---|---|---|
| Sinai/الطور mismatch | 701 | `the light of Sinai.` plain (familiar class); Tur keeps `(الطور)` at its true site, line 45 | RESOLVED |
| Vocative أبا beside nominative Abu | 987, 1019 | Unchanged bytes, but glossary now deliberately curates `أبا صالح` / `أبا الخير` — both sites are vocative address ("O Abu Salih"), script matches the scan's own form, annotation matches glossary glyph-for-glyph | RESOLVED by curation |
| Definite-article inconsistency | 13, 358–374 | Latin side now uniform bare citation form (bab, wasi, duat, nuqaba, hujaj, natiq, tawil). Script side still mixes باب (bare) vs الوصي/الدعاة/النقباء (article) per glossary curation | SUBSTANTIALLY RESOLVED — residual noted as BK6 |
| Adam under the verse | 462 | Annotation removed; script آدم on the page in the adjacent Quranic block (adjacent-block rule) | RESOLVED |

Also closed from the prior run: BK5 (teach vocabulary unnameable in Latin) — the `(name, script)`
introduction form restores every core term's Latin name except awliya (BK4); BK6 (imla'i-rasm false
positive) — audit now reports 0 `vowelling_review` items after the a8df8dd normalizer fix; BK7
(stale sidecars) — see below.

## Sidecar freshness (VERIFIED current)

`_system/book-arabic-audit.json` and `_system/book-duplication-check.json` are stamped one second
AFTER the current `book.md` bytes (mtime 1784726497 vs 1784726496). Audit totals: 58 Arabic runs =
25 canonical-mushaf + 32 ocr + 1 honorific-formula + **0 unverified**, 0 vowelling_review. This
matches the current inventory (30 inline parentheticals + blockquote runs). Duplication check:
schema v1, findings empty.

## Per-chapter verdicts
| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface — How to Read a Conversation Made of Doors | pass | pass (4 teach intros verified) | SHIP-READY |
| 1. The Persian Who Was Dead and Revived | pass | pass | SHIP-READY |
| 2. A Stranger in the City | pass | pass | SHIP-READY |
| 3. The Boy at the Door — Limits and Conditions | pass | pass (BK3 advisory) | SHIP-READY |
| 4. How the World Was Made | pass | pass (BK4 advisory) | SHIP-READY |
| 5. The World, the Hereafter, and the Speech of Parables | pass | pass | SHIP-READY |
| 6. Three Layers of Knowledge | **fail — BK1 (inherited from refined source)** | pass | **SHIP-WITH-CAUTION** |
| 7. The Five Shares and the Long Road to the Shaykh | pass | pass | SHIP-READY |
| 8. Homecoming, the Father, and the Debate with Abu Malik | pass | pass (BK5 advisory) | SHIP-READY |

## Whole-book passes
| Check | Result |
|---|---|
| BK-A1 voice consistency | pass (zero prose deltas) |
| BK-A2 segmentation sanity | pass (inherited; TOC/crosswalk unchanged) |
| BK-A3 preface + TOC integrity | pass — headings monotonic, match book-toc.json |
| BK-A4 plain transliteration | pass — zero Latin diacritics book-wide |
| BK-A5 tradition fit | n/a — source_only, no enrichment |
| BK-N1 narrative person | pass (inherited — no narration changed) |
| BK-N2 speech attribution | pass — zero tag deltas |
| BK-N3 frame consistency | pass — transmitted_report, one narrator |
| BK-N4 Arabic script retention | pass with advisories (BK2/BK4); no script removed without introduction |
| BK-N5 supplied diacritics | pass — no new diacritics; عُبيد الله damma is scan vowelling |
| BK-N6 enumeration | pass — untouched |
| BK-N7 register/terminology | pass — Latin citation forms now MORE consistent than prior run |
| BK-P7 duplicated passage | pass — findings empty, restamped over current bytes |

## Findings (P1 → P2)

### BK1 · BK-P4 · P1 · VERIFIED (NEW — pre-existing text, upstream of the annotation change)
- **Chapter:** 6 — Three Layers of Knowledge
- **book.md:** line 567 — "The seven green ears are al-Khidr, a cause between God and the guardians."
- **Source:** `_system/source/ocr/raw-extract.md` (offset ~36700) — `والسبع السنبلات الخضر أسباب بين الله وبين الأوصياء` — "And the seven green ears are CAUSES between God and the guardians."
- **Why it fails:** الخضر here is the ADJECTIVE khudr, "green" (plural of akhdar), modifying السنبلات — the Quranic phrase of the king's dream (Q 12:43, سنبلات خضر), which the boy's own question two lines above (line 565) already renders "seven green ears of grain." The predicate is أسباب, indefinite PLURAL: "are causes." The shipped sentence reads الخضر a second time as the PERSON al-Khidr and flattens plural "causes" to "a cause" — inserting a named figure the source never mentions (the scan's ONLY الخضر is this adjective) and breaking the passage's sevenfold parallelism (fat cows = causes of God; lean cows = the seven natiqs; green ears = causes; dry ears = the guardians — seven ears cannot be one person). The compose is NOT at fault: `refined-english.md` line 447 already reads "The seven green ears are al-Khidr, a cause…", so the defect is in the Phase-0b refined translation and every prior challenge inherited it as ground truth. The glossary's al-Khidr entry (class `name`, EMPTY `arabic_script` — the curator could find no matching script, because there is none) is a symptom of the same misreading.
- **Worker action:** correct `refined-english.md` line 447 to "The seven green ears are causes between God and the guardians [awliya]", then fix the shipped sentence through the Book Composer (the singular PDF edit path): "The seven green ears are causes between God and the guardians." Remove or reclassify the glossary's al-Khidr entry. Escalate to Asif — this is an author-judgment translation correction, not a re-run.

### BK2 · BK-P3 · P2 · VERIFIED
- **Glossary:** `_system/glossary.yml` — entry `al-Khidr`, class `name`, `arabic_script` empty.
- **Why:** The policy's intent ("names gained script once at first mention") is unmet for this entry — but per BK1 the entry itself encodes a misreading; the fix is BK1's, not curation of الخضر as a person.

### BK3 · BK-N7 · P2 · VERIFIED (open editorial call)
- **Chapter:** 3 — line 244 — "he had entered the Party of God (*Hizb Allah*)"
- **Why:** Hizb Allah is silent-class ("carries nothing"), yet the site carries a machine-written romanization that never existed in any committed book.md (verified via `git log -S`). `_normalize_annotations` judged the old `(حزب الله)` a gloss site (the phonetic does not precede the paren — "Party of God" does) and reseeded `(*Hizb Allah*)` to preserve a re-derivation anchor. The romanization is correct Arabic and arguably useful; it just deviates from the stated silent-class contract. Either accept as convention or teach the normalizer that a paren matching a SILENT term's script is removed, not reseeded.

### BK4 · BK-P3 · P2 · VERIFIED (fossil annotation, pre-existing)
- **Chapter:** 4 — line 296 — "the friends of God (أولياء الله)"
- **Why:** Script `أولياء الله` matches NO glossary `arabic_script` (glossary `awliyāʾ` = `أولياء`), so the derive-from-scratch normalizer cannot see, fold, or restyle it — it is fossilized outside the policy loop. It is also the teach-class term awliya's only introduction, and it is script-only: "awliya" appears in Latin nowhere in the book, so a reader without Arabic cannot name the one teach term the policy meant to make nameable. The script itself is correct (appears 16× in the scan) — no accuracy defect. Fix: curate glossary `arabic_script: أولياء الله` (or align the site), letting the next derivation restyle it `(awliya, أولياء الله)`.

### BK5 · BK-N7 · P2 · VERIFIED
- **Chapter:** 8 — line 885 — `the man they called … "Kab al-Ahbar (كعب الأحبار)".`
- **Why:** The reshape moved the script inside the quotation marks and left the period OUTSIDE the closing quote — British placement in an American-spelling edition (locked convention). Prior form was `"Kab al-Ahbar" (كعب الأحبار).` Cosmetic; content identical.

### BK6 · BK-P3 · P2 · VERIFIED (residual of prior definite-article advisory)
- **Chapters:** preface (13), 5 (358–374)
- **Why:** Latin citation forms are now uniformly bare (bab, wasi, duat…), resolving the reader-facing inconsistency; the script side still mixes bare باب against articled الوصي / الدعاة / النقباء / الحجج / الناطق / التأويل per glossary curation. Advisory only.

## Verified vs Inferred summary
6 findings, all VERIFIED — against `book.md` (working tree), git history (HEAD, 26a349b~1, 1b750a3,
`git log -S`), `_system/glossary.yml`, `_system/annotation-policy-report.json`,
`_system/source/ocr/raw-extract.md`, `_system/source/text/refined-english.md`, and the audit/dup
sidecars. 0 INFERRED. Arabic accuracy not silently passed: all 24 surviving term annotations
glyph-checked; audit reports 0 unverified runs; the one newly-found mismatch (BK1) is verified
against the scan, not model recall.

## Ledger emission summary
6 records appended to `_learning/findings.jsonl` (source `book-challenger`, version 1.0, resolution
`flagged`): 0 × P0, 1 × P1, 5 × P2.

**Verdict: SHIP-WITH-CAUTION.** The annotation change under review is APPROVED — every delta is
annotation-only, glossary-exact, and policy-conformant; all four prior editorial advisories are
resolved; sidecars describe the current bytes. The verdict downgrade is carried entirely by BK1, a
newly discovered upstream translation misreading (al-Khidr for "green") in text this change did not
touch — an author-judgment fix via the Composer, then re-challenge of that one sentence.
