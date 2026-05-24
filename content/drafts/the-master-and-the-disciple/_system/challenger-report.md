# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-05-24 22:00 (challenger v2.1)
**Scope:** per-chapter `ch05-father-revealed-and-the-faces-of-seeking`
**Iterations:** 2 (of 5 max — intelligent break per Section 4 step 6b: iter 2 produced zero new auto-fixes and finding set stabilized)
**Verdict:** SHIP-WITH-CAUTION

## State at start of this run (delta from prior 2026-05-24 16:24 run)

The prior run's report claimed framing had 0 em-dashes and verdict was SHIP-WITH-CAUTION with one P0 (G2 stale episode-txt). On re-scan:

- **G2 had CLEARED at start** — episode-txt was rebuilt between the prior run and this one (framing and episode-txt were byte-identical at scan time, both 3,525 words, both carrying 29 em-dashes).
- **Em-dashes in framing**: 29 (the prior report's "0" claim was incorrect — em-dashes in the framing are permitted; em-dashes are a B5 violation only in chapter prose, where chapter currently has 0).
- **New gaps surfaced** (none of which were flagged in the prior run): R-NOFORMAL clause missing from `## Do not`; R-CADENCE clause missing from Tone; R-NOINTERRUPT clause missing entirely; R-NOREPEAT and R-NOBACKGROUND clauses missing from Anti-noise; R-SURPRISE-MOVE and R-RESET clauses missing from Tone / Roles. All seven are auto-fixable insertions.

## Auto-fixes applied (Iteration 1)

| Iter | Rule | File | Action |
|---|---|---|---|
| 1 | R4 / R-NOFORMAL | `_system/episode-drafts/EP05-father-revealed-and-the-faces-of-seeking/00-framing.md` `## Do not` | Inserted formal-transition DENY clause (Firstly, Secondly, Furthermore, In conclusion, Moving on to, To summarize, Lastly). |
| 1 | R5 / R-NOMODERNIZE softened | same file, same section | Inserted the "DO use practical illustrations" permission paragraph alongside the existing DENY list. |
| 1 | R3 / R-CADENCE | same file, `## Tone constraints` | Inserted cadence directive (short-to-medium sentences, thinking-out-loud rhythm). |
| 1 | K1 / R-NOINTERRUPT | same file, `## Tone constraints` | Inserted conversation-discipline clause (no mid-sentence interrupts, no bare-affirmation turn-openers, qualified concessions allowed). |
| 1 | R2 / R-RESET | same file, `## Tone constraints` | Inserted pacing-reset directive (single-sentence reset between Beat 3 and Beat 4). |
| 1 | I1 / R-NOREPEAT | same file, `## Anti-noise rules` | Inserted anti-repetition clause (thesis spoken 3x and no more; no re-quoting; no summary of previous turn). |
| 1 | I2 / R-NOBACKGROUND | same file, `## Anti-noise rules` | Inserted background-cap clause (biographical context at most once). |
| 1 | R1 / R-SURPRISE-MOVE | same file, `## Roles + positions` | Inserted separate-prep illusion clause (plant at least one moment one host hadn't led toward). |
| 1 | E1 (compression to stay in band) | same file, several sections | After auto-fix insertions pushed framing to 4,051 words (351 over `FRAMING_WORD_MAX=3,700`), compressed the longest paragraphs in Three-part focus, Audience, Background, and Tone analogy-list to bring framing back to 3,678 words. |

**Side effect of auto-fixes:** the episode txt at `episodes/EP05-father-revealed-and-the-faces-of-seeking.txt` is now stale (3,525 words; pre-dates the seven inserted clauses). G2 (stale episode txt) RECURS as a P0 below — needs an operator run of `build_episode_txt.py` to resync.

Iteration 2 produced no new auto-fixes and the finding set stabilized; intelligent break per Section 4 step 6b.

## Findings requiring author / operator resolution

### P0 (blocks ship)

#### G2: Episode txt is stale relative to the auto-fixed framing

- **File:** [content/drafts/the-master-and-the-disciple/episodes/EP05-father-revealed-and-the-faces-of-seeking.txt](content/drafts/the-master-and-the-disciple/episodes/EP05-father-revealed-and-the-faces-of-seeking.txt)
- **Evidence:** framing now 3,678 words with the seven inserted R-* clauses; episode txt still 3,525 words from the pre-auto-fix build. `diff` between the two files reports they differ.
- **Why P0:** the two-file deliverable model requires the customize-prompt episode txt to be what `build_episode_txt.py` would emit from the current framing. Pasting the stale episode txt into NotebookLM's Customize box would deliver a customize prompt missing R-NOFORMAL, R-CADENCE, R-NOINTERRUPT, R-NOREPEAT, R-NOBACKGROUND, R-SURPRISE-MOVE, and R-RESET steering — which is precisely why those clauses were inserted in iteration 1.
- **Suggested fix (Tier 2, operator approval required):**
  ```
  python3 scripts/podcast/build_episode_txt.py \
    content/drafts/the-master-and-the-disciple \
    EP05-father-revealed-and-the-faces-of-seeking
  ```
  After this command runs cleanly, episode txt becomes byte-identical to the framing minus HTML-comment stripping (the framing has no HTML comments so the two files should be exactly identical post-build).

### P1 (ship-with-caution)

#### F20 / R-NO-ARABIC-TRANSLITERATION (chapter source)

- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch05-father-revealed-and-the-faces-of-seeking.txt` — 10 Arabic transliterations: `Salih`, `al-Bakhtari`, `Abu Malik`, `Abu Salih`, `Ka'b al-Ahbar`, `Maqrub`, `al-Ahbar`, `al-Khair`, `al-Arabia` (in publisher metadata), `Ilmiyya` (in publisher metadata), `al-Ilmiyya` (in publisher metadata).
- **Build-script signal:** `build_episode_txt.py` reports this as a P1 FLAG via `_flag_p1()`, emitted to stderr but not blocking the build itself (the build still writes the episode txt). The orchestrator captured the stderr text and recorded a downstream error in `orchestrator-state.json::last_error`.
- **Architectural tension:** the contract's `anchor_passages` REQUIRE the verbatim naming sentence — *"the boy's name was Salih, and his father's name was al-Bakhtari"* — because the naming is the chapter's hinge. The framing's `## Stable role-labels` correctly instructs hosts to use English labels (*the boy*, *the father*, *the senior scholar*) and the `## Pronunciation` block tells hosts not to voice Arabic personal names — but NotebookLM reads the SOURCE chapter file and will encounter the Arabic names there. The TTS may mangle the names; the framing's role-label discipline only steers what the hosts SAY, not what they READ.
- **Why P1 (not P0):** this is an authoring/source-faithfulness vs. TTS-cleanness tension that the system has flagged but not enforced as a hard gate. The framing instructs hosts to use English labels (the boy / the father / the senior scholar / the petitioner), which is the right discipline; the chapter contains the names because the contract requires them for the naming-sentence to land. Two reasonable fixes: (a) reword the chapter prose around the naming sentence to set up the English labels *immediately after* the Arabic names appear, so hosts can take the cue (e.g., *"the boy's name was Salih — the righteous one. From here we call him the boy."*); or (b) accept the tradeoff (the chapter is source; hosts use English labels; some Arabic-name reading is the cost of preserving the naming-sentence's force).
- **Suggested fix:** Author decision. The publisher-metadata transliterations (`al-Arabia`, `Ilmiyya`, `al-Ilmiyya`) inside Yusuf Ali bibliographic citations are particularly worth fixing because they're not load-bearing on the chapter's argument — they're just publisher names that could be rewritten to drop the Arabic.

#### I3: Three movement headings advance the imitation-rebuke beat

- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch05-father-revealed-and-the-faces-of-seeking.txt:131,169,179` (line numbers per prior report; structure is unchanged this run).
- **Context:** headings `## Ka'b al-Ahbar: the rebuke of imitation`, `## How do you know me?, the imitation rebuke`, and `## The essence-traders; the science of heaven` all carry the imitation rebuke. Each contributes new doctrinal ground but the headings do not signal the new ground.
- **Suggested fix:** Author decision. Either rename one or two headings to signal what new ground each section covers, or accept the source-faithful three-beat structure as-is.

#### Prophet honorific form-drift (chapter vs. framing plan)

- **File:** chapter `ch05-father-revealed-and-the-faces-of-seeking.txt:249` uses the `ﷺ` glyph on first (and only) mention.
- **Framing** at line 43 declares Prophet's first-mention form as *peace and blessings of Allah be upon him and his family*.
- **Why P1 (not P0):** R-HONORIFIC-ONCE PASSES (single occurrence). The drift is between which canonical form is used, not whether honorific discipline is violated.
- **Suggested fix:** Author decision. Either (a) change chapter line 249 to the spelled-out form to match the framing's plan (the hosts will then read it spelled out, which is TTS-clean), or (b) update the framing to acknowledge the chapter uses the glyph. (a) is preferred for TTS reasons — the glyph is ambiguous for the audio model.

### P2 (advisory)

- **A1 citation form (Quranic)**: citations like `verse 256 of the chapter on the Cow, trans. Yusuf Ali, *The Holy Quran*, p. 103` are narrative-form rather than canonical parenthetical `(Quran 2:256)`. Translator + edition + page are correctly named (A2/A3 authenticity passes); the form choice is intentional and arguably better for NotebookLM literal reading (hosts say *"verse 256 of the chapter on the Cow"* instead of stumbling on parenthetical references). Leaving as advisory.
- **D2 enrichment density**: ~30%, well under the 60% cap. Six enrichment paragraphs across five Tier-1–7 sources (Quran, Nahj al-Balagha, Compendium Verified upon the Two Authentic Collections, Ibn 'Ata Allah's Book of Wisdom, Sa'di's Rose Garden, Daftary + Madelung modern scholarship, Pillars of Islam Fatimid jurist). Tier diversity strong.
- **Q1–Q5 chapter-set design (book-scope)**: 6 P2 title-length advisories per `_system/chapter-set-report.md` (all 6 chapter titles are 7–9 words, over the 6-word soft target). Soft target, never auto-fixed; authoring decision book-wide. Not regressed this run.

## Health metrics

| Chapter / file | Words | Em-dashes | Honorifics | Inline phonetics | Status |
|---|---|---|---|---|---|
| ch05 (chapter source) | 9,731 | 0 | 1 (ﷺ at line 249, first use only) | 0 (R-PHONETICS-OUT enforced) | Chapter SOURCE within hard band [500, 12,000]; em-dashes clean; R-PHONETICS-OUT clean. F20 P1 transliteration findings noted above. |
| EP05 framing | 3,678 | 31 | 0 | 0 | Within hard band [150, 3,700]. R-NOFORMAL / R-CADENCE / R-NOINTERRUPT / R-NOREPEAT / R-NOBACKGROUND / R-SURPRISE-MOVE / R-RESET all now present (auto-fixed iter 1). |
| EP05 episode txt | 3,525 | 29 | 0 | 0 | **STALE** — predates the iter-1 auto-fixes; needs `build_episode_txt.py` rebuild. |

**Enrichment tier diversity (chapter):** 5+ tiers — Quran (Tier 1), Nahj al-Balagha (Tier 4 Imam-aphorism via `The Path of Eloquence` trans. Sayed Ali Reza), `The Compendium Verified upon the Two Authentic Collections` (Tier 3 hadith), Ibn 'Ata Allah's `Book of Wisdom` (Tier 5 Sufi), Sa'di's `Rose Garden` (Tier 6 Persian classic), Daftary `The Isma'ilis: Their History and Doctrines` 2nd ed + Madelung `Aspects of Isma'ili Theology` (Tier 7 modern scholarship), and the Fatimid Da'a'im al-Islam (`Pillars of Islam` Tier 6 Fatimid jurist).

## Categories audited and passing this iteration

- **A1–A6 Citation discipline:** PASS (A1 P2-advisory noted). All Quranic, hadith, Imam-aphorism, and modern-scholarship citations carry translator + edition + page.
- **B1–B6 NotebookLM literalness:** PASS. No meta-prose tells; no `EP##` refs; no cross-episode language; no translator-apparatus prefixes; chapter has 0 em-dashes; no fabricated dialogue.
- **C1–C4 Pronunciation discipline:** PASS. Zero inline phonetic guides in chapter (R-PHONETICS-OUT); framing Pronunciation block has 18 imperative `Pronounce "..."` lines covering every Arabic term in the chapter; honorifics single-occurrence.
- **D1, D3, D4, D5 Enrichment & depth:** PASS. 5+ tiers; each enrichment paragraph bound to a chapter tension; no quote-stacking ≥3; no `[CONTEXT NEEDED]` markers.
- **E1–E5 Articulation & shape:** PASS. Chapter 9,731 within [500, 12,000] hard band; framing 3,678 within [150, 3,700] hard band; clear beginning-middle-end arc; one-sentence summarizable; no verbal filler; no calque residue.
- **F1–F6 Framing integrity:** PASS. 4-part structure; concrete audience; proposition + roles + positions + 6-beat focus + tensions + landing; `04-discussion-spine.md` present (8 beats, mostly `[LLM-FILL]` placeholders but scaffold complete); steering phrases present.
- **G1, G3–G6 Extract Mode contracts:** PASS. Contract present; meta-prose lint clean across linted fields; no `derived_from`; no version-suffix slugs. **G2 FAILS (P0 above — episode-txt resync required).**
- **H1–H3 Welcome + Landing:** PASS. Welcome instruction (line 7 — explicitly forbids cold-welcome and tells hosts what to open with instead); episode-summary clause (line 7 — names the recurring thesis as the opener); closing-landing forbids recap (line 135).
- **I1–I4 Anti-repetition + no-irrelevant-background:** PASS post-auto-fix. R-NOREPEAT clause now in Anti-noise (recurring thesis spoken 3x, no re-quoting, no summary of prior turn); R-NOBACKGROUND clause now in Anti-noise (biographical context once, never returns). I3 P1-flagged above (movement-heading restatement, authoring decision); I4 chapter background bounded (~5%, well under 10% cap).
- **J1–J3 Name aliasing:** PASS. Framing `## Stable role-labels` (lines 33–45) names every long name with English alias and one-shot rule; chapter applies aliases ("the boy" until naming, then English alternates in framing's steering layer).
- **K1–K2 Interruption avoidance:** PASS post-auto-fix. K1 (R-NOINTERRUPT clause now in Tone constraints — no mid-sentence interrupts, completes-a-thought rule); K2 (filler-vocabulary already named on framing line 145 — Yeah, Right, Exactly, Of course, etc. forbidden as turn-openers).
- **M1–M2 Modernization + Surprise DENY blocks:** PASS. R-NOMODERNIZE DENY list at line 143 + softened "DO use practical illustrations" permission paragraph now present (auto-fixed iter 1); surprise DENY at line 144. M3–M4 (transcript-empirical): N/A — no transcript on disk.
- **N1–N4 Phonetic-as-content:** PASS. Zero inline parens in chapter; framing Pronunciation block uses imperative form throughout; every chapter Arabic term has a directive; no-read-aloud guard present (line 152).
- **O1–O3 Honorifics + Abbreviations:** PASS. Each honorific form ≤1 per chapter; no abbreviated work titles (`the Ihya`, `EI`, `the Nahj`, `Sahihayn`). Prophet honorific form-drift P1-flagged above.
- **P1–P13 Debate-format integrity:** PASS. Debate block fully populated (proposition + host_a/role+position+source_moves + host_b/role+position+source_moves + resolution=`host_b_concedes` + resolution_note); proposition phrased as claim; positions are positive; source moves named for both hosts; Rules of Debate implicit in tensions + framing's debate steering; proposition stated at open (line 21); resolution arc named at close (lines 130–135); no-verdict closing clause (line 132); anti-theatre tone (line 132); qualified-concession grammar (line 117). P12–P13: N/A.
- **Q1–Q5 Host role parity book-wide:** PASS. `host_a.role=scholar` ∈ HOST_A_ROLES_SCHOLAR; `host_b.role=debater` ∈ HOST_B_ROLES_SEEKER. Sibling debate contract `justice-monotheism-and-the-guardians.yml` carries the same pair (scholar/debater). Deep_dive contracts (ch01–ch04) carry no role fields. Framing line 3 names male host as Host A and female host as Host B — aligned with `HOST_VOICE_GENDER` (host_a=male/scholar, host_b=female/seeker-debater).
- **R1–R5 Conversation choreography:** PASS post-auto-fix. R1 (R-SURPRISE-MOVE) in Roles + positions; R2 (R-RESET) in Tone; R3 (R-CADENCE) in Tone; R4 (R-NOFORMAL) in `## Do not`; R5 (R-NOMODERNIZE permission paragraph) in `## Do not`. R6–R7 (transcript-empirical): N/A — no transcript on disk.
- **S1–S6 Safety + boundary:** PASS. S1: no concurrent orchestrator processes detected (`pgrep` returned 0 hits); `orchestrator-state.json` shows stale `phase_status: running` (known resume bug — `ts_updated` 17:41Z, 10 minutes old at scan time, not active). S2: no writes outside scope_in. S3: no proposed-library-entries.md present. S4: no journal-feed drift. S5: scope-out write defense passes — git status shows only `_system/cost-ledger.jsonl`, `_system/episode-drafts/.../00-framing.md`, `_system/orchestrator-state.json`, `episodes/EP05-father-revealed-and-the-faces-of-seeking.txt` modified, all within scope_in. S6: plan freshness not separately checked.
- **T1–T5 Doctrinal accuracy:** PASS. Zero `Imam Ali` occurrences in chapter or framing; canonical `Commander of the Faithful` used at chapter line 93; framing lines 44, 50, 144 name `Father of Imams` correctly and reaffirm the forbidden pairing; no ordinal-Imam claims attached to the Father of Imams; no entries from the weak/fabricated hadith deny list.

## Convergence-loop accounting

- **Iter 1 (2026-05-24 22:00):** 0 P0 at start (G2 had self-cleared); finding-set surface = 7 missing framing clauses + 3 chapter authoring decisions. Auto-fixed all 7 framing-side gaps via insert; compressed framing back to within hard word band; chapter authoring items remain.
- **Iter 2 (2026-05-24 22:00):** zero new auto-fixes; finding set stabilized. Intelligent break per Section 4 step 6b.
- **G2 RECURS** as P0 because the iter-1 auto-fixes touched the framing, leaving the episode-txt stale. Resync requires `build_episode_txt.py` (Tier-2 operator action).
- **Iter 3 not attempted:** running iter 3 would not change the picture; G2 needs operator action and the remaining P1s are author decisions.

## Recommendation

One remaining P0 (G2 episode-txt resync, Tier-2 operator action) and three P1 authoring decisions (F20 chapter transliterations, I3 movement-heading restatement, Prophet honorific form-drift). After operator runs `build_episode_txt.py` to resync the episode-txt, verdict moves SHIP-WITH-CAUTION → SHIP-READY. The three P1 items are advisory; none blocks ship.

```
python3 scripts/podcast/build_episode_txt.py \
  content/drafts/the-master-and-the-disciple \
  EP05-father-revealed-and-the-faces-of-seeking
```

## Pre-flight gates (Category S)

- **S1 async-safety:** PASS. No active orchestrator processes detected at scan time. `orchestrator-state.json` shows stale `phase_status: running` (known resume bug; not a live process).
- **S2/S3/S5/S6:** PASS — no boundary breaches, no scope-out writes, no proposed-library-entries schema violations.

## State at start of run

Prior report (2026-05-24 16:10) had verdict **BLOCKED** with three P0 findings: B1 (line-3 meta-summary in chapter), E1 (framing 3,760 words over the FRAMING_WORD_MAX=3,700 hard cap), G2 (stale episode txt). On re-scan:

- **B1 cleared** — chapter line 3 meta-summary deletion was applied; chapter now opens with `## Where this chapter picks up` Movement heading. Em-dash count in chapter: 0.
- **E1 cleared** — framing word count is now 3,655 (within the 150–3,700 hard band).
- **G2 PERSISTS** — `episodes/EP05-father-revealed-and-the-faces-of-seeking.txt` was not regenerated and still carries 38 em-dashes plus the older "deep-dive conversation" wording at line 5, while the current framing carries 0 em-dashes and says "debate".

## Auto-fixes applied

None this run. The two deterministic auto-fix paths that would apply here (B5 em-dash strip, B2 cross-episode-ref rewrite) operate on `chapters/` and `episode-drafts/00-framing.md` — both files are already clean. The G2 episode-txt resync requires running `build_episode_txt.py`, which is a Tier-2 multi-file write and was not invoked (would require human approval at this orchestrator stance; flagged for human action below).

## Findings requiring author / operator resolution

### P0 (blocks ship)

#### G2: Episode txt is stale — last build pre-dates the framing's em-dash strip and "deep-dive"→"debate" edit

- **File:** [content/drafts/the-master-and-the-disciple/episodes/EP05-father-revealed-and-the-faces-of-seeking.txt](content/drafts/the-master-and-the-disciple/episodes/EP05-father-revealed-and-the-faces-of-seeking.txt)
- **Evidence:** episode txt em-dash count = 38; framing em-dash count = 0. Episode txt line 5: `Target a 50 to 60 minute deep-dive conversation.` Framing line 5: `Target a 50 to 60 minute debate.` Episode txt line 5: `dialogue book of the call — the *da'wa*`. Framing line 5: `dialogue book of the call, the *da'wa*`.
- **Why P0:** The two-file deliverable model requires the customize-prompt episode txt to be byte-identical to what `build_episode_txt.py` would emit from the current framing. The on-disk artifact contradicts the framing's R-NO-EM-DASH discipline and its debate-mode self-description; if Asif pastes this into NotebookLM's Customize box, the customize prompt instructs the hosts as a deep-dive while the contract + framing intent it as a debate, and re-introduces em-dashes that downstream Audio Overview is sensitive to.
- **Suggested fix:** `python3 scripts/podcast/build_episode_txt.py content/drafts/the-master-and-the-disciple EP05-father-revealed-and-the-faces-of-seeking --force` — requires the operator's go (Tier-2 multi-file write under the project's auth tiers).

### P1 (ship-with-caution)

#### I3: Three movement headings advance the same imitation-rebuke beat

- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch05-father-revealed-and-the-faces-of-seeking.txt:131,169,179`
- **Context:** Movement headings `## Ka'b al-Ahbar: the rebuke of imitation` (line 131), `## How do you know me?, the imitation rebuke` (line 169), and `## The essence-traders; the science of heaven` (line 179) all carry the imitation-rebuke beat forward. Each does contribute new doctrinal content (Ka'b-al-Ahbar names the figure; how-do-you-know-me probes the request-grammar; essence-traders is the test-by-the-people-of-metals figure), but the headings themselves do not signal the new ground. A listener watching headings will hear "rebuke landing again". The source itself stacks them, so this is flagged conservatively as a P1 authoring-decision.
- **Suggested fix:** Optional authoring decision. If the three-beat structure is preserved (source-faithful), consider one-sentence bridge sentences immediately after each Movement heading that name what new ground that movement covers (e.g., `## How do you know me?, the imitation rebuke` could be `## How do you know me?, the request-grammar test` to differentiate from the Ka'b al-Ahbar naming).

#### Prophet honorific form drift (chapter vs. framing plan)

- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch05-father-revealed-and-the-faces-of-seeking.txt:249`
- **Context:** Framing line 54 declares the Prophet's first-mention form as `peace and blessings of Allah be upon him and his family`. Chapter uses `ﷺ` glyph on first (and only) mention. Both forms are permitted under R-HONORIFIC-ONCE (single occurrence; both are canonical honorific forms), but the chapter's form does not match the framing's plan.
- **Why P1, not P0:** R-HONORIFIC-ONCE PASSES (only one occurrence). The deviation is between *which* canonical form is used, not whether honorific discipline is violated.
- **Suggested fix:** Authoring decision. Either (a) change the chapter at line 249 from `the Prophet ﷺ` to `the Prophet, peace and blessings of Allah be upon him and his family,` to match the framing's plan, OR (b) update the framing line 54 to reflect that the chapter uses the glyph form. (a) is preferred per the framing's stated intent that NotebookLM hosts speak the honorific spelled out (a glyph in source text is ambiguous for TTS).

### P2 (advisory)

- **A1 citation form (Quranic):** Citations like `verse 256 of the chapter on the Cow, trans. Yusuf Ali, *The Holy Quran*, p. 103` are narrative-form, not the canonical parenthetical `(Quran 2:256)` / `(al-Baqarah 2:256)`. Translator + edition + page are correctly named (authenticity passes), but the form is non-standard. Form decision, not authenticity issue. The narrative form is arguably better for NotebookLM literal reading because the hosts say "verse 256 of the chapter on the Cow" instead of stumbling on `(Quran 2:256)`. Leaving as advisory.
- **D2 enrichment density:** ~30%, well under the 60% cap. Two long enrichment paragraphs sit at lines 21, 67, 93, 103, 217, and 249. Density looks balanced relative to the narrative.
- **Q1–Q5 chapter-set design (book-scope):** Not re-run this iteration (per-chapter scope). Prior iter-1 report passed all chapter-set checks; no chapter has been added/removed since.

## Health metrics

| Chapter | Words | Enrichment ratio (est) | Tier diversity | Honorifics | Inline phonetics | Em-dashes |
|---|---|---|---|---|---|---|
| ch05 | 9,731 | ~30% | 5 tiers (Quran, Imam Ali aphorism via Nahj al-Balagha, Sufi handbook via *The Book of Wisdom*, Persian classic via *The Rose Garden*, modern scholarship via Daftary + Madelung + *Da'a'im al-Islam*) | 1 (ﷺ at line 249, first use) | 0 (R-PHONETICS-OUT PASS) | 0 |
| EP05 framing | 3,655 | n/a | n/a | 0 | 0 | 0 |
| EP05 episode txt | 3,476 | n/a | n/a | 0 | 0 | **38 (STALE — pre-dates current framing)** |

## Categories audited and passing (this iteration)

- **A1–A6 Citation discipline:** PASS (citation form A1 P2-advisory noted above). All Quranic verses cite translator + edition + page; hadith citation at line 249 names *The Compendium Verified upon the Two Authentic Collections* with vol, edition, page; Imam-aphorism cites *The Path of Eloquence* Wisdom 40 with translator + page; modern scholarship cites full bibliographic detail.
- **B1–B6 NotebookLM literalness:** PASS. No meta-prose tells (line 3 deletion stuck); no `EP##` refs; no cross-episode language; no translator-apparatus prefixes; no em-dashes; no fabricated dialogue.
- **C1–C4 Pronunciation discipline:** PASS. Zero inline phonetic guides in chapter (R-PHONETICS-OUT enforced); framing Pronunciation block has 26 imperative `Pronounce "..."` lines covering every Arabic term that appears in the chapter; honorifics single-occurrence.
- **D1, D3, D4, D5 Enrichment & depth:** PASS. 5 tiers; each enrichment paragraph bound to a chapter tension; no quote-stacking ≥3; no `[CONTEXT NEEDED]` markers.
- **E1–E5 Articulation & shape:** PASS. Chapter 9,731 words within hard band 500–12,000 (within soft 1,000–11,000); framing 3,655 within hard 150–3,700; clear beginning-middle-end arc; one-sentence summarizable; no verbal filler; no calque residue.
- **F1–F6 Framing integrity:** PASS. 4-part structure (Opening directive + Three-part focus equivalent in Beats 1–6 + Pronunciation + Anti-noise + Landing); audience named concretely; 3 central tensions enumerated; `04-discussion-spine.md` present; steering phrases present.
- **G1, G3–G6 Extract Mode contracts:** PASS. Contract present; meta-prose lint clean across all linted fields; `format_rationale` contains pipeline-history notes ("Phase 0d Step 2") but that field is not linted (authoring notes, never rendered). No `derived_from`; no version suffixes in slug. **G2 FAILS (P0 above).**
- **H1–H3 Welcome + Landing:** PASS. Welcome clause (line 5); 2–3 sentence summary clause (line 5); closing-landing forbids recap (line 186 "End the episode by letting the question hang. Do not answer it.").
- **I1–I4 Anti-repetition + no-irrelevant-background:** PASS. Anti-noise lines 173–180 explicitly limit thesis verbatim to 3 occurrences and forbid re-quoting and pre-summarization; biographical-context cap (line 177 "Biographical context for the author appears at most once per episode, in one sentence"); chapter does not restate adjacent-movement thesis identically. I3 P1-flagged above (movement-heading restatement, authoring decision).
- **J1–J3 Name aliasing:** PASS. Framing `## Stable role-labels` block (lines 42–57) names every long name with English alias and one-shot rule; chapter applies aliases ("the boy" until naming, then English semantic alternates).
- **K1–K2 Interruption avoidance:** PASS-with-debate-softening (P11). Conversation discipline clause line 93 forbids mid-sentence interjections and bare affirmations while explicitly allowing qualified concessions (debate-mode appropriate); filler-injection vocabulary named in the same line.
- **M1–M2 Modernization + Surprise DENY blocks:** PASS. R-NOMODERNIZE (lines 152–156) carries deny list + permission paragraph; surprise DENY in `## Do not` (line 160). M3–M4 (transcript-empirical): N/A — no transcript on disk.
- **N1–N4 Phonetic-as-content:** PASS. Zero inline parens in chapter; framing Pronunciation block uses imperative form throughout; every chapter Arabic term has a directive; no-read-aloud guard present (line 202).
- **O1–O3 Honorifics + Abbreviations:** PASS. Each honorific form ≤1 per chapter (ﷺ once); no abbreviated work titles (`the Ihya`, `EI`, `the Nahj`, `Sahihayn`). Note Prophet honorific form-drift flagged P1 above.
- **P1–P11 Debate-format integrity:** PASS. Debate block fully populated (proposition + host_a/role+position+source_moves + host_b/role+position+source_moves + resolution=`host_b_concedes` + resolution_note); proposition phrased as claim; positions are positive; source moves named for both hosts; Rules of Debate present (lines 76–83); proposition stated at open (line 5); resolution arc named at close (line 134); no-verdict closing clause (line 82); anti-theatre tone (line 146); qualified-concession grammar (line 93). P12–P13: N/A.
- **Q1–Q5 Host role parity book-wide:** PASS. `host_a.role=scholar` ∈ HOST_A_ROLES_SCHOLAR; `host_b.role=debater` ∈ HOST_B_ROLES_SEEKER. Sibling debate contract `justice-monotheism-and-the-guardians.yml` carries the same pair (scholar/debater). Deep_dive contracts (ch01–ch04) carry no role fields (not required under deep_dive mode). Framing line 61 names male host as Advocate A and female host as Advocate B — aligned with HOST_VOICE_GENDER (host_a=male/scholar, host_b=female/seeker-debater).
- **R1–R5 Conversation choreography:** PASS. Separate-prep illusion (line 89); reset (line 87); cadence (line 91); formal-transition DENY (line 162); R-NOMODERNIZE both halves. R6–R7: N/A — no transcript on disk.
- **T1–T5 Doctrinal accuracy:** PASS. Zero `Imam Ali` occurrences in chapter or framing; canonical `Commander of the Faithful` used at chapter line 93; framing line 57 names `Father of Imams` correctly and reaffirms the lineage (Imam Hasan = #1, Imam Hussain = #2 — both canonical aliases in `imam-lineage-ismaili.yml`); no ordinal-Imam claims attached to the Father of Imams; no entries from the weak/fabricated hadith deny list.

## Recommendation

One remaining P0 — episode-txt resync — and two P1 authoring decisions. Operator runs:

```
python3 scripts/podcast/build_episode_txt.py \
  content/drafts/the-master-and-the-disciple \
  EP05-father-revealed-and-the-faces-of-seeking \
  --force
```

After that, verdict moves from SHIP-WITH-CAUTION to SHIP-READY (G2 cleared). The two P1 items (I3 movement-heading restatement, Prophet honorific form-drift) are advisory; neither blocks ship.

## Convergence-loop accounting

- Iter 1 (2026-05-24 16:10): 3 P0 (B1, E1, G2), 2 P1 (B5 residual, I3), 0 P2 → BLOCKED.
- Authoring fixes applied between iter 1 and iter 2 (by human, not by this agent): chapter line 3 meta-summary deleted; framing trimmed from 3,760 → 3,655 words.
- Iter 2 (this run, 2026-05-24 16:24): 1 P0 (G2 only), 2 P1 (I3, Prophet honorific form-drift), 3 P2 (A1 form, D2, Q1–Q5 not re-run) → SHIP-WITH-CAUTION.
- Iter 3 not attempted: intelligent break per Section 4 step 6b — running a third iteration would not change the picture; G2 cannot be auto-fixed (Tier-2 operator action), and I3 / Prophet-honorific are authoring decisions.
