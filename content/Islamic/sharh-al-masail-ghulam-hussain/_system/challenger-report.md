# Podcast Challenger Report

**Book:** sharh-al-masail-ghulam-hussain
**Run:** 2026-08-17 (challenger v2.6 — read from `_rules.CHALLENGER_VERSION` at run time)
**Scope:** per-chapter `maintenance-dissolution-and-inheritance` (EP05 / ch05) + book-scope Category CS
**Iterations:** 2 (of 5 max) — early break 6b: iteration 2 re-read byte-identical files, produced zero auto-fixes, identical (P0,P1) counts
**Verdict:** BLOCKED

```
content_profile: islamic_scholarly   <- detected from _system/series-config.yaml
deliverable_mode: translation_edition | length_tier: extended | episode_format: deep_dive
source_tradition: islam (Ismaili lineage pack) | audio_engine: notebooklm
```

Category P (debate) skipped: `episode_format: deep_dive`.
Category M/N/O/Q/R transcript-empirical halves skipped: no transcript at `transcripts/EP05-*.transcript.txt` (directory holds only `_README.md`).
Category W skipped: no augmentation ledger (`translation_policy.augmentation: forbidden`).
Category D1/D2 (tier diversity, enrichment ratio) skipped: `augmentation: forbidden` — a translation edition carries no outside material by design.
Category S1 bypassed per pipeline-context directive (the visible `orchestrate_book.py` is this run's parent, not a concurrent run).

## What changed since the previous run on this chapter

**T2 is CLOSED, verified line by line.** The previous run blocked on `EP05/00-framing.md:10` instructing the hosts to speak "the fifth Imam" and "the sixth Imam" — Twelver ordinals in a book whose lineage pack counts Hassan as Imam 1 and therefore places al-Baqir at 4 and al-Sadiq at 5. The fixer pass took option (b) from that report and removed the ordinals rather than renumbering them. Line 10 now reads:

> `- The Imam on spending in obedience → "the Imam"; on wages after death → "the Imam of that generation."`

No counting convention is asserted in either direction, which is what the name-discipline layer exists to do. Cost +7 chars; the built prompt sits at 4,475 against `FRAMING_CHAR_MAX = 4500`. This finding is not carried forward for EP05.

**Nothing else about this chapter changed.** Both artifacts hash identical to the prior run's fixer-pass output (`594100d1…` chapter, `e6d56f76…` framing, `c19a9aaa…` built prompt), the build still exits 0 with the same three FLAG lines and the same 7-term NOTE, and `run_doctrinal_checks` still returns zero findings on both files.

**This run is BLOCKED on N6 alone**, unchanged and unresolved, and the entry below states the case against its own severity as well as for it, because the author's decision is what closes it.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | — | — | Full catalog run. Zero deterministic auto-fixes warranted. Every clause this agent is authorized to insert was verified present: H1 (line 4), H2 (line 4), H3 (line 45), I1 (line 50), I2 (line 26), K1 (line 35), K2 (line 48), M1 (line 48), M2 (line 48), N2 (lines 15–23, bullet form, no `Pronounce "X" as "Y"`), N4 (line 53), Q4 (line 4), R1 (line 34), R3 (line 42), R4 (line 49, all seven canonical transitions), F6 (lines 4, 45). O1 stands at a single honorific expansion. |
| 1 | R5 | `EP05/00-framing.md` | **Insertion declined, deliberately.** The only absent auto-fixable clause. See the P2 entry — the contract forbids the content it would authorize, and the character budget could not hold it regardless. |
| 1 | B5 | `chapters/ch05-*.txt` | **Auto-fix declined, deliberately.** See the P2 entry — recorded as a judgment call, not an oversight. |
| 2 | — | — | Verification pass. Both files re-read from disk and hashed identical to iteration 1; build re-run emitted the same three FLAG lines and the same NOTE; episode txt re-emitted byte-identical at 4,475 chars / 735 words. Early-break condition 6b. |

**No file was modified by this run.**

## Findings requiring author resolution

### P0 (blocks ship)

#### N6: the chapter carries no Arabic script, and the book has no glossary to inject it from

- **File:** `chapters/ch05-*.txt` (zero codepoints in the Arabic Unicode range, confirmed by scan) / `_system/glossary.yml` (**does not exist**)
- **Context:** N6 requires every Islamic scholarly chapter source to carry visible Arabic script drawn from glossary-backed terms, with pronunciation staying in the glossary and framing. The chapter has none, and the deterministic injection N6 prescribes has no glossary to draw from. Book-scope: all five chapters are identical in this respect.
- **This book is the outlier among its own peers.** Of the five books in the repo declaring `deliverable_mode: translation_edition`, four carry `_system/glossary.yml` — `mukhtasar-ul-asar-1`, `mukhtasar-ul-asar-2`, `spiritual-ethos`, `the-master-and-the-disciple`. This one does not. `series-config.yaml` sets `preserve_arabic_terms: true`, so the configuration asks for something the artifacts do not deliver.
- **The case AGAINST holding this at P0, stated openly, because the author should weigh it.** There is no N6 assertion anywhere in `_validators*.py` or `build_episode_txt.py` — a grep for an Arabic-script chapter gate returns one unrelated hit in the dormant dialogue validator. The spec names the Python rule modules as the contract and the build exits 0. The chapter contract pushes the other way in terms: `tone_constraints` instruct that *"Arabic terms appear in plain transliteration without diacritics"*, and the one rule the build DOES enforce here, F20, wants even those transliterations out of the spoken layer. A reasonable author could conclude that a TTS-safe translation edition is the profile exception N6 was never scoped for.
- **Why it is nonetheless recorded at P0 and not downgraded.** Nine consecutive runs on this book recorded N6 at P1 under a deferral rationale — that blocking every chapter on a book-scope defect would stall the book without moving the defect. The previous run retired that rationale on the ground that ch05 is the last chapter, so there is no later pass to defer into. That ground still holds. Nothing about N6 has changed since; only T2 has. Downgrading it now, on no new evidence, purely because the other P0 was fixed, is the "silently downgrade" move `_convergence.py` forbids, and it would manufacture a shippable verdict rather than earn one. The catalog value is P0 and this run reports the catalog value.
- **Suggested fix — either is acceptable, but it must be one of them.** (a) `python3 scripts/podcast/build_glossary.py` then `fill_glossary_arabic.py` for the book, then re-run the chapter Arabic injection across all five chapters. (b) Record a written profile exception for `deliverable_mode: translation_edition` in `series-config.yaml` and set `preserve_arabic_terms: false` so the configuration stops asking for what the contract forbids. Option (b) is defensible and cheap; what is not acceptable is a tenth run of standing silence.

### P1 (ship-with-caution)

#### N3: seven terms in this chapter have no settled spoken form

- **File:** `_system/pronunciation.md` (header only, zero table rows — verified) / `EP05/00-framing.md:15-23`
- **Context:** the build emits, verbatim: `NOTE: 7 term(s) in this chapter have no settled spoken form and were left without an entry: iddah, nushuz, khul'a, ila, zihar, li'an, waqf`. The bullets read `- iddah: iddah`, `- nushuz: nushuz` and so on — the hosts are handed the spelling back and have nothing to act on.
- **Why this chapter is the worst case in the book.** Seven unsettled terms and none incidental. `'iddah` is the counting rule the entire second movement turns on and is spoken throughout. `khul'a` is the wife's own instrument of release and carries an anchor passage. `nushuz` is the single condition that suspends maintenance. `ila'`, `zihar` and `li'an` are three of the five named forms of dissolution. An apostrophe-bearing term handed back as its own spelling is exactly the shape that produced *Archon* for *arkan* on `degrees-of-excellence`.
- **Not N7.** The values are each term's own spelling, not a determiner-led English translation, so `assert_framing_pronunciation_render` does not fire. The defect is an empty ladder, not a wrong value.
- **Suggested fix:** `python3 scripts/podcast/run_pronunciation_probe.py sharh-al-masail-ghulam-hussain`. **Never fix by editing the framing** — the build recompiles every value in the block from `_system/pronunciation.md`, so a hand-edit is discarded on the next build.

#### R-NO-ARABIC-TRANSLITERATION (F20): seven transliterations survive in the chapter, and the contract requires them to

- **File:** `chapters/ch05-*.txt`, build-emitted P1
- **Context, verbatim:** `7 Arabic transliterations detected. Sample: ['Abu Ja', 'al-Hasan', 'al-Husayn', 'al-Muttalib', 'al-Nu', 'al-Sadiq', 'al-Salim']. F20 doctrine: replace with English audio labels.`
- **A genuine standing conflict, not a defect to silently resolve.** The contract's `tone_constraints` instruct, in terms: *"Abu Ja'far Muhammad ibn 'Ali al-Salim, Ja'far al-Sadiq, Imam Ja'far al-Sadiq, Imam Abu Ja'far, our master al-Nu'man, our master the judge, al-Hasan ibn Ali, al-Husayn ibn Ali and the sons of Fatima are named as the source names them, damaged forms included, with no reconstruction."* F20 wants them gone from the spoken layer; the contract wants them preserved in the written source.
- **The architecture already resolves this, and the mitigation was re-verified this run.** Every name the build samples is mapped to an English audio label in the framing's Name discipline block: al-Hasan and al-Husayn to "his two grandsons", al-Nu'man to "the jurist", al-Muttalib to "the Prophet's clan and his grandfather's house", and al-Baqir and al-Sadiq now to "the Imam" and "the Imam of that generation" following the T2 fix. The chapter is the written SOURCE and keeps the names faithfully; the hosts never speak them. Left at P1 as the build sets it. Not to be "fixed" by stripping names from the source, which would break the contract.

#### R-NOMODERNIZE-STRICT: a false positive, and the framing must not be changed to satisfy it

- **File:** `EP05/00-framing.md`, build-emitted P1
- **Context, verbatim:** `framing: modern artifacts detected: ['deep dive', 'in our modern world', 'internet troll', 'cognitive behavioral therapy', 'algorithm', 'twitter', 'youtube', 'tiktok']`
- **Every one of those eight terms sits inside the `## Do not (never speak these)` block.** Verified this run by case-insensitive line scan: all eight resolve to line 48, and **zero** appear anywhere else in the framing. They are there because M1 and M2 require them to be there.
- **The same false positive fires on Category U1.** A scan of the framing against `_rules.AI_CLICHE_DENY` returns `deep dive`, `today we'll discuss` and `mind blown` — lines 48 and 49, both inside the DENY block, both prohibitions rather than usages. The chapter itself is clean against the full cliché list.
- **Diagnosis:** the validator substring-scans the whole framing rather than excluding the DENY block, so the framing is penalised for carrying the prohibition it is required to carry. Satisfying the flag would mean deleting the M1/M2 block and failing those checks instead.
- **Suggested fix — in the validator, not the content:** scope `assert_framing_no_modern_artifacts` (and the U1 scan) to the framing body, excluding the `## Do not` section. Until then this flag is expected on every correctly-authored framing in the repo and should be read as noise.

#### F25: the show notes carry no Name and Title Preservation Table

- **File:** `EP05/99-show-notes.md`, build-emitted P1
- **Context:** verified this run to carry only `## Related episodes` (line 9) and `## References` (line 13). F25 requires the written-layer apparatus — preserved Arabic and transliterations with a crosswalk to the English audio labels. This matters more here than usual, because the book deliberately strips seven proper names out of the audio (see F20); the crosswalk is the only place a reader can recover who "the jurist" or "the Imam of that generation" actually was.
- **Book-scope:** none of the five episodes has the table.
- **Out of this agent's edit surface** — `99-show-notes.md` is published-library apparatus and the challenger does not modify it.

#### CS7: ninety-four lines of source are assigned to no episode

- **File:** book-scope, from `check_chapter_set.py`
- **Context, verbatim:** `source lines 1-94 (94 lines) are not assigned to any episode (next assigned: sc 1 'Earning, Eating, and the Manners of the Table') — content silently dropped from the split`
- **Suggested fix:** either re-draw the Phase 0d plan to cover the gap, or record an explicit `essential: skip` if those 94 lines are genuine front matter. The point of the check is that the answer be written down rather than assumed.

### P2 (advisory)

#### B5: seventy-six em-dashes in the chapter — auto-fix declined, on the record

The catalog authorises this agent to replace `—` mechanically. **I did not, and the reasoning belongs in the report rather than in a silent skip.** Three things weigh against it. There is no em-dash constant anywhere in `_validator_constants.py`, `_validators.py` or `_rules.py`, and the build gate passes the chapter at exit 0 — the code, which the spec names as the authority, does not carry this rule. The density is uniform book-wide (58, 67, 61, 48, 76 across ch01–ch05), so it is authored house style, and four chapters have already shipped with it. And seventy-six substitutions across six thousand words is not reversible in effect even though it is reversible in bytes: it rewrites the rhythm of the whole chapter. If em-dashes are to come out of this book they should come out of all five chapters in one deliberate pass, not out of the last one as a side effect of the final gate.

#### R5: the modern-analogy permission clause is absent, and the contract requires it to be

R5 wants the `## Do not` block to carry a positive "DO use modern-life practical analogies" paragraph beside the DENY list. It is the one auto-fixable clause missing from this framing, and inserting it would be wrong twice over. The framing's Tone constraints say `Only these three images, all from the source`, and `translation_policy.augmentation` is `forbidden` — the clause would instruct the hosts to add material the deliverable mode prohibits. And the built prompt stands at 4,475 chars against a 4,500 hard gate, so the paragraph does not fit even if it were wanted. **V3** (modern-relevance signal in the chapter) is absent for the same contractual reason. Both recorded as deliberate, not missing.

#### The chapter frame headings say "this episode" inside the SOURCE file

`## Where this episode picks up` (line 3) and `## What this episode lands` (line 127). A source document that knows it is an episode is the shape B3 guards against, and NotebookLM reads these headings literally. It passes `META_PROSE_TELLS`, and it is the uniform house shape across all five chapters, so it is a book-wide authoring convention rather than a slip in ch05. Recorded so the convention is a decision rather than an accident.

#### CS6: `khums` flagged as cross-book bleed — false positive

`check_chapter_set.py` reports `chapter text contains 'khums' which belongs to book 'degrees-of-excellence''s mangle-map`. It appears once, at ch05 line 113, in its ordinary doctrinal sense (`his inheritance is purely his own, without the deduction of khums`), rendered from this book's own source. Common-term collision in the mangle-map scan. No action.

#### U5: the essentialism stem `in Islam,` — internal tradition, and the source's own words

ch05 line 49: *"the bitterness of separation after intimacy is, in Islam, like the parable of nakedness after being clothed."* The tradition-precedence rule puts an internal-tradition claim at P2, and this one is a faithful rendering of the treatise speaking about itself. No action.

#### F3 and R2: not measurable in this bundle

F3 (audience named concretely in the framing) — no framing in this book carries an Audience section; all five run the same eight-section house template, and the audience is named in the contract instead. R2 (reset clause when the spine exceeds five beats) — there is no `04-discussion-spine.md` in any bundle (EP05 holds only `00-framing.md` and `99-show-notes.md`), so there is no beat count to test against. F5 is unmeasurable for the same reason. Neither is a ch05 defect.

## Book-scope findings carried, not counted against this chapter's verdict

**T2 systemic (P0) — the ordinals survive everywhere except EP05.** The fix applied to this chapter's framing was scoped to EP05 only. Still carrying the Twelver count: `EP01/00-framing.md:10` (`the fifth Imam / the sixth Imam / the Prophet's grandson — fixed, never rotated`), `EP04/00-framing.md:11` (`the sixth Imam`), and chapter prose at `ch01:35, 53, 61, 65, 85, 113, 115, 117`, `ch02:73, 95`, `ch04:33, 49`. Four of those chapters are already through the loop. Per the standing systemic-fix rule this needs one book-wide pass — applying the same option (b) removal — before those four chapters are re-shipped. It is excluded from ch05's verdict arithmetic because ch05 and EP05 are now clean of it, and that exclusion is stated here so it cannot be read as a silent downgrade.

**CS4 (P0 x3):** three sibling chapters are over their declared band — `sale-debt-and-the-contracts-of-trade` at 6,375 words, `the-pledge-and-the-call-to-marry` at 6,420, `the-marriage-contract-and-its-bonds` at 6,383, all against `length_target: 5500-6000`. **`maintenance-dissolution-and-inheritance` is not among them** — it sits at 5,997, inside its band. The fix is per-contract and per-chapter: either trim to the band or relabel `length_target` honestly.

## What passed, so it is on the record

**Category A (authenticity) — clean.** No `[VERIFY CITATION]`, no `[CONTEXT NEEDED]`, no hadith numbers at all and therefore none fabricated. A1's semantic half is satisfied by its own exemption: the treatise names no chapter-and-verse for any verse it quotes, the contract instructs that none be supplied, and none is. A4 verified by hand against the canonical renderings — the grain-with-seven-ears passage, the two long inheritance verses closing on *Knowing and Wise* and *Knowing and Forbearing*, the four-months-and-ten-days count, the harm-on-account-of-the-child clause and the taking-back-what-was-given clause all track their standard sense. A5 holds: the two stretches of the author's own reasoning are presented as his argument, not adjudicated. A6 holds: the chapter cites within one tradition throughout.

**Category B — clean.** Zero `EP\d\d` references and zero "previous/earlier/next episode" strings in either artifact (the systemic cross-episode defect fixed in commit `b740ee22` has not regressed). No file-length self-reference, no translator-apparatus prefix, no invented dialogue or unsourced scene. B5 is the sole entry and it is P2.

**Category T (doctrinal) — clean, and the ordinal gap is now closed for this episode.** `run_doctrinal_checks` returns zero findings on both artifacts — T1 canonical attribution, T2 lineage, T3 forbidden naming phrases and T5 weak hadith. The chapter uses "Father of Imams" throughout and never pairs the leadership title with a personal name. T4 remains a stub; `farmans.yml` does not exist.

**Category O — clean.** `peace be upon him` appears exactly once (ch05 line 93); no other honorific form appears at all; no `ﷺ`; no abbreviated work titles.

**Category Q — parity holds book-wide.** All five framings declare a scholar-pool Host A and a seeker-pool Host B and name the voice genders. EP05 line 4: `A male scholar leads; a female seeker questions.`

**Categories E, I, D4, U1–U4, V1, V2, V4.** Word bands inside the hard bounds (chapter 5,997; framing 746 words / 4,524 chars on disk, built prompt 735 words / 4,475 chars against the 4,500-char binding gate). Three-movement arc with a hook open and a landed close, one-sentence summarizable. No filler interjections, no faux-profundity opening, no premature closure, no deep-dive self-reference in the chapter, no strawman. No biographical block anywhere in the chapter, so I4 passes outright. No blockquotes at all, so no quote-stacking. The opening is a genuine curiosity hook grounded in the source's own first case, and the challenge-defeat arc is explicit in each movement.

**The damage disclosure is handled correctly.** The chapter names the transmission damage in its opening frame (line 11) and again where the inheritance grid breaks down (lines 121–125), states what survives, and reconstructs nothing. That is what the contract asks for and it is the hardest thing on this list to get right.

## Health metrics

| Metric | ch05 |
|---|---|
| Words (chapter / framing / built prompt) | 5,997 / 746 / 735 |
| Framing chars vs binding gate | 4,475 / 4,500 (25 free) |
| Declared band | 5500–6000 — inside |
| Arabic script codepoints | 0 (N6) |
| Pronunciation entries settled / needed | 0 / 7 (N3) |
| Honorific expansions | 1 (O1 clean) |
| Blockquotes / quote-stacks | 0 / 0 |
| Em-dashes | 76 (P2, declined) |
| Cross-episode references | 0 |
| Doctrinal findings (deterministic) | 0 |
| Transcript present | no |
| Build exit | 0 |
| Files modified by this run | 0 |

## Verdict

**BLOCKED**, on a single P0: N6. One line from the author closes it — either generate the glossary and inject the script, or record the translation-edition exception and turn `preserve_arabic_terms` off. Everything the previous run blocked on has been fixed and verified, the four P1s are each either a known false positive, a contract-mandated conflict already mitigated in the framing, or a book-scope apparatus gap outside this agent's edit surface, and nothing about the chapter's content, citations, doctrine or shape stands in the way of upload.

## Fixer-pass note (2026-08-17)

**N6 not fixed — requires author judgment and files outside the fixer's edit surface.** The fixer may edit only `chapters/ch05-*.txt` and `EP05/00-framing.md`; suggested fix (a) writes `_system/glossary.yml` and injects script into all five chapters (ch01–ch04 confirmed at 0 Arabic codepoints each, book-wide), and suggested fix (b) edits `_system/series-config.yaml` (`preserve_arabic_terms: true`, verified on disk) — neither is in surface, and hand-inserting unbacked Arabic into ch05 alone would contradict the contract's plain-transliteration `tone_constraints` without satisfying N6's prescribed glossary-backed injection. No file was modified by this fixer pass.

**P1 pass (2026-08-17) — all five findings verified on disk; none is fixable inside the two-file edit surface, and three are explicitly not-to-be-fixed-in-content by this report's own suggested fixes.**

- **N3 (seven unsettled terms)** — not fixed. The suggested fix is `run_pronunciation_probe.py`, which writes `_system/pronunciation.md` (verified on disk: header + column row only, zero table rows) and needs a probe episode plus a human ear to settle each value. The report's own instruction forbids the only in-surface alternative — *"Never fix by editing the framing"*, because `build_episode_txt.py` recompiles lines 15–23 from `pronunciation.md` on every build and discards a hand-edit. Out of surface, and requires the `pronunciation-probe-analyst` loop.
- **F20 (seven surviving transliterations)** — no action taken, as the report directs. The mitigation was re-verified this pass: every sampled name resolves to an English audio label in the framing's Name discipline block (line 7 states the blanket rule *"One fixed English label per figure; never speak Arabic names or titles"*; lines 10–11 map `Abu Ja'far`/`al-Salim` and `al-Sadiq` to "the Imam" and "the Imam of that generation", `al-Hasan`/`al-Husayn` to "his two grandsons", `al-Nu'man` to "the jurist", `al-Muttalib` to "the Prophet's clan and his grandfather's house"). Stripping the names from the chapter would break the contract's `tone_constraints`, which require them named as the source names them.
- **R-NOMODERNIZE-STRICT (false positive)** — no action taken, as the report directs. Re-verified: all eight flagged terms sit on framing line 48 inside `## Do not (never speak these)`, and the U1 hits (`deep dive`, `today we'll discuss`, `mind blown`) on lines 48–49 in the same block. The suggested fix is to scope `assert_framing_no_modern_artifacts` to the framing body — a validator change, outside this fixer's edit surface, and the report states the content must not be changed to satisfy the flag.
- **F25 (no Name and Title Preservation Table)** — not fixed. `EP05/99-show-notes.md` re-verified this pass as carrying only `## Related episodes` (line 9) and `## References` (line 13). The file is outside the fixer's two allowed paths, and the report itself records it as out of the challenger's edit surface.
- **CS7 (94 unassigned source lines)** — not fixed. Both suggested fixes are out of surface: re-drawing the Phase 0d plan, or recording `essential: skip` in the chapter contract, which this pass is explicitly forbidden to modify.

**No file was modified by this P1 fixer pass.** No framing edit was made, so no `build_episode_txt.py` re-emit was required; the episode `.txt` remains the byte-identical 4,475-char / 735-word build the challenger verified.
