# Book Challenger Report

**Book:** asaas-al-taveel-vol-01
**Run:** 2026-07-29 (book_challenger_version 1.0)
**Scope:** whole-book
**Chapters reviewed:** 5
**Iterations:** 1 (of 5 max — stopped early: P0 findings are content-accuracy defects requiring author/scholarly resolution, not re-compose noise; further iterations would not change the underlying Arabic-fidelity gap without a targeted fix)
**Content profile:** islamic_scholarly (from `_system/series-config.yaml`)
**Route classification:** `series-config.yaml` has no `deliverable_mode: translation_edition` key, so per the routing rule this book is technically on the **augmented-companion route**, not the translation-edition route the invocation named. Practically this changes nothing about the findings below (the full augmented-companion catalog applies), and the absence of `book/source-crosswalk.json` is exactly what the augmented-companion route predicts (optional/absent) — not a defect. Flagged as BK-META-1 below because the config's silence on both `deliverable_mode` and `narrative_frame` leaves this book's frame governed by an ad hoc `book-toc.json` field instead of the canonical mechanism.
**Verdict (book-level):** BLOCKED

## Per-chapter verdicts

| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| 1. What Ismaili Interpretation Is | pass (content) / fail (attribution) | fail (BK-N1/BK-A2) | SHIP-WITH-CAUTION |
| 2. The Call to Inner Meaning | fail (BK-P3 x3, BK-P2 x1) | pass | BLOCKED |
| 3. The Four Limits of the Testimony | pass (sampled only) | pass | SHIP-WITH-CAUTION (unverified Arabic volume) |
| 4. Adam, the Tree, and the Iblis Pact | pass (sampled only) | pass | SHIP-WITH-CAUTION (unverified Arabic volume) |
| 5. Two Parties and the Line to Noah | pass (sampled only) | pass — but see BK-A1 citation-apparatus note | SHIP-WITH-CAUTION (unverified Arabic volume) |

## Whole-book passes

| Check | Result |
|---|---|
| BK-A1 voice consistency | fail (P2) — chapter 5 alone adds `(Qur'an S:V)` citations; 1–4 never do |
| BK-A2 segmentation sanity | fail (P1) — chapter 1 folds two distinct authorial voices under one heading with no up-front signal |
| BK-A3 preface + TOC integrity | pass — headings monotonic 1–5, match `book-toc.json`; `preface.include:false` by design, chapter 1 does the orienting work instead |
| BK-A4 plain transliteration | pass — zero diacritic-leak characters found in a full-file scan |
| BK-A5 tradition fit | pass by absence — no `enable_knowledge_augmenter` in `meta.yml`, no enrichment markers found in body |
| BK-N3 frame consistency | pass — chapters 2–5 consistently render al-Nu'man's own first-person-plural authorial voice; only chapter 1 (Tamir's editorial voice) differs, and that difference is source-grounded, not a compose defect |
| declared narrative_frame | not declared in `series-config.yaml`; `book-toc.json` carries an ad hoc `"voice": "author first-person"` instead of the canonical `_rules.NARRATIVE_FRAMES` enum |
| BK-P7 duplication | pass — no `_system/book-duplication-check.json` exists (older compose path); manual paragraph-repeat scan of the whole file found only two duplicate-looking pairs, both legitimate re-citations of the same Qur'an verse in different chapters, not narrative duplication |

## Findings

### BK1 · BK-P3 · P0 · VERIFIED
- **Chapter:** 2 — The Call to Inner Meaning
- **book.md:** line 167 — `بَلْ أَكْثَرُهُمْ فَاسِقُونَ فَهُمْ لَا يَسْمَعُونَ` / "But most of them are insolently disobedient, and they do not hear."
- **Source:** OCR `_system/source/ocr/raw-extract.md` lines 484–485 — `الا النينَ آمَنُوا وَعَمْلُوا الْمَّاِحَاتِ وَقَيْلٌ مَا هُمْ)) وقال : ((فَأَعْرَضَ أَكْتَرُهُمْ نَهُمْ لا يَسْمَعُونْ`
- **Canonical check:** the mirror (`content/knowledge-base/mirror.db`, `fts_quran`) resolves the actual ayah as Q41:4 — `بَشِيرًۭا وَنَذِيرًۭا فَأَعْرَضَ أَكْثَرُهُمْ فَهُمْ لَا يَسْمَعُونَ`. The source (both OCR and canonical mushaf) reads `فَأَعْرَضَ أَكْثَرُهُمْ` ("most of them turned away"). book.md instead prints `بَلْ أَكْثَرُهُمْ فَاسِقُونَ` ("most of them are defiantly disobedient") — a different word, not a spelling variant. This is a genuine scripture corruption, not an Uthmani/imla'i orthography difference.
- **Why it fails:** the model supplied Arabic that does not match either the source page or the canonical ayah it is drawn from.
- **Worker action:** replace with the OCR/canonical wording `فَأَعْرَضَ أَكْثَرُهُمْ فَهُمْ لَا يَسْمَعُونَ` and re-verify the English gloss still tracks ("but most of them turned away, and they do not hear").

### BK2 · BK-P3 · P0 · VERIFIED
- **Chapter:** 2 — The Call to Inner Meaning
- **book.md:** line 203 — `إِنْ هَٰذَا إِلَّا أَسَاطِيرُ الْأَوَّلِينَ اكْتَتَبَهَا فَهِيَ تُمْلَىٰ عَلَيْهِ بُكْرَةً وَأَصِيلًا` / "These are nothing but fables of the ancients which he has written down; they are dictated to him morning and evening."
- **Source:** OCR lines 502–503 — `وَقَالَ الذينَ كَفَرُوا إِنْ هَذَا الَّ إِفْكٌ أَفَتَرَاهُ وَأَعَانَهُ عَلَيْهِ قَوْمٌ آخَرَوُنَ فَقَّدْ جَاؤُوا ظُلْمَا وَزُوراً، وَقَالُوا أَسَاطِيرَ الأَولِينْ أَكْتَبَهَا فِيَ تُلَى عَليهِ بُكْرَةً وَأَصْلًاً` — two consecutive ayat, Q25:4 ("وَقَالَ الَّذِينَ كَفَرُوا إِنْ هَٰذَا إِلَّا إِفْكٌ افْتَرَاهُ...") and Q25:5 ("وَقَالُوا أَسَاطِيرُ الْأَوَّلِينَ اكْتَتَبَهَا...").
- **Why it fails:** book.md's Arabic splices the opening clause of Q25:4 (`إِنْ هَٰذَا إِلَّا`) directly onto the body of Q25:5 (`أَسَاطِيرُ الْأَوَّلِينَ اكْتَتَبَهَا...`), producing a string that is not the wording of either ayah. Q25:4 itself — the ayah the source actually quotes first — is dropped entirely, uncited.
- **Worker action:** quote Q25:4 and Q25:5 as two separate blocks (as the OCR source does), or, if compressing to match the already-condensed English gloss, use the verbatim tail of Q25:5 alone (`وَقَالُوا أَسَاطِيرُ الْأَوَّلِينَ اكْتَتَبَهَا فَهِيَ تُمْلَىٰ عَلَيْهِ بُكْرَةً وَأَصِيلًا`) rather than a hybrid. Companion BK-P1 note: Q25:4 is present in the source and absent from book.md — restore it or fold its sense into the English explicitly.

### BK3 · BK-P3 · P0 · VERIFIED
- **Chapter:** 2 — The Call to Inner Meaning
- **book.md:** line 365 — `الْإِيمَانُ قَوْلٌ بِاللِّسَانِ وَاعْتِقَادٌ بِالْجَنَانِ وَعَمَلٌ بِالْأَرْكَانِ` / "Faith is a saying with the tongue, a conviction in the heart, and an action with the limbs." (attributed to al-Sadiq)
- **Source:** OCR line 731 — `((ان الايمان قول باللسان، وتصديق بالجنان، وعمل بالاركان.))`
- **Why it fails:** the source's own quotation says `تَصْدِيقٌ بِالْجَنَانِ` ("affirmation/attestation in the heart"). book.md substitutes `اعْتِقَادٌ بِالْجَنَانِ` ("a creed/conviction in the heart") — a different word for a hadith the book is directly quoting and attributing by name to al-Sadiq.
- **Worker action:** restore `تَصْدِيقٌ بِالْجَنَانِ` and adjust the English gloss to "affirmation in the heart" if needed for register.

### BK4 · BK-P2 · P1 · VERIFIED
- **Chapter:** 4 — Adam, the Tree, and the Iblis Pact
- **book.md:** line 737 — "Al-Sadiq (peace be upon him) said: 'One day **I argued with** my father, and he set out to walk around the House…'"
- **Source:** OCR line 1233 — `قال الصادق عليه السلام : ((حججت مع والدي يوماً فطاف بالبيت` — "I **made Hajj with** my father one day, and he circled the House…" (root ح-ج-ج, hajj/circumambulation — not ح-ا-ج-ج, dispute/argue).
- **Why it fails:** this mistranslation already exists in `_system/source/text/refined-english.md` line 750 (i.e., it predates book compose, originating in the phase-0b refine stage), but it ships unchanged in the reader-facing PDF and changes the opening premise of a hadith the book attributes by name to Ja'far al-Sadiq.
- **Worker action:** correct to "I performed Hajj with my father" (or "I went on pilgrimage with my father") in both `refined-english.md` and `book.md`; this is an upstream-refine fix that must also be re-applied through book compose since chapter 4 carries no Composer edit lock on this passage.

### BK5 · BK-N1 / BK-A2 · P1 · VERIFIED
- **Chapter:** 1 — What Ismaili Interpretation Is
- **book.md:** lines 5–149 (all of chapter 1) — continuous first person ("I held this book back from the press…", "It is worth noting that al-Nu'man… was born in Morocco… it is known that he died in Cairo in the year 363 AH…")
- **Source:** `_system/source/text/refined-english.md` lines 1–213 (Arif Tamir's dated editorial introduction, signed "Aref Tamer / Beirut, Lebanon / 1960" at lines 211–213) versus line 216 ("**Author's Introduction**") onward, which is al-Nu'man ibn Hayyun's own 10th-century text.
- **Why it fails:** the source itself draws an explicit, unambiguous line between two different historical speakers — a 1960s Beirut editor discussing manuscripts, orientalists (Ivanow), and al-Nu'man's death date in the THIRD person, versus the 10th-century author's own first-person "we." book.md's chapter 1 renders both under one undifferentiated "I," with no heading, byline, or signal that the speaker is Arif Tamir rather than al-Nu'man, until the very last sentence of the chapter ("What follows now is the author's own introduction…"). `book-toc.json` declares the whole book's `"voice": "author first-person"`, which is only true of chapters 2–5; chapter 1's "I" is a different person entirely.
- **Worker action:** give chapter 1 its own explicit attribution at the top — e.g. a sub-heading or opening line identifying it as "Arif Tamir's Introduction (Beirut, 1960)" — rather than relying on a closing-sentence reveal. This is a presentation/attribution fix, not a re-compose of the prose itself.

### BK6 · BK-A1 · P2 · INFERRED
- **Chapter:** 5 — Two Parties and the Line to Noah
- **book.md:** lines 925, 931, 939, 947, 955, 963, 969, 975, 989, 999, 1005, 1011 — parenthetical `(Qur'an S:V)` citations
- **Why it flags:** chapters 1–4 never cite chapter:verse numbers after a Qur'an quotation; chapter 5 does so on almost every quote. Spot-checked eight of these citations (58:14–19, 58:22, 4:110, 7:20–21, 2:37, 4:64, 5:68, 5:51) against the canonical mushaf — all accurate — so this is not a fabrication risk, only an inconsistent apparatus across the book.
- **Worker action:** either extend the citation apparatus to chapters 1–4 for consistency, or drop it from chapter 5 to match the rest of the book's voice.

### BK7 · BK-META-1 · P2 · VERIFIED
- **File:** `_system/series-config.yaml`
- **Why it flags:** no `narrative_frame` key is declared. The `islamic_scholarly` profile default (`transmitted_report`, third person) would be WRONG for this book's actual source (al-Nu'man's authored portions are genuinely `first_person_author`), so the compose evidently relied on `book-toc.json`'s ad hoc `"voice"` field instead of the canonical `_rules.NARRATIVE_FRAMES` mechanism. The output happens to be substantively correct for chapters 2–5, but the governance is undocumented and would silently regress to `transmitted_report` if book-toc.json's field were ever dropped or a future recompose ignored it.
- **Worker action:** add `narrative_frame: first_person_author` to `series-config.yaml` explicitly.

### BK8 · Process gap · P1 · VERIFIED
- **Directory:** `_system/` (whole book)
- **Why it flags:** none of `_system/book-arabic-audit.json`, `_system/book-vowelling.json`, `_system/book-duplication-check.json`, or `book/book-compose-log.md` exist for this book. These are the deterministic seeding artifacts Pass 1/Pass 3 are supposed to read first. Their absence meant this review had to hand-verify a sample of the 143 Arabic blocks in `book.md` rather than triage a machine-generated candidate list — and the sample alone surfaced three confirmed P0 corruptions (BK1–BK3). The remaining ~130 Arabic blocks were NOT individually hand-verified against OCR/mushaf in this pass.
- **Worker action:** run the current `vowel_book.py` / Arabic-audit pipeline against this book explicitly so the full Arabic inventory gets machine-checked, then re-run this challenger against the resulting `_system/book-arabic-audit.json`.

## Verified vs Inferred summary

- **VERIFIED (direct evidence in files):** BK1, BK2, BK3, BK4, BK5, BK7, BK8 — 7 findings, each cross-checked against `_system/source/ocr/raw-extract.md`, `_system/source/text/refined-english.md`, and/or `content/knowledge-base/mirror.db`.
- **INFERRED (heuristic judgment):** BK6 — citation-apparatus inconsistency is a judgment call, not a factual error (all sampled citations are accurate).

## Coverage caveat

Only a sample of the 143 Arabic blocks in `book.md` was hand-verified (concentrated in chapter 2, with spot checks in chapters 3–5). The sample's ~3-in-10 confirmed-corruption rate on close inspection means **BK-P3 is not cleared for the book as a whole** — per the mission constant, an unverified Arabic block is a finding, not a pass. Full clearance requires either (a) a complete manual pass over all 143 blocks, or (b) running the deterministic Arabic-audit tooling (BK8) and reviewing its output.

## Ledger emission summary

8 findings emitted to `_learning/findings.jsonl` with `source: book-challenger`, `book: asaas-al-taveel-vol-01`, `challenger_version: 1.0`, `resolution: flagged`. Severities: 4 × P0 (BK1–BK3 are the same check_id BK-P3, BK4 is BK-P2), 3 × P1 (BK5, BK-A2 companion, BK8), 2 × P2 (BK6, BK7).
