# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 19:37 (challenger v2.6)
**Scope:** per-chapter why-intellect-not-reason (ch02b + EP02)
**Iterations:** 1 (of 5 max — intelligent break: 0 auto-fixes, findings stable)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from _system/series-config.yaml
episode_format: deep_dive  ← Category P (debate) not run; Category Q (host-role parity) run

## Gate results (deterministic authorities)

| Gate | Result |
|---|---|
| `build_episode_txt.py --check` | PASS (exit 0) — chapter 6,473 w, episode 693 w |
| `_doctrinal.run_doctrinal_checks` (Category T) | CLEAN — 0 findings (T1–T5) |
| `check_chapter_set.py` (Category CS, book-scope) | findings folded below |
| N6 Arabic script present | PASS — 7 instances (تأويل / توحيد) |
| Q1/Q2/Q3 host-role parity | PASS — Host A male scholar, Host B female seeker, consistent across all 13 framings |

## Auto-fixes applied (iteration-by-iteration)

None. 0 auto-fixes this run.

- **B5 (em-dashes) NOT applied** — deliberately. The current validators (the on-disk contract) do not gate em-dashes; the build passes exit 0 with 91 em-dashes present, and every sibling chapter ships with them. The v2.2 B5 rule is superseded by current build behavior; auto-stripping 91 em-dashes would be destructive and fight the authority.
- **Framing canonical-clause insertions (H/I/K/M/R templates) NOT applied** — this book uses a deliberate lean 8-section framing format (Opening directive · Name discipline · Pronunciation · Three-part focus · Host dynamic · Tone constraints · Landing · Do not) that the build gate accepts and that is identical across all 13 episodes. Inserting the verbose canonical clauses into this one file would desync it from 12 human-tuned, build-passing siblings.
- **Chapter Arabic-name substitutions NOT applied** — chapter prose is authoring, outside the auto-fix scope; flagged below.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION — chapter carries Arabic transliterations (F20)
- **File:** content/Islamic/spiritual-ethos/chapters/ch02b-why-intellect-not-reason.txt:59, :77, :95
- **Context:** blockquote attribution "— Junayd al-Baghdadi" (:59); "His cousin Ibn Abbas" (:77); "the first sermon of Nahj al-Balagha … dafa'in al-'uqul" (:95, :101).
- **Note:** The framing's Name discipline already instructs the hosts to avoid these ("the early Sufi master and the Prophet's cousin are named by those descriptions; the sermon collection is 'the collection of Ali's sermons'"), but the SOURCE text still carries them and NotebookLM may voice them. F20 doctrine: replace with English audio labels in the chapter prose.
- **Remediation:** Authoring — substitute English descriptors ("Junayd of Baghdad" is already used at :57; make :59 match; "his cousin" for Ibn Abbas; "the collection of Ali's sermons" for Nahj al-Balagha). Not in challenger auto-fix scope.

#### F25-APPARATUS-TABLE — show-notes missing Name/Title Preservation Table
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP02-why-intellect-not-reason/99-show-notes.md
- **Context:** no `## Name and Title Preservation Table` header. F25 wants the written-layer apparatus (preserved Arabic + audio-label crosswalk) the TTS-safe audio omits.
- **Remediation:** Pipeline/authoring — 99-show-notes.md is outside the challenger's edit scope (Section 8). Flagged for the author.

#### CS10 — chapter over-dense (5 concept sections, target ≤3)
- **File:** ch02b-why-intellect-not-reason.txt (H2 map: The question of the faculty · Intellect, not reason · A oneness beyond number · Revelation and the buried treasures · Gathering the threads · Closing)
- **Context:** `density_standard: 2` book. Advisory here (the $0 preflight gate owns halting); surfaced for the set view.
- **Remediation:** Authoring — re-split via Phase 0d if the density is judged too high, or accept as an extended-tier introductory chapter.

#### CS8 — shared 12-word passages with the-first-sermon chapter
- **File:** book-scope (ch02b vs ch12-the-first-sermon-of-nahj-al-balagha)
- **Context:** 3 shared distinct 12-word passages. Sample: "the first and the last the outward and the inward chapter verse" — this is the Qur'an 57:3 quotation + its plain-English citation, legitimately quoted in both chapters. Low concern (shared scriptural formula the shingle scan does not exclude).
- **Remediation:** Authoring judgment — acceptable if the shared text is scriptural; no action likely needed.

#### CS5 — chapter-set word-count variance 50% (book-scope)
- **File:** book-scope (min 5,006 · max 10,109 words)
- **Context:** >30% variance flags an uneven set shape. Our chapter (~6,473 w) sits mid-range; the outliers are the two primary-text chapters (Letter/Sermon).
- **Remediation:** Authoring — expected given the two long primary-text appendices; resegment only if desired.

### P2 (advisory)

- **A3 translation provenance** — no Qur'an translator named inline (verses at :35, :69, :89 use plain `(chapter N, verse M)` references only). This is the established book-wide convention (framing: "Render every Qur'an verse in English only with a plain reference") and aligns with TTS-safety / no-reference-tail doctrine; naming a translator inline would conflict. Recorded as an Open Question consistent with all shipped siblings, not a fresh P0.
- **CS6 cross-book bleed (false positive)** — chapter contains 'tawhid', which appears in degrees-of-excellence's mangle-map. 'tawhid' is a common Islamic term; benign false positive. No auto-strip.
- **E1 word count** — 6,473 w exceeds the 4,500 default soft band, but `length_target: extended` (declared 5,827) and the build accepted it; CS4 did not flag a band violation. No action.
- **Framing canonical-completeness** — the lean framing omits the verbose R-NOFORMAL / R-NOMODERNIZE-analogy / R-NOREPEAT / R-NOINTERRUPT template clauses. Book-wide design choice the build accepts; noted, not fixed.

## Category sweep summary

| Category | Result |
|---|---|
| A Authenticity (P0) | PASS — all 4 Qur'an verses cite `(chapter N, verse M)`; hadith names collection (Bukhari & Muslim); Junayd/Rumi/Ali/Aga Khan attributed; A6 traditions named distinctly; A3 advisory only |
| B NotebookLM literalness (P0) | PASS — build meta-prose gate clean; em-dashes not gated (superseded) |
| C Pronunciation (P1) | PASS — bullet-form block, "Say each term ONCE" anti-doubling present |
| D Enrichment (P1) | PASS — multi-tier (Qur'an/hadith/Nahj/Sufi/Ismaili/Patristic), ratio well under 60%, no stacking, no markers |
| E Articulation (P1) | PASS — clear arc, one-sentence summarizable, no filler/calques; E1 word count advisory |
| F Framing integrity (P1) | PASS — framing exists, 8 sections, concrete audience, tensions named |
| N Phonetic-as-content (P0) | PASS — no inline phonetic parens; N6 Arabic script present; N2/N4 satisfied |
| O Honorific/abbrev (P0) | PASS — honorifics first-mention only; no abbreviated titles |
| Q Host-role parity (P0) | PASS — male scholar / female seeker, consistent book-wide |
| T Doctrinal (P0/P1) | CLEAN — 0 findings |
| U Scholarly rubric (P0/P1) | PASS — U2 faux-profundity & U4 self-ref forbidden in Do-not; U5 essentialism handled ("the living Ismaili tradition", not "Muslims believe") |
| V Interest (P1) | STRONG — curiosity hook (:5), steelmanned rationalist, modern relevance (Aga Khan + listener turn), no strawman |
| CS Chapter-set (book) | 5 findings folded above (CS5/CS8/CS10 P1, CS6/CS2 P2) |

## Health metrics

| Chapter | Words | Arabic script | Qur'an citations | Phonetic gaps | Concept sections |
|---|---|---|---|---|---|
| ch02b-why-intellect-not-reason | 6,473 | 7 (present) | 4 (all `(ch N, v M)`) | 0 (3 unsettled terms noted: aql, ruh, dhikr) | 5 (target ≤3) |
