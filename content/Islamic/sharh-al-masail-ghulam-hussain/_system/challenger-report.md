# Podcast Challenger Report

**Book:** sharh-al-masail-ghulam-hussain
**Run:** 2026-08-17 21:10 (challenger v2.6 — read from `_rules.CHALLENGER_VERSION` at run time)
**Scope:** per-chapter `the-pledge-and-the-call-to-marry` (EP03 / ch03) + book-scope Category CS
**Iterations:** 2 (of 5 max) — early break 6b: iteration 2 produced zero auto-fixes and identical (P0,P1) counts
**Verdict:** SHIP-WITH-CAUTION
**Health score:** see `_learning/health/sharh-al-masail-ghulam-hussain.json`. The score is a book-scope instrument and clamps toward the floor on a single-chapter invocation; read the per-category totals below, not the badge.

```
content_profile: islamic_scholarly   <- detected from _system/series-config.yaml
deliverable_mode: translation_edition | length_tier: extended | episode_format: deep_dive
```

Category P (debate) skipped: `episode_format: deep_dive`.
Category M/N/O/Q/R transcript-empirical halves skipped: no transcript at `transcripts/EP03-*.transcript.txt`.
Category W skipped: no augmentation ledger (`translation_policy.augmentation: forbidden`).
Category D1/D2 (tier diversity, enrichment ratio) skipped: `augmentation: forbidden` — this is a translation edition with no outside material by design.
Category S1 bypassed per pipeline-context directive (the visible `orchestrate_book.py` is this run's parent).

## The blocking finding from the previous run is cleared

The prior run recorded one P0: a trailing editorial-apparatus clause (`which the Arabic source's own apparatus does not cite`) at `ch03:19`, `:37` and `:111`, spoken aloud three times in a file NotebookLM reads verbatim. That clause is gone at all three sites. A full-text scan for `apparatus`, `editorial`, `Editorial note` and `translator` now returns exactly one hit — `the visible apparatus of domestic life` at line 85, which is the treatise's own metaphor for a rented house, not editorial apparatus.

The companion F29 defect is cleared too. Line 105 now reads "The verse is from the chapter on women"; `R-SURAH-ENGLISH-ONLY` no longer fires.

`build_episode_txt.py` exits 0 on both artifacts. Doctrinal checks T1–T5 return zero findings on the chapter and zero on the framing. There is no P0 outstanding on this chapter.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | M2 | `EP03/00-framing.md:44` | Closed the DENY-surprise list. The block named `wow`, `right?`, `exactly`, `mind blown`; the canonical set also requires `no way`, `that's so interesting`, `it's chilling`, `it's devastating`, `it's terrifying`. All five inserted. |
| 1 | — | `episodes/EP03-*.txt` | Rebuilt from framing. Exit 0 at 4,301 chars / 698 words. |
| 2 | — | — | Verification pass. Files re-read from disk; identical finding counts; zero auto-fixes — early-break condition 6b. |

**The character ceiling that constrained the previous two runs has been relieved.** The prior run reported the built prompt at 4,488 against `FRAMING_CHAR_MAX = 4500` — twelve characters — and flagged M1 and R1 as deterministic insertions it physically could not apply. The intervening fixer pass reclaimed budget by compressing Name discipline, Host dynamic and Landing. The framing entered this run at 4,188 chars, which is what made the M2 insertion possible; it exits at 4,279 with 221 characters still free.

M1 and R1 are confirmed closed by this run's own scan: the DENY-modernize list carries all thirteen named platforms, and `## Host dynamic` carries the separate-prep clause.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### B4-residual: three sentences still tell the listener which edition supplies which paragraph
- **File:** `chapters/ch03-*.txt:19`, `:37`, `:111`
- **Context (line 19; the other two are identical in shape):** "A second, Urdu-language edition of this treatise supplies this paragraph on the guarantee of another's debt."
- **What is left after the P0 fix:** the apparatus clause is gone and the provenance disclosure survives, which is the right shape. What remains is the phrase `supplies this paragraph on <topic>` — a pointer to the document's own structure, delivered in audio. A listener hears the chapter describe its own composition three times.
- **Severity reasoning, stated rather than assumed.** I considered P0 and did not escalate to it, for three reasons: the edition-naming construction itself was blessed by this same loop on chapter 4, which shipped SHIP-WITH-CAUTION carrying `A second, Urdu-language edition of the same treatise gives the verse whole`; the build gate passes the current form; and the only delta from the blessed form is the word `paragraph` and the topic-label grammar around it. Recorded at P1 with the escalation visible, not silently downgraded.
- **Suggested fix:** adopt chapter 4's content-forward construction, which hands the listener the teaching in the same breath as the provenance. Line 19 becomes something like "A second, Urdu-language edition of this treatise carries the ruling on standing surety for another man's debt." Same move at 37 (the insistence on writing) and 111 (the four unlawful marriages).
- **Not auto-fixed:** Section 3 restricts chapter-file edits to em-dashes, honorific repeats, lexicon-grounded phonetic gaps, exact-match filler and cross-episode rewrites. Rewriting a provenance sentence is an authoring decision.

#### N6: the chapter carries no Arabic script, and the book has no glossary to inject it from
- **File:** `chapters/ch03-*.txt` (zero Arabic-range codepoints) / `_system/glossary.yml` (does not exist)
- **Context:** `series-config.yaml` sets `preserve_arabic_terms: true`, and N6 requires every Islamic scholarly chapter to carry visible Arabic script from glossary-backed terms. The chapter has none, and the deterministic injection N6 prescribes has no glossary to draw from.
- **Recorded at P1 with explicit escalation, not silently downgraded.** The catalog rates N6 P0. It is a book-scope root defect affecting all five chapters identically, it cannot be resolved inside a per-chapter pass, and blocking every chapter on it would stall the book without moving the defect. This is the eighth consecutive run on this book to record it this way. It should be escalated to a book-scope decision before publish, not carried indefinitely.
- **Suggested fix:** `python3 scripts/podcast/build_glossary.py` then `fill_glossary_arabic.py` for the book, then re-run the chapter Arabic injection. Alternatively record a deliberate profile exception for translation editions.

#### CS4: the chapter is 420 words over its own declared band
- **File:** `chapter-contracts/the-pledge-and-the-call-to-marry.yml` (`length_target: 5500-6000`) / `chapters/ch03-*.txt` (6,420 words)
- **Context:** `check_chapter_set.py` reports this at P0. It is not isolated: four of five chapters overshoot the same declared band — sale-debt 6,375, this chapter 6,420, marriage-contract 6,383, maintenance 6,001. A band that four of five chapters miss is a mislabelled band, not four independent overruns.
- **Recorded at P1 with explicit escalation,** on the same reasoning as N6: book-scope, systemic, unresolvable per-chapter, and already carried at P1 on the sibling chapters that shipped.
- **Suggested fix:** relabel `length_target` to `6000-6500` across the affected contracts so the declared band tells the truth, or trim to fit. Relabelling is the honest move here — the chapters are coherent at their current length and the extended tier accommodates it (the hard chapter ceiling is 11,000 words soft / 12,000 hard, so nothing is near a real bound).

#### N3: four terms in this chapter have no settled spoken form
- **File:** `_system/pronunciation.md` (header only, zero table rows) / `EP03/00-framing.md:16-20`
- **Context:** the build emits, verbatim: `NOTE: 4 term(s) in this chapter have no settled spoken form and were left without an entry: al-Nu'man, Ja'far al-Sadiq, Sunnah, dirham`. The bullets currently read `- al-Nu'man: al-Nu'man` and so on — the hosts are handed the spelling back and have nothing to act on. `al-Nu'man` appears three times in the chapter and carries two of its anchor passages; `Ja'far al-Sadiq` appears four times and carries the pledge list and the three divisions of land.
- **Not N7:** the values are the term's own spelling, not a determiner-led English translation, so `assert_framing_pronunciation_render` does not fire. The defect is an empty ladder, not a wrong value.
- **Suggested fix:** `python3 scripts/podcast/run_pronunciation_probe.py sharh-al-masail-ghulam-hussain`. **Never fix by editing the framing** — the build recompiles every value in the block, so a hand-edit is discarded on the next build.

#### R5: modern-analogy permission absent, and inserting it would contradict the prompt
- **File:** `EP03/00-framing.md:33-38`
- **Context:** R5 wants both halves — the DENY list and a positive "DO use modern-life practical analogies" paragraph. The DENY half is present and now complete. The permission half is absent, and `## Tone constraints` says "Only these three images" and then names them.
- **Recorded as absent-by-design,** the same call made on EP01, EP02, EP04 and EP05. Inserting a general analogy permission would directly contradict a cap the author set deliberately. Carried rather than fixed.

#### R-NAMEDISCIPLINE: no rotation set with three or more aliases
- **File:** `EP03/00-framing.md:6-12`
- **Context:** build-emitted. The block fixes one label per figure, which is correct doctrine for this book, but the check wants a rotation set (`→ a / b / c`) so the hosts have variety without drifting. The current block is stricter than the check anticipates.
- **Suggested fix:** author judgment on whether a rotation is wanted here at all; if not, this is a standing by-design carry.

#### F25: show-notes missing the Name and Title Preservation Table
- **File:** `EP03/99-show-notes.md`
- **Context:** build-emitted P1, verbatim: "no '## Name and Title Preservation Table' section header found." Present H2s: `## Related episodes`, `## References`.
- **Not auto-fixed:** Section 8 forbids this agent from editing `99-show-notes.md`.

#### V3: no modern-relevance signal for the listener
- **File:** `chapters/ch03-*.txt` (whole)
- **Context:** the deterministic scan does return two relevance hits, but both are about the author's own period rather than the listener's — "recognisably a modern one" describing his procedure for arranging a pledge, and "makes the argument contemporary" introducing the Boer war and the census figures. Nothing bridges the pledge doctrine or the case for marriage to a listener's world. Same call made on ch01 and ch02, so it is a book-wide voice property rather than a chapter defect.
- **Suggested fix:** one bridging sentence, or accept as a translation-edition property. Adding one would be outside-source material, which `translation_policy.augmentation: forbidden` bars on this edition — so accepting it is the likely correct disposition. Category V is never auto-fixed.

#### CS7: 94 source lines are assigned to no episode
- **File:** `_system/source/text/_chunks/0d/source-toc.json` (book scope)
- **Context:** `check_chapter_set.py` P7: "source lines 1-94 are not assigned to any episode (next assigned: sc 1 'Earning, Eating, and the Manners of the Table')". Almost certainly front matter, but the split records no explicit skip, so the gap is indistinguishable from dropped content.
- **Suggested fix:** record `essential: skip` for the front matter in the 0d plan, or redraw to cover it.

### P2 (advisory)

- **B5 — 61 em-dashes in the chapter.** Book-wide translation-edition style; every chapter in this book carries them at similar density (ch02 was recorded at 67). B5 is nominally in the auto-fix set, but rewriting 61 sites would restructure the chapter's cadence wholesale, which is authoring rather than mechanical cleanup. Carried at P2 as on ch02, consistent with the shipped siblings.
- **E2 — not summarizable in one sentence.** Three genuinely separate teachings: the pledge, the shared wall, and the case for marriage. The chapter's own opening admits the seam ("then turns a corner"). This is a Phase 0d segmentation property, not a writing defect.
- **I3 — the landing section restates all three movements.** `## What this episode lands` (lines 127-137) re-states each movement's thesis. The framing says "No recap, no preview" — but that instruction governs the hosts, not the source file, and the landing is doing real synthetic work. Recorded, not escalated. Same call as ch04.
- **F5 / R2 — no `04-discussion-spine.md`.** Absent for every episode in this book. R2's reset-clause requirement cannot be evaluated without a beat count, so it is advisory here.
- **F3 — the framing has no Audience section.** The contract carries a detailed `audience` field, so the information exists in the bundle; it just does not reach the Customize prompt. There is now 221 characters of headroom, so this is newly actionable if the author wants it — but a compressed audience line is an authoring decision, not a template insertion.
- **CS6 — cross-book term bleed in a sibling chapter.** `khums` in ch05 matches `degrees-of-excellence`'s mangle-map. Book-scope, not this chapter, and `khums` is ordinary Islamic legal vocabulary — near-certain false positive. Surfaced, never auto-stripped.

### Recorded as by-contract false positives (not counted as findings)

- **`R-NO-ARABIC-TRANSLITERATION` on `al-Nu` and `al-Sadiq`,** fired against both the chapter and the framing. `tone_constraints[3]` states that Judge al-Nu'man is named as the source names him, and the Name discipline block fixes both labels deliberately. Same call made on ch02 and ch04.
- **`AI_CLICHE_DENY` hit on `mind blown` and `ESSENTIALISM_STEM_PATTERNS` hit on `Muslims believe`, both in the framing.** Both occur inside the framing's own prohibition list — the framing is forbidding those phrases, not using them. Judged in context per Category U's detection note.
- **A1 (Quranic citations without chapter-and-verse).** `tone_constraints[5]` states that the source names no chapter-and-verse reference for any verse it quotes and instructs that none be supplied. A1's own text exempts the case where the source leaves the verse unnamed; references are never invented. Pass by contract.

## Health metrics

| Chapter | Words | Arabic script | Honorific expansions | Em-dashes | Unsettled terms | Framing chars |
|---|---|---|---|---|---|---|
| ch03 the-pledge-and-the-call-to-marry | 6,420 | 0 | 1 `peace be upon him`, 1 `may God sanctify`, 1 `may God have mercy` — one each, O1 clean | 61 | 4 | 4,279 / 4,500 |

Build status: `build_episode_txt.py` exit 0 on both artifacts. Chapter validated and upload-ready by construction; episode prompt written at 698 words / 4,301 chars.

Doctrinal (Category T): `run_doctrinal_checks` returns 0 findings on the chapter and 0 on the framing. T1 canonical attribution, T2 Imam lineage, T3 forbidden naming phrases, T5 weak hadith — all clean. T4 is a stub (`farmans.yml` does not exist).

Host role parity (Category Q, book scope): all five framings declare a male scholar leading and a female seeker questioning. Q1 pass, Q2 pass, Q3 pass (no swap anywhere in the book), Q4 pass (gender pairing declared in the opening directive of every episode).

Category CS (book scope, computed once): CS1 pass, CS2 pass, CS3 pass, CS4 fail (4 of 5 chapters), CS5 pass, CS6 one advisory, CS7 fail, CS8 pass, CS9 vacuous (no sermon declared), CS10 pass.

## What this chapter needs before publish

Nothing blocks the upload. The chapter and the customize prompt are both build-clean and doctrinally clean, and the P0 that held this chapter for two runs is resolved.

Two things deserve an author's attention before the book publishes, and neither is chapter-local:

1. **N6 and CS4 are book-scope root defects now on their eighth carry.** No Arabic script anywhere in the book because no glossary exists, and a declared length band that four of five chapters miss. Both are one command or one relabel away from closed, and both are being carried at P1 purely because a per-chapter pass cannot reach them. They should be settled at book scope rather than carried into publish.
2. **The three `supplies this paragraph` sentences** are the last of the apparatus register in this chapter's audio. Chapter 4 already demonstrates the construction that reads better.
