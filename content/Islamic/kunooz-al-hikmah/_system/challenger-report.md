# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 9:14 PM EST (challenger v2.5)
**Scope:** per-chapter two-foundational-questions
**Content profile:** islamic_scholarly (default — series-config.yaml absent)
**Iterations:** 1 (of 5 max — intelligent break: single auto-fix applied, remaining findings are authoring decisions)
**Verdict:** SHIP-WITH-CAUTION

## Auto-fixes applied

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | B3 / U4 | ch03-two-foundational-questions.txt:7 | Replaced file-self-reference "This episode walks…" with source-anchored "What follows walks…" |

## Findings requiring author resolution

### P0 (blocks ship)
None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION: 11 Arabic transliterations in chapter prose
- **File:** content/Islamic/kunooz-al-hikmah/chapters/ch03-two-foundational-questions.txt
- **Context:** Build script (F20 R-NO-ARABIC-NAMES) detected 11 long transliterations: `Abu Talib`, `al-Abidin`, `al-Awwal`, `al-Farsi`, `al-Hikmah`, `al-Latifah`, `al-Munawwirah`, `al-Musfiyah`, plus reference titles inside italicized work names. F20 doctrine: replace with English audio labels (the framing's Name discipline block already uses "the Adam of the family" for Ali Zayn al-Abidin, "the Father of Imams", etc.). The chapter prose has more residual transliterations than the framing assumes.
- **Suggested fix:** Author judgment — many hits are inside *italicized book titles* (e.g. *Anwar al-Latifah*, *al-Munawwirah lil-Basair*) which the framing explicitly instructs "Never speak Arabic book titles", so audio is already steered. The non-title hits (`Abu Talib`, `al-Farsi`, `Salman al-Farsi`, `Ali Zayn al-Abidin`) could be narrated by descriptive title on first mention. Non-blocking; flagged for author awareness.

#### R-SURAH-ENGLISH-ONLY: two Arabic surah names in chapter prose
- **File:** content/Islamic/kunooz-al-hikmah/chapters/ch03-two-foundational-questions.txt
- **Context:** F29 doctrine: surah references must use the English meaning ("the chapter on Joseph", "the chapter on Abraham"). Detector flagged `ibrahim` and `yusuf` tokens. On manual inspection both appear in legitimate personal-name contexts (Sayyidna Ibrahim ibn Muhammad ibn Fahd; the Joseph verse is already cited as "the chapter on Joseph, verse twenty-four"). False positive likely on the personal-name uses; the actual Quranic citations already use the English form.
- **Suggested fix:** Author judgment — likely no change needed. Verify by audit that every Quranic citation already names the English chapter; personal-name hits are not violations.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP03-two-foundational-questions/99-show-notes.md
- **Context:** F25 doctrine requires the written-layer apparatus table that audio omits — preserved Arabic / transliterations + audio-label crosswalk. Build script flags but does not block. Same finding flagged on EP07 prior pass (book-wide pattern).
- **Suggested fix:** Author adds the apparatus table per F25 template.

### P2 (advisory)

#### CS-SCRIPT-CRASH: check_chapter_set.py crashes on contract length_target type
- **File:** scripts/podcast/check_chapter_set.py:275
- **Context:** `'int' object has no attribute 'lower'` — book-wide chapter-set integrity scan could not run; one or more chapter-contract `length_target` fields are integers instead of strings. Pre-existing across prior SHIP-WITH-CAUTION episodes of this book; same as EP07 report.
- **Suggested fix:** Book-wide cleanup (out of per-chapter scope). Normalize `length_target` to string enum in chapter-contracts.

## Health metrics

| Chapter | Words | Citations | Tier diversity | Honorifics | Phonetic gaps |
|---|---|---|---|---|---|
| ch03-two-foundational-questions | 6531 | 5 Quran (17:85, 12:24, 95:4-5, 36:38, 55:33) + 1 Nahj al-Balagha (Sermon 1) + 1 Corbin (Cyclical Time) + 1 Musnad/Sunan hadith pair | 4 tiers (Quran, Peak of Eloquence, modern scholarship, Sunni/Shia hadith) | All via descriptive titles — name discipline applied (Father of Imams, fourth Imam, Adam of the family, Commander of the Faithful) | 0 — terms covered in framing imperative Pronunciation block (riyat, nasut, lahut, falak al-mustaqim, shahadah, sahri, iftar, barzakh) |

Notes:
- Word count 6531 is over the Default Deep Dive band (1800–2800) and over Longer (2800–4500); chapter is best classified as Extended. Contract declares `length_target: extended`. Defensible for the foundational two-questions architecture but at the very top of E1 hard cap.
- Citation discipline (A1): every Quran ref carries translator (Sahih International 1997, Pickthall 1930) per A3; Corbin cite includes pages 87–95 + edition + year per A1; Nahj al-Balagha Sermon 1 carries translator (Sayyid Ali Reza, AL Digital Islamic Library 1996); Musnad/Sunan hadith carries volume + page + edition per A1.
- Verbatim integrity (A4): Quran translations match the named editions on inspection. The Joseph verse (12:24) is given in full Sahih International rendering at the second occurrence per author intent.
- Doctrinal (Category T): no T1–T3 violations. The Father of Imams is referenced by leadership-title only, NEVER paired with the personal name (the forbidden phrase per `naming-conventions.yml`); the lineage "fourth Imam = Adam of the family = Ali Zayn al-Abidin" matches `imam-lineage-ismaili.yml`. The "two ranks with Hasan / two ranks with Husayn" cosmology is internally consistent with the Ismaili-Tayyibi tradition.
- Framing carries: welcome clause (H1), spine-repeat directive (R-RECURRING-THESIS three times: opening / pivot / close), Name discipline block (J1), imperative Pronunciation block (N2: 8 terms with "Say each term ONCE" anti-doubling guard per CLAUDE.md R-PRONUNCIATION-DOUBLE), no-read-aloud guard (N4), Do-not block with modernize + surprise tells (M1/M2), host dynamic with friction quotes + single-concession discipline (K1), three governing analogies, anti-recap landing (H3 — reflective question on station treatment).
- Host role parity (Q1–Q5): Host A = male scholar, Host B = female curious questioner — matches book-wide pair across EP01–EP07 prior reports. No drift.
- Conversation choreography (R1–R5): host dynamic carries the three-friction + one-concession pattern (R1 separate-prep illusion implied via friction); cadence not explicitly named in Tone section (R3 minor gap, P2 advisory only).
- Category U (scholarly-conversation rubric): no AI cliches (U1), no faux-profundity opener (U2 — the "What if…" hook is V1 curiosity-building, not U2 rhetorical hand-waving), no premature closure (U3 — the close lands on the architecture of the wall+map and explicitly names what later chapters will draw from, no false resolution), no deep-dive self-reference after the auto-fix (U4), no essentialism-external (U5 — discussion is internal to Ismaili tradition).
- Category V (interest & engagement): V1 curiosity hook present ("What if the boldest question…"), V2 challenge-defeat arc (forbidden question → corrected veils-scheme → resolved map), V3 modern-relevance signal (ablution / sahri / iftar as ordinary intake stations in the listener's week), V4 no strawman, V5 rhetorical question cadence present.
- Loop M / N empirical (transcript): only SOURCE-language teaching transcript present at `transcripts/EP03-part-3.transcript.txt` (320 words, Arabic→English raw from turboscribe). No NotebookLM rendered episode exists yet, so Loop M/N empirical checks against modernization/surprise-noise/phonetic-doublings do not apply.
