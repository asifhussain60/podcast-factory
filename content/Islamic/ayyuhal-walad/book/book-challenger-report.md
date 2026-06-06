# Book Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-06-04 19:30 (book_challenger_version 1.0)
**Scope:** whole-book
**Chapters reviewed:** 9
**Iterations:** 1 (of 5 max)
**Verdict (book-level):** SHIP-READY

## Per-chapter verdicts
| Chapter | Pass 1 | Verdict |
|---|---|---|
| 1. Knowledge That Will Not Save You | pass | SHIP-READY |
| 2. The Striving That Mercy Meets | pass | SHIP-READY |
| 3. The Hours Before Dawn | pass | SHIP-READY |
| 4. Worship Is Obedience, Nothing Less | pass | SHIP-READY |
| 5. Eight Lessons from Thirty-Three Years | pass | SHIP-READY |
| 6. Finding a True Guide | pass | SHIP-READY |
| 7. Sufism, Servitude, Trust, Sincerity | pass | SHIP-READY |
| 8. Four to Avoid, Four to Embrace | pass | SHIP-READY |
| 9. A Prayer for the Road | pass | SHIP-READY |

## Whole-book passes
| Check | Result |
|---|---|
| BK-A1 voice consistency | pass |
| BK-A2 segmentation sanity | pass |
| BK-A3 preface + TOC integrity | pass |
| BK-A4 plain transliteration | pass |
| BK-A5 tradition fit | pass (no enrichment atoms woven; zero Ismaili-doctrine bleed) |

## Headline duty — BK-P3 Arabic-script accuracy

The compose model supplied ALL Arabic script; the source carried Arabic only as Latin transliteration. Every Arabic block was verified against (a) the source transliteration it replaced and (b) known canonical text.

**Qur'anic verses — all VERIFIED against the mushaf consonantal text (clean, no departures):**
53:39 (L51), 99:7-8 (L57), 18:110 (L61), 18:107-108 (L65), 25:70 (L71), 7:56 (L87),
51:17 (L272), 17:79 (L290), 51:18 (L298), 3:17 (L304), 79:40-41 (L436), 16:96 (L446),
49:13 (L456), 43:32 (L466), 35:6 (L476), 36:60-61 (L482), 11:6 (L490), 65:3 (L500),
49:5 (L560), 18:70 (L568), 21:37 (L574), 30:9/35:44 phrase (L580), 53:29 (L615),
7:179 phrase (L250). All consonantally correct; tashkil appropriate.

**Canonical hadith — VERIFIED (well-attested wording):** Pillars of Islam (L77, Bukhari/Muslim
riwaya, Sawm-before-Hajj order matches source translit), most-punished-scholar (L33),
Throne-trembled-for-Sa'd (L244, Bukhari 3803), the two heart-hadith variants correctly
differentiated (L208 short / L661 long, each matching its own source span), hasbi wa
ni'mal-wakil dhikr (L506).

**Faithful-to-source reconstructions (non-Sahih narrative/devotional sayings — Arabic supplied
to match the source transliteration; not part of a canonical corpus to verify against, but
internally coherent and faithful to the translit):** Junayd-dream report is prose (no Arabic),
the forty-questions address (L202), the daily inner-voice saying (L216), Abu Bakr's "cages of
birds" (L232), Hatim's eight-benefit framing verses (all Qur'anic, verified above), Shibli's
"4000 hadith" account (L388), the al-Balkhi reward formula (L394), Sufyan al-Thawri's
wind-of-the-dawn saying (L314), Luqman's rooster counsel (L322), the dove-poem (L328-335),
the jealousy-poem (L608-609), Dhu al-Nun's saying (L590), the ruler-praise hadith (L641),
the closing du'a (L683/688/693). Every one of these matches its source transliteration.

**Structural BK-P2 confirmation:** Every Arabic block has its English translation beneath it
(the dove-poem renders all six Arabic lines then the English block — confirmed present, not a
defect). No Arabic block lacks a source-transliteration basis (no invented quotations).

## Findings (P0 -> P1 -> P2)

### BK1 · BK-P3 · P2 · INFERRED
- **Chapter:** 2 — The Striving That Mercy Meets
- **book.md:** line 149 — "الْكَيِّسُ مَنْ دَانَ نَفْسَهُ ... وَالْأَحْمَقُ مَنِ اتَّبَعَ نَفْسَهُ هَوَاهَا وَتَمَنَّى عَلَى اللَّهِ"
- **Source:** lines 191-192 — "Al Kayyisu Man Dana Nafsahu ... Wal Ahmaqu Man Ittaba'a Nafsahu Hawaha Wa Tamanna 'Alal Allahi"
- **Why it fails:** The strongest Tirmidhi riwaya (no. 2459) reads الْعَاجِزُ ("the incapable") where this text has الْأَحْمَقُ ("the fool"); the divergence is NOT a model invention — it faithfully reproduces the source transliteration's own variant. Advisory only.
- **Worker action:** None required. If a future pass wants strict-canonical alignment, footnote the al-Ajiz/al-Ahmaq variance; do not silently overwrite the source's chosen wording.

### BK2 · BK-P3 · P2 · INFERRED
- **Chapter:** 1, 3, 5, 8, 9 (multiple — class-level note)
- **book.md:** e.g. lines 202, 216, 232, 314, 322, 388, 394, 683-693
- **Source:** corresponding transliteration spans (e.g. 217, 224, 238, 299, 308, 352, 354, 688-698)
- **Why it fails:** These blocks are devotional/narrative sayings and a closing du'a that are NOT part of the Qur'an or the Sahih corpus, so there is no external canonical text to verify the supplied Arabic against. The script faithfully matches the source transliteration and is internally coherent, but "VERIFIED canonical" cannot be asserted. Per spec, an Arabic block that cannot be VERIFIED against a canonical reference is a flag for scholarly review, not a silent pass.
- **Worker action:** None blocking. Optional: a scholarly reviewer confirms the reconstructed vocalisation of the non-canonical sayings and the du'a before print; the Qur'anic and Sahih blocks need no further review (already verified clean).

## Verified vs Inferred summary
- VERIFIED: all 24 Qur'anic citations (mushaf-clean); all canonical hadith blocks; plain-transliteration fold (BK-A4, zero diacritic leaks); no-teaching-lost across all 9 chapters; segmentation coverage; voice fidelity (zero meta-commentary leaks); tradition fit (zero Ismaili-doctrine bleed); every Arabic block carries its English translation.
- INFERRED: BK1 (al-Ahmaq/al-Ajiz variance — advisory), BK2 (non-canonical reconstructed sayings + du'a cannot be externally verified — advisory).

## Ledger emission summary
2 P2 advisory findings emitted (BK1, BK2). No P0, no P1. Verdict floor across chapters: SHIP-READY.
