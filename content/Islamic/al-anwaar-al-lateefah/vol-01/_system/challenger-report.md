# Podcast Challenger Report

**Book:** al-anwaar-al-lateefah/vol-01
**Run:** 2026-06-17 16:45 (challenger v2.5)
**Scope:** per-chapter ascent-decline-and-the-birth-of-a-god (EP07)
**content_profile:** islamic_scholarly  ← detected from _system/orchestrator-state.json (no series-config.yaml on disk)
**Iterations:** 2 (of 5 max — intelligent break: iteration 2 produced zero auto-fixes and identical findings)
**Verdict:** SHIP-WITH-CAUTION

> Pipeline context: invoked from within orchestrate_book.py (parent process). Category S1 async-safety bypassed per invocation directive (the visible orchestrator IS this challenger's parent, not a concurrent run).

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | R4 | EP07-ascent-decline-and-the-birth-of-a-god/00-framing.md:33 | Added formal-essay-transition DENY clause (Firstly/Secondly/Furthermore/In conclusion/Moving on to/To summarize/Lastly) to the `## Do not` block; compressed to keep framing under the 4500-char NotebookLM Customize ceiling; re-ran build_episode_txt.py to sync the episode txt. |

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION: 5 transliterations in citation apparatus
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch07d-ascent-decline-and-the-birth-of-a-god.txt:23,51,3
- **Context:** `al-Amidi`, `al-Hikam`, `al-Iman`, `al-Kalim`, `al-Lateefah` — all inside required citation apparatus: the hadith reference `Sahih Muslim, Kitab al-Iman, no. 82` (line 23), the Father of Imams' citation `Ghurar al-Hikam wa Durar al-Kalim (compiled by al-Amidi)` (line 51), and the book title `Al-Anwaar al-Lateefah` (line 3 frame).
- **Tension (recorded, not auto-fixed):** F20 audio-safety (replace transliterations with English audio labels) collides head-on with A1 citation discipline (a hadith MUST name collection+book+number; the Imam's saying MUST name the work). These are not stray transliterations — they are the scholarly references A1 requires. The framing already instructs the hosts to cite by content and never speak Arabic titles, so the audio layer is covered. **Author decision:** accept as citation apparatus, or move the Arabic work-titles into the 99-show-notes written layer and use English audio labels in the chapter body. Recommend accepting — stripping them would break A1.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/_system/episode-drafts/EP07-ascent-decline-and-the-birth-of-a-god/99-show-notes.md
- **Context:** the episode's 99-show-notes.md carries no `## Name and Title Preservation Table` section — the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) that the TTS-safe audio omits.
- **Suggested fix:** add the apparatus table to 99-show-notes.md. NOT auto-fixed — 99-show-notes.md is published-library apparatus, outside the challenger's edit surface (Section 8).

#### CS10: chapter over concept-density target
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch07d-ascent-decline-and-the-birth-of-a-god.txt
- **Context:** 6 concept H2 sections (Two men one platform / The parting of prayer / The lesson of the animals / The transmuted soul / Where purity is real / The birth of a god) vs target ≤3 (docs/standards/chapter-density.md). Book-wide pattern: every one of the 11 chapters in vol-01 is over the ≤3 target (5–8 concepts each), so this is a book-level design choice (`length_target: longer`), not a defect unique to this chapter. Advisory in the challenger report; the preflight smoke gate owns any halting for `density_standard: 2` books.
- **Suggested fix:** author decision — accept the denser `longer` band or re-split via Phase 0d. Given the chapter coheres around one doctrine (ascent/decline by inner prayer, proved through men and animals, landing on the disciplined "god"), the density reads as movements of one argument rather than six disconnected concepts. Recommend accept.

### P2 (advisory)

#### A1 (advisory): Quranic refs use the terse `Quran N:M` numeral form
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch07d-...txt:29,37
- **Context:** `Quran 7:179 (the chapter of the Heights)` and `Quran 16:66 (the chapter of the Bee)`. The deterministic gate `assert_quran_citation_format` PASSES (it only flags the *parenthesized* terse forms `(Q N:M)`/`(Quran N:M)`/`(N:M)`; the unparenthesized `Quran 7:179` followed by the plain-English chapter name is not caught). The chapter already pairs each ref with its plain-English chapter name, and the framing instructs hosts to "Cite Quran verses by content, never an Arabic surah name." Audio layer covered; no action required. Surfaced only as a forward-looking note.

#### V3 (advisory): chapter-internal modern-relevance is thin
- **Context:** the chapter body carries no explicit "today / this week" bridge to the listener's world; the modern-relevance signal lives in the framing's Landing ("which inner prayer have I let collapse... what would it cost to establish it again this week"). Satisfied at the episode level via the framing. No action required.

## Checks that PASSED (notable)

- **Category T (doctrinal):** 0 findings. "Ali ibn Abi Talib, the Father of Imams" used correctly (not "Imam Ali", no leadership-title+personal-name pairing); "the Commander of the Faithful" in the framing. T1–T5 clean.
- **Category A (authenticity):** every quote carries a full citation — hadith (collection+book+number+narrator), Quran (chapter name + translator: The Study Quran / Nasr et al.), Father of Imams (Ghurar al-Hikam), Rumi (Mathnawi Bk III + translator). Translator named on first Quranic translation (A3). No `[VERIFY CITATION]`, no fabricated numbers (A2). Verbatim quotes (A4). No source-shifting (A5). Cross-tradition citations annotated as parallel, not collapsed (A6).
- **Category B:** build-script hard gate passes — no HTML comments, no meta-prose tells, no inline phonetics, no doubled phrases. B5 (em-dash) is SUPERSEDED — no em-dash validator exists in the current `validate_chapter()` chain; the 26 chapter em-dashes are not a violation and were NOT auto-stripped (code is authority; the gate passes clean).
- **Category C/N:** no inline phonetic parens; framing `## Pronunciation` uses the correct `- term: phonetic` imperative form (`assert_framing_pronunciation_imperative` passes).
- **Category D:** 4 distinct source tiers (Quran / Sunni hadith / Ismaili-Shia / Sufi). Enrichment ratio 4.7% (≤60%). No quote-stacking.
- **Category F/H/I/K/Q/R:** framing carries welcome+summary opening (H1/H2), no-recap landing (H3), interruption discipline (K1), filler-vocabulary DENY (K2), cadence (R3), DENY-modernize+surprise blocks (M1/M2), no-read-aloud guard (N4), separate-prep + recurring-thesis directives. Host A = male/scholar, Host B = female/seeker (Q1/Q2/Q4 PASS); Q3 vacuously satisfied (EP07 is the only framing so far). All framing-side validators pass (0 hard-fails).
- **Note on R5:** the "DO use modern-life practical analogies" permission half is intentionally ABSENT — the framing declares `EXACTLY three governing analogies, all the chapter's own; invent no others`. Inserting an R5 modern-analogy permission would contradict the author's deliberate constraint, so it was NOT auto-fixed. Recorded as intentional, not a finding.

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Citations | Phonetic gaps | Concept sections |
|---|---|---|---|---|---|---|
| ch07d-ascent-decline-and-the-birth-of-a-god | 3,601 | 4.7% | 4 tiers | 5 | 0 | 6 (vs ≤3) |
