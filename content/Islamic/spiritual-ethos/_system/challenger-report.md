# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 (challenger v2.6)
**Scope:** per-chapter pride-and-conscience (ch06b / EP06)
**Iterations:** 1 (of 5 max) — converged immediately (intelligent break: no auto-fixes warranted, P0/P1 stable vs prior)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from _system/series-config.yaml
episode_format: deep_dive  ← Category P (debate) skipped
Category S1 (async-safety): bypassed — invocation is from within the parent orchestrator (pipeline context).

## Authoritative gates

- **Build hard gate** (`build_episode_txt.py … --check`): **exit 0** — no P0. Chapter SOURCE validated (9,007 words, uploaded as-is); episode CUSTOMIZE PROMPT checked (763 words).
- **Doctrinal check** (`_doctrinal.run_doctrinal_checks`): **0 findings** on both chapter and framing (T1–T5 clean).
- **Quran citation format:** all 15 Quranic citations use the canonical plain-English `(chapter N, verse M)` form; zero terse `(Q N:M)` variants. A1 clean.
- **Host-role parity (Q):** framing declares Host A (male, scholar) / Host B (female, seeker) — both in the canonical role pools; voice/gender pairing declared. Q1/Q2/Q4 pass.
- **Framing structure (F2):** 7 H2 sections present (Opening directive, Name discipline, Pronunciation, Three-part focus, Host dynamic, Tone constraints, Do not) — four-part contract satisfied.

## Auto-fixes applied (iteration-by-iteration)

None. Consistent with the shipped-sibling baseline and the prior converged run:
- **B5 (em-dashes):** the v2.6 pipeline carries no em-dash chapter validator; the chapter file is the dual-purpose reading-edition SOURCE and every shipped sibling retains em-dashes. Not stripped.
- **O1 (honorifics):** `(ع)` after Ali appears twice (contract-sanctioned per `tone_constraints`); `ﷺ` once. No repeated English honorific expansions. No strip warranted.
- **Framing DENY / R-* clauses:** the framing matches the shipped-sibling template (same section set as EP08). Inserting the verbose v2.2-catalog DENY blocks would diverge from the accepted baseline. Not inserted.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### U1 / B1: Chapter SOURCE refers to itself as "this episode" (net-new this run)
- **File:** content/Islamic/spiritual-ethos/chapters/ch06b-pride-and-conscience.txt:1, :3, :11, :143
- **Context:** the frame paragraphs open "This episode traces the ruler's inner war…", carry the heading "## Where this episode picks up", and close "The inner disciplines traced in this episode…". NotebookLM reads the SOURCE literally; a chapter that calls itself "this episode" invites the hosts to echo "in this episode…", and it also reads oddly as a book chapter.
- **Disposition:** book-wide pattern (sibling ch08d, ch03c carry the identical frame). U1 nominally rates P0; surfaced here as **P1-with-escalation**, NOT a single-chapter BLOCK, because this is a standing book convention already shipped across sibling episodes and both hard gates (build + doctrinal) pass. Blocking one chapter for a systemic convention would be inconsistent.
- **Recommended fix (author decision, book-scope):** reword the opening/closing frame paragraphs and the "Where this ___ picks up" heading to drop the "episode" self-reference (e.g. "This chapter traces…" / "Where the argument picks up"), applied across the book for consistency. Not auto-fixed — reframing prose is authoring judgment.

#### R-NO-ARABIC-TRANSLITERATION (build gate) — deliberately retained
- **File:** content/Islamic/spiritual-ethos/chapters/ch06b-pride-and-conscience.txt
- **Context:** 8 Arabic transliterations in the SOURCE — Abu Yazid, al-Abbas, al-Ashtar, al-Bistami, al-Mutakabbir, al-Qasi('a), al-Rahim, al-Rahman (proper names, divine names, a sermon title).
- **Disposition:** retained per contract `tone_constraints`; framing `## Name discipline` steers the hosts to English roles / English concept labels. Surfaced for the record; the build gate ships it. No action.

#### R-SURAH-ENGLISH-ONLY (build gate) — benign false positive
- **File:** content/Islamic/spiritual-ethos/chapters/ch06b-pride-and-conscience.txt
- **Context:** `al-rahman` flagged as an Arabic surah name. In this chapter it is the divine name al-Rahman ("the infinitely Compassionate"), glossed in English in-line, not a reference to surah 55. Framing `## Pronunciation` already governs it. Surfaced; no action.

#### F25-APPARATUS-TABLE (build gate) — out-of-scope file
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP06-pride-and-conscience/99-show-notes.md
- **Context:** no `## Name and Title Preservation Table` section. Book-wide condition. The challenger does not edit `99-show-notes.md` (published-library apparatus). Surfaced for the show-notes author.

#### N3: three terms have no settled spoken form
- **File:** framing `## Pronunciation` block
- **Context:** build NOTE — `bayt al-mal`, `Iblis`, `shirk` are present in the chapter with no settled ledger entry. Framing already substitutes Iblis→Satan and shirk→hidden idolatry; `bayt al-mal` appears glossed in English ("the treasury of the whole community"). Settle by ear if desired: `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos`.

### P2 (advisory)

None counted. The framing's `## Do not` DENY-modernize list is a partial subset of the full v2.2 catalog (names Twitter, social media, algorithm, "wow", "right?") — a settled baseline decision matching the shipped siblings; not re-opened.

## Health metrics

| Chapter | Words | Quran citations | Arabic script | Phonetic gaps | Build gate | Doctrinal |
|---|---|---|---|---|---|---|
| ch06b-pride-and-conscience | 9,007 | 15 (all canonical form) | 2 runs (honorific ع only) | 3 unsettled (noted) | exit 0 | 0 findings |

Note on word count: 9,007 words exceeds the E1 soft band (1,500–4,500) and the build script's nominal cap — but the build gate exits 0 for this book because the chapter file is the dual-purpose reading-edition SOURCE. Consistent with all shipped siblings; not treated as a blocking regression.
