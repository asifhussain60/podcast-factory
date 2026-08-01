# Book Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-07-31 21:05 EST (book_challenger_version 1.0)
**Scope:** whole-book
**Chapters reviewed:** 9 + preface
**Iterations:** 1 (of 5 max)
**Content profile:** `islamic_scholarly` (full probe catalog, no gating)
**Route:** augmented-companion (no `deliverable_mode` in series-config)
**Resolved knobs:** `{augmentation: source_only, voice: faithful, visuals: manual_only, narrative_frame: first_person_author, narrator_subject: ''}` — confirmed via `_pipeline_flags.book_knobs`
**Verdict (book-level):** BLOCKED

---

## Headline

The edition is a **better translation of Ayyuha al-Walad than the previous one, composed against the
wrong witness**. `_book_pipeline_v2.compose_book_v2` reuses `author_translation_edition_compose` as
the faithful base for every `islamic_scholarly` book, and that base hands the model
`_system/source/ocr/raw-extract.md` — which for this book is not a page-aligned transcription aid but
**the complete Arabic original of the treatise**. Given the original beside a translation-of-a-Urdu-
translation, the model translated from the original. Chapters 1, 3, 5, 7 and 8 follow the Arabic
wherever the two witnesses disagree.

That produced a leaner, more accurate book — and it silently discarded four pieces of substantive
content that exist only in the declared English source, none of which any deterministic gate can see,
because the gates measure the book against a length floor and a section list, not against the source
line by line.

It also produced the defect this agent exists to catch. **Four Qur'anic verses are printed with
corrupted consonantal text, copied character-for-character out of the OCR.** The Arabic audit reports
them as `resolution: ocr` — verified — because they were corrupted badly enough that
`_mushaf.is_quranic` failed to recognise them as scripture at all, so the canonical-mushaf-first ladder
never ran on them. The audit's clean sheet on those four runs is an artifact of the corruption, not
evidence against it.

---

## Per-chapter verdicts

| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface. A Letter Across the Centuries | fail (BK-P4) | pass | SHIP-WITH-CAUTION |
| 1. Knowledge That Will Not Save You | fail (BK-P2, BK-P3, BK-P8) | pass | BLOCKED |
| 2. The Striving That Mercy Meets | fail (BK-P7, BK-P5, BK-P8) | pass | BLOCKED |
| 3. The Hours Before Dawn | fail (BK-P1, BK-P8) | fail (BK-N4) | BLOCKED |
| 4. Worship Is Obedience, Nothing Less | pass | pass | SHIP-READY |
| 5. Eight Lessons from Thirty-Three Years | fail (BK-P1, BK-P2) | pass | BLOCKED |
| 6. Finding a True Guide | pass | fail (BK-N7) | SHIP-WITH-CAUTION |
| 7. Sufism, Servitude, Trust, Sincerity | fail (BK-P3, BK-P8) | pass | BLOCKED |
| 8. Four to Avoid, Four to Embrace | fail (BK-P1, BK-P3, BK-P8) | pass | BLOCKED |
| 9. A Prayer for the Road | fail (BK-P2, BK-P3) | pass | BLOCKED |

## Whole-book passes

| Check | Result |
|---|---|
| BK-A1 voice consistency | **fail** — honorific register breaks at chapter 6 |
| BK-A2 segmentation sanity | pass |
| BK-A3 preface + TOC integrity | pass (one P2: editorial note after the book's terminal sentence) |
| BK-A4 plain transliteration | pass — zero scholarly diacritics in Latin text |
| BK-A5 tradition fit (`enable_knowledge_augmenter: true`) | pass **by outcome, not by construction** — see note |
| BK-N1 narrative person | pass |
| BK-N2 speech attribution | pass |
| BK-N3 frame consistency | pass — one narrator across all nine chapters |
| BK-N4 Arabic script retention | **fail** — chapter 3 |
| BK-N5 vowelling integrity | pass — all 20 refusals are correct marks-only refusals |
| BK-N6 structural enumeration | pass — the four conditions, the eight benefits and the eight admonitions all survive as enumerated lists |
| BK-N7 register / elegant variation | **fail** — honorifics, `mujahadah`/`Mujahada` |
| declared narrative_frame | `first_person_author` — **correct, see adjudication** |
| resolved book_voice | `faithful` |
| BK-P8 articulation conformance | **fail** — REQ-BA-010, REQ-BA-020, REQ-BA-100 |
| BK-P7 duplication (seeded from `book-duplication-check.json`: empty) | **fail** — chapter 2, invisible to the run-length rule |

---

## Adjudications requested

### 1. The 14 UNVERIFIED Arabic runs — 13 are noise, 1 is a real defect

| Run | Chapter | Call |
|---|---|---|
| `إِحْيَاءُ عُلُومِ الدِّيْن` | preface | **Correct.** Standard title. (Nit: `الدِّيْن` carries a redundant sukun.) |
| `كِيمِيَاءُ السَّعَادَةِ` | preface | **Correct.** |
| `جَوَاهِرُ الْقُرْآنِ` | preface | **Correct.** |
| `أَرْبَعُون` | preface | **Correct** as a citation form; the source transliterates the oblique `Arba'een` (`أربعين`). Cosmetic. |
| `مِنْهَاجُ الْعَابِدِينَ إِلَى جَنَّةِ رَبِّ الْعَالَمِينَ` | preface | **Correct.** |
| `إِلَّا مَنْ تَابَ وَ آمَنَ وَعَمِلَ صَالِحًا` | ch1 | **Correct — and the book fixed the OCR.** The scan reads `الَّ مَنْ تَابَ` (garbled `إلا`); the book restored the canonical Q19:60 opening. Unverified only because the matcher compared against the garbled scan. |
| `يَا أَحْمَقُ أَنْتَ مِنْ هُنَاكَ تَجِيءُ` | ch3 | **Correct — book fixed the OCR** (`تحئ` → `تَجِيءُ`). |
| `إِذَا كَانَ أَوَّلُ اللَّيْلِ نَادَىٰ مُنَادٍ مِنْ تَحْتِ الْعَرْشِ` | ch3 | **Correct.** Matches OCR p.11 verbatim; unverified because the run is long and the matcher windowed it. |
| `يَا بُنَيَّ، لَا يَكُونَنَّ الدِّيكُ أَكْيَسَ مِنْكَ` | ch3 | **Correct — book fixed the OCR** (`يكونّ` → `يَكُونَنَّ`). |
| `اَلتَّوْفِيق` | ch5 | **Correct** glossary citation form. |
| `اَلْبَيْعَة` | ch6 | **Correct.** |
| `اَلصِّحَاحُ اَلسِّتَّة` | ch9 | **Correct.** |
| `شَيْخُ الْكَامِل` | ch6 | **DEFECT.** Ill-formed. A definite adjective cannot follow an indefinite head in a genitive construct; the Arabic is either `الشَّيْخُ الْكَامِل` or `شَيْخٌ كَامِل`. |
| `مُرْشِد اَلْكَامِل` | ch6 | **DEFECT.** Same error. |

Net: the unverified list is **not where the Arabic problems are**. Twelve of the fourteen are correct
(including three places where the book silently repaired OCR damage, which is exactly right), and the
two real defects are manufactured glossary constructs, not scripture. **The scripture defects are all
in runs the audit marked `ocr` and therefore counted as verified.** That inversion is the most
important thing in this report.

### 2. Length — your framing is half right, and the wrong half matters

13,706 words against a 14,906-word source is **not** "the source rendered faithfully minus front
matter", and the 17,426-word June edition was not simply inflated prose. The real accounting:

| Chapter | Source-span words | Book words | Ratio |
|---|---|---|---|
| 1 | 1,568 | 1,195 | **0.76** |
| 2 | 799 | 763 | 0.95 |
| 3 | 1,614 | 1,098 | **0.68** |
| 4 | 1,509 | 1,495 | 0.99 |
| 5 | 2,068 | 1,795 | 0.87 |
| 6 | 1,256 | 1,330 | 1.06 |
| 7 | 957 | 801 | 0.84 |
| 8 | 3,545 | 2,463 | **0.69** |
| 9 | 598 | 705 | 1.18 |

The compression is concentrated in exactly the chapters where the book abandoned the English source for
the Arabic original. **Most of the missing 1,200 words are the Urdu translator's amplification**, and
dropping it is a genuine improvement — the science list in chapter 3 is the clearest case: the English
source's "ethics, linguistics, the science of warfare" is a corruption of the original's
`الخلاف / العروض / التصريف`, and the book restores juristic disagreement, prosody and morphology. I am
**not** reporting that as a loss, because reporting it would be recommending a regression.

But **not all of it is amplification.** Four substantive items exist only in the English source and are
now gone from the book entirely (findings BK09–BK12). Two are Qur'anic verses. One is a named
Companion. So: the new figure is defensible, the old one was inflated, **and** the compression
swallowed real content on the way down. Both things are true, and only the second one is actionable.

### 3. The narrative frame — the declaration is correct

`first_person_author` with `narrator_subject` deliberately unset is the right call, and I would not
change it. The Arabic opens `إعلم، أيها الولد والمحبّ العزيز ... فأي حاجة لك في نصيحتي` — first person,
authorial, addressed to a named "you", from the first line of the treatise to the last. All nine
chapters are that letter. The profile default (`transmitted_report`) would have instructed the model to
convert Ghazali's own letter into a report about Ghazali.

The two-layer preface is handled **honestly**, and this is the part I looked hardest at:

- The compiler's third-person preamble (`إعلم انّ واحدا من الطّلبة المتقدّمين لازم خدمة الشيخ...`) is
  rendered in the third person, as the source has it — book lines 17–27.
- It is separated from the modern editorial framing by an explicit `### The book's own opening`
  heading, inside the `<!-- edition-intro -->` fence.
- The fluency pass recorded the decision out of band rather than writing it into the prose
  (`editorial_queries`: *"forcing first person would misattribute the narration, so the source's
  grammatical person was preserved"*) — which is REQ-BA-160 behaving exactly as written.
- Leaving `narrator_subject` unset keeps `_narrative`'s self-report check off that preamble, which is
  the only reason it passes; had it been set, the preface would fail permanently for being what the
  source makes it.

BK-N1 and BK-N3 pass. Chapter 5 is almost entirely Hatim's quoted first-person speech, which is correct
under every frame and is not a finding.

### 4. The compose-run facts you asked me to check rather than assume

- **Chapter 2 was reverted and the revert did not fix the defect.** The gate fired on
  `fluency-03: narrative-announcement opening: 'My dear son, hold firmly to this... Let me tell you of a man'`.
  The base it reverted to reads *"My dear son, be firmly convinced of this: without effort you will not
  find its reward. / Let me tell you of a man among the Children of Israel..."* — the same construction,
  in the same position. The gate reverted a chapter to a version carrying the thing it objected to.
  Reported as BK14 (BK-P5). Chapter 2 therefore also received no articulation pass, and it is one of the
  two chapters where BK-P8 finds the most surviving calque.
- **Chapter 3's "copied, not re-voiced" warning is real and load-bearing.** It is the chapter with the
  worst length ratio (0.68), it carries the single most opaque sentence in the book (BK17), and it
  carries the one BK-N4 failure. Treat that warning as a finding, not a note.
- **The 4 accepted / 1 dropped editorial blocks are in contract.** `_book_augment` runs *only* when
  `book_augmentation == source_only`; the knob enables KB enrichment, it does not forbid it. Three of the
  four blocks are etymology and one is entirely book-internal. One raises a judgment call — BK25, P2.
- **The 62 glossary refusals and 20 book refusals are correct.** Every one I sampled is a genuine
  letters-changed refusal (`إشهدوا` for `اشهدوا`, `أن` for `ان`, Persian yeh normalisation). The gate
  did its job. Not defects — but see BK13, where the gate correctly refusing to fix OCR damage means the
  damage prints.
- **Paragraph alignment / mirroring skipping is correct.** This edition has no numbered paragraphs.

---

## Findings

### BK01 · BK-P3 · P0 · VERIFIED — Qur'an 49:5 printed with a corrupted word
- **Chapter:** 7 — Sufism, Servitude, Trust, Sincerity
- **book.md:** line 511 — `(وَلَوْ اَلُهُمْ صَبَرُوا حَتَّى تَخْرُجَ اِلَيْهِمْ لَكَانَ خَيْرًا لَهُمْ * الحجرات: ٥)`
- **Source:** `_system/source/ocr/raw-extract.md` line 452 (same corruption); English source line 538
- **Canonical (`content/knowledge-base/mirror.db`, fts_quran 49:5):** `وَلَوْ أَنَّهُمْ صَبَرُوا۟ حَتَّىٰ تَخْرُجَ إِلَيْهِمْ لَكَانَ خَيْرًۭا لَّهُمْ`
- **Why it fails:** `أَنَّهُمْ` is printed as `اَلُهُمْ` — a nun/shadda replaced by a lam. This is not a
  vowelling difference; the consonantal skeleton of a Qur'anic verse is wrong. `_mushaf.is_quranic()`
  returns `False` on the printed form and `True` on the canonical form, which is why the resolution
  ladder never reached the mushaf and the audit logged it as `ocr`-verified.
- **Worker action:** re-resolve every `resolution: ocr` run that is scripture against `fts_quran` and
  set it from the mushaf. Do not hand-patch.

### BK02 · BK-P3 · P0 · VERIFIED — Qur'an 21:37 printed with a changed word, and its English disagrees with it
- **Chapter:** 7 — Sufism, Servitude, Trust, Sincerity
- **book.md:** lines 523–525 — `(سَأُرِيكُّمْ آيَاتٍ فَلاَ تَسْتَعْجِلوُنِ * الْأَنْبِيَاءُ: ٣٧)` / "I will show you My signs, so do not seek to hasten them."
- **Source:** OCR line 454–455 (same corruption); English source line 548
- **Canonical (fts_quran 21:37):** `سَأُو۟رِيكُمْ آيَتِى فَلَا تَسْتَعْجِلُونِ`
- **Why it fails:** two defects. `آيَاتِي` ("My signs") is printed `آيَاتٍ` — the possessive `ya` is gone
  and replaced by tanwin, so the printed Arabic says "signs", while the English directly beneath it says
  "**My** signs". A shadda has also been invented on the kaf (`سَأُرِيكُّمْ`), and `تَسْتَعْجِلوُنِ`
  carries its vowel before its waw. The Arabic block and its facing translation are no longer the same
  sentence.
- **Worker action:** as BK01.

### BK03 · BK-P3 · P0 · VERIFIED — Qur'an 53:29 printed with a dropped letter
- **Chapter:** 8 — Four to Avoid, Four to Embrace
- **book.md:** line 557 — `فَاَعْرِضْ عَنْ مَنْ تَوَلَّى عَنْ ذِكْرِنَا وَلَمْ يُرِدْ اِلاَّ الْحَيَوَةَ الدُّنَا (النَّجْم: ٢٩)`
- **Source:** OCR line 500 (same corruption); English source line 591
- **Canonical (fts_quran 53:29):** `فَأَعْرِضْ عَن مَّن تَوَلَّىٰ عَن ذِكْرِنَا وَلَمْ يُرِدْ إِلَّا ٱلْحَيَوٰةَ ٱلدُّنْيَا`
- **Why it fails:** `ٱلدُّنْيَا` is printed `الدُّنَا` — the `ya` is dropped from the last word of the
  verse. `is_quranic()` returns `True` here, so the run *was* recognised as scripture and still was not
  set from the mushaf: the corruption survived a resolver that had the correct text available.
- **Worker action:** as BK01. This one also proves the resolver gap is not only a recognition failure.

### BK04 · BK-P3 · P0 · VERIFIED — Qur'an 35:44 printed with broken orthography
- **Chapter:** 7 — Sufism, Servitude, Trust, Sincerity
- **book.md:** line 529 — `(آَوَ لَمْ يَسِيرُوا فِيِ اْلاَرْضِ فَيَنْظُرُوا * فاطر: ٤٤)`
- **Source:** OCR line 456 (same); English source line 554
- **Canonical (fts_quran 35:44):** `أَوَلَمْ يَسِيرُوا۟ فِى ٱلْأَرْضِ فَيَنظُرُوا۟`
- **Why it fails:** the skeleton survives, but the page prints `آَوَ` (alif-madda **and** a fatha) for
  `أَوَ`, `فِيِ` (a kasra on a long-vowel ya), and `اْلاَرْضِ` (a sukun on a word-initial alif). None of
  these are valid Arabic; all three are scanner artifacts printed as scripture. `is_quranic()` returns
  `True`, so the mushaf text was reachable and was not used.
- **Worker action:** as BK01.

### BK05 · BK-P2 · P0 · VERIFIED — four quotations in chapter 1 carry no Arabic script
- **Chapter:** 1 — Knowledge That Will Not Save You
- **book.md:** line 77 "So whoever does an atom's weight of good will see it…"; line 95 "Islam is built
  upon five things: to testify that there is none worthy of worship but Allah…"; line 99 "Faith is
  affirmation with the tongue, assent with the heart, and action with the limbs."; line 103 "Indeed, the
  mercy of Allah is near to those who do good."
- **Source:** lines 115, 133, 136, 141 — each carries an italicized transliteration
  (`*"Faman Ya'mal Mithqala Zarratin…"*`, `*"Buniyal Islamu 'Ala Khams…"*`,
  `*"Al Imanu Iqraarun Bil Lisani…"*`, `*"Inna Rahmata Allahi Qaribun Minal Muhsinin."*`)
- **Why it fails:** every other quotation in this chapter is set as Arabic script above its English.
  These four are English-only. Two of the four are in the Arabic ground truth verbatim (OCR lines
  116–118 and 119) and two are canonical Qur'an available in `fts_quran` (99:7–8 and 7:56) — so the
  Arabic was in hand for all four and was dropped.
- **Worker action:** restore all four Arabic blocks; take 99:7–8 and 7:56 from the mushaf and the two
  hadith from OCR p.6.

### BK06 · BK-P2 · P0 · VERIFIED — `إنا لله وإنا إليه راجعون` reduced to English
- **Chapter:** 5 — Eight Lessons from Thirty-Three Years
- **book.md:** line 372 — `At this Shaykh Shafeeq said: "To Allah we belong, and to Him we shall return."`
- **Source:** lines 374–376 — `"Inna Lillahi Wa Inna Ilaeyhe Raji'oon."` / *"a supplication from the Quran recited at times of loss and grief"*
- **Why it fails:** the most recognisable formula in the book is the one place it is rendered English-only.
  The text is Qur'an 2:156, present in `fts_quran`. The source's gloss explaining when it is said is also
  dropped, so a reader who does not already know the formula cannot tell why the shaykh says it.
- **Worker action:** set `إِنَّا لِلَّهِ وَإِنَّا إِلَيْهِ رَاجِعُونَ` from the mushaf above the English and restore the gloss.

### BK07 · BK-N4 · P0 · VERIFIED — an Arabic run truncated below its own translation
- **Chapter:** 3 — The Hours Before Dawn
- **book.md:** lines 206–208 —
  `كُلُّ يَوْمٍ يَنْظُرُ فِي قَلْبِكَ يَقُولُ: مَا تَصْنَعُ لِغَيْرِي وَأَنْتَ مَحْفُوفٌ بِخَيْرِي`
  / "What are you doing for the sake of another, when My bounty surrounds you on every side? **Yet you
  are deaf, and you do not hear.**"
- **Source:** OCR lines 170–171 — `... وأنت محفوف بخيري. أمّا أنت فأصمّ لا تسمع!`
- **Why it fails:** the closing clause `أمّا أنت فأصمّ لا تسمع` is in the Arabic ground truth and is
  translated in the English printed beneath, but is missing from the Arabic block itself. A reader
  following the script against the translation finds a sentence in the English with no Arabic behind it.
- **Worker action:** extend the Arabic run to the end of the sentence the translation covers.

### BK08 · BK-P2 · P0 · VERIFIED — the closing supplication prints one prayer in Arabic and a different one in English
- **Chapter:** 9 — A Prayer for the Road
- **book.md:** lines 645–655
- **Source:** English source lines 690–698; OCR lines 642–665
- **Why it fails:** the Arabic block is the original du'a; the English beneath it is the Urdu-derived
  translation from the English source. They diverge substantially and are printed as facing texts.
  The English names divine attributes **that are not in the Arabic**: *Ya Haleem*, *Ya Azeem*,
  *Ya Qahhar*, *Ya Rahman*, *Ya Raheem*. The Arabic contains petitions and attributes **that are not in
  the English**: `و اجعل التّقوى زادنا، و في دينك إجتهادنا` ("make God-consciousness our provision and
  striving in Your religion our effort"), `يا خالق اللّيل و النّهار` ("O Creator of night and day"),
  `خلّصنا من همّ الدّنيا و عذاب القبر و النّار` ("deliver us from the anxiety of this world and the
  punishment of the grave and the Fire"), `و يا أول الأوّلين، و يا آخر الآخرين`,
  `و يا ذا القوّة المتين`, `ويا راحم المساكين`, and the closing
  `لا إله إلا أنت سبحانك إنّي كنت من الظّالمين`. Mid-block the English says "Grant us salvation at our
  death; set our deeds right" where the Arabic says `اختم بالسعادة آجالنا. و حقّق بالزّيادة آمالنا`
  ("seal our appointed terms with felicity; fulfil our hopes with increase"). This is the book's
  benediction and the passage a reader is most likely to actually recite.
- **Worker action:** translate the printed Arabic du'a clause by clause and replace the facing English.
  Do not adjust the Arabic to match the English.

### BK09 · BK-P1 · P0 · VERIFIED — Qur'an 51:17 and its exposition dropped
- **Chapter:** 3 — The Hours Before Dawn
- **book.md:** line 244 goes straight from the pre-dawn call to "Once a group of Companions were praising Abdullah ibn Umar…"
- **Source:** lines 262–265 — *"Were knowledge alone enough, this proclamation… would be rendered
  meaningless. In truth, this divine call at dawn is directed toward those of whom it is said:
  `Kanu Qaleelum Minal Laili Ma Yahja'oon.` 'There are only a few servants of Allah who sleep but little
  in the last part of the night — that blessed hour of nearness to Allah.'"*
- **Why it fails:** a Qur'anic citation (51:17, `كَانُوا۟ قَلِيلًۭا مِّنَ ٱلَّيْلِ مَا يَهْجَعُونَ`) plus the
  sentence that tells the reader *whom* the dawn call is addressed to. Without it the chapter's central
  hinge — the call is for a specific few — is asserted rather than grounded.
- **Ambiguity, stated plainly:** this verse is **not** in the Arabic original. It is the Urdu
  translator's addition. The Worker's choice is (a) restore it, honouring the declared source, or (b)
  keep the original's shape and record the decision in an artifact. What is not acceptable is the
  current state, where it vanished without any record that a choice was made.

### BK10 · BK-P1 · P0 · VERIFIED — Qur'an 36:60–61 and the *Sirat al-Mustaqeem* sentence dropped from the sixth benefit
- **Chapter:** 5 — Eight Lessons from Thirty-Three Years
- **book.md:** line 430 ends the sixth benefit at "…gave myself wholly to His worship and service."
- **Source:** lines 442–448 — *"This is the correct way — the Sirat al-Mustaqeem, the straight path of
  guidance in which there is no crookedness — as Allah, the Exalted, has Himself declared:
  `Alam A'had Ilaeykum Ya Bani Aadama…` 'Did I not make this covenant with you, O Children of Adam…
  and that you should worship Me alone? This is the straight path.'"*
- **Why it fails:** the longest single omission in the book — a two-verse Qur'anic citation (36:60–61,
  both present in `fts_quran`) with the sentence that names the straight path. The sixth benefit is the
  only one of Hatim's eight that now ends without the scriptural warrant the other seven carry, which
  breaks the chapter's own rhythm as well as losing the citation.
- **Ambiguity:** as BK09 — absent from the Arabic original, present in the declared source.

### BK11 · BK-P1 · P0 · VERIFIED — the Mizan and the plain of Hashr dropped from the account of preaching
- **Chapter:** 8 — Four to Avoid, Four to Embrace
- **book.md:** line 589 — "…his condition at the Resurrection and its stations, and whether he will
  cross the Bridge in safety or fall into the abyss."
- **Source:** line 617 — "…of the fearsome spectacle of accountability on the **plain of Hashr**, where
  all of humankind will be assembled after resurrection; of the **weighing of deeds in the Mizan — the
  mighty scale created by Almighty Allah for that purpose**; of the crossing of the bridge called
  Sirat…"
- **Why it fails:** the source's eschatological sequence is Angel of Death → Munkar and Nakir → Hashr →
  Mizan → Sirat. The book keeps four of the five and drops the Mizan, which is the one a reader is most
  likely to be looking for in a list of what a sermon must cover.
- **Ambiguity:** as BK09.

### BK12 · BK-P1 · P0 · VERIFIED — 'Aisha Siddiqa and the Mothers of the Believers dropped
- **Chapter:** 8 — Four to Avoid, Four to Embrace
- **book.md:** line 637 — "He did not set it aside for all his chambers; rather he set it aside for the
  one in whose heart he knew there was a weakness. As for her who was a possessor of certainty, he would
  set aside for her no more than the provision of a day, or half of it."
- **Source:** line 684 — "…the **Azwaj al-Mutahharat**… For those among the **Ummahatil Mu'mineen, the
  Mothers of the Believers**, whose certainty in Allah was perfect… Among them was **'Aisha Siddiqa, may
  Allah be pleased with her**, and others like her among the Mothers of the Believers."
- **Why it fails:** a named person present in the source span is absent from the chapter, together with
  two collective titles. I checked whether this was policy: **`scripts/podcast/_doctrinal.py` contains no
  Aisha generalization rule** (grep returns nothing), and the book names Abu Bakr al-Siddiq, Ali,
  Abdullah ibn Umar and Sa'd ibn Mu'adh without generalization — so this is not a doctrinal decision, it
  is collateral damage from the witness switch.
- **Note in the book's favour:** the substantive correction here is right. The English source says the
  certain wives received nothing; the Arabic says `فما كان يعدّ لها أكثر من قوت يوم أو نصف` — a day's
  provision or half. The book follows the Arabic and is correct. Restore the names without reverting the
  correction.
- **Worker action:** restore "'Aisha Siddiqa (may Allah be pleased with her)" and "the Mothers of the
  Believers", and translate `حجراته` rather than transliterating it as "chambers" (see BK20).

### BK13 · BK-P7 · P0 · VERIFIED — the chapter's governing maxim is stated twice
- **Chapter:** 2 — The Striving That Mercy Meets
- **book.md:** line 109 — "My dear son, be firmly convinced of this: without effort you will not find
  its reward." — and line 129 — "My dear son, so long as you do not act, you will not find the reward."
- **Source:** line 146 (English source, before the parable) and OCR line 126
  (`أيّها الولد، ما لم تعمل لم تجد الأجر` — also before the parable)
- **Why it fails:** both witnesses state this maxim **once**, immediately before the parable of the
  tested worshipper. The book renders the English source's wording before the parable and the Arabic's
  wording after it, so the same proposition is asserted twice, twenty lines apart, with no signal that
  the repetition is deliberate. Elsewhere the letter marks its own repetitions explicitly ("Woe unto you,
  and again woe unto you"; "I say this weighty point again"), which makes the silent one read as a seam.
  `_system/book-duplication-check.json` is empty because a single-paragraph twin is below the
  consecutive-run threshold — this is the class the deterministic check cannot see.
- **Mapped clause by clause against both witnesses:** neither copy contains anything the other lacks;
  both are one sentence and both say the same thing. No source clause is missing from both, so no
  companion BK-P1 finding arises here.
- **Worker action (merge, not delete):** keep line 109 in place — it holds the position both witnesses
  give the maxim — and delete line 129's sentence, promoting the rest of that paragraph ("Hear now what
  the Messenger of Allah… says:") to a clean transition. Recommended replacement for line 129:
  *"Hear now what the Messenger of Allah (may Allah bless him and grant him peace) says:"* Nothing is
  lost: line 129's clause and line 109's clause are the same proposition, verified against both sources.

### BK14 · BK-P5 · P1 · VERIFIED — narrator-announcement opening survived the revert that was meant to remove it
- **Chapter:** 2 — The Striving That Mercy Meets
- **book.md:** lines 109–111 — "My dear son, be firmly convinced of this: without effort you will not
  find its reward. / **Let me tell you of a man** among the Children of Israel who worshipped Allah…"
- **Source:** line 146 — "There was a man among the Children of Israel who worshipped Allah with great
  devotion." / OCR line 126 — `حكي أنّ رجلا من بني إسرائيل عبد الله تعالى سبعين سنة`
- **Why it fails:** neither witness has the author announce that he is about to narrate; the Arabic uses
  the impersonal `حكي أنّ` ("it is related that"). `_system/book-fluency-report.json` reverted this
  chapter for `fluency-03: narrative-announcement opening` — and
  `book/_chapters/ch02-the-striving-that-mercy-meets.txt` (the base that was restored) opens with the
  identical construction at the identical position. The gate reverted to a copy carrying the defect it
  fired on.
- **Worker action:** `book-rearticulator ayyuhal-walad ch02-the-striving-that-mercy-meets`, opening the
  parable as *"It is related that a man among the Children of Israel worshipped Allah the Exalted with
  great devotion for seventy years."* The gate's own detector should also be extended to the base, not
  only to the candidate — otherwise this revert path will keep producing this result.

### BK15 · BK-A1 + BK-N7 · P1 · VERIFIED — six honorific forms, with a hard register break at chapter 6
- **Chapter:** whole book; break localized to 6 — Finding a True Guide
- **book.md:** `(ع)` ×25 (chs 1–5, 7–9); `(صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ)` ×9 — **all nine in chapter 6
  alone** (lines 458, 460, 462, 464, 466); `(رض)` ×9; `(رضي الله عنه)` ×1 (line 17);
  `(عليه السلام)` ×1 (line 33); "(may Allah bless him and grant him peace)" ×3 (lines 17, 129, 165);
  "(may Allah have mercy on him)" ×3 (lines 238, 282, 533)
- **Why it fails:** chapter 6 sets the Prophet's honorific at full length nine times in nine lines while
  every other chapter uses the two-character compact form — a register break a reader will feel on the
  page turn. The compose flagged it itself (`terminology_notes`: *"honorific forms should be kept
  consistent book-wide in the compact shape the surrounding text already uses"*) and shipped anyway.
- **Worker action:** run the honorifics pass over the whole book and normalise to the compact form;
  chapter 6 is the only chapter that needs real work.

### BK16 · BK-P4 · P1 · VERIFIED — Imam Ghazali given a Companion's honorific
- **Chapter:** Preface — A Letter Across the Centuries
- **book.md:** line 17 — "Know that one of Imam Ghazali's **(رضي الله عنه)** foremost students…";
  lines 23, 25, 27 — "Imam Ghazali **(رض)**"
- **Source:** line 60 — "Imam Ghazali **(Rahmatullahi Alayhe [RA — May Allah shower His mercy upon
  him])**"; OCR line 34 — `أبي حامد بن محمد الغزالي، **قدّس الله روحه**`
- **Why it fails:** both witnesses give Ghazali a scholar's honorific — "may Allah have mercy on him" in
  the English source, "may God sanctify his soul" in the Arabic. The book substitutes
  `رضي الله عنه` / `رض`, "may Allah be pleased with him", which is the formula reserved for the
  Companions. It is an attribution formula changed to one neither source uses, and it is the very first
  thing on the book's first page of body text. The book uses the *same* `(رض)` for Abu Bakr, Ali and
  Ibn Umar two pages later, so a reader is given no way to tell a Companion from an eleventh-century
  jurist.
- **Worker action:** render Ghazali as `(رحمه الله)` throughout the preface, matching the source.

### BK17 · BK-P8 · P1 · VERIFIED — REQ-BA-010 + REQ-BA-020: a calqued sentence a general reader cannot parse
- **Chapter:** 3 — The Hours Before Dawn (the "copied, not re-voiced" chapter)
- **book.md:** line 220 — *"My dear son, fix your resolve upon the spirit, defeat upon the lower self,
  and death before the body, for your dwelling place is the grave…"*
- **Source:** OCR line 178 — `اجعل الهمّة في الرّوح، والهزيمة في النفس، والموت في البدن`; English source
  line 236 — "Summon courage within yourself and stir your body to strive upon the Path of God."
- **Why it fails:** the Arabic's three parallel `في` phrases are carried straight across, and the third
  lands as "death before the body", which is not English and means nothing on first read (`في البدن` is
  "in the body", not "before" it). The clause chain is Arabic rhetorical scaffolding preserved at the cost
  of idiom — REQ-BA-020's named failure — and the sentence is not understandable on first read —
  REQ-BA-010.
- **Plain-English rendering it should have had:** *"My dear son, set your ambition on the spirit, defeat
  on the lower self, and keep death always before your body, for your dwelling place is the grave…"*
- **Worker action:** `book-rearticulator ayyuhal-walad ch03-the-hours-before-dawn`. This chapter's
  `fluency-04: output near-identical to base` warning is the reason it still reads translated.

### BK18 · BK-P8 · P1 · VERIFIED — REQ-BA-010 + REQ-BA-020: "magnifying the creation"
- **Chapter:** 7 — Sufism, Servitude, Trust, Sincerity
- **book.md:** line 505 — *"Know that Riya is born of magnifying the creation."*
- **Source:** OCR line 436 — `واعلم أنّ الرّياء يتولّد من تعظيم الخلق`; English source line 532 — "You
  should know that Riya is born from the praises and honors of people."
- **Why it fails:** `تعظيم الخلق` is rendered word-for-word. "Magnifying the creation" is not an English
  phrase; a general reader will read "the creation" as the cosmos rather than as other people, and
  "magnifying" as enlarging rather than as over-valuing. The declared source already says it plainly.
- **Plain-English rendering it should have had:** *"Know that showing off is born of thinking too highly
  of other people."*
- **Worker action:** `book-rearticulator ayyuhal-walad ch07-sufism-servitude-trust-sincerity`.

### BK19 · BK-P8 · P1 · VERIFIED — REQ-BA-020: a demonstrative chain carried across intact
- **Chapter:** 8 — Four to Avoid, Four to Embrace
- **book.md:** line 589 — *"This boiling of these fires and this wailing over these calamities is what is
  called admonition."*
- **Source:** OCR line 530 — `فغليان هذه النّيران، و نوحة هذه المصائب يسمّى تذكيرا`
- **Why it fails:** four demonstratives in fourteen words, reproducing the Arabic `هذه … هذه` pattern
  exactly. This is the "pronoun chain carried into English" REQ-BA-020 names, and the sentence stalls a
  reader mid-clause trying to work out which "this" governs.
- **Plain-English rendering it should have had:** *"It is this boiling up of the fires, this lament over
  the calamities, that we call admonition."*
- **Worker action:** `book-rearticulator ayyuhal-walad ch08-four-to-avoid-four-to-embrace`.

### BK20 · BK-P8 · P1 · VERIFIED — REQ-BA-010: an untranslated metonym leaves the sentence unreadable
- **Chapter:** 8 — Four to Avoid, Four to Embrace
- **book.md:** line 637 — *"He did not set it aside for all his chambers; rather he set it aside for the
  one in whose heart he knew there was a weakness."*
- **Source:** OCR line 635 — `و لم یکن یعدّ ذلك لكلّ حجراته بل كان يعدّه لمن علم أنّ في قلبها ضعفا`;
  English source line 684 — "the Prophet did not set aside provisions for all of his wives"
- **Why it fails:** `حجراته` is the Prophet's wives' apartments, used metonymically for the wives
  themselves. Printed as "chambers", it reads as rooms — and then the next clause says "the one in whose
  **heart** he knew there was a weakness", which a room does not have. The sentence is incoherent on
  first read, and the declared source already renders it correctly.
- **Plain-English rendering it should have had:** *"He did not set aside a year's provision for all of
  his wives; he set it aside only for the one in whose heart he knew there was a weakness."*
- **Worker action:** as BK19; restore the names lost in BK12 in the same pass.

### BK21 · BK-P8 · P1 · VERIFIED — REQ-BA-010 + REQ-BA-020: "presuming himself in no need"
- **Chapter:** 2 — The Striving That Mercy Meets (reverted; received no articulation pass)
- **book.md:** line 139 — *"Whoever supposes that he will arrive without striving is a wishful dreamer,
  and whoever supposes that he will arrive by the mere expending of his effort is presuming himself in no
  need."*
- **Source:** OCR line 143–144 — `ومن ظنّ أنّه ببذل الجهد يصل فهو مستغن`
- **Why it fails:** `مستغن` is rendered by its dictionary parts. "Presuming himself in no need" leaves the
  reader with no object — in no need of *what*? The answer (God's help) is exactly the point of Ali's
  saying, and the sentence withholds it.
- **Plain-English rendering it should have had:** *"…and whoever supposes that he will arrive by his own
  effort alone is presuming he can do without God's help."*
- **Worker action:** `book-rearticulator ayyuhal-walad ch02-the-striving-that-mercy-meets`, in the same
  pass as BK13 and BK14.

### BK22 · BK-P8 · P1 · VERIFIED — REQ-BA-100: three chapters materially shorter than their source spans
- **Chapters:** 3 (0.68), 8 (0.69), 1 (0.76)
- **Measured:** ch3 1,614 → 1,098 English words; ch8 3,545 → 2,463; ch1 1,568 → 1,195
- **Why it fails:** REQ-BA-100 requires output length to stay approximately the source length. The 60%
  compose gate did not fire because all three clear 0.60, but three chapters losing between a quarter and
  a third of their span is materially short, and BK09/BK11/BK12 are inside exactly those three chapters.
- **Honest qualification, stated because it changes the fix:** most of the shortfall is the Urdu
  translator's amplification, and dropping it is right. The correct remedy is **not** to inflate these
  chapters back toward the ratio — it is to restore the four substantive items in BK09–BK12 and leave the
  ratio where it lands.
- **Worker action:** treat BK09–BK12 as the fix; re-measure afterwards and record the accepted ratios so
  the next run does not re-litigate this.

### BK23 · BK-P3 · P1 · VERIFIED — the closing du'a prints malformed forms of "Allahumma" and "Allah"
- **Chapter:** 9 — A Prayer for the Road
- **book.md:** line 645 `«أَلَّهُمَّ إِنِّي أَسْأَلُكَ…»`; line 647 `ألّهمّ كن لنا`; line 649
  `ألّهمّ اختم بالسعادة` and `يا الله، يا ألله، يا ألله` — while the **same paragraph** prints the correct
  `اللَّهُمَّ ثَبِّتْنَا عَلَى نَهْجِ الْإِسْتِقَامَةِ`
- **Source:** OCR lines 642–662 (identical malformations)
- **Why it fails:** `أَلَّهُمَّ` and `ألله` are not words; both are scanner damage. The vowelling gate saw
  the model propose the corrections and refused them for changing letters — the refusals are recorded in
  `_system/book-vowelling.json` (*"first difference at character 3: source `هم كن لنا` vs proposal
  `لهم كن لنا`"*). The gate behaved correctly under the marks-only rule; the consequence is that the
  book's benediction prints two spellings of the same vocative three lines apart. This is the one place
  where "refusals are bare on purpose" is not the whole story: the run was not merely left unvowelled, it
  was left **wrong**.
- **Worker action:** correct the OCR at source (`_system/source/ocr/raw-extract.md`) so the marks-only
  gate has a clean skeleton to vowel, then re-run `5a-vowelling`. Do not patch `book.md`.

### BK24 · BK-N7 · P1 · VERIFIED — the same term glossed twice, two spellings, two Arabic forms
- **Chapters:** 4 and 6
- **book.md:** line 316 — "*mujahadah* (مُجَاهَدَة), the intense inner struggle"; line 464 — "every manner
  of Riazat (اَلرِّيَاضَة) and **Mujahada (الْمُجَاهَدَة)**, spiritual struggles and disciplines"
- **Why it fails:** one technical term, two transliterations (`mujahadah` / `Mujahada`), two Arabic forms
  (bare / with the article), and two first-use glosses. The annotation policy introduces a teach-class
  term **once per book**; a reader tracing the argument's central term through chapters 4 and 6 cannot
  tell that these are the same word. `_narrative` has no deterministic check for this, which is why it
  reached the page.
- **Worker action:** standardise on `mujahadah (مُجَاهَدَة)` at chapter 4's first use and use bare
  *mujahadah* thereafter; drop the chapter 6 annotation.

### BK25 · BK-P3 · P1 · VERIFIED — a Qur'anic citation that points at the wrong verse
- **Chapter:** 1 — Knowledge That Will Not Save You
- **book.md:** line 73 — "And that man shall have nothing but that for which he strives." **(Quran,
  an-Najm: 38)**
- **Canonical (`fts_quran`):** 53:**39** is `وَأَن لَّيْسَ لِلْإِنسَنِ إِلَّا مَا سَعَىٰ` — the verse quoted.
  53:**38** is `أَلَّا تَزِرُ وَازِرَةٌۭ وِزْرَ أُخْرَىٰ`, a different verse.
- **Source:** the English source gives **no** verse number (line 110); the number was added by the book,
  copied from the Arabic print's marginal apparatus (OCR line 102, `النجم: ٣٨`).
- **Why it fails:** an added citation, not present in the declared source, that sends a reader to the
  wrong ayah. Every other citation in the book checks out against `fts_quran` — I verified 18:110, 99:7–8,
  7:56, 7:179, 7:50, 17:79, 51:18, 3:17, 79:40–41, 16:96, 49:13, 43:32, 35:6, 11:6, 65:3, 49:5, 18:70,
  21:37, 35:44, 53:29 — so this is the single outlier and cheap to fix.
- **Worker action:** correct to `an-Najm: 39`, and validate every added citation against `fts_quran`
  rather than against the print's marginalia.

### BK26 · BK-P3 · P2 · VERIFIED — two manufactured Arabic terms are ungrammatical
- **Chapter:** 6 — Finding a True Guide
- **book.md:** line 458 — `Shaykh al-Kamil (شَيْخُ الْكَامِل)` and `Murshid al-Kamil (مُرْشِد اَلْكَامِل)`
- **Why it fails:** both are ill-formed. A definite adjective cannot modify an indefinite head; correct
  Arabic is `الشَّيْخُ الْكَامِل` / `الْمُرْشِدُ الْكَامِل` (or indefinite `شَيْخٌ كَامِل`). Neither construct
  appears in the Arabic original, which says `شيخ مرشد مربّ` and `شخص بصير`. These are the two runs the
  Arabic audit flagged UNVERIFIED in this chapter and they are the only two of the fourteen that are real.
- **Worker action:** fix the glossary entries; the transliterations may stay as the source has them.

### BK27 · BK-P3 · P2 · VERIFIED — supplied Arabic does not match the transliteration it glosses
- **Chapter:** 4 — Worship Is Obedience, Nothing Less
- **book.md:** line 312 — `is called *athim* (أَثِيْم), a sinner`
- **Source:** line 334 — "*athim* (a sinner)"
- **Why it fails:** "athim" is `آثِم` (one who sins). `أَثِيْم` is *athīm*, a different word (the
  intensive, as at Qur'an 44:44). The glossary supplied the wrong lexeme for the transliteration it was
  glossing.
- **Worker action:** correct the glossary entry to `آثِم`.

### BK28 · BK-P3 · P2 · VERIFIED — Persian yeh in the closing du'a
- **Chapter:** 9 — A Prayer for the Road
- **book.md:** line 649 — `و يا أول الأوّلین، و يا آخر الآخرین`
- **Why it fails:** both words end in Persian yeh (`ی`, U+06CC) rather than Arabic yaa (`ي`, U+064A),
  copied from OCR line 662. It will render with the wrong glyph and will not match on search.
- **Worker action:** normalise the character in the OCR source, then re-run vowelling.

### BK29 · BK-P2 · P2 · VERIFIED — scanner marginalia printed inside quoted scripture
- **Chapters:** 7 and 8
- **book.md:** lines 511, 517, 523, 529, 557 — e.g. `(فَلاَ تَسْئَلْنِي عَنْ شَيْءٍ … * الكهف: ٧٠)`
- **Why it fails:** the surrounding parentheses, the `*` separator and the Arabic-numeral sura:ayah label
  are the print edition's marginal apparatus, now sitting inside the Arabic blockquote — while the same
  citation is given again in English directly beneath. Every other Arabic block in the book is clean text.
  Five blocks in two chapters carry the apparatus; those are precisely the five lifted verbatim from OCR.
- **Worker action:** strip the apparatus from the Arabic runs; keep the English citation line.

### BK30 · BK-P2 · P2 · VERIFIED — one Arabic block has its English above it rather than beneath
- **Chapter:** 8 — Four to Avoid, Four to Embrace
- **book.md:** lines 591–593 — "…so you cry out, 'Beware, beware! Flee from the flood!'" followed by
  `الْحَذَرَ الْحَذَرَ، فِرُّوا مِنَ السَّيْلِ`
- **Why it fails:** inverts the book's own script-then-translation convention, so the Arabic block appears
  to stand untranslated.
- **Worker action:** reorder to match the convention used everywhere else.

### BK31 · BK-A3 · P2 · VERIFIED — an editorial note is printed after the book's closing sentence
- **Chapter:** 9 — A Prayer for the Road
- **book.md:** line 657 — "Here this book comes to an end, with the help of Al-Malik… and Al-Wahhab…" —
  followed by lines 659–670, a fenced editorial note
- **Why it fails:** the treatise declares its own ending, and then something else speaks after it. The
  note's content is sound (it is drawn entirely from the book's own preface and chapter 1), but placing
  apparatus after the terminal sentence undercuts the closing.
- **Worker action:** move the note ahead of the closing sentence, or into back matter.

### BK32 · BK-P4 · P2 · INFERRED — an editorial note introduces a hadith that cuts against its chapter
- **Chapter:** 2 — The Striving That Mercy Meets
- **book.md:** lines 188–191 — *"The wider tradition also records the assurance that whoever says there
  is no god but Allah will enter Paradise, but with a qualification worth holding beside this chapter's
  counsel: that it be said with sincerity."*
- **Why it flags:** the block is correctly fenced, correctly labelled, and drawn from the reliable KB
  corpus, so it is **in contract** for `augmentation: source_only` and I am not reporting it as a
  violation. But the chapter it is attached to argues, at length and against an imagined objector, that
  faith without deeds does not save; appending an unattributed assurance that the testimony alone admits
  one to Paradise obliges the note to spend two sentences reconciling it. This is an editorial judgment
  that deserves your eye rather than a silent ship.
- **Worker action:** none automatic. Escalate — keep, cut, or attribute.

### BK33 · artifact hygiene · P2 · VERIFIED — a translation-edition manifest for a book that is not one
- **Files:** `_system/translation-edition-manifest.json` (`"mode": "translation_edition"`,
  `"augmentation": "forbidden"`), `book/source-crosswalk.json`
- **Why it flags:** `series-config.yaml` declares no `deliverable_mode`, and the resolved knobs are
  `{source_only, faithful}` — this is the augmented-companion route. The manifest is a byproduct of
  `compose_book_v2` reusing `author_translation_edition_compose` as the shared faithful base with
  `enforce_contract=False`, so it is **not** a routing bug. But it asserts a mode and an augmentation
  policy that are both false for this book, and it directly contradicts the four editorial blocks the
  augment pass legitimately added forty minutes later. Any reader — human or agent — who classifies the
  route from this file will classify it wrongly, and will then judge the four editorial blocks as contract
  violations.
- **Worker action:** have the shared base skip or clearly mark the manifest when `enforce_contract=False`.

---

## Notes recorded, deliberately NOT reported as findings

These are the places where the book departs from the declared English source and is **right** to. Reporting
them would recommend a regression.

- **Chapter 3, the list of sciences.** Source line 214 gives "ethics (*Ilmul Ikhlaq*)… linguistics…
  the science of warfare"; the book gives "the science of juristic disagreement (*al-khilaf*)… prosody
  (*al-arud*)… morphology (*al-tasrif*)". The Arabic (OCR line 157–158) is
  `علم الكلام و الخلاف والطبّ و الدّواوين والأشعار و النّجوم و العروض و النّحو و التّصريف`. The book is
  correct and the source list is a chain-of-translation corruption.
- **Chapter 2, Ali's saying.** Source has "merely exhausting himself" (`مُتْعِب`); the Arabic has
  `مستغن`. The book follows the Arabic. Correct (though see BK21 on how it renders it).
- **Chapter 8, the four turnings a sermon should work.** The book gives the Arabic's pairs (doubt →
  certainty, heedlessness → wakefulness); the source gives different ones. Neither loses count.
- **Chapter 7, "if you travel you will see wonders."** Source line 557 substitutes "if you illuminate
  your heart"; the Arabic is `إن تسر تر العجائب في كلّ منزل`. The book is correct.
- **Chapter 8, the wives' provision.** The Arabic says the certain wife received a day's provision or
  half; the source says none. The book is correct — see BK12, which asks only for the names back.
- **Preface, the opening hadith.** The book gives `اللّهمّ أعوذ بك من علم لا ينفع` ("O Allah, I seek refuge
  in You…") per the Arabic; the source transliterates `A'auzu Billahi` ("I seek Allah's refuge"). The
  book is correct.
- **Chapter 4, the hadith of Shibli.** OCR line 288 reads `و اعمل الله بقدر` (missing the lam); the book
  prints `وَاعْمَلْ لِلَّهِ بِقَدْرِ`. A correct silent repair, of the kind BK01–BK04 needed and did not get.
- **Chapter 6, "rarer than red sulphur."** The Arabic has `أعزّ من الكبريت الأحمر`; both the English source
  and the book say "exceedingly hard to find". The image was flattened by the Urdu translator, not by this
  pass, so REQ-BA-050 does not attach — but it is the one image in the book worth restoring editorially.
- **BK-A5 note.** `enable_knowledge_augmenter: true` with `tradition_affinity: fatimid-ismaili` fed twelve
  `doctrine:wisdom:*` atoms and one `quote:mawla-amir-al-muminin` atom into a Ghazali edition. **No
  tradition-distinctive claim and no Shi'i honorific reached the visible prose**, so BK-A5 passes — but it
  passes by outcome. The `knowledge_tags` filter in `meta.yml` is the only thing standing between that
  corpus and this book, and one atom carrying an Ismaili honorific for Ali was selected. Worth watching.

---

## Verified vs Inferred summary

- **VERIFIED: 32 of 33** — every finding is anchored to a quoted line in `book.md` plus its counterpart in
  `_system/source/text/refined-english.md`, `_system/source/ocr/raw-extract.md`, or
  `content/knowledge-base/mirror.db` (`fts_quran`).
- **INFERRED: 1** — BK32 (editorial judgment on an in-contract enrichment block).
- All four Qur'anic corruptions (BK01–BK04) and the citation error (BK25) were checked directly against
  `fts_quran` in this run; none rests on model recall.

## Ledger emission summary

33 records emitted to `_learning/findings.jsonl` with `source: "book-challenger"`,
`challenger_version: "1.0"`, `book: "ayyuhal-walad"`, `resolution: "flagged"`.
Severity split: **13 P0, 12 P1, 8 P2.**

## Verdict

**BLOCKED.** Thirteen P0 findings. The book must not publish until at minimum BK01–BK08 (Arabic and
scripture integrity) and BK09–BK12 (content lost in the witness switch) are resolved. BK22's remedy is
BK09–BK12, not re-inflation.

The P1 set is largely one re-articulation pass over chapters 2, 3, 7 and 8 plus an honorifics sweep, and
per the archetype-over-rerun discipline should be batched with the P0 fixes rather than run separately.
BK32 needs Asif, not a Worker.
