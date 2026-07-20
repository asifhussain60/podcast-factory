# Book Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-07-20 18:05 EST (book_challenger_version 1.0)
**Scope:** whole-book, with an adversarial audit of the authored front matter
**Content profile:** islamic_scholarly
**Route:** augmented companion (`book_augmentation: source_only`, `book_voice: faithful`); translation-edition manifest forbids outside augmentation, so apparatus is judged on whether its CLAIMS are supported
**Declared narrative_frame:** `transmitted_report`
**Chapters reviewed:** 8 + front matter
**Iterations:** 4 (of 5 max)
**Verdict (book-level):** SHIP-WITH-CAUTION

> Supersedes the 17:20 EST report. Re-derived from `book.md` at commit 6c2e4d0, working tree clean.

---

## Scope correction — six chapter changes, not none

The brief said "nothing was reordered, nothing was cut, no chapter was touched." The diff from
`370e0d6` to `6c2e4d0` carries **seven hunks**, and six of them are outside the front matter. Four
are the P2 repairs from the last run, applied correctly and verified here. **Two are new authored
apparatus that the brief did not mention and that therefore arrived unreviewed.** They are audited
below with the introduction.

| book.md | Change | Status |
|---|---|---|
| 126 | `a great sheikh of the Arabs` → `a great chief of the Arabs` | prior BK4 — fixed; now matches the introduction verbatim |
| 250-252 | **new** `<!-- bridge:begin -->` aside in chapter 4 | **new apparatus — audited below** |
| 723-726 | **new** `<!-- bridge:begin -->` aside in chapter 7 | **new apparatus — audited below** |
| 841 | `May Allah unlock your provision…His guidance` → `And seek from Allah the opening of your provisions, and the goodness of His enabling grace toward you` | prior BK5 — fixed; the imperative and `tawfiq` both restored |
| 1021, 1037 | `Salih said to him,` → `Salih said to him:` | prior BK3 — fixed; 37 of 37 now colon |

Nothing was reordered or cut. Chapter word counts move only by the two bridges (ch4 +37, ch7 +54).

---

## The six claims, checked against the files

### 1. Attribution and tradition — SUPPORTED, and better sourced than the brief claims

`refined-english.md:3` is not the primary evidence; the scan is. `raw-extract.md:5` (page 1) carries
`تأليف ١ سيدنا جعفر بن منصور ٢ اليمن٣` — "authored by our master Ja'far ibn Mansur al-Yaman", printed
on the manuscript's own first page above the basmala. The introduction's careful wording, "that the
manuscript itself attributes to", is exactly right and is confirmed at the scan, not merely at the
refined text. `meta.yml doctrinal_context` gives `school: Ismaili (Fatimid-era daʿwa tradition)`,
which is what "belongs to the Ismaili da'wa tradition of the Fatimid period" asserts — no more.
**Not overstated.**

One observation, not a finding: `كتاب العالم والغلام` is glossed "The Book of the Master and the Boy".
`al-ʿAlim` is literally the Learned One; "Master" is this edition's own rendering, adopted book-wide.
Internally consistent, and a reader who reads Arabic will see the choice rather than an error.

### 2. "Nobody narrates it in his own person" — SUPPORTED

Agrees with `narrative_frame: transmitted_report` and with this run's BK-N1 result (deterministic
clean on all nine sections). The scan opens `(١) بلغنا` — "it has reached us" — and the same formula
reintroduces the narrative at §3 (`raw-extract.md:25`). The book's last narratorial act, `The author
said` at 1407, is still a transmitter reporting a speaker, not a narrator speaking. **Accurate.**

### 3. The five figures — four fully supported, one not as worded

| Descriptor | Evidence | Verdict |
|---|---|---|
| Master: a Persian who came to knowledge late, after years of ignorance | 49 — "a man among the people of Persia… ignorance had gained the upper hand over him… for it had come upon him early, and he had grown up within it" | ✓ |
| …spends the rest of his life carrying it to others | 57-61 — "delivering this trust to those who come after me"; "he went out from his family and his wealth… summoning others" | ✓ |
| boy: youngest and most thoughtful of the company | 126 — "the youngest of them in years and the most thoughtful of them in mind" | ✓ near-verbatim |
| …follows him, is refused, and is admitted only on conditions | 126 "One of the company followed him"; 138 "I will not show you mercy by doing for you what your own effort ought to do"; 196 "it has limits… and conditions"; 220 "My conditions upon you are five" | ✓ fair compression |
| …his name, given much later, is Salih | named off-stage in ch7 (the Shaykh defers it, 797-813), stated at 887 "The boy's name was Salih" | ✓ |
| father: al-Bakhtari, a chief among the Arabs, honorable in lineage, hard against the people of religion | 126 — "a great chief of the Arabs, the most honorable of them in lineage and the harshest of them against the people of religion"; named 887 | ✓ verbatim |
| Shaykh: the greater teacher at the far end of the journey | 741-829 | ✓ |
| …**who tests him for seven days** | 797 "That must wait upon the completion of seven days"; 801 "For the dignity of the newborn" | **✗ see BK6** |
| Abu Malik: the scholar whom the grown Salih debates in the final chapter | 887 "a scholar of theirs named Abu Malik"; the debate is ch8 | ✓ |

### 4. The two Masters — SUPPORTED, and the Arabic supports it more firmly than the English does

This is the load-bearing claim and it holds. Three independent signals in the scan:

- §1 introduces the first teacher as `لعالم لهم` (`raw-extract.md:7`) — "to a scholar **of theirs**",
  definite, a teacher this community already has.
- §3 introduces the Persian as `أن رجلاً من أهل فارس` (`raw-extract.md:25`) — "that **a man** from the
  people of Persia", grammatically indefinite. A text does not re-introduce a character it has just
  been quoting as an unknown man.
- Both are governed by the transmitter's own `بلغنا`. §3 opens `وأما مذاهب الصالحين وآداب الطالبين
  فإنه بلغنا` — "as for the doctrines of the righteous and the manners of the seekers, **it has
  reached us**". So the narrative is not the first teacher's speech continuing; it is the transmitter
  resuming to answer the third thing the questioners asked for. Had it been his own continued speech
  the formula would be `بلغني`, not `بلغنا`.

"He answers once and is not heard from again" is also true — he does not recur after §2. **State it
as firmly as you have.** The source does not identify the two men, but it does everything short of
that to separate them, and the indefinite `رجلاً` is close to decisive.

### 5. The vocabulary paragraph — the doctrine is right, the framing is wrong

All four terms do appear with inline glosses: `the speaking Imam (al-Imam al-Natiq)` at 354,
`his summoners (du'at)` at 358, `the gate (bab)… his successor (wasi)` at 362.

"They name ranks in one structure" is **not an interpretation you should hesitate over — it is the
book's own statement**, and that is the problem. Line 288 (chapter 4): "Among them are the imams and
the speakers; among them are the arguments and the chiefs; and among them are the summoners to the
good… Their imam is like the great sun among the lights… The argument, the gate of their imam, is
like the shining moon… Their summoners are like the radiant stars." Line 290 adds the counts: twelve
chiefs to each speaker, twelve arguments to each imam, summoners under every argument. So the claim
"what it never says outright is that they belong together" is contradicted by the very chapter it
points at. See **BK2**. The rest of the paragraph stands.

### 6. The edition's self-description — one claim true, one incomplete, one false

| Claim | Verdict |
|---|---|
| "translates the whole of the source without abridgement" | **true** — ratios 0.98-1.25, TOC covers source 8-1353 contiguously |
| "keeps the Arabic where the source carries it with the English set beneath" | **incomplete** — true of what it keeps (all 29 display runs carry a gloss within four lines), but the edition also SUPPLIES Arabic the source does not print: seven Qur'anic verses whose Arabic has no counterpart anywhere in the scan (553, 563, 575, 621, 673, 1329, 1367) |
| "leaves a word unvowelled wherever the original scan leaves it unvowelled" | **false as a universal** — see BK1 |
| "The few editorial notes are fenced and labelled" | **false as of this commit** — see BK3 |

---

## The two new bridges

**Chapter 4, line 251** — *"Everything that follows to the end of this chapter is the Master's own
discourse to the boy, so the 'I' and 'we' in it are his and not the edition's."* The claim is
**accurate and useful**: chapter 4 carries first person at 270 ("Here we return"), 274 ("I do not
mean"), 290 and 296 ("I have described to you"), and every instance is the Master's. It does exactly
what BK-N1 exists to protect. Two defects in how it lands — BK4 (placement) and BK3 (no label).

**Chapter 7, line 724** — *"…'father' now carries three men: the Master's own elder father here, the
Master himself when the boy speaks, and the Arab chief who fathered the boy."* All three referents
verified: the Master's elder father at 719 and 867; **the Master called "my father" by the boy
himself at 831** ("be kind to me by sending my father along with me to my country" — addressed to the
Shaykh, meaning the Master); al-Bakhtari at 833, 841, 869. The underlying usage is the source's own
(`الوالد الأكبر`). **Substantively correct**, and placed sensibly. Same two defects of form.

---

## Per-chapter verdicts

| Chapter | Pass 1 | Pass 3 | Verdict |
|---|---|---|---|
| Front matter — How to Read a Conversation Made of Doors | **fail** (BK-P4 ×2) | pass | **SHIP-WITH-CAUTION** |
| 1. The Persian Who Was Dead and Revived | pass | pass | SHIP-READY |
| 2. A Stranger in the City | pass | pass | SHIP-READY |
| 3. The Boy at the Door — Limits and Conditions | pass | pass | SHIP-READY |
| 4. How the World Was Made | pass | pass | SHIP-READY (P2 only) |
| 5. The World, the Hereafter, and the Speech of Parables | pass | pass | SHIP-READY |
| 6. Three Layers of Knowledge | pass | pass | SHIP-READY |
| 7. The Five Shares and the Long Road to the Shaykh | pass | pass | SHIP-READY (P2 only) |
| 8. Homecoming, the Father, and the Debate with Abu Malik | pass | pass | SHIP-READY |

## Whole-book passes

| Check | Result |
|---|---|
| BK-P1 no-teaching-lost | pass — ratios 0.98-1.25; the ch7 restoration holds |
| BK-P2 verbatim-quote survival | pass — every Arabic display run glossed |
| BK-P3 Arabic-script accuracy | pass — 0 unverified; 52 run objects unchanged |
| BK-P4 faithfulness-against-addition | **fail** — two unsupported claims in the front matter (BK1, BK2) plus BK6 |
| BK-P5 voice fidelity | pass |
| BK-P6 prose craft | pass — no scaffolding; one typographic nit (BK5) |
| BK-P7 duplicated passage | pass — independent all-pairs sweep returns only the source's own chiastic pair at 585/589 |
| BK-A1 voice consistency | pass — head tags 100% colon after the last two were fixed |
| BK-A2 segmentation sanity | pass |
| BK-A3 preface + TOC integrity | **pass on orientation, fail on apparatus discipline** — the preface now genuinely orients (who wrote it, what tradition, who narrates, who the figures are, what the edition did); heading sequence still matches `book-toc.json`; but BK3, BK4 and BK7 are open |
| BK-A4 plain transliteration | pass — zero scholarly diacritics; `Kitab al-Alim wa-l-Ghulam` correctly folded |
| BK-A5 tradition fit | pass |
| BK-N1…N7 | pass — deterministic probes clean on all nine sections |

---

## Findings

### BK1 · BK-P4 · P1 · VERIFIED
- **Chapter:** front matter
- **book.md:** 15 — `leaves a word unvowelled wherever the original scan leaves it unvowelled`
- **Why it fails:** false as a universal, and falsifiable by any reader with the scan. Two runs are printed fully vowelled where the scan prints them bare — `بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ` (284) and `حَوْلَيْنِ كَامِلَيْنِ` (535) — and seven more are printed vowelled with no counterpart in the scan at all (553, 563, 575, 621, 673, 1329, 1367), all Qur'anic verses the source cites in prose only. The rule the edition actually follows is better than the one it claims and is the rule this challenger verified: **the source's own words carry the scan's vowelling; Qur'anic quotation carries the mushaf's.** The same sentence's earlier clause, "keeps the Arabic where the source carries it", is incomplete for the same reason — it does not disclose the supplied verses.
- **Worker action:** replace with something like — "It keeps the Arabic the source carries, with the English set beneath, and supplies the Arabic of Qur'anic verses the source quotes in translation only. Where the words are the book's own, they are left unvowelled exactly as the scan leaves them; where they are Qur'an, they carry the vowelling of the mushaf."

### BK2 · BK-P4 · P1 · VERIFIED
- **Chapter:** front matter
- **book.md:** 13 — `The book glosses each where it first appears. What it never says outright is that they belong together — they name ranks in one structure`
- **Source:** `book.md` 288 and 290 (chapter 4)
- **Why it fails:** the book says it outright, twice, in the chapter the sentence points to. Line 288 sets the ranks in an explicit hierarchy — imam as the sun, the argument and gate as the moon, the summoners as the stars — and 290 gives the counts binding them (twelve chiefs to a speaker, twelve arguments to an imam, summoners under every argument). The introduction's conclusion is right; its premise tells a reader the book withholds something it states plainly, which undersells the text and will not survive a reader turning to chapter 4.
- **Worker action:** invert it — "The book sets them out as ranks in a single structure in chapter four, imam and gate and summoners figured as sun and moon and stars; the cosmology of chapters four through six is describing that structure rather than decorating it."

### BK3 · BK-A3 · P2 · VERIFIED
- **Chapter:** 4 and 7
- **book.md:** 251, 724 — fenced with `<!-- bridge:begin -->` and rendered as bare italic blockquotes with no label
- **Why it fails:** the front matter promises, in the same commit, "The few editorial notes are fenced and labelled, so a reader can always tell the book's voice from a note about it." The two editorial notes carry `**Editorial note (source-grounded).**`; the two bridges carry nothing. A reader meets an unattributed italic aside inside the Master's discourse and has only the italics to tell him it is not the book.
- **Worker action:** label both, or narrow the front-matter claim to the editorial notes and describe the bridges separately.

### BK4 · BK-A3 · P2 · VERIFIED
- **Chapter:** 4 — How the World Was Made
- **book.md:** 248-256 — 248 ends `so that He says to whatever He wills:` / 251 is the bridge / 254 is `كُنْ فَيَكُونُ` / 256 is `"Be," and it is.`
- **Why it fails:** the bridge is inserted between a colon and the quotation it introduces, severing the book's most famous sentence from its own verb. Placing it before 248, or after the gloss at 256, costs nothing and reads cleanly.
- **Worker action:** move the block above line 248.

### BK5 · BK-P6 · P2 · VERIFIED
- **Chapter:** 4 and 7
- **book.md:** 251 — `the “I” and “we” in it are his` / 724 — `so “father” now carries three men`
- **Why it fails:** these are the only two lines in 1,407 that use curly quotation marks; the other 1,405 use straight quotes throughout. In the rendered PDF the two asides will visibly differ from every other quotation in the book.
- **Worker action:** straight quotes.

### BK6 · BK-P4 · P2 · VERIFIED
- **Chapter:** front matter
- **book.md:** 9 — `**The Shaykh** is the greater teacher at the far end of the boy's journey, who tests him for seven days.`
- **Source:** `book.md` 797-813 — the Shaykh defers the naming "upon the completion of seven days"; asked why, he answers "For the dignity of the newborn." On the seventh day the boy is told to wash and dress, and is then taught.
- **Why it fails:** the seven days are a deferral for the dignity of a newborn, not a test, and nothing happens in them but waiting. The Shaykh *does* test the boy — the catechism on his name at 777-791, "who freed you from a master?", "how can a thing be known when it has no name?" — but that precedes the seven days. The compression inverts the sequence.
- **Worker action:** "who tests him on his name and holds his naming back for seven days."

### BK7 · BK-A3 · P2 · VERIFIED
- **Chapter:** front matter
- **book.md:** 13 — `From the fourth chapter onward a set of terms recurs… The book glosses each where it first appears.`
- **Why it fails:** the four terms first appear in chapter 4 as plain English — "the imams and the speakers", "the argument, the gate of their imam", "Their summoners" (288, 290) — with no transliteration and no gloss. The transliterated glosses all land one chapter later, at 354, 358 and 362. True of the named terms, not of the concepts, and the sentence points the reader at chapter 4.
- **Worker action:** "The terms first appear in chapter four and the book glosses each when it names it, in chapter five."

### BK8 · process · P2 · VERIFIED
- **File:** `_system/book-render-checks.json` — mtime 13:40, `pages: 121`, `verdict: RENDER-CAUTION`
- **Why it fails:** it describes a render of a `book.md` that has been superseded twice (16:47). The PDF on disk is 16:47 and the brief reports 122 pages. Its three `BR-PAGE-FILL` findings belong to `book-render-challenger`, not to this challenger, but they cannot be acted on or dismissed while the artifact is stale.
- **Worker action:** re-run the render checks; refer the page-fill findings to the render peer.

---

## The comprehension warning — heuristic artifact, not a reader problem

`Imam: first used p6, explained p30` is an artifact and can be dismissed. The checker measures the
distance from a term's first token occurrence to its explanation and cannot distinguish apparatus
from body. At its first occurrence the term is not unexplained: the introduction writes "the speaking
Imam (*al-Imam al-Natiq*)", which glosses it in place, and the same sentence tells the reader the
book will gloss these terms where they appear. Naming the vocabulary early and pointing forward is
what an introduction is for; the metric reads that service as a defect. The one condition that would
make it real — a term named in the front matter with no gloss anywhere near it — does not hold here.
Worth noting only that fixing BK7 will move the "explained" page earlier anyway, since the honest
statement points at chapters four and five rather than implying chapter four alone.

## Verified vs Inferred summary

| | Count |
|---|---|
| VERIFIED | 8 |
| INFERRED | 0 |

## Ledger emission summary

8 records appended to `_learning/findings.jsonl`, ids BK1-BK8, `resolution: "flagged"`.

## Verdict

**SHIP-WITH-CAUTION.** No blockers. The introduction is a real improvement and its load-bearing
claim — that the teacher of the opening pages is not the Master of the story — is firmer in the
Arabic than it is in the English, so state it as confidently as you have. Two of its factual claims
do not survive checking: the vowelling rule it announces is not the rule the edition follows, and it
tells the reader the book never links the Imam/gate/summoner vocabulary when chapter 4 links it
explicitly. Both are small rewrites of sentences the introduction is better off without in their
current form, and neither touches the body of the book. The six advisories are form, placement and
one stale artifact.
