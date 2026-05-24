# KAHSKOLE Taxonomy — Round 1 Proposal

**Generated:** 2026-05-24
**Scope:** Dedup findings + 122 chapter retitle proposals
**Status:** Awaiting approval — NO bundles modified

This document is the Round 1 output of `tools/content_classifier/`. It is purely advisory; the source bundles under `_workspace/kashkole-ksessions/extracted/kashkole/` remain byte-faithful to the KAHSKOLE SQL source. Topic-level retitling (1,337 topics) is deferred to Round 2.

## How to review this document

Mark each block with one of:
- ✅ **approve** — adopt as proposed
- ✏️  **revise** — write your replacement title or alternate cluster decision below
- ⏭️  **skip** — defer this finding to a later pass

The proposal index at the bottom collects per-block decisions.

---

## Part A — Dedup findings (mechanical)

All findings below are computed against the source SQL database, not the bundle files. The bundles faithfully reflect what's in the DB; if the DB has the same Topic linked to two Chapters, the bundle shows it in both — that's correct behavior.

### A.1 Exact-byte image duplicates (35 clusters)

Already actionable: 35 SHA-256-identical image clusters. Drop one canonical sidecar per cluster; the propagator already does this (see `_workspace/plan/_drivers/image_dedupe.py`).

**Highlights:**
- 1 cluster of **40 PNGs all identical** (likely a pause-button/session-divider graphic in `01-musawwadat/07-initial-12-sessions/`). One canonical sidecar covers all 40.
- 8 cross-chapter clusters of size 2–3 between binders 6/19/18 (the Tawheed/Wilayat/Imam Ali binders share several Quran-verse images).
- 4 cross-chapter clusters between binder 2 (Quranic Studies) and binder 3 (The Wise Reminder) — same chiastic-structure diagrams reused across chapters.

**Proposed action:** Already handled by image_dedupe.py's `propagate` command — no further action needed. Just confirm we treat these as deduplicated in the adaptation layer (the *adapted* English output cites the diagram once and references prior chapters where it also appeared).

- [ ] **Approve A.1** (default: ✅)

### A.2 Perceptual near-duplicate images (55 clusters)

NEW finding from dHash analysis. These are images that are content-identical but byte-different — e.g., the same chiastic diagram re-rendered at slightly different resolution, or a Quran widget rendered in two different KAHSKOLE export passes. Hamming distance ≤ 8 on 64-bit dHash.

**Top 5 examples (illustrative):**

| Cluster size | Spans binders | Sample paths |
|---|---|---|
| 5 images, 5 distinct SHAs | b1 (12-maratib-aur-majame) + b8 (03-bism-allah-ki-taweel) | The تسبیح/zikr diagram |
| 4 images, 4 SHAs | b5 + b8 + b10 (Wilayat-related) | Same wilayat-line diagram across binders |
| 4 images, 4 SHAs | b8 + b8 + b12 (al-Fatihah / Quranic Ayat taweel) | Same surah-chart |
| 4 images, 3 SHAs | b8 + b12 + b18 (Quran/Wilayat/Imam Ali) | Same isnad/genealogy diagram |
| 3 images | b1 chiastic diagrams in 12-maratib-aur-majame | Internal-to-one-chapter variants |

**Proposed action:** Treat as soft dupes — the adaptation layer renders one canonical version with a footnote `"(also rendered in §X.Y of …)"`. The 55 clusters are likely to include 10–15% false positives (different diagrams with similar overall layouts), so each cluster gets flagged for human spot-check before merge.

- [ ] **Approve A.2 with manual spot-check policy** (default: ✅)

### A.3 Exact topic content duplicates (21 clusters) — **MOST ACTIONABLE**

This is the highest-confidence dedup signal: 21 cases where the SAME `TopicDataUnicode` blob in the DB is linked from MULTIPLE chapters via `ChapterTopics`. The bundle faithfully replicates the content in each chapter's `raw-extract.md`.

#### A.3.1 — **Chapter 71 ("اسلام اور ایمان") appears in TWO binders identically**

| Binder | Bundle path | Topic count |
|---|---|---|
| **19** (دعائم الاسلام : ولایت) | `12-daaim-al-islam-wilayat/04-x7946-aur-x8101/` | 13 topics, all shared |
| **24** (توحید مبدع تعالی) | `06-tawheed-mubdi-taala/03-x7946-aur-x8101/` | 13 topics, all shared (same SHA) |

All 13 topics: `ایمان کیا ہے؟`, `دل، زبان اور جسم کا ایمان`, `ایمان اور مومنین کی ۳ اقسام`, `ایمان کے ۸ طبقات کا بیان`, `صاحب ایمان کے خصائل`, `ایمان میں سباقیت اور درجات`, `ظاھری اور باطنی ایمان`, `ایمان کو علم پر فضیلت حاصل ہے`, `اسلام اور ایمان کا فرق`, `ایمان، شرک و گمراہی کی ادنی ترین شرائط`, `اسلامی دعوت کا اصل مقصد کیا تھا؟`, `اسلامی و ایمانی جنت`, `اسلام و ایمان کا انبعاث`.

**This is structural, not duplication.** The compiler intentionally placed this chapter under both Tawhid (binder 24) and Wilayat (binder 19) because it bridges the two themes. Either preserve both bundles with a cross-reference, OR mark one as primary and treat the other as a soft-link.

**Proposed action:** Primary = **binder 19** (Wilayat — chapter is more semantically about ولایت ایمانی); binder 24 keeps a soft-link entry that points to the binder-19 bundle. The pipeline ingests it once.

- [ ] **Approve A.3.1 primary=b19** (default: ✅)
- [ ] Alternative: primary=b24 (Tawhid)
- [ ] Alternative: keep both as independent ingest targets

#### A.3.2 — **Chapter 174 ("SALAAMS") and Chapter 156 ("سلام علی رسول اللہ و آلہ") share 4 of 4–5 topics**

| Source | Bundle path |
|---|---|
| **b36/c174** | `04-islam-iman-ihsan/01-salaams/` |
| **b34/c156** | `02-quranic-studies/02-x6371-ali-x6384-allah-wa-x4903/` |

Shared topics (TopicIDs 5679, 5680, 5681, 5683): the Arabic salutation formulas. b36/c174 has an extra English-titled section ("SALAAMS"); b34/c156 has an extra Urdu-titled section ("منصوب داعی کی فاتحۃ").

**Proposed action:** Primary = **b34/c156** (more complete chapter); b36/c174 becomes a cross-reference. OR keep both — they're framed differently (one Urdu, one English).

- [ ] **Approve A.3.2: keep both, mark as cross-references** (default: ✅)
- [ ] Alternative: merge into primary b34/c156, deprecate b36/c174

#### A.3.3 — Other single-topic cross-chapter duplicates (~7 cases)

These are individual topics linked from two chapters via `ChapterTopics`. The DB has one Topic row; the bundle replicates content in both chapters. The pipeline should cite the topic in its "primary" chapter; the other chapter's bundle gets a cross-reference stub at that section.

| Topic | TopicID | Primary chapter (proposed) | Cross-ref chapter |
|---|---|---|---|
| ولایت کی اہمیت | 821 | b19/c122 (Wilayat ki ahmiyyat aur awsaf — dedicated chapter) | b6/c46 (Mawlana Ali ki Fada'il — supporting context) |
| جسمانی و نفسانی بیمار اور اس کا علاج | 3553 | b23/c87 (Kitab al-Alim wal-Ghulam — primary text) | b8/c18 (Qurani Ayat ki Taweel — secondary citation) |
| پانی پر بسم اللہ پڑھ کر دم کرنے کی روایت | 599 | b8/c9 (Ahadith Nabawi ki Taweel — hadith treatment) | b8/c24 (Bismillah ki Taweel — basmala context, secondary) |
| من عرف نفسہ فقد عرف ربہ | 9 | b8/c9 (hadith treatment, primary) | b24/c121 (Tawhid ka Tasawwur — secondary) |
| ولایت دل پر کیوں فرض کی گئی ہے؟ (vs. معاذ تمہیں سارے دین کا خلاصہ بتاؤں؟) | 1425 / 4660 | These two topics share normalized text but have different IDs — likely two retellings of the same hadith. Primary = b19/c122 | Cross-ref from b28/c150 (Sunday Sessions — breakups) |

**Proposed action:** Apply the proposed primary/cross-ref scheme above. The adaptation layer renders each topic once in its primary chapter; the cross-ref chapter's adapted output cites the primary with a one-sentence summary.

- [ ] **Approve A.3.3 primary/cross-ref assignments** (default: ✅)

### A.4 Near content duplicates (≥90% match)

**0 clusters found.** The conservative threshold caught nothing beyond what A.3 already surfaced. This suggests that beyond the exact-DB-link cases, the corpus is genuinely heterogeneous — different chapters discussing similar topics use different prose.

(Round 2 will re-run this with a lower threshold and against the English translation, where semantic similarity is easier to detect.)

- [ ] **A.4: no findings; nothing to approve**

---

## Part B — Proposed English chapter titles (122)

Format: `<binder>:<chapter>  <Urdu/source name>  →  <Proposed English title>  [confidence]`

**Confidence key:** ★★★ high (term is standard Ismaili/Arabic, gloss is well-established); ★★ medium (proposed title is interpretive); ★ low (chapter name is opaque without reading content).

### Binder 1 — علوم مبدا و معاد → **"Sciences of Origin and Return"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 73 | تشکیل عالم روحانی | *Tashkīl al-ʿĀlam al-Rūḥānī* — The Forming of the Spiritual World | ★★★ |
| 74 | عقل اول | *Al-ʿAql al-Awwal* — The First Intellect | ★★★ |
| 75 | سات عقول | *Sabʿat al-ʿUqūl* — The Seven Intellects | ★★★ |
| 76 | عاشر کی دعوت | *Daʿwat al-ʿĀshir* — The Call of the Tenth Intellect | ★★★ |
| 78 | تشکیل عالم حیات | *Tashkīl ʿĀlam al-Ḥayāt* — The Forming of the World of Life | ★★★ |
| 80 | تشکیل عالم کون و فساد | *Tashkīl ʿĀlam al-Kawn wa-l-Fasād* — Forming the World of Generation and Corruption | ★★★ |
| 81 | نفوس اور ان کی اقسام | *Al-Nufūs* — The Souls and Their Categories | ★★★ |
| 82 | معاد محمود | *Maʿād Maḥmūd* — The Praiseworthy Return | ★★★ |
| 84 | موالید کی پیدائش | *Mawālīd* — The Generation of the Three Kingdoms (mineral, vegetable, animal) | ★★★ |
| 125 | منبعثین | *Al-Munbaʿithūn* — The Emanators (Second and Third Intellects) | ★★★ |
| 20 | معاد مزموم | *Maʿād Madhmūm* — The Blameworthy Return | ★★★ |
| 21 | مراتب اور مجامع | *Marātib wa-Majāmiʿ* — Ranks and Convergences (of Spiritual Hierarchy) | ★★★ |

### Binder 5 — منتخب اشعار → **"Selected Devotional Poetry"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 12 | نوحا اور مرسیۃ امام حسین | Elegies and Marsiya for Imam Husayn | ★★★ |
| 13 | عربی کے اشعار | Arabic Poetic Compositions on the Ahl al-Bayt | ★★★ |
| 50 | مختلف مناقب | Manāqib (Praise Poems) for the Family of the Prophet | ★★★ |

### Binder 6 — علی ابن ابی طالب علیہ السلام → **"ʿAlī ibn Abī Ṭālib (Peace be upon him)"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 11 | مناقب | *Manāqib ʿAlī* — Praise Poems for Imam ʿAlī | ★★★ |
| 16 | نہج البلاغۃ کے خطبے | Sermons from *Nahj al-Balāgha* | ★★★ |
| 37 | لو کشف الغطا ما الزدت یقینا | *"Were the veil lifted, my certainty would not increase"* — Sayings on ʿAlī's Certitude | ★★★ |
| 46 | مولانا علی کی فضائل | *Faḍāʾil Mawlānā ʿAlī* — Virtues of Mawlānā ʿAlī | ★★★ |
| 47 | علی کے خطوط | *Rasāʾil ʿAlī* — Letters of Imam ʿAlī | ★★★ |
| 48 | علی کے مخلافین | Refutations of ʿAlī's Opponents | ★★★ |
| 51 | سلونی قبل ان تفقدونی | *"Ask me before you lose me"* — ʿAlī's Responses to Questions | ★★★ |
| 141 | خطبہ کمیل کا تجزیہ | Analysis of the *Khuṭba* to Kumayl ibn Ziyād | ★★★ |
| 144 | نہج البلاغۃ فی العربیۃ | *Nahj al-Balāgha* — Arabic Original | ★★★ |

### Binder 8 — کلمات ربانی کی تاویلات → **"Taʾwīl (Esoteric Exegesis) of the Divine Words"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 9 | احادیث نبوی علیہ السلام کی تاویل | *Taʾwīl al-Aḥādīth al-Nabawiyya* — Esoteric Exegesis of Prophetic Traditions | ★★★ |
| 18 | قرآنی آیات کی تاویل | *Taʾwīl āyāt al-Qurʾān* — Esoteric Exegesis of Qurʾānic Verses | ★★★ |
| 22 | قرآنی سوروں کی تاویل | *Taʾwīl al-Suwar* — Esoteric Exegesis of Selected Surahs (al-Nās, al-Takāthur, al-Tīn, al-Nāziʿāt, al-Qadr) | ★★★ |
| 23 | سورۃ الفاتحۃ کی تاویل | *Taʾwīl Sūrat al-Fātiḥa* — Esoteric Exegesis of Surat al-Fātiḥa | ★★★ |
| 24 | بسم اللہ الرحمن الرحیم کی تاویل | *Taʾwīl al-Basmala* — Esoteric Exegesis of *Bismillāh al-Raḥmān al-Raḥīm* | ★★★ |
| 25 | اعراب اور مقطعات کی تاویل و حقائق | *Taʾwīl al-Iʿrāb wa-l-Muqaṭṭaʿāt* — Esoteric Exegesis of Vowel Marks and the Disconnected Letters | ★★★ |
| 85 | سورۃ الأخلاص کی تاویل | *Taʾwīl Sūrat al-Ikhlāṣ* — Esoteric Exegesis of Surat al-Ikhlāṣ | ★★★ |
| 132 | قرآن الکریم و الفرقان الحمید | The Noble Qurʾān and the Praiseworthy Discriminator | ★★★ |

### Binder 12 — دعات اور مناصیب کی سیرت و واقعات → **"Lives and Episodes of the Duʿāt and Their Ranks"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 36 | حدود کبار | *Ḥudūd Kibār* — The Greater Hierarchs (Mālik al-Ashtar, Uways al-Qaranī, Sayyidnā al-Muʾayyad al-Shīrāzī, Karbalāʾ martyrs) | ★★★ |
| 138 | سیرت المناصیب | *Sīrat al-Manāṣib* — Biography of the Officeholders | ★★ |
| 143 | شخصیات | Personalities (incl. Nānā Mullā Shafqat Ḥusayn) | ★★ |

### Binder 16 — منتخب دعاؤں کا مجموعۃ → **"A Collection of Selected Supplications (Duʿāʾ)"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 41 | دعا و مناجات | *Duʿāʾ wa-Munājāt* — Supplications and Intimate Discourse | ★★★ |
| 42 | فجر کے بعد کی دعائیں | Duʿāʾs Recited After Fajr | ★★★ |
| 44 | روزانہ کی دس دعائیں | Ten Daily Duʿāʾs (organized by weekday) | ★★★ |

### Binder 18 — قرآنی قصص الانبیا کے حقائق → **"Inner Realities of the Qurʾānic Prophet Stories"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 52 | حضرت آدم علیہ السلام | The Story of Ādam, Peace Be Upon Him | ★★★ |
| 131 | نطقا کا بیان | *Nuṭaqāʾ* — The Speaker-Prophets (Discourse on Their Function) | ★★★ |
| 137 | حضرت عیسی علیہ السلام | The Story of ʿĪsā (Jesus), and His Parallel with Mawlānā ʿAlī | ★★★ |
| 147 | ظاہری واقعات | Outer Events (sparse) | ★ |
| 168 | حضرت نوح علیہ السلام | The Story of Nūḥ (Noah), Peace Be Upon Him | ★★★ |

### Binder 19 — دعائم الاسلام : ولایت → **"Daʿāʾim al-Islām: Wilāya (The Authority)"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 10 | احکامات شریعت کی تاویل | *Taʾwīl Aḥkām al-Sharīʿa* — Esoteric Exegesis of Sharīʿa Rulings | ★★★ |
| 54 | ولایت اہل بیت | *Wilāyat Ahl al-Bayt* — The Authority of the Prophet's Family | ★★★ |
| 64 | امام کی واجبیت اور فضائل | *Wujūb al-Imāma wa-Faḍāʾiluhā* — The Necessity and Virtues of the Imāmate | ★★★ |
| 71 | اسلام اور ایمان ★ DUPE w/ b24 ★ | *Al-Islām wa-l-Īmān* — Islam and Faith (primary chapter — see A.3.1) | ★★★ |
| 86 | دعائم الاسلام کے معنی | Meaning of *Daʿāʾim al-Islām* | ★★★ |
| 122 | ولایت کی اہمیت اور اوصاف | Importance and Attributes of Wilāya | ★★★ |
| 123 | ایمان کی خصلتیں | *Khiṣāl al-Īmān* — The Traits of Faith (sincerity, taqwā, ṣabr, tawakkul, zuhd) | ★★★ |

### Binder 23 — منتخب علمی مضامین → **"Selected Scholarly Treatises"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 38 | کتاب مصباح الشریعۃ | *Miṣbāḥ al-Sharīʿa* — The Lamp of the Sharia (attributed to Imam Jaʿfar al-Ṣādiq) | ★★★ |
| 55 | کتاب حکایات بنی اسرائیل | Stories of the Bānū Isrāʾīl (moral parables) | ★★★ |
| 59 | رسالۃ الماھیۃ اللذۃ و الالم | *Risāla fī Māhiyyat al-Ladhdha wa-l-Alam* — Treatise on the Nature of Pleasure and Pain | ★★★ |
| 60 | رسالۃ حکمت الموت | *Risāla fī Ḥikmat al-Mawt* — Treatise on the Wisdom of Death | ★★★ |
| 63 | ضروری معلومات | Essential Knowledge (ʿIlm al-ʿAdad and the Beautiful Names) | ★★ |
| 69 | ظاھر و باطن کا ازدواج | *Izdiwāj al-Ẓāhir wa-l-Bāṭin* — The Marriage of Outer and Inner | ★★★ |
| 70 | عقل اور علم | *Al-ʿAql wa-l-ʿIlm* — Intellect and Knowledge | ★★★ |
| 72 | قضا قدر اور قصاص | *Qaḍāʾ, Qadar, wa-Qiṣāṣ* — Divine Decree, Determination, and Just Retribution | ★★★ |
| 83 | مستفید کے خواص | Attributes of the *Mustafīd* (the Truth-Seeker) | ★★★ |
| 87 | کتاب العالم والغلام | *Kitāb al-ʿĀlim wa-l-Ghulām* — The Book of the Master and the Disciple (attributed to Jaʿfar ibn Manṣūr al-Yaman) | ★★★ |
| 148 | مفاتیح الحکمۃ | *Mafātīḥ al-Ḥikma* — Keys of Wisdom (animal parables) | ★★★ |

### Binder 24 — توحید مبدع تعالی → **"Tawḥīd of the Originator (al-Mubdiʿ Taʿālā)"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 1 | وجود مبدع کی حقانیت | The Reality of the Originator's Existence | ★★★ |
| 2 | کلمۃ التوحید کی معرفت | Recognition of the Word of Unity (*lā ilāha illā Allāh*) | ★★★ |
| 67 | کلمۃ التوحید کی ۲۸ نشانیاں | The 28 Signs of the Kalima of Unity | ★★★ |
| 71 | اسلام اور ایمان ★ DUPE w/ b19 ★ | *Al-Islām wa-l-Īmān* — Islam and Faith (cross-reference — see A.3.1) | ★★★ |
| 118 | کلمہ التوحید کے مختلف ابواب | The Various Chapters of the Kalima of Unity (5 abwāb) | ★★★ |
| 121 | توحید کا تصور | The Concept of *Tawḥīd* | ★★★ |
| 130 | توحید فی النہج البلاغۃ | *Tawḥīd* in *Nahj al-Balāgha* | ★★★ |

### Binder 25 — دعائم الاسلام : طہارت → **"Daʿāʾim al-Islām: Ṭahāra (Purity)"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 88 | طہارت سے متعلق روایتیں | Traditions on Ṭahāra | ★★★ |
| 89 | طہارت کا بیان | Discourse on Ṭahāra (with the 7 obligatory and 12 sunna acts of wuḍūʾ) | ★★★ |
| 90 | نجاست سے طہارت | Purification from *Najāsa* (Impurity) | ★★★ |
| 91 | ارکان وضو کے باطنی معنی | The Inner Meaning of the Pillars of Wuḍūʾ | ★★★ |
| 92 | غسل کا بیان | Discourse on Ghusl (ritual bathing) | ★★★ |

### Binder 26 — دعائم الاسلام : صلواۃ → **"Daʿāʾim al-Islām: Ṣalāt (Prayer)"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 93 | نماز سے متعلق احادیث | Aḥādīth on Ṣalāt | ★★★ |
| 94 | نماز کا بیان | Discourse on Ṣalāt | ★★★ |
| 95 | مساجد کا بیان | Discourse on Masājid (Mosques) | ★★★ |
| 96 | نماز کے اوقات | The Times of Ṣalāt | ★★★ |
| 97 | اذآن و اقامت | *Adhān* and *Iqāma* | ★★★ |
| 98 | نماز کی رکعات کے ممثولات | *Mamthūlāt* of the *Rakaʿāt* — Inner Symbolism of the Prayer Cycles | ★★★ |
| 99 | ارکان نماز کے ممثولات | *Mamthūlāt* of the Pillars of Ṣalāt | ★★★ |
| 100 | مبارک ایام کی نمازیں | Prayers for Blessed Days (Niṣf al-Shaʿbān, Rajab) | ★★★ |

### Binder 27 — آداب و اخلاق حسنہ → **"*Ādāb* and Noble Character (*Akhlāq Ḥasana*)"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 14 | آداب کے متعلق اقوال | Sayings on *Ādāb* | ★★★ |
| 17 | ولایت سے متعلق مضامین | Treatises Related to *Wilāya* | ★★★ |
| 56 | کتاب وصایا ابلیس | *Kitāb Waṣāyā Iblīs* — The Book of Iblīs's Counsels (cautionary text) | ★★★ |
| 127 | اقوال الحکمۃ | *Aqwāl al-Ḥikma* — Sayings of Wisdom (Ahl al-Bayt, ʿAlī, etc.) | ★★★ |
| 128 | ضرب الحکم | *Ḍarb al-Ḥikam* — Sayings of Maxim | ★★★ |
| 140 | سیرت نبی علیہ السلام | Episodes from the *Sīra* of the Prophet | ★★★ |

### Binder 28 — مسودے → **"Drafts and Misc. Compilations" (compiler's own working drafts)**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 115 | [مسودۃ] مسودے | *Musawwadāt* — Compiler's Working Drafts | ★★ |
| 117 | دیگر تاویلات و حقائق | Additional *Taʾwīlāt* and Realities | ★★ |
| 119 | مبدا و معاد | *Mabdaʾ wa-Maʿād* — Origin and Return (Notes) | ★★★ |
| 124 | دعائم الاسلام - صوم | *Daʿāʾim al-Islām*: Ṣawm (notes) | ★★★ |
| 126 | دعائم الاسلام - نماز | *Daʿāʾim al-Islām*: Ṣalāt (notes) | ★★★ |
| 145 | Initial 12 Sessions | The Initial 12 Sessions (Foundational Bayāns) | ★★ |
| 149 | sunday sessions | Sunday Sessions (assorted bayāns, 2014–2015) | ★★ |
| 150 | Sunday Sessions - breakups | Sunday Sessions — Topical Breakdowns | ★★ |
| 161 | ملا اسحاق ضیائی مضامین | Treatises by Mullā Isḥāq Ḍiyāʾī | ★★★ |
| 172 | دعائم | The Five Foundations (*Arkān*) of Islam | ★★★ |

### Binder 29 — دعائم الاسلام : الصوم → **"Daʿāʾim al-Islām: Ṣawm (Fasting)"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 133 | صوم | Discourse on *Ṣawm* | ★★★ |
| 134 | الکواکب الدریۃ | *Al-Kawākib al-Durriyya* — The Pearl-Like Planets (Ramaḍān treatise) | ★★★ |
| 135 | لیالی الفاضلۃ | *Layālī al-Fāḍila* — The Excellent Nights (of Ramaḍān) | ★★★ |
| 136 | صلوۃ العیدین | The Two ʿĪd Prayers | ★★★ |

### Binder 32 — غزالی - کیمیائی السعادۃ → **"Al-Ghazālī — *Kīmiyāʾ al-Saʿāda* (Alchemy of Happiness)"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 139 | Disciplining The Soul | Disciplining the Soul (from al-Ghazālī's *Iḥyāʾ*) | ★★★ |
| 146 | Controlling Lust For Food and Sex | Controlling Appetite — Food and Lust | ★★★ |

### Binder 34 — Quranic Studies → **"Qurʾānic Studies"** *(English-source binder)*

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 153 | أعجاز القرآن | *Iʿjāz al-Qurʾān* — The Inimitability of the Qurʾān | ★★★ |
| 154 | عقل | *Al-ʿAql* — Intellect (with the Restraint/Ramaḍān thread) | ★★★ |
| 155 | مسودہ | Draft Notes (Quotes, Definitions, Aḥādīth) | ★★ |
| 156 | سلام علی رسول اللہ و آلہ ★ shares 4 topics w/ b36/c174 ★ | Salutations on the Prophet and His Family | ★★★ |
| 157 | آغاز اور مقاصد | Introduction and Purpose of Sessions | ★★★ |
| 158 | سورۃ الفاتحۃ | Sūrat al-Fātiḥa (draft + analysis) | ★★★ |
| 159 | Misconceptions Arguments | Common Misconceptions Addressed | ★★★ |
| 160 | دین اور سائنس | Religion and Science | ★★★ |
| 162 | استعاذۃ | *Istiʿādha* — Seeking Refuge (Sūrat al-Falaq and al-Nās) | ★★★ |
| 163 | بسم اللہ الرحمن الرحیم | *Bismillāh al-Raḥmān al-Raḥīm* — The Basmala | ★★★ |
| 164 | الحمد للہ رب العلمین | *Al-Ḥamdu lillāhi Rabb al-ʿĀlamīn* — Praise be to the Lord of the Worlds | ★★★ |
| 165 | مالک یوم الدین | *Mālik Yawm al-Dīn* — Master of the Day of Judgment | ★★★ |
| 166 | ایاک نعبد و الصراط | *Iyyāka Naʿbudu* and *al-Ṣirāṭ* — Worship and the Straight Path | ★★★ |
| 167 | الرحمن الرحیم | *Al-Raḥmān al-Raḥīm* — The Merciful, The Compassionate | ★★★ |

### Binder 35 — The Wise Reminder → **"The Wise Reminder"** *(English-source binder)*

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 176 | Miracles of Quran | Miracles of the Qurʾān | ★★★ |
| 177 | The Human Spirit | The Human Spirit (Rūḥ, Qalb, ʿAql, Nafs) | ★★★ |

### Binder 36 — ISLAM IMAN IHSAN → **"Islām, Īmān, Iḥsān"**

| Ch | Source name | Proposed English title | Conf |
|---|---|---|---|
| 173 | Introduction | Introduction — Ādāb and the Ten Foundations | ★★★ |
| 174 | SALAAMS ★ shares topics w/ b34/c156 ★ | Salutations on the Prophet | ★★★ |
| 175 | ISLAM | The Three Levels: Islām, Īmān, Iḥsān (full discourse) | ★★★ |

---

## Part C — Cross-reference map

Once Part B is approved, this map will be machine-readable at `tools/content_classifier/data/kashkole-r1-decisions.yaml`. Format:

```yaml
chapter_retitles:
  - bid: 1
    cid: 73
    new_title: "Tashkīl al-ʿĀlam al-Rūḥānī — The Forming of the Spiritual World"
  ...
dedup_clusters:
  - kind: chapter_dupe
    cluster_id: A.3.1
    primary: { bid: 19, cid: 71 }
    cross_refs: [ { bid: 24, cid: 71, action: soft_link } ]
  - kind: topic_dupe
    cluster_id: A.3.3.1
    primary: { bid: 19, cid: 122, tid: 821 }
    cross_refs: [ { bid: 6, cid: 46, tid: 821, action: cross_ref } ]
  ...
binder_retitles:
  - bid: 1
    new_title: "Sciences of Origin and Return"
  ...
```

The translation/adaptation pipeline will read this YAML at intake and emit English chapter titles + cross-reference stubs in the appropriate places. No bundle modification, no SQL modification.

---

## Approval index

Use the checkboxes below to signal which findings to adopt. Anything unchecked stays as proposed in this Round 1 draft.

- [ ] Part A.1 — 35 exact-byte image dupe clusters → adopt (already mechanical)
- [ ] Part A.2 — 55 perceptual near image dupes → adopt with spot-check policy
- [ ] Part A.3.1 — chapter 71 primary=b19 (Wilāya); b24 cross-ref
- [ ] Part A.3.2 — chapters 156/174 stay independent with cross-refs
- [ ] Part A.3.3 — primary/cross-ref assignments for the 7 single-topic dupes
- [ ] Part B — adopt the 122 chapter title proposals (mark exceptions in-line above)
- [ ] Part B-binders — adopt the 19 binder title proposals

After approval, Round 2 will retitle the 1,337 topics (one approval block per binder) and produce the machine-readable `kashkole-r1-decisions.yaml`.
