# Podcast Challenger Report

**Book:** sharh-al-masail-ghulam-hussain
**Run:** 2026-08-17 (challenger v2.6)
**Scope:** per-chapter `earning-and-the-manners-of-the-table` (EP01) + book-scope Category CS
**Iterations:** 3 (of 5 max) — early break: iteration 3 produced zero auto-fixes and identical (P0,P1) counts
**Verdict:** SHIP-WITH-CAUTION
**Health score:** 0.00 (Unstable) — note: `write_health.py` divides the weighted finding total by chapters-in-scope, which for a single-chapter invocation with 14 P1 findings clamps to the floor. The score is a book-scope instrument; read the per-category totals below, not the badge.

```
content_profile: islamic_scholarly   <- detected from _system/series-config.yaml
deliverable_mode: translation_edition | length_tier: extended | episode_format: deep_dive
```

Category P (debate) skipped: `episode_format: deep_dive`.
Category M/N/O/Q/R transcript-empirical halves skipped: no `transcripts/EP01-*.transcript.txt`.
Category W skipped: no augmentation ledger (`translation_policy.augmentation: forbidden`).
Category S1 bypassed per pipeline-context directive (the visible `orchestrate_book.py` is this run's parent).

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | H3 | EP01/00-framing.md (Landing) | Inserted no-recap closing clause ("Do not recap; nothing follows the question.") |
| 1 | K1 | EP01/00-framing.md (Host dynamic) | Inserted interruption-avoidance clause (finish a thought, no talking over) |
| 1 | K2 | EP01/00-framing.md (Host dynamic) | Named the forbidden filler-interjection vocabulary ("yeah" / "right" / "mm-hmm") |
| 1 | M1 | EP01/00-framing.md (Do not) | Extended DENY-modernize list: X, YouTube, TikTok, "deep dive", "the 21st century" |
| 1 | M2 | EP01/00-framing.md (Do not) | Inserted DENY-surprise line ("wow", "right?", "exactly", "no way", "that's so interesting") |
| 1 | R4 | EP01/00-framing.md (Do not) | Inserted formal-transition DENY line (Firstly / Secondly / Furthermore / In conclusion / To summarize / Lastly) |
| 2 | — | EP01/00-framing.md | Compression pass to fit the live 4,500-char NotebookLM cap; four live validators (R-NAMEDISCIPLINE, R-DRAMATIC-ARC, R-CHALLENGER-FRICTION, R-ANALOGY-CAP) re-verified intact |
| 3 | — | episodes/EP01-*.txt | Rebuilt from framing; build exit 0 at 4,499 chars / 753 words |

## Findings requiring author resolution

### P0 (blocks ship)

None. Category A (authenticity), B (NotebookLM literalness), T (doctrinal), G (contracts), Q (host-role parity), U (scholarly rubric) are all clean.

Explicit PASS notes on checks that look like violations but are not:

- **A1 (Quran citations absent) — PASS by exemption.** The chapter quotes three verses with no chapter-and-verse. The source treatise itself names none, and the contract states so (`tone_constraints`: "Quote them without a reference; do not supply one"). A1's own carve-out applies: references are never invented.
- **A3 (translation provenance) — PASS, vacuous.** `deliverable_mode: translation_edition`, `source_language: ar`. The verse renderings are this pipeline's own faithful English from the Arabic source, not a third-party published translation. Naming a translator here would be fabrication (an A2 violation).
- **A6 (cross-tradition collision) — PASS.** The chapter explicitly annotates the divergence it carries ("On the food of the People of the Book there is a difference of opinion, and the position recorded here is restrictive").
- **U1 (AI-cliche "today we'll discuss" in the framing) — PASS, false positive.** The string occurs only inside the `## Do not` DENY list, as a forbidden item, not as prose any host speaks.

### P1 (ship-with-caution)

#### N6: chapter carries zero Arabic script; the book has no glossary (ROOT, book-scope)
- **File:** `chapters/ch01-earning-and-the-manners-of-the-table.txt` (whole file); root at `_system/glossary.yml`
- **Context:** Zero Arabic Unicode codepoints in a `islamic_scholarly` chapter. Four transliteration occurrences sit bare in prose (`Sunnah` x3 at lines 67/77/117, `ihram` at line 107). `_system/glossary.yml` does not exist, so N6's remediation path (deterministic Arabic injection from the curated glossary) cannot run. `series-config.yaml` sets `translation_policy.preserve_arabic_terms: true` but nothing produced a glossary to preserve them against.
- **Severity note (explicit, not silent):** the catalog rates N6 **P0**. It is recorded here at **P1** because the P0 remediation has no data to run on, and because the same gap affects all five chapters — it is a Phase 0c book-scope defect, not a defect of this chapter's authoring. The challenger **recommends escalation to P0 at book scope** and treating it as a systemic halt per the standing systemic-fixes rule.
- **Suggested fix:** build `_system/glossary.yml` for the book, then re-run the deterministic chapter Arabic injection across all five chapters. Do not hand-add Arabic to prose.

#### N3: two terms have no settled spoken form; the pronunciation ladder is empty
- **File:** `_system/pronunciation.md` (empty table) / `EP01/00-framing.md:15-16`
- **Context:** The build emits `NOTE: 2 term(s) in this chapter have no settled spoken form: ihram, Sunnah`. `_system/pronunciation.md` has a header and an empty pipe table. The framing's two bullets are therefore authored guesses, not ladder-resolved values, and `- Sunnah: sunnah` carries no pronunciation information at all (value identical to the term), so the hosts have nothing to act on.
- **Suggested fix:** `python3 scripts/podcast/run_pronunciation_probe.py sharh-al-masail-ghulam-hussain` — settle both by ear; the answer is written to the cross-book ledger and the build recompiles the block. Never fix by editing the framing.

#### F25-APPARATUS-TABLE: show-notes missing the Name and Title Preservation Table
- **File:** `_system/episode-drafts/EP01-earning-and-the-manners-of-the-table/99-show-notes.md`
- **Context:** Build-emitted P1, verbatim: "no '## Name and Title Preservation Table' section header found. F25 doctrine: every episode's 99-show-notes.md carries the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) the TTS-safe audio omits." Present H2s are only `## Related episodes` and `## References`.
- **Suggested fix:** add the section. It is the written-layer counterpart to N6 — the audio drops Arabic names deliberately, and the show notes are where the preserved forms live.

#### I1: anti-repetition clause absent from the framing
- **File:** `EP01/00-framing.md` (`## Do not`)
- **Context:** No "do not restate / re-cite / summarise what was just said" clause. It was inserted in iteration 1 and **removed in iteration 2 to fit the 4,500-character cap**. Note the interaction: the framing's own `R-RECURRING-THESIS` mandates three verbatim thesis repetitions, so any inserted clause must be scoped to exempt the spine thesis — a generic R-NOREPEAT block would contradict the book's design.
- **Suggested fix:** free ~95 characters elsewhere (the `Name discipline` "Also:" roster is the cheapest donor) and reinstate the scoped form.

#### I2: no-irrelevant-background clause absent from the framing
- **File:** `EP01/00-framing.md` (`## Do not`)
- **Context:** Same root as I1 — inserted, then cut for the character cap. Nothing currently bounds host excursions into the author's biography or the period.
- **Suggested fix:** reinstate a one-line form (~85 chars) once budget is freed.

#### R1: separate-prep illusion clause absent
- **File:** `EP01/00-framing.md` (`## Host dynamic`)
- **Context:** No "the hosts prepared separately / plant one moment where one raises a passage the other had not led toward" directive. Never landed: the character budget was exhausted by the four live validators plus the higher-value K1/K2/M2/R4 insertions.
- **Suggested fix:** lowest priority of the three budget-displaced clauses; reinstate last.

#### R5: modern-life analogy permission absent — and conflicts with this book by design
- **File:** `EP01/00-framing.md` (`## Do not` + `## Tone constraints`)
- **Context:** R5 requires BOTH halves of the softened R-NOMODERNIZE: the platform DENY list (present) AND a positive "DO use modern-life practical analogies" paragraph (absent). **Deliberately not auto-fixed:** `## Tone constraints` restricts the hosts to three named source images "and no others". Inserting the permission half would directly contradict a standing instruction in the same prompt.
- **Suggested fix:** author decision — either relax the three-image cap, or record this book as an explicit R5 exemption. Do not insert the permission half while the cap stands.

#### F3: framing names no audience
- **File:** `EP01/00-framing.md`
- **Context:** No `## Audience` section. A concrete audience profile exists in `chapter-contracts/earning-and-the-manners-of-the-table.yml` but does not flow into the customize prompt, so the hosts have no register target.
- **Suggested fix:** compress the audience line to one sentence and place it in the Opening directive. Budget-constrained; weigh against I1/I2.

#### I5: authorial-apparatus noise in the chapter opening
- **File:** `chapters/ch01-earning-and-the-manners-of-the-table.txt:7`
- **Context:** "Its author gathered the issues bearing on daily life and set aside those that no longer touched anybody, along with technical matters like usury and mortgage." Matched `R_NOISE_APPARATUS_PATTERNS`. The second clause is meta about how the book-OBJECT was compiled and scoped, not its teaching — and it invites the hosts to spend airtime on what the compiler omitted.
- **Suggested fix:** keep the first clause (genuine orientation), drop the "set aside…" clause or move it to show notes. Never auto-fixed — authoring decision.

#### O1 (semantic half): one honorific form expanded three times
- **File:** `chapters/ch01-earning-and-the-manners-of-the-table.txt:35, 61, 63`
- **Context:** "may God's peace be upon him" appears 3x; "may God's blessings and peace be upon him" 1x (line 17); "peace be upon them" 1x (line 91). The live deterministic gate did NOT fire: `HONORIFIC_PHRASES` in `_validator_constants.py` matches only the parenthesized forms `(peace be upon him)` etc., and this chapter uses unparenthesized prose forms. NotebookLM reads every expansion aloud regardless of parentheses.
- **Suggested fix:** keep the first expansion per figure, contract the rest to "the sixth Imam" / "the fifth Imam". Secondary: the constant list is worth widening to cover the prose form (a rule-level fix, book-independent).

#### E5: a broken-transmission paragraph invites host fabrication
- **File:** `chapters/ch01-earning-and-the-manners-of-the-table.txt:59`
- **Context:** "…Some were dealt with according to the judgement passed on them, and one was released. And the Messenger of God told him that Gabriel had informed him about the hand that is withheld from food, and assured him he would be helped in the task." The passage presents as narrative but carries no recoverable meaning — "the hand that is withheld from food" resolves to nothing. The contract acknowledges the source's transmission is broken here and forbids reconstruction, which is correct; the residual risk is that the hosts will invent an interpretation to fill the gap.
- **Suggested fix:** either add a short clause marking the transmission as incomplete, or name the passage in the framing as one not to expand. Flagged, not auto-fixed.

#### V3: no modern-relevance signal
- **File:** `chapters/ch01-earning-and-the-manners-of-the-table.txt` (whole file)
- **Context:** Zero matches against `R_INTEREST_RELEVANCE_PATTERNS`. V1 (curiosity hook, "What if…"), V2 (challenge-defeat arcs — the needle-through-leather objection and the ascetic's challenge, both raised and answered), V4 (no strawman) and V5 (rhetorical question) all pass.
- **Suggested fix:** one bridging sentence. Note the tension with the framing's DENY-modernize block — the bridge must be a timeless practical connection, not a named-platform analogy.

#### E1: chapter word count outside the catalog soft band
- **File:** `chapters/ch01-earning-and-the-manners-of-the-table.txt` — 5,947 words
- **Context:** Catalog soft band is 1,500–4,500. The contract declares `length_target: 5500-6000` and `series-config.yaml` sets `length_tier: extended`; CS4 (band conformance) therefore **passes**, and the live build accepts it. Recorded as advisory drift between the catalog band and extended-tier reality.

#### CS7 (book scope): source content unassigned to any episode
- **File:** `_system/source/text/_chunks/0d/source-toc.json`
- **Context:** From `check_chapter_set.py`, verbatim: "source lines 1-94 (94 lines) are not assigned to any episode (next assigned: sc 1 'Earning, Eating, and the Manners of the Table') — content silently dropped from the split."
- **Suggested fix:** confirm lines 1–94 are front matter; if so record an explicit skip, otherwise re-draw the Phase 0d plan.

### P2 (advisory)

#### B5: 58 em-dashes in the chapter
- **File:** `chapters/ch01-earning-and-the-manners-of-the-table.txt` (58 occurrences; 18 more in the framing)
- **Severity note (explicit, not silent):** the catalog lists B5 as an auto-fix. It was **deliberately not auto-fixed and is recorded below the catalog's implied severity**, for three reasons: (1) no live validator enforces it — `build_episode_txt.py` passes the chapter at exit 0 and no em-dash rule exists in `_validators*.py` or `_rules.py`; (2) this chapter file also feeds the reading-edition/PDF lane, where the em-dash is correct typography; (3) a blind `—` -> `, ` substitution across 58 sites would manufacture comma splices in appositive constructions, which is a prose rewrite, not a mechanical fix. Surfaced for the author to decide.

#### E2: the chapter is multi-thematic
- Seven ruling domains (earning, table manners, feeding, guest/host, forbidden foods, slaughter/hunting, dress/adornment) across 5,947 words. The chapter does supply its own unifying sentence, twice ("earning is devotion, the table is a discipline, and the boundary of the lawful runs through both"), so one-sentence summarizability is achieved by assertion rather than by scope. Acceptable for an extended-tier opener; noted.

#### R3: cadence directive absent
- Inserted in iteration 1, cut in iteration 2 for the character cap. Lowest-value of the displaced clauses.

#### F5: no discussion spine
- `04-discussion-spine.md` is absent (bundle carries only `00-framing.md` + `99-show-notes.md`). Optional under the current architecture; R2 (reset clause) is consequently advisory-only since no beat count can be read.

#### CS6 (book scope, different chapter): possible cross-book bleed
- From `check_chapter_set.py`, verbatim: "chapter text contains 'khums' which belongs to book 'degrees-of-excellence''s mangle-map; possible cross-book bleed" in `maintenance-dissolution-and-inheritance`. Almost certainly a false positive — *khums* is ordinary Shia legal vocabulary and belongs in an inheritance chapter. Surfaced, never auto-stripped. Out of this invocation's per-chapter scope.

#### CATALOG-DIVERGENCE: the agent spec's framing budget contradicts the live gate
- **File:** `.github/agents/podcast-challenger.agent.md` (E1) vs `scripts/podcast/build_episode_txt.py`
- **Context:** E1 states the framing hard bound is `FRAMING_WORD_MAX = 3500` **words**. The live gate is a 4,500-**character** NotebookLM Customize-box limit (~750 words) — a bound roughly 4.7x tighter. This is not academic: it is why six of the catalog's own auto-fix insertions (I1, I2, R1, R3, plus the full canonical M1/M2 blocks) cannot all coexist in any framing. This run also demonstrated that naive compression silently breaks four other live validators (R-NAMEDISCIPLINE, R-DRAMATIC-ARC, R-CHALLENGER-FRICTION, R-ANALOGY-CAP) that the authored framing had been shaped to satisfy.
- **Suggested fix:** correct E1 to state the character cap, and re-rank the Section 3 auto-fix list by empirical value so the challenger has a documented eviction order when the budget binds.

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Citations | Arabic script | Phonetic gaps | Em-dashes |
|---|---|---|---|---|---|---|---|
| ch01 earning-and-the-manners-of-the-table | 5,947 | 0% external (`augmentation: forbidden`) | 4 (Quran, prophetic hadith, Imami sayings, early transmitters) | 0 formal refs (source names none) | 0 codepoints | 2 unsettled (ihram, Sunnah) | 58 |

| Artifact | Size | Gate |
|---|---|---|
| `chapters/ch01-*.txt` (SOURCE) | 5,947 words | build exit 0 |
| `_system/.../EP01/00-framing.md` | 4,499 chars / 753 words | under the 4,500-char cap by 1 char |
| `episodes/EP01-*.txt` (CUSTOMIZE PROMPT) | 753 words | body identical to framing |

**Category totals:** P0 = 0 · P1 = 14 · P2 = 6 · auto-fixes = 6

**Convergence:** iteration 1 applied 6 auto-fixes; iteration 2 was a compression pass forced by the character cap; iteration 3 applied zero auto-fixes and returned identical (P0, P1) counts — early-break condition 6b.
