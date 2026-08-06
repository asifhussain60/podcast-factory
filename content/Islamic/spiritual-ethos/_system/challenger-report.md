# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 (challenger v2.6)
**Scope:** per-chapter — the-sacred-conception-of-justice (ch05a / EP05)
**Iterations:** 1 (of 5 max) — intelligent-break: 0 auto-fixes warranted; all deterministic gates ran live
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from _system/series-config.yaml
density_standard: 2  ← CS P0 findings are HALTING for this book (none fired for THIS chapter)

> Invoked from within the orchestrator pipeline (phase=per-chapter). Category S1
> async-safety was bypassed for the parent orchestrate_book.py process per the invocation
> directive. `CHALLENGER_VERSION` = 2.6, read at run time from scripts/podcast/_rules.py.

## Summary

Ran the full islamic_scholarly catalog against the ch05a SOURCE and the EP05 framing. Every
deterministic gate executed live this pass:

- `build_episode_txt.py --check` — exit 0 (no hard-fail; episode txt in sync at 701 words).
  Emitted 4 P1 flags + 1 pronunciation NOTE.
- `_doctrinal.run_all` (T1–T5) — 0 findings on both chapter and framing. No forbidden
  title+name pairing; the Mu'awiya quotation's "Ali ibn Abi Talib" carries no leadership
  title, so T3 is clean.
- `check_chapter_set.py` (book scope) — the ONE CS P0 (P4 band overflow, 10,109 words) is on
  ch13-the-letter-of-ali-to-malik-al-ashtar, NOT this chapter. ch05a (5,897 words) sits inside
  the extended band (5,500–9,500). ch05a draws one CS8/P8 duplication P1 + two P6 false-positive P2s.
- Quran-citation scan — all 4 references use the canonical `(chapter N, verse M)` form
  (16:90, 12:53, 30:30, 35:15); zero terse variants.
- Host-role parity (Q1/Q2/Q4) — Host A (male, scholar) / Host B (female, seeker); consistent
  with the book.
- B2 (cross-episode / series-position) — CLEAN. A prior fixer pass already neutralised the
  line-1 "second half of the series" / "mid-series" and the line-29/61 "the earlier teaching …
  need not be reopened here" pointers; the current SOURCE carries none of them.
- Unfilled markers (A2/D5 `[VERIFY]`/`[CONTEXT]`), HTML comments, AI-cliché "deep dive" (U1) —
  all clean on chapter, framing, and show-notes.

The chapter is SHIP-WITH-CAUTION on P1 findings — none blocking. The most substantive is a
chapter-set duplication: ch05a and ch06b (pride-and-conscience) share 13 distinct 12-word
passages (the Aga Khan "authority held in trust" passage among them) — the same teaching carried
in two chapters. This is an authoring/chapter-set design decision, never auto-stripped.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | None. No literal-pattern auto-fix warranted. Em-dashes deliberately preserved (build silent; house style). Framing DENY/pronunciation/name/welcome coverage already present; the framing-style gaps (R-DRAMATIC-ARC, R4) are book-wide decisions that would drift EP05 out of sync with 11 sibling framings if fixed in isolation — left for a book-wide framing-style pass per the systemic-fix-at-root rule. |

## Findings requiring author resolution

### P0 (blocks ship)

None for this chapter. (The book-scope CS4/P4 band-overflow P0 — 10,109 words — is on
ch13-the-letter-of-ali-to-malik-al-ashtar, a different chapter, and does not block ch05a.)

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION: 7 transliterations in the SOURCE (build P1, F20)
- **File:** content/Islamic/spiritual-ethos/chapters/ch05a-the-sacred-conception-of-justice.txt
- **Context:** `Ibn Ata`, `al-Ashtar`, `al-Balagha`, `al-Iskandari`, `al-Karim`, `al-Rahim`,
  `al-Rahman`. These are proper names (Malik al-Ashtar the governor; the Sufi master Ibn Ata
  Allah al-Iskandari), a primary-text title (Nahj al-Balagha), and the divine Names under
  explicit discussion (al-Karim; al-Rahman al-Rahim) — largely unavoidable in a faithful
  exposition of Shah-Kazemi's essay.
- **Suggested fix (authoring decision, not auto-fixed):** the framing's Name-discipline block
  already routes the SPOKEN layer to English roles / "the divine Names" and forbids speaking
  Arabic names and titles; confirm these stay out of the audio layer. Removing them from the
  written SOURCE is a content call, not a mechanical fix.

#### R-DRAMATIC-ARC: framing uses a 4-beat arc, not the 6-beat form (build P1)
- **File:** …/episode-drafts/EP05-the-sacred-conception-of-justice/00-framing.md:18
- **Context:** `## Three-part focus` carries 4 Beat markers (Crisis / ground / Pivot / Close)
  and only 2/4 structure tells; the build wants a 6-beat crisis→failed-answer→pivot→stakes arc.
  This is the established shape across the book's sibling episodes.
- **Suggested fix:** authoring decision (book-wide framing-style question). Not auto-edited to
  keep EP05 in sync with the sibling framings.

#### F25-APPARATUS-TABLE: show-notes missing the Name and Title Preservation Table (build P1)
- **File:** …/episode-drafts/EP05-the-sacred-conception-of-justice/99-show-notes.md
- **Context:** F25 doctrine expects a `## Name and Title Preservation Table` (preserved Arabic /
  transliterations + audio-label crosswalk) in the written apparatus. 99-show-notes.md is
  published-library apparatus and outside the challenger's edit scope.
- **Suggested fix:** publisher/authoring step — add the apparatus table before publish.

#### CS8 (script P8): same content taught in two chapters (13 shared 12-word passages)
- **File:** content/Islamic/spiritual-ethos/chapters/ch05a-the-sacred-conception-of-justice.txt:49
- **Context:** ch05a and ch06b (pride-and-conscience) share 13 distinct 12-word passages — the
  Aga Khan "authority is held in trust / justice and compassion as ethical foundation" passage
  (ch05a line 49) among them, carried near-verbatim in both chapters.
- **Suggested fix (authoring decision, never auto-stripped):** decide which chapter owns the Aga
  Khan passage and the other shared spans, then cut or re-voice the duplicate from the other so
  each teaching is delivered once across the set.

### P2 (advisory)

#### R-SURAH-ENGLISH-ONLY: `al-rahman` — assessed FALSE POSITIVE (build P1, downgraded)
- **File:** ch05a-…-justice.txt (divine-Names paragraph)
- **Context:** the build's F29 surah-name scan matched `al-rahman`, but in context this is the
  divine Name — "al-Rahman al-Rahim, the Merciful, the Compassionate" — not a reference to Surah
  55. Explicitly downgraded with justification (not silently ignored). No action.

#### CS6 (script P6): `vicegerent` cross-book bleed — assessed FALSE POSITIVE
- **File:** ch05a-…-justice.txt (vicegerent/slave paragraphs)
- **Context:** P6 flags `vicegerent` as belonging to degrees-of-excellence's mangle-map. It is
  an ordinary English rendering of khalifa ("God's vicegerent upon the earth") and central to
  this chapter's argument. No cross-book contamination; no action.

#### A3: Quranic translation provenance not named inline (book-wide convention)
- **File:** ch05a-…-justice.txt (the 4 Quranic quotations)
- **Context:** the 4 Quranic quotations are rendered in English with plain-English references
  but no inline translator attribution. The renderings are the source essayist's own
  (Shah-Kazemi, *Justice and Remembrance*), and all sibling chapters shipped under the same
  convention. Recorded as advisory rather than escalated to a per-chapter P0 to stay consistent
  with the shipped set; recommend the human confirm the book-wide translation-provenance
  convention once.

#### R4: framing `## Do not` omits the formal-transition DENY list (book-wide framing style)
- **File:** …/EP05-…/00-framing.md:34
- **Context:** the DENY block names platforms (Twitter, social media, algorithm) + surprise
  fillers (wow, right?, Exactly) but not the R-NOFORMAL essay transitions (Firstly, Secondly,
  In conclusion…). Not auto-inserted to keep EP05 in sync with the sibling framings and clear of
  the framing char-gate; retained for a book-wide framing-style pass.

#### B5: 79 em-dashes in chapter prose (deliberately preserved)
- **File:** ch05a-…-justice.txt
- **Context:** 79 em-dashes. Not auto-fixed — the build gate is silent on them (B5 is not
  enforced by the v2.6 code authority) and all sibling chapters shipped with them intact.
  Mass-rewriting 79 spans of exposition would be an unreviewed content change out of step with
  the book's house style. Noted for the record only.

### Pronunciation NOTE (N3 — not a flag)

`ihsan` and `fitra` have no settled spoken form in the cross-book ledger. The framing handles
both by substitution (`- ihsan: substitute *spiritual excellence*`, `- fitra: substitute *the
primordial nature*`), which is valid and keeps them out of the audio layer. If they are ever to
be spoken, settle by ear: `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos`.

## Health metrics

| Chapter | Words | Band | Quran cites | Citation form | Doctrinal | Phonetic |
|---|---|---|---|---|---|---|
| ch05a | 5,897 | extended (5,500–9,500) — IN BAND | 4 | all canonical `(chapter N, verse M)` | 0 findings | ihsan/fitra substituted; 0 inline phonetic parens |

**Framing (EP05):** 701 words (within the 200–3,500 extended band). Warm one-sentence welcome +
book-name + spine present (H1/H2); spine repeated at pivot + close; DENY-modernize + DENY-surprise
present (M1/M2); N2 bullet-form pronunciation + N4 no-read-aloud guard present; name-discipline
block present (J1); host roles A=scholar / B=seeker with voice/gender declared (Q1/Q2/Q4).
Concept H2 sections in the chapter: 3 (Justice beyond fairness / Justice as the nature of God /
Becoming like God) — within the ≤3 density target; ch05a is NOT in the P10 over-dense list.

Chapter honorific glyphs: ﷺ ×1, (ع) ×8 — no honorific-repetition (O1 clean). No HTML comments,
no `[VERIFY]`/`[CONTEXT]` markers, no cross-episode literal refs.
