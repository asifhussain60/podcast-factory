# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 (challenger v2.5)
**Scope:** per-chapter doctrinal-synthesis-and-supplementary
**Content profile:** islamic_scholarly (default — series-config.yaml absent)
**Iterations:** 1 (of 5 max — intelligent break: no deterministic auto-fix applicable, remaining findings are authoring decisions consistent with prior chapters in this book)
**Verdict:** SHIP-WITH-CAUTION

## Auto-fixes applied

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | None. Build-script validator did not require any deterministic auto-fix; all flagged items require author judgment. |

## Findings requiring author resolution

### P0 (blocks ship)
None. Build-script `validate_chapter()` + `validate_framing()` passed without `sys.exit`. Doctrinal pack (Category T1–T5) clean: zero canonical-attribution, lineage, forbidden-phrase, or weak-hadith hits. The Father of Imams is referenced by leadership-title only; the fourth Imam is named correctly as Ali Zayn al-Abidin (Adam of the Family of the Cloak — matches `imam-lineage-ismaili.yml`); Hasan/Husayn cosmology is internally consistent with the Ismaili-Tayyibi tradition.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION: 4 distinct Arabic transliterations in chapter prose (16 total token occurrences)
- **File:** `content/Islamic/kunooz-al-hikmah/chapters/ch13-doctrinal-synthesis-and-supplementary.txt`
- **Context:** Distinct hits: `al-Abidin` (×3 — lines 11/59/79, all paired with "Ali Zayn"), `al-Adha` (×1 — line 21, "Eid al-Adha meat"), `al-Hikmah` (×1 — line 19, inside the italicized work title *Kunooz al-Hikmah*), `al-Yamani` (×1 — line 57, "Hudhayfa al-Yamani"). Also non-`al-` transliterations: `jazair` (×1 line 11), `mansub` (×1 line 11), `Ajabshah` (×1 line 23), `Najran` (×2 line 67), `Habasha` (×1 line 67), `karrah` (×1 line 7), `mawr` (×1 line 7), `aqiqa` (×2 lines 21/25), `Hudhayfa` (×1 line 57). F20 doctrine: replace with English audio labels.
- **Suggested fix:** Author judgment — many hits are inside legitimate proper nouns (Hudhayfa al-Yamani, Najran, Habasha, Ajabshah) or italicized work titles (the chapter already uses the English "Treasures of Wisdom" form in most places; the lone `al-Hikmah` instance at line 19 is the doctrinal-introduction passage). `Ali Zayn al-Abidin` already has the descriptive title "Adam of the Family of the Cloak" in the same paragraph (line 59), and the framing's Name discipline block instructs "The fourth Imam — for Ali Zayn al-Abidin", so the audio-layer steering is already in place. Consider replacing remaining un-titled instances with descriptive labels on next pass. Non-blocking; flagged for awareness.

#### R-SURAH-ENGLISH-ONLY: `ibrahim` token flagged
- **File:** `content/Islamic/kunooz-al-hikmah/chapters/ch13-doctrinal-synthesis-and-supplementary.txt`
- **Context:** F29 doctrine: surah references must use the English meaning. Detector flagged `ibrahim` — on manual inspection this appears only inside the duat-name "Ibrahim the traveler" (line 27), which is a personal-name use, NOT a surah citation. The chapter's actual Quranic citation (line 55) already uses "the chapter on the Prophets, verse eighty-seven". False positive on personal-name use.
- **Suggested fix:** No change. Personal-name reference, not a surah citation.

#### R-NAMEDISCIPLINE: framing Name discipline block lacks 3+ alias rotation
- **File:** `content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP13-doctrinal-synthesis-and-supplementary/00-framing.md:8-18`
- **Context:** Each entry is a single first-mention rule + descriptive paraphrase, not a rotation of 3+ aliases. Same pattern across all prior EP##-* framings in this book — book-wide convention, not chapter-specific drift.
- **Suggested fix:** Book-wide cleanup if/when the Name discipline rotation form is required; non-blocking and consistent with the rest of the book.

#### R-NO-ARABIC-TRANSLITERATION (framing): 1 transliteration
- **File:** `content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP13-doctrinal-synthesis-and-supplementary/00-framing.md:14`
- **Context:** Single hit: `al-Abidin` in "The fourth Imam — for Ali Zayn al-Abidin". This is the Name-discipline anchor entry whose purpose is precisely to instruct the hosts to use "the fourth Imam" in audio; the prose presence is the author-facing key.
- **Suggested fix:** No change needed — the line's purpose is to declare the audio substitution rule.

#### R-ANALOGY-CAP-STRICT + R-NOMODERNIZE-STRICT: `broadcast` flagged in framing
- **File:** `content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP13-doctrinal-synthesis-and-supplementary/00-framing.md:21` (Pronunciation block) and the `## Do not` analysis pulls the word from the doctrine of the "boundary of broadcasting" referenced in Beat 2 reasoning.
- **Context:** Detector treats `broadcast` as a forbidden modern artifact. In this chapter the word is doctrinally precise — "broadcasting" names the second of the six boundaries the author lays out (the discipline of NOT carrying inner doctrine beyond those prepared to receive it). This is the author's own technical vocabulary, not a modern-platform allusion.
- **Suggested fix:** Author judgment — either accept as doctrinally precise (preferred — "the boundary of broadcasting" is the author's chosen English rendering) or rephrase to "the boundary of public-disclosure" for stricter F29 hygiene. Non-blocking.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** `content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP13-doctrinal-synthesis-and-supplementary/99-show-notes.md`
- **Context:** F25 doctrine requires the written-layer apparatus table that audio omits. Show-notes currently carries `## Related episodes` and `## References` only. Build script flags but does not block. Same finding flagged on every prior EP##-* in this book — book-wide pattern.
- **Suggested fix:** Author adds the apparatus table per F25 template. Book-wide cleanup; not chapter-specific.

#### B6-DOUBLED-PHRASE: `Three hundred and sixty:` repeated back-to-back
- **File:** `content/Islamic/kunooz-al-hikmah/chapters/ch13-doctrinal-synthesis-and-supplementary.txt:23`
- **Context:** Detector flags `Three hundred and sixty: three hundred and sixty manifestations...`. On manual inspection this is the legitimate stylistic pattern of the entire structural-numbers paragraph: every number in the run uses the same `<Number>: <number>...` form ("Twelve: twelve islands...", "Twenty-eight: two plus three...", "Twenty-nine: twenty-nine of the abbreviated..."). It is the author's deliberate parallel construction, not a copy-paste accident. False positive.
- **Suggested fix:** No change. The pattern is consistent across the paragraph and reflects the chapter's lattice-of-numbers rhetorical structure.

### P2 (advisory)

#### CS-SCRIPT-CRASH: check_chapter_set.py crashes on contract length_target type
- **File:** `scripts/podcast/check_chapter_set.py:275`
- **Context:** `'int' object has no attribute 'lower'` — book-wide chapter-set integrity scan could not run; one or more chapter-contract `length_target` fields are integers instead of strings. Pre-existing across prior SHIP-WITH-CAUTION episodes of this book.
- **Suggested fix:** Book-wide cleanup (out of per-chapter scope). Normalize `length_target` to string enum in chapter-contracts.

## Health metrics

| Chapter | Words | Citations | Tier diversity | Honorifics | Phonetic gaps |
|---|---|---|---|---|---|
| ch13-doctrinal-synthesis-and-supplementary | 5824 | 4 (Daftary *The Ismailis* 2nd ed. pp.128-131; Corbin *Cyclical Time and Ismaili Gnosis* pp.96-99; Quran 21:87 trans. Yusuf Ali p.240; Fyzee/Poonawala *Pillars of Islam* vol.1 pp.22-25; Qutbuddin *Treasury of Virtues* §28 p.16) | 5 tiers (Quran with named translator, modern Ismaili scholarship × 2, foundational Ismaili compendium, Peak-of-Eloquence aphorisms) | Single "peace be upon him" for Jonah at line 55 — no repetition (O1 clean) | 0 — terms covered in framing imperative Pronunciation block (Allah, Quran, Dai, duat, Aimmah, Qaim, Ghadir, Karbala, Treasures of Wisdom) |

Notes:
- Word count 5824 is over the Default Deep Dive band (1800-2800) and over Longer (2800-4500); chapter is best classified as Extended. Appropriate for the final-chapter triple movement (synthesis + closing + supplementary expositions). Framing targets a 50-60 minute long-form discussion per its own opening directive.
- Citation discipline (A1): every reference carries author + work + edition + page. Quran citation gives translator (Yusuf Ali), publisher (Amana 1989), and page. Daftary, Corbin, Fyzee/Poonawala, Qutbuddin all carry edition + page-range per A1.
- Citation authenticity (A2): no `[VERIFY CITATION]` markers; no `[CONTEXT NEEDED]` markers (D5).
- Translation provenance (A3): Yusuf Ali named at first occurrence per A3 standard.
- Verbatim integrity (A4): the Yusuf Ali Quranic blockquote at line 55 matches the canonical Amana 1989 rendering.
- Doctrinal (Category T): zero T1-T5 findings. The Father of Imams is referenced ONLY by leadership-title (never paired with the personal name — the forbidden phrase per `naming-conventions.yml`); the fourth Imam = Adam of the Family of the Cloak = Ali Zayn al-Abidin lineage matches `imam-lineage-ismaili.yml`; Hasan/Husayn four-ranks cosmology is internally consistent with prior chapters in this book.
- Framing carries: welcome clause (H1), spine-repeat directive (R-RECURRING-THESIS three times: opening / pivot / close placements explicitly numbered 1-2-3), Name discipline block (J1) with 10 entries, imperative Pronunciation block (N2: 9 terms with "Say each term ONCE" anti-doubling guard per CLAUDE.md R-PRONUNCIATION-DOUBLE), no-read-aloud guard (N4), Do-not block with modernize + surprise tells (M1/M2 — Twitter, social media, algorithm, "wow", "right?"), host dynamic with friction quotes + single-concession discipline (K1), three governing analogies (gathered sheaf / storehouse-and-key / depth-and-formula), anti-recap landing (H3 — reflective single-teaching question), Verbatim Recitation directive for the author's final closing.
- Host role parity (Q1-Q5): Host A = male scholar, Host B = female seeker — matches book-wide pair (consistent with EP01-EP12 per prior reports). No drift.
- Conversation choreography (R1-R5): host dynamic carries 3-friction + 1-concession; spine-repeat acts as R-RESET equivalent via the explicit placement-marks across beats; cadence not explicitly named in Tone section (R3 minor gap, P2 advisory).
- Category U (scholarly-conversation rubric v2.2): no AI cliches (U1), no faux-profundity opener (U2 — the "What does it mean to *finish*..." opener is V1 curiosity-building, not abstract hand-waving), no premature closure (U3 — landing is explicitly open and reflective, not falsely resolved), no deep-dive self-reference (U4), no essentialism-external (U5 — discussion is internal to Ismaili-Tayyibi tradition; positionality is explicitly marked in Host dynamic). U6 (concession-arc resolution) not applicable — episode_format is deep-dive, not debate.
- Category V (interest & engagement): V1 curiosity hook present ("What does it mean to *finish* a book whose treasures are, by the author's own admission, not transferred but only displayed?"), V2 challenge-defeat arc (the apparent tension of Husayn-as-Imam vs Ali-Zayn-al-Abidin-as-first-complete is raised and resolved in the supplementary section), V3 modern-relevance signal (the "scaling of action to the great cycle" and Corbin gloss connect the doctrine to the reader's measure of his own life), V4 no strawman, V5 rhetorical question cadence present (chapter opens with one and the landing closes with one).
- Loop M / N empirical (transcript): no NotebookLM rendered episode `.transcript.txt` present at `transcripts/EP13-*.transcript.txt`, so Loop M/N empirical checks against modernization/surprise-noise/phonetic-doublings do not apply on this run.
- Build-script validator (`build_episode_txt.py --check`) ran clean (exit 0); all findings above are flags, not gates.

## Fixer pass note (2026-06-15)

Fixer pass reviewed every P1 finding. Each one carries an explicit "No change" / "Book-wide cleanup, non-blocking" / "Author judgment, non-blocking" disposition in its own Suggested fix line (false-positive personal-name + deliberate parallel-construction hits, book-wide framing conventions consistent across EP01–EP12, doctrinally-precise author vocabulary). No per-chapter edit applicable; deferred to book-wide cleanup pass.
