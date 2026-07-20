# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-20 17:20 EST (book_challenger_version 1.0)
**Scope:** whole-book
**Content profile:** islamic_scholarly
**Route:** augmented companion (`series-config.yaml` carries no `deliverable_mode`; `book_augmentation: source_only`, `book_voice: faithful`). `_system/translation-edition-manifest.json` records `mode: translation_edition, augmentation: forbidden`, so the stricter faithfulness posture was applied everywhere outside the two labelled editorial notes.
**Declared narrative_frame:** `transmitted_report` (third person outside direct discourse)
**Chapters reviewed:** 8 + preface
**Iterations:** 3 (of 5 max)
**Verdict (book-level):** SHIP-READY

> This run SUPERSEDES the 16:05 EST report. Every check was re-derived from `book.md` at
> commit 370e0d6 (working tree clean), the OCR scan, `fts_quran` in
> `content/knowledge-base/mirror.db`, and `book/_chunks/translation/`. No line number,
> count, or verdict was carried over; the file was re-read from the top.

---

## The two adversarial questions

### 1. The merged chapter-7 passage — verified against the scan as if unseen

Read clause by clause against `raw-extract.md` 1146-1165 (sections 300, 301, 302), without reference
to either original telling. **The merge introduces nothing the scan does not support and drops
nothing either telling carried.**

| Arabic (raw-extract.md) | book.md | Verdict |
|---|---|---|
| 1146 `ثم قاما فصافحا وتعانقا، وودّع كل واحد منهما صاحبه` | 815 "Then the two rose, clasped hands, and embraced, each bidding the other farewell" | ✓ |
| 1147 `وهو لا يملك نفسه من العبرة ولا يستطيع الكلام إلا بالإشارة. ثم افترقا` | 815 "unable to hold back his tears and unable to speak except by a sign. Then they parted." | ✓ the weeping survives |
| 1148 `فخرج العالم والغلام يسيران حتى إذا قربا مدينة الغلام التي فيها أبوه` | 815 "The Master and the boy set out and traveled on until they drew near the boy's own city, where his father was." | ✓ |
| 1149-1150 `قد عرفتُ وصيّة الشيخ، ولا تعرف؛ الرشد إلا في قوله` | 817 "I have grasped the counsel of the Shaykh, and you have not yet grasped it. There is no right guidance except in his words." | ✓ `ولا تعرف` survives |
| 1150-1152 `وهذه مدينتك قد وصلنا بدءها، فاجلس بنا في معزل عن الطريق، فإني أريد أن أذكرك بعض أمري وأوصيك بما تعمل عليه` | 817 "This is your city… Sit with me here, apart from the road… remind you of something of my own affair and to counsel you in what you should act upon." | ✓ |
| 1153-1154 `قد علمت حال أبيك وعداوته لأهل هذا الشأن` | 819 "I know your father's state and his enmity toward the people of this way" | ✓ first-person reading; the scan is unvowelled and both readings are open — see BK-A3 note below |
| 1154-1155 `وقد رادف عليه ذلك خروجك معي وغيبتك عنه بغير إذنه ولا أمنه` | 819 "have come one upon another to weigh on him" | ✓ `رادف` rendered |
| 1155-1156 `وأنا أريد أن أنفذ رأي والدي بالاستتار في بعض هذه البادية وترجع أنت إلى أبيك` | 819 "carry out my own father's counsel and keep hidden somewhere in this open country, while you go back to your father" | ✓ the reading the discarded telling got wrong |
| 1156 `فتطيّب نفسه ويسكن عنا بأسه` | 819 "his soul may be set at ease and his anger toward us may subside" | ✓ the anger survives |
| 1156-1157 `وأنا أرجو - إن لطفت به - أن يكون أقرب لما تريد من غيره` | 819 "if you are gentle with him, that he will be nearer than any other to what you desire" | ✓ |
| 1157-1158 `فقد راعته الغيبة وأجزعه الإنفراد` | 819 "the absence has alarmed him and the loneliness has distressed him" | ✓ |
| 1158+1161 `واعلم، يا بنيّ، أن الله قد فتح لك بأهون سعيك ما لم أظن أنك بالغه إلا بعد مدّة` | 819 "God has opened for you, by the lightest of your striving, what I did not think you would attain except after a long while" | ✓ **restored and corrected** |
| 1161-1162 `وقد أحسن الله إليك، فأحسن إلى نفسك، وأكرم من أكرمك الله به` | 819 "God has been good to you, so be good to yourself, and honor the one through whom God has honored you" | ✓ **restored, was in neither telling** |
| 1162 `فقد حسن ظننا بك وعظم رجاؤنا فيك` | 819 "for our opinion of you has been good and our hope in you great" | ✓ **restored, was in neither telling** |
| 1162-1163 `وعليك بحفظ أمانتك التي أوصاك بها والدك والتثبت في أمرك` | 819 "guard the trust your father laid upon you, and stand firm in your affair" | ✓ |
| 1163-1164 `والتقوى والتقية ملاك دينك وعملك، والشكر والصبر زيادة في نورك` | 819 "Piety and God-wary discretion are the twin guardians… thanksgiving and patience are an increase to your light" | ✓ `تقية` kept as discretion |
| 1164-1165 `واستفتح من الله موادّك وحسن توفيقه لك` | 819 "May Allah unlock your provision and grant you the goodness of His guidance" | mood shift — see BK5 |

**Mechanical corroboration.** A vocabulary diff of the merged three paragraphs against the six they
replaced returns exactly thirteen new words — `after, attain, been, did, good, great, honored,
opinion, our, think, through, whom, would, yourself` — every one of them belonging to the three
restored/corrected clauses. Nothing else was introduced. The forty-one words that fall away all
belong to discarded duplicate phrasings (`gesture`, `weight`, `separate`, `ways`, `veiled`,
`quieted`, `worn`, `fright`, `none`…), and each maps to an Arabic clause the merged text carries
under the more faithful wording. Chapter 7 fell from 7,304 to 7,090 words against a 6,771-word
source span — ratio 1.05, in line with every other chapter.

### 2. The 93-tag punctuation sweep — no collateral damage

Every changed line between `e58f187` and `370e0d6` was classified mechanically. **92 lines differ by
exactly one character** — the head-tag comma becoming a colon, with the comma count dropping by
exactly one and nothing else touched. The 93rd is line 51 (`He answered, "` → `He answered: "`), the
same transformation on a synonym tag. The remaining 21 changed lines are all named repairs (the
merge, the vowelling, the two renamings, the chapter-5 quotation marks, the three attributions, the
chapter-8 father, the chapter-2 sermon quote). Nothing unexplained.

Specifically checked and clean:

| Risk | Result |
|---|---|
| An inverted tag converted | none — zero lines match `"…," X said: "`; the 79 inverted tags are byte-identical to before |
| A nested/embedded quotation broken | 53 lines carry three or more quote marks, before and after — unchanged. The sweep correctly left `so that it be said, "this is like God,"` (396) and `or, "this is like the argument."` (404) alone |
| A mid-sentence tag converted | correctly left alone — `and said, "O Allah, open the hearing…` (991) keeps its comma, which is right after a narrative clause |
| Something that was not a speech tag | none |
| Head tags missed | **2** — `Salih said to him, "` at 999 and 1015, against 35 occurrences of `Salih said to him: "`. Trivial residue, filed as BK3 (P2) |

**On the inverted tags: your reasoning holds and I accept it.** Converting `"Yes," Abu Malik said.`
into `Abu Malik said: "Yes."` rewrites the sentence rather than repunctuating it, the inverted form
is correct English, and it is used consistently within its stretch. I am downgrading that half of the
old BK3 from P1 to **P2 advisory** — recorded below as BK2, because the split still correlates
exactly with a window boundary rather than with anything in the text, which is what made me raise it.
It no longer blocks or cautions anything.

### 3. Duplicate sweep — re-run independently, confirmed

`_system/book-duplication-check.json` reports `findings: []`. I did not take that on trust. An
all-pairs comparison of every prose paragraph within each chapter at any distance (not the
deterministic check's consecutive-twin window) returns **one** pair above 0.55 similarity, and a
repeated-12-word-sequence sweep across the whole book returns **two** line pairs. All three are
legitimate:

| Lines | Similarity | Why it is not a duplication |
|---|---|---|
| 567 / 571 | 0.80 | The source's own chiastic pair — "one who knows the inward but not the outward" against "one who knows the outward but not the inward". Opposite content, both in the source |
| 617 / 623 | 12-gram | The boy asks "the people of this world are ranked in classes within their world" and the Master opens his answer by repeating it — the source's own echo |
| 316 / 320 | 12-gram | The deliberate parallel questions, poverty→ease and ignorance→knowledge, both in the source |

The twice-told farewell is gone and nothing replaced it.

---

## Per-chapter verdicts

| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Preface — How to Read a Conversation Made of Doors | pass | pass | SHIP-READY (P2 only) |
| 1. The Persian Who Was Dead and Revived | pass | pass | SHIP-READY |
| 2. A Stranger in the City | pass | pass | SHIP-READY (P2 only) |
| 3. The Boy at the Door — Limits and Conditions | pass | pass | SHIP-READY (P2 only) |
| 4. How the World Was Made | pass | pass | SHIP-READY |
| 5. The World, the Hereafter, and the Speech of Parables | pass | pass | SHIP-READY |
| 6. Three Layers of Knowledge | pass | pass | SHIP-READY |
| 7. The Five Shares and the Long Road to the Shaykh | pass | pass | SHIP-READY (P2 only) |
| 8. Homecoming, the Father, and the Debate with Abu Malik | pass | pass | SHIP-READY (P2 only) |

## Whole-book passes

| Check | Result |
|---|---|
| BK-P1 no-teaching-lost | **pass** — the two omitted §302 sentences are restored; ratios 0.98-1.25; proper-noun diff resolves entirely to rendering choices already adjudicated against the scan |
| BK-P2 verbatim-quote survival | pass — retention findings empty in all 9 sections; every Arabic display run carries an English gloss within 4 lines |
| BK-P3 Arabic-script accuracy | **pass, 0 unverified** — 52 run objects, 50 distinct skeletons, all resolved. The chapter-6 verse now resolves `canonical-mushaf` |
| BK-P4 faithfulness-against-addition | pass — the chapter-7 duplicate is gone; the two editorial notes remain accurate and source-grounded |
| BK-P5 voice fidelity | pass — no chapter opens by announcing narration; no meta-commentary |
| BK-P6 prose craft | pass — zero hits on the scaffolding phrase set |
| BK-P7 duplicated passage | **pass** — confirmed independently, above |
| BK-A1 voice consistency | pass with advisory — head tags now uniform (429 colon / 2 comma); residual dialogue-typography split filed P2 |
| BK-A2 segmentation sanity | pass — source 8-1353 contiguous, headings match `book-toc.json` |
| BK-A3 preface + TOC integrity | pass on TOC, **open P2** on the preface (deferred to Asif by design) |
| BK-A4 plain transliteration | pass — zero scholarly diacritics in Latin text; one spelling variant filed P2 |
| BK-A5 tradition fit | pass — 13 `doctrine:wisdom:*` atoms + `etymology:shr`, Ismaili corpus, Ismaili source |
| BK-N1 narrative person | pass |
| BK-N2 speech attribution integrity | pass — the three narratorial verdicts are plain attribution again; deterministic check clean |
| BK-N3 frame consistency | pass — one transmitted narrator; `The narrator said` ×4, the source's own colophon at 1385 |
| BK-N4 Arabic script retention | pass |
| BK-N5 supplied diacritics | **pass** — the chapter-2 run matches the specified bare form byte for byte; every remaining vowelled run is either canonical Qur'an or carries the scan's own marks (`عبثاً`, `الذرّة`, `تثبّت`) |
| BK-N6 enumeration preserved | pass |
| BK-N7 register + terminological consistency | pass — `Shaykh` names exactly one man in 22 of 22 occurrences, `the greater Master` ×2, `the master of the house` for the host, zero `the scholar` as a character |
| Seam integrity ch7 / ch8 | pass — chapter 7 now joins cleanly; chapter 8's four joins re-verified non-overlapping |

### Repairs confirmed at their own sites

| Item | Verified how |
|---|---|
| Chapter-2 vowelling | `book.md:89` is byte-identical to the specified after-form: `فتبارك` bare, Q 25:62 core vowelled, the nine-word doxology bare with the scan's own `نذيراً` |
| Chapter-7 merge | clause table above; six paragraphs became three |
| Head-tag sweep | 92 single-character changes + 1 synonym; 2 missed |
| Naming | `the greater scholar` 0, `the greater Master` 2, `the master of the house` 2, `Shaykh` 22 all one referent, `sheikh`/`Shaykh` collision gone from chapter 8 |
| Chapter-5 exchange | 316-322: each question closes at its question mark, each reply quoted in its own right |
| Chapter-8 attributions | `pressed the point`, `conceded the ground`, `Salih pressed` — zero occurrences |
| Chapter-8 father | `said his father` / `His father said` / `His father's heart`; no `Shaykh` anywhere in chapter 8 |
| Mushaf discriminator | audit `unverified` 1 → 0; the `arabic_runs` total moving 30 → 29 is the totals field excluding `canonical-mushaf` by design, not a lost run — all 52 run objects and 50 skeletons are identical before and after |
| Chapter-2 sermon quote | 85 opens, 87 re-opens and closes — the book's own multi-paragraph convention, matching 140/142, 1251/1253 and 1359/1361 |

---

## Findings (P2 only — none affect the verdict)

### BK1 · BK-A3 · P2 · VERIFIED
- **Chapter:** preface — How to Read a Conversation Made of Doors
- **book.md:** 5 — `We have been informed that some groups among the believers, and a number of the preachers of religion, came to a Master among them…`
- **Why it fails:** the preface is a translation of the source's own §1-3 rather than an orientation; it never tells a modern reader who Ja'far b. Mansur al-Yaman was, who the speakers are, or why the text still matters. Carried forward unchanged and correctly deferred — authoring a real preface and demoting the translated opening is a structural decision about the edition, not a defect repair.
- **Worker action:** none. Asif's call.

### BK2 · BK-A1 · P2 · VERIFIED (downgraded from P1)
- **Chapter:** 8 — Homecoming, the Father, and the Debate with Abu Malik
- **book.md:** 1343 — `"You have spoken the truth, O Abu Malik," said Salih.` against 819 — `The Master said: "…"`
- **Why it fails:** 71 of the book's 79 quote-first inverted tags sit in chapter 8, clustered at lines 1250-1390, where chapters 1-7 have eight between them. In the same stretch a speech interrupted by a display block re-opens with a quotation mark (1347, 1353, 1359), where chapters 5, 6 and 7 resume unquoted (300, 605, 627). Both are legitimate English conventions; the concern is only that the boundary falls exactly on a compose-window seam rather than on anything in the text.
- **Worker action:** none required. If a future pass unifies it, unify the display-block resumption rule first — that one is invisible to a reader mid-sentence and cheap to normalise; the inverted tags are not worth rewriting sentences for.

### BK3 · BK-A1 · P2 · VERIFIED
- **Chapter:** 8 — Homecoming, the Father, and the Debate with Abu Malik
- **book.md:** 999 — `Salih said to him, "So you come to me accusing, O Ka'b al-Ahbar…"` and 1015 — `Salih said to him, "To know its faces…"`
- **Why it fails:** two paragraph-opening head tags the sweep did not reach, against 35 occurrences of `Salih said to him: "` elsewhere.
- **Worker action:** two commas to colons.

### BK4 · BK-N7 · P2 · VERIFIED
- **Chapter:** 3 — The Boy at the Door
- **book.md:** 112 — `The boy had a father who was a great sheikh of the Arabs`
- **Source:** `refined-english.md` — the same word `شيخ` the book sets as *Shaykh* 22 times elsewhere
- **Why it fails:** one Arabic word, two Latin spellings — `sheikh` once, `Shaykh` twenty-two times.
- **Worker action:** `sheikh` → `shaykh`.

### BK5 · BK-N7 · P2 · VERIFIED
- **Chapter:** 7 — The Five Shares and the Long Road to the Shaykh
- **book.md:** 819 — `May Allah unlock your provision and grant you the goodness of His guidance.`
- **Source:** `raw-extract.md` 1164-1165 — `واستفتح من الله موادّك وحسن توفيقه لك`
- **Why it fails:** `استفتح` is an imperative addressed to the boy — "and seek from God the opening of your provisions" — rendered here as the Master's prayer, which moves the agency from the disciple to the speaker at the close of the charge. Separately `توفيق` is "His guidance" here where line 807 renders the same word "His enabling grace". Both are inherited from `_chunks/translation/bk-07-part-03.md` and from `refined-english.md` §302; **neither was introduced by the merge** — this clause came across unchanged from the surviving telling. Raised because the merged paragraph was the object of this review, not because the merge did it.
- **Worker action:** optional — "and seek from God the opening of your provisions and the goodness of His enabling grace".

---

## Verified vs Inferred summary

| | Count |
|---|---|
| VERIFIED (concrete evidence in the files) | 5 |
| INFERRED (heuristic judgment) | 0 |

## Ledger emission summary

5 records appended to `_learning/findings.jsonl` with `source: "book-challenger"`, ids BK1-BK5,
all severity P2, all `resolution: "flagged"`, deduped within the run by signature.

## Verdict

**SHIP-READY.** Zero P0, zero P1. All three blockers from the previous run are closed at their own
sites and re-verified against the scan rather than against the commit message: the chapter-2 doxology
is bare where the scan is bare and vowelled only where the Qur'an is, the chapter-7 scene is told
once, and the two sentences that were in neither telling are back in the book at their source
position. The five remaining items are advisory — one deferred preface decision, two typographic
residues, one spelling variant, and one inherited mood shift in a single clause. None of them touches
fidelity, doctrine, Arabic, or narrative frame, and none blocks publication.
