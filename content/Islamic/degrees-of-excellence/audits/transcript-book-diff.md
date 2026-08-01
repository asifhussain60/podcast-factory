# Transcript-to-book diff — Degrees of Excellence

**Date:** 2026-08-01
**Inputs:** six NotebookLM episodes (3 h 18 m), transcribed via Azure Speech, diffed against `book/book.md` (24,904 words, introduction + 9 chapters).
**Route:** articulated faithful translation edition (`book_voice=faithful`, `book_augmentation=source_only`).

The controlling constraint: on this route the reading edition may carry nothing that is not
grounded in the source. NotebookLM output is AI-generated commentary, not source. It is used
here as **signal** — evidence of where the book is opaque — never as content.

Findings are sorted into three classes. A and B are actionable. C is a rejection list, recorded
so the rejections are auditable rather than silent.

---

## Class A — Apparatus completion (no augmentation)

The book prints these Quranic quotations without a reference, while citing verses inline
elsewhere (`(Quran 21:98)`, `(5:13)`, `(41:53)` …). Supplying the reference adds no word to the
author's text; it completes an apparatus the edition already uses inconsistently.

Every reference below was verified against the canonical mushaf in
`content/knowledge-base/mirror.db` (`fts_quran`). None is from model recall.

| book.md | Quoted text (opening) | Verified reference |
|---|---|---|
| L23 | "Ismail was indeed faithful in fulfilling his promise…" | Q 19:54 |
| L31 | "when His Lord tried Abraham with His commands…" | Q 2:124 |
| L356 | "If only when they wronged themselves, they had come to you…" | Q 4:64 |
| L364 | "Take alms (sadaqa) from their wealth, purify them…" | Q 9:103 |
| L386 | "Do you command people to do good and forget it yourselves?" | Q 2:44 |
| L390 | "You are the best community (umma) that has been raised…" | Q 3:110 |
| L480 | "And the earth shines by the light of her Lord…" | Q 39:69 |
| L544 | "We do not desire either reward or gratitude from them." | Q 76:9 |
| L552 | "He made before them a barrier and behind them a barrier" | Q 36:9 |

Also uncited but **not** Quranic, so out of scope for this pass: the Jafar al-Sadiq report (L35),
the hadith at L352, and the saying at L508.

Note L43/L84: the horizons verse is quoted twice, cited as `(41:53)` at L142 but uncited at both
earlier occurrences. Same verse, inconsistent apparatus within one edition.

---

## Class B — Comprehension bridges

Places where the audio shows a reader hitting something the book does not give them. The
sanctioned fix is one orienting sentence in `_system/comprehension-bridges.json`, injected by
`_book_bridges.apply_bridges` — never a rewrite, never a reorder.

### B1. Chapter 9's "Commander of the Faithful" is al-Hakim, not Ali — SEVERE

Chapter 9 describes the reigning Fatimid imam-caliph al-Hakim in the present tense throughout
("the Commander of the Faithful bestows…", "he hides the means…"). The book signals this exactly
twice, both obliquely: an editorial bracket at L289 (`just as the Commander of the Faithful
[al-Hakim] does`) and the reckoning at L496 (`the seventh, al-Muizz, who has passed away, is
perfected through the ninth, al-Hakim`). Everywhere else the same title means Ali — and L542
attaches Ali's name explicitly *inside* chapter 9.

**Evidence this is a real gap, not a theoretical one:** episode 6 spends 34 minutes on this
chapter and identifies the summit figure as Ali throughout — "the commander of the faithful, the
father of imams, the first imam." al-Hakim is never named once across all six episodes.

**Compounding homograph:** `al-Hakim` at L300 means *the Wise One*, a divine name, and the whole
paragraph turns on it. The same string means the reigning imam at L289 and L496. The book's own
comprehension checker reports `referent_collisions: 0` because it cannot see this.

### B2. "the imam's rising in the Maghrib… as I have witnessed with my own eyes" (L179–181)

The book asserts an esoteric interpretation "has proven correct" and offers the reader no anchor
for what was witnessed. It refers to the Fatimid establishment in North Africa — a fact already
recorded in the book's own `meta.yml` provenance block. Without it the sentence reads as an
unsupported claim.

### B3. The Khidr–Moses allusion (L532)

The book names "the story of the sage Khidr with Moses" and explains nothing, while resting a
load-bearing argument about *taslim* on it. The hosts had to narrate the whole episode — boat,
youth, wall — before the argument could land.

### B4. "the owner of the vineyard and the owner of the bull" (L532)

The book itself calls this story "perplexing and astonishing" and then supplies neither the story
nor a reference. Same sentence as B3.

### B5. Abu Hanifa, al-Shafii, Malik, Ahmad b. Hanbal (L396)

The passage's force depends entirely on the reader knowing these four names are the founders of
the four Sunni schools of law — i.e. that the author is naming the whole rival legal
establishment, not four arbitrary jurists. The book never says so.

### B6. *qutb* rendered "pole" (L17, L72)

The load-bearing image of the entire treatise. English "pole" suggests a flagpole or a polar
axis; the sense carrying the argument is the fixed pivot of a millstone, the still point that
lets everything else turn. The edition already carries a tradition-grounded etymology note on
*imam* (L52–61); this is the same apparatus applied to the term the book opens with.

---

## Class C — Rejected: outside material the hosts introduced

None of the following is in the book. All are the hosts' own additions and must not enter the
edition. Recorded for auditability.

**Hadith and reports (7):** the tradition of the two weighty things (EP01); "the earth is never
left without a proof," attributed to Ali (EP01, EP04); the date-palm riddle attributed to an early
compiler (EP02); Ali's letter to Malik al-Ashtar on mercy toward subjects (EP03); "each of you is
a shepherd" (EP03); Ali on the judge who rules by guesswork (EP04); "My mercy has overtaken my
wrath" (EP06).

**Quranic verses not in the book (8):** Q 17:82 (EP02); Q 18:68 (EP03); Q 10:35 (EP03); Q 16:78
(EP04); Q 14:37 (EP04); Q 24:35 (EP05); Q 13:26 (EP06); Q 38:26 (EP06).

**Sayings attributed to Ali (3):** knowledge is better than wealth (EP05); "like the axle to the
millstone" (EP05); the three types of worship — merchant, slave, free (EP06).

**Poetry (2):** "a traveler without a guide turns a two day journey into a hundred year wandering"
(EP01); "should your tree but bear the fruit of knowledge…", attributed to a Fatimid poet (EP02).

**Narrative material (3):** the Khidr episode narrated in full (EP03); the Kharijite slogan and
Ali's reply (EP03); **Ghadir Khumm** (EP05).

### On Ghadir Khumm specifically

Episode 5 presents Ghadir Khumm as "the climax of sacred history" and quotes the declaration
verbatim. The book does not contain it anywhere. This is not an oversight by al-Naysaburi — it is
his stated programme. At L80 he writes that predecessors relying on "the well-known Quranic verses
revealed concerning the imamate… and the traditions reported from the Prophet" have "left nothing
in this matter for those who come after," and that he intends instead to argue "from the outer
horizons and from our own selves… in a manner the elders of the dawa never attempted."

The hosts inserted precisely the class of argument the treatise was written to avoid. Admitting it
would not augment the book; it would contradict its thesis about its own method.

---

## Not found

No factual error in the book was surfaced by the comparison. No passage was found where the hosts
understood the source better than the edition renders it. The gaps above are all gaps of
*orientation* — things the book assumes — not of accuracy.
