# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-05-25 11:05 UTC (challenger v2.1) — re-validation of 10:52 UTC pass
**Scope:** per-chapter `ch04-the-greater-shaykh-and-the-naming`
**Iterations:** 1 (of 5 max; early break — no auto-fixable findings, every remaining item is author-judgment; re-run confirms 10:52 UTC findings unchanged)
**Verdict:** SHIP-WITH-CAUTION

> Per-chapter convergence pass on EP04. Loop M (transcript audit) skipped — no transcript at `transcripts/EP04-*.transcript.txt`. Loop S (safety pre-check) passed with one note: `orchestrator-state.json` shows `phase: per-chapter`, `phase_status: running`, `last_error.ts: 2026-05-25T10:11:00Z` from a prior challenger invocation that exited rc=1. No live process per `pgrep` — same stale-running-flag pattern as the EP01 run. Proceeded under the documented orchestrator-resume bug. The chapter content is doctrinally clean and source-faithful; the heavy P0 + P1 load comes from a single architectural decision the chapter has inherited book-wide — it is authored as a written-layer scholarly essay (Arabic transliterations with diacritics, ʿaqīqa-style technical vocabulary in-line, full translator/publisher/page citations) when the v3.4 pipeline now expects TTS-safe chapter prose (F20 doctrine, R-PHONETICS-OUT, F27 #1 + #6 Tier 2.5). The framing scaffolding is structurally excellent and ready to ship.

## Pre-flight gates (Category S)

- **S1 async-safety:** `orchestrator-state.json` shows `phase_status: running` with `last_error.ts: 2026-05-25T10:11:00Z` — a prior challenger invocation that exited rc=1. `pgrep -fl 'orchestrate_book|claude -p|extract_chapter|build_episode'` returns no live processes. State file mtime predates this run; matches the known orchestrator-resume bug pattern (stale `running` flag from unclean shutdown). **PASS — no HALT.**
- **S2 boundary contract:** chapter + framing text contain no write paths into `content/babu-memoir/` or `content/_shared/` (paths in scholarly citations are publisher/city names, not filesystem paths). PASS.
- **S3 proposed-library-entries schema:** N/A — file not present for EP04.
- **S4 automatic journal feed:** N/A.
- **S5 scope-out write defense:** PASS — only `challenger-report.md`, `findings.jsonl`, and `_learning/health/<book>.json` touched.
- **S6 plan staleness:** advisory only; not blocking.

## Build-script hard gates (Categories A, B, N, O, T)

`build_episode_txt.py` could not be executed in this sandbox (process invocation blocked); all gates verified by direct grep / Read equivalents against the same regex / substring tables in `scripts/podcast/_rules.py` and `scripts/podcast/build_episode_txt.py`.

| Gate | Rule | Chapter result | Framing result |
|---|---|---|---|
| HTML comments | structural | none | none |
| Meta-prose tells (substring + EP-regex) | B1 | none | none |
| Inline phonetic parens `*Term* (PHO-NE-TIC; ...)` | N1 / R-PHONETICS-OUT | none | n/a |
| Abbreviated work titles (the Ihya / the Nahj / Sahihayn / EI / IUD / NJB) | O2 / R-NO-ABBREVIATION | none | n/a |
| Honorific repetition (`peace be upon him` / `peace and blessings…` / ﷺ / PBUH / SAW / RA) | O1 / R-HONORIFIC-ONCE | none — chapter does not name the Prophet directly in body prose | one `peace be upon him` in `## Stable role-labels:38` (correct: exactly one expanded form, naming the Commander of the Faithful) |
| Forbidden phrases (T3 — `Imam Ali` / `Imam Fatima` / `1st Imam Ali`) | doctrinal | none in chapter prose | one literal `Imam Ali` in chapter-contract at line 463 inside the doctrinal rule that bans the phrase ("The phrase \"Imam Ali\" is FORBIDDEN per `imam-lineage-ismaili.yml`") — contract is not rendered into NotebookLM; this is a rule-example reference and is acceptable. Framing carries the paraphrased form only ("the leadership-title of the Father of Imams with his personal name") — no literal pairing reaches NotebookLM. PASS. |
| Imam lineage (T2 — `Nth Imam` ordinals match the canonical Ismaili lineage) | doctrinal | n/a — no Imam ordinals in this chapter | framing references "the fourth Imam to whom the supplications are attributed" at line 39 — correct per `imam-lineage-ismaili.yml` (4th Imam = Ali Zayn al-Abidin = source of `The Psalms of Islam`). PASS. |
| Arabic transliterations (F20) | R-NO-ARABIC-TRANSLITERATION | **FAIL** — chapter is densely transliterated (al-Bakhtari, al-Yaman, al-āya al-kubrā, Sayyidina, Ja'far ibn Mansur, ʿaqīqa, ta'wīl, ḥadd, mudda, hurr, hujja, bāb, hawl, quwwa, batin, zahir, taqiyya, da'wa, fiqh, Sa'd, Ubayd Allah, Abd Allah, ihram, Hajj, Kitab al-'Alim wa-l-Ghulam, Kaʿba, plus the verbatim Arabic formula `la hawla wa la quwwata illa billah` at line 17). The build script's `assert_no_arabic_transliteration` is a P1-flag (warning, not hard refuse), so the build does not block — but R-PHONETICS-OUT doctrine is broken: NotebookLM will TTS these as content, with empirical-audit-proven mangling like "tassel wolf" for *Tasawwuf*. | none — pronunciation block uses imperative form for 7 terms |
| Surah names (R-SURAH-ENGLISH-ONLY) | structural | PASS — chapter refers to surahs by English meaning ("verse 286 of the chapter on the cow" line 45; "verses 24-25 of the chapter on Abraham" line 111; "verse 125 of the chapter on the bee" line 123) | PASS |
| Forbidden literal alqaab (`the Striker` pattern) | R-ALQAAB-FUNCTIONAL-PARAPHRASE | none | none |
| Inline modern artifacts | R-NOMODERNIZE-STRICT | n/a | PASS — modern terms confined to the `## Do not` block (line 129), correctly scrubbed |
| Forbidden analogies | R-ANALOGY-CAP-STRICT | n/a | PASS — 3 governing analogies all source-grounded (yellowing of the body; freshwater spring; root watered + branch raised) |
| Pronunciation block imperative form | R-PRONUNCIATION-IMPERATIVE | n/a | PASS — 7 `Pronounce "..." as "..."` lines (Quran, Sinai, Hajj, ihram, Sa'd, Ubayd Allah, Abd Allah) |
| Name discipline section | R-NAMEDISCIPLINE | n/a | PASS — `## Stable role-labels` at line 30 (7 figures with English alias rotations using `→`) + `## Name discipline` at line 45 |
| Dramatic arc (≥6 beats OR ≥3 structure tells) | R-DRAMATIC-ARC | n/a | PASS — 6 distinct Beat markers across `## Three-part focus` (Beat 1–6 at lines 53, 55, 57, 59, 61, 63) |
| Challenger friction (≥2 pushback patterns) | R-CHALLENGER-FRICTION | n/a | PASS — 3 of 4 canonical patterns at lines 23–25 (`I don't buy that yet` / `That sounds like wordplay` / `How is this different`); challenger/pushback/friction language at lines 21–27 |
| Analogy cap (3-5 governing analogies declared in Tone constraints) | R-ANALOGY-CAP | n/a | PASS — 3 enumerated at lines 105–107 (yellowing of body; freshwater spring; root watered + branch raised) |
| Recurring thesis (≥3 verbatim) | R-RECURRING-THESIS | not author's primary register — chapter quotes the thesis ("The name belongs to you, and you belong to the name…") once verbatim at line 75 | PASS — framing instructs 3 verbatim repetitions at Opening directive line 7 (first time), Beat 4 line 59 (second time), Landing line 127 (third time) |
| DENY block present (Twitter / social media / algorithm / wow / right? + Do-not-read-aloud guard) | R-NOMODERNIZE + R-NOSURPRISE + R-NO-READ-PROMPT | n/a | PASS — `## Do not` at line 129 names all required canonical phrases plus R-NOFORMAL transitions; no-read-aloud guard at line 145 |
| Word count (chapter hard band [500, 12000]) | structural | 10,958 — PASS (under 12,000 hard cap; 42 words under the 11,000 soft warning ceiling) | n/a |
| Word count (framing hard band [150, 3700]) | structural | n/a | 3,683 — PASS (within hard cap; 17 words under the 3,700 ceiling) |
| Host A in scholar pool (Q1) | R-HOST-ROLE-PARITY | n/a | PASS — Host A = "scholar / teacher / elder's voice" (line 19; male voice = John) |
| Host B in seeker pool (Q2) | R-HOST-ROLE-PARITY | n/a | PASS — Host B = "seeker / questioner — the boy's voice" (line 19; female voice = Hannah) |
| Voice-gender pairing declared (Q4) | R-HOST-ROLE-PARITY | n/a | PASS — `Host A (male voice — John)` / `Host B (female voice — Hannah)` (line 19) |
| Host role parity across episodes (Q3) | R-HOST-ROLE-PARITY | n/a | PASS — EP01 (deep_dive), EP05 (debate, host_a.role=scholar / host_b.role=debater), EP06 (debate, same pairing), EP04 (this run) all consistent: Host A scholar/male, Host B seeker-or-debater/female. No mid-book role swap. |

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | None — every remaining finding requires author judgment (citation form / chapter rewrite / band reclassification). The deterministic auto-fix envelope (em-dash strip, repeated-honorific strip, cross-episode-ref rewrite, exact-match filler strip, missing-pronunciation insert from `_phonetics.md`) found no in-scope targets. |

## Findings requiring author resolution

### P0 (blocks ship if strict-mode-read)

#### F20-R-PHONETICS-OUT: Chapter is densely Arabic-transliterated against the v3.4 TTS-safe doctrine
- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch04-the-greater-shaykh-and-the-naming.txt` (entire chapter)
- **Sample hits:** `al-Bakhtari` (line 165), `al-Yaman` (3), `al-āya al-kubrā` (101), `Sayyidina Ja'far ibn Mansur` (3), `ʿaqīqa` (71), `ta'wīl` (17, 75 implied), `ḥadd` (75), `mudda` (75), `hurr` (65), `hujja` (17, 101), `bāb` (17, 101), `hawl` (17), `quwwa` (17), `batin` (51, 71, 75, 93, 101 et al.), `zahir` (51, 71, 75, 83, 93, 101), `taqiyya` (95, 137), `da'wa` (5, 9, 117 et al.), `fiqh` (71), `Sa'd` (85, 99), `Ubayd Allah` (61, 65), `Abd Allah` (61), `ihram` (99, 101), `Hajj` (99, 101, 165), `Kitab al-'Alim wa-l-Ghulam` (3), `Kaʿba` (101). Plus the verbatim multi-word Arabic formula `la hawla wa la quwwata illa billah` at line 17.
- **Problem:** Per F27 Tier 2.5 doctrine (`build_episode_txt.py:811-846`) and R-PHONETICS-OUT (2026-05-17 architectural pivot), the chapter file is uploaded as-is to NotebookLM as the SOURCE — every italicized Arabic transliteration becomes spoken content. Empirical audits across v3/v4/v4-revised episodes show systematic mangling: phonetic doublings ("Sahih Sitta, sahasita"), name mangling ("tassel wolf" for *Tasawwuf*), and host doctrine drift onto whatever the TTS produces. The chapter's authored register here is the WRITTEN-LAYER scholarly essay register (the Henry Corbin / Farhad Daftary / David Hollenberg / Paul Walker / Heinz Halm citations at lines 21, 57, 77, 97, 103, 111, 123, 151 belong to the apparatus the v3.4 architecture moved to `99-show-notes.md` and stripped from chapter prose).
- **Build-script note:** `assert_no_arabic_transliteration` is a `_flag_p1` (P1 FLAG, not hard `sys.exit`) per `build_episode_txt.py:838-846`. The build does NOT refuse on this. It is filed P0 in this report because v3.4 doctrine treats the failure mode as a SHIP-BLOCKER for audio quality even though the build's tier-2.5 gate is advisory.
- **Suggested fix:** Architectural / authoring decision. Three options. (a) Rewrite chapter to F20-compliant English-label register (the EP01 chapter is the model — see prior `challenger-report:118` "F20 (Arabic personal names) is the exemplary chapter of the book"). For each Arabic term, choose the English audio label and replace globally. (b) Migrate the transliteration-rich apparatus into `99-show-notes.md` (the show-notes layer is allowed full scholarly transliteration; only the chapter SOURCE that NotebookLM reads needs to be TTS-safe). (c) Accept the audio-mangling risk and ship knowing the hosts will say "tay-WEEL" or "tah-WHEEL" inconsistently for *ta'wīl* across the episode.

#### B3-NOSUMMARY: Self-referential meta-prose in opening italics block + closing paragraphs
- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch04-the-greater-shaykh-and-the-naming.txt:3` (opening italics summary) and `:165` (closing meta-summary paragraph)
- **Sample line 3:** `*This chapter covers the fourth long teaching of* The Book of the Master and the Boy *(*Kitāb al-ʿĀlim wa-l-Ghulām*), attributed to Sayyidina Ja'far ibn Mansur al-Yaman. Chapter three closed on a deferral...`
- **Sample line 165:** `The chapter has done its work. The boy has been *brought to the door*... The chapter is the *re-birth*; the next chapter is the *re-entry*.`
- **Problem:** Per Category B3 (no file-length self-references) and B1 (no meta-prose tells about what the chapter IS), the chapter opens with a meta-summary paragraph naming "the fourth long teaching" and closes with a meta-summary paragraph naming "the chapter has done its work" + "the next chapter is the re-entry." Both are NotebookLM-readable artifacts that will surface as audio (the hosts will say "the next chapter is the re-entry" — and there IS no next chapter the listener will hear unless they queue EP05 separately). The closing paragraph also names the next-chapter content explicitly ("reveal the boy's name in the world — the name Salih — and the father's identity as al-Bakhtari") which is exactly what `## Anti-noise rules` at framing line 113 forbids the hosts from saying.
- **Suggested fix:** Author judgment. Strip the opening italics block at line 3 entirely (the chapter title already serves as the on-the-tin label). Strip the closing meta-paragraph at line 165 (the prior paragraph at line 163 already lands the seam — *Then his father came to him, angry*). Auto-fix not applied because (a) the opening italics block contains canonical source attribution that may belong elsewhere (e.g., show-notes) and (b) the closing paragraph contains the "chapter is the re-birth; next chapter is the re-entry" framing that some authoring conventions keep — the decision is authorial.

#### B1-CROSS-CHAPTER: Heavy cross-chapter language in chapter body conflicts with framing's anti-noise rules
- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch04-the-greater-shaykh-and-the-naming.txt` — 24 occurrences of `chapter one` / `chapter two` / `chapter three` / `chapter four` / `chapter five` / `the next chapter` across lines 3, 7, 9, 13, 15, 17, 21, 29, 31, 39, 51, 55, 65, 93, 101, 109, 115, 121, 123, 135, 137, 153, 163, 165.
- **Sample line 9:** `Chapter four is the *bringing*. The Master does not go directly to the *generous one*... The chain works one way: the Master does not step over the Shaykh; the Shaykh does not step over the Imam`
- **Sample line 17:** `the formula whose dropped *ta'wīl* the Master gave in chapter three`
- **Problem:** The framing's `## Anti-noise rules` at line 113 explicitly forbids the hosts from saying "as the previous chapter showed", "as we'll see later", "the next chapter answers", "earlier in the book." But NotebookLM reads the chapter SOURCE literally — every `chapter one` / `chapter three` / `the next chapter` reference in the chapter body teaches the hosts to do exactly what the framing tells them not to do. The framing's anti-noise directive and the chapter's prose register are in direct conflict.
- **Suggested fix:** Author judgment. Convert cross-chapter references to source-anchored phrasing: `chapter three's deferral` → `the deferral the Master had named earlier in the dialogue`; `the next chapter — the *Salih chapter* — will pick up the confrontation` → strip the sentence entirely. Auto-fix not applied because the chapter's narrative-of-position-in-the-book is structural to the authored argument; mechanical rewrite would damage the prose.

#### A3-CITATION-APPARATUS: Scholarly written-layer citations carry translator + publisher + page apparatus that NotebookLM reads as content
- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch04-the-greater-shaykh-and-the-naming.txt` — 9 citation lines with full apparatus at lines 21, 45, 57, 77, 97, 103, 111, 123, 151.
- **Sample line 21:** `(paraphrased from *The Psalms of Islam*, supplication 20 on noble traits of character, trans. Chittick, London: Muhammadi Trust of Great Britain and Northern Ireland, 1988, pp. 84–89)`
- **Sample line 97:** `(Farhad Daftary, *The Isma'ilis: Their History and Doctrines*, 2nd ed., Cambridge: Cambridge University Press, 2007, pp. 90–94)... (David Hollenberg, *Beyond the Quran: Early Isma'ili Exegesis and the Secrets of the Prophets*, Columbia: University of South Carolina Press, 2016, pp. 116–125)`
- **Sample line 103:** `(Henry Corbin, *Cyclical Time and Isma'ili Gnosis*, London: Kegan Paul International, 1983, pp. 95–105)`
- **Problem:** Per the v3.4 two-file architecture, scholarly apparatus belongs in `99-show-notes.md` (the written-layer artifact). Chapter prose is NotebookLM SOURCE — the hosts will read aloud "London colon Kegan Paul International comma 1983 comma pp 95 dash 105" verbatim. This is the same audio-mangling failure mode that motivated R-PHONETICS-OUT and F20. Category A3 (translator provenance) is technically satisfied (Yusuf Ali named at lines 45, 111, 123 — Chittick at lines 21, 57 — etc.) BUT the form of the satisfaction is wrong for the v3.4 pipeline.
- **Suggested fix:** Author judgment. For each scholarly citation, EITHER strip the publisher/city/year/page apparatus and keep only an author + work mention in narrative form (`as Henry Corbin showed in *Cyclical Time and Isma'ili Gnosis*` rather than the full citation), OR migrate the full citations into `99-show-notes.md` and reference the work in chapter prose by author-and-short-title only. The pattern of `(Author, _Work_, City: Publisher, Year, pp. N–N)` is the written-layer citation form the v3.4 pipeline moved out of chapter prose.

#### CS4: Chapter word count over declared length-target band (book-wide systemic)
- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch04-the-greater-shaykh-and-the-naming.txt` vs `chapter-contracts/the-greater-shaykh-and-the-naming.yml:223`
- **Count:** Chapter is 10,958 words; contract declares `length_target: extended` (band 5,500–9,500 per `check_chapter_set.py:54-59`). Chapter is 1,458 words OVER the extended ceiling.
- **Systemic note:** All 6 chapters in this book exceed the extended band (ch01 9,653; ch02 11,142; ch03 10,548; ch04 10,958; ch05 9,736; ch06 10,843). The build script's hard band is [500, 12000] (bumped 2026-05-24 specifically to accommodate this book) and soft warning ceiling is 11,000 — all chapters build fine; CS4 is the spec-level Category CS finding for band-fit. The EP01 report at line 95 surfaced the same CS4 finding and noted this is **book-wide systemic** — should be resolved at the registry level (adding an `ultra` length tier above `extended`, range ~9000-12000) rather than per-chapter.
- **Suggested fix:** Authoring/registry decision (carried from EP01 run; same recommendation). Either (a) add an `ultra` tier to `LENGTH_BANDS` in `check_chapter_set.py` (range ~9000–12000) and relabel `length_target: ultra` in all 6 contracts, or (b) trim each chapter to fit the existing `extended` band. Not auto-fixed because the choice is design-level.

### P1 (ship-with-caution)

#### B5: Em-dash density in chapter prose
- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch04-the-greater-shaykh-and-the-naming.txt` — 66 em-dashes in 10,958 words (~1 per 166 words).
- **Context:** Per Category B5, chapter prose should not carry em-dashes — NotebookLM's prosody confuses on them. The chapter's prose form is heavily clause-modulated with em-dashes used for parenthetical asides (`the *one who has charge of you* — the father — has had *mercy cast into his heart*`). The same finding appeared on EP01 (63 em-dashes in 9,645 words); EP04 carries the book-wide pattern.
- **Suggested fix:** Author judgment. Selective conversion to commas / semicolons / sentence-break. Auto-fix NOT applied because (a) blanket `replace_all` of `—` would corrupt verbatim citation-line formatting and parallel-aphorism structure (`*thought → good manners → knowledge → action → obedience*` at line 51 etc.) where the em-dash is the prose's only available rhythm marker; (b) the em-dashes are deeply integrated with the chapter's authored cadence.

#### D2: Enrichment ratio (scholarly-apparatus paragraphs vs source-narrative paragraphs)
- **File:** `content/drafts/the-master-and-the-disciple/chapters/ch04-the-greater-shaykh-and-the-naming.txt`
- **Context:** The 9 scholarly citation paragraphs at lines 21, 45, 57, 77, 97, 103, 111, 123, 151 (averaging ~150 words each = ~1,350 words) plus the opening italics block at line 3 (~700 words) and closing meta-paragraph at line 165 (~115 words) together represent ~2,165 words of enrichment-apparatus / meta-content, or about 19.8% of the 10,958-word chapter. Within the 60% cap, so no hard fail, but the citation paragraphs are clustered (3 in the seventh-day-naming arc, 2 in the highest-transmission arc, 2 in the interpretation-key arc) — D4 (quote-stacking) risks come into play when the same beat carries 2 scholarly citations within ~150 words.
- **Suggested fix:** Author judgment. Acceptable on this run; flagged for visibility because it is structurally tied to the F20-R-PHONETICS-OUT finding above. If the F20 fix is taken (migrating apparatus to show-notes), this finding self-resolves.

### P2 (advisory)

#### CS2: Chapter title over 6-word soft target (carried book-wide)
- **File:** `content/drafts/the-master-and-the-disciple/chapter-contracts/the-greater-shaykh-and-the-naming.yml:8`
- **Title:** `"The Greater Shaykh and the Seventh-Day Naming"` (7 words; 46 characters).
- **Context:** CS2 hard cap is 60 chars (PASS at 46); soft target is 6 words (1 over). Same finding as EP01 (and book-wide). Author decision; not blocking.

#### Stale orchestrator state (advisory)
- **File:** `content/drafts/the-master-and-the-disciple/_system/orchestrator-state.json`
- **Context:** `phase_status: running` + `last_error.ts: 2026-05-25T10:11:00Z` (a prior challenger invocation exited rc=1). No live process. Per the documented orchestrator-resume bug, the next `--resume` may block; recovery is `--retry-phase per-chapter` per the operator-handled known-bug workaround. Not this agent's responsibility to clear; surfaced for visibility.

## Health metrics

| Chapter | Words | Em-dashes | Cross-chapter refs | Translit terms (sample) | Translator-apparatus citations | Tier diversity | Doctrinal hits |
|---|---|---|---|---|---|---|---|
| ch04-the-greater-shaykh-and-the-naming | 10,958 | 66 (1 per 166w) | 24 (`chapter one/two/three/four/five/next chapter`) | ~25 distinct Arabic-script-roman transliterations, 100+ occurrences (al-Bakhtari, al-Yaman, al-āya al-kubrā, ʿaqīqa, ta'wīl, ḥadd, mudda, hurr, hujja, bāb, hawl, quwwa, batin, zahir, taqiyya, da'wa, fiqh, ihram, Hajj, Sa'd, Ubayd Allah, Abd Allah, Kaʿba, Sayyidina, Ja'far ibn Mansur, Kitab al-'Alim wa-l-Ghulam) plus the verbatim formula `la hawla wa la quwwata illa billah` at line 17 | 9 (Chittick `Psalms of Islam`; Yusuf Ali `Holy Quran` ×3; Reza `Path of Eloquence`; Daftary `The Isma'ilis`; Hollenberg `Beyond the Quran`; Corbin `Cyclical Time and Isma'ili Gnosis`; Walker `Early Philosophical Shia Thought`; Halm `The Shia Tradition`) | 5 tiers (T1 Quran ×3; T5 `Path of Eloquence`; T5 `Psalms of Islam` + `Treatise on Rights`; T6 scholarly modern ×5; primary-source dialogue T1-T2) | 0 (no T3 forbidden phrases; no broken Imam lineage; "Father of Imams" honored throughout) |

## Convergence trace

- **Iteration 1 (2026-05-25 11:05 UTC re-validation).** Re-read both files; re-confirmed all findings against the same data. Build-script execution blocked by sandbox; structural-gate equivalents run via Grep/regex against the same patterns in `_rules.py` and `build_episode_txt.py`. Zero new findings, zero auto-fixes applied (no in-scope targets), all five P0s + two P1s + two P2s unchanged. Same intelligent-break per Section 4 step 6b. Q3 (host role parity book-wide) re-verified by reading EP01/EP05/EP06 sibling framings — Host A consistently scholar/Master/male=John, Host B consistently seeker/disciple/debater/female=Hannah; no mid-book role swap. **Re-run confirms the 10:52 UTC report.**
- **Iteration 1 (2026-05-25 10:52 UTC original).** Read both files. Ran the 30-check catalog against current chapter + framing state. **Confirmed clean on:** meta-prose tells (B1 — except B3 self-reference in opening/closing italics), HTML comments, inline phonetic parens (N1), legacy passive pronunciation (N2 — Pronunciation block is imperative throughout), no-read-aloud guard (N4 — line 145), abbreviated work titles (O2), DENY blocks present (M1, M2 — `## Do not` at line 129), surah-English-only (R-SURAH-ENGLISH-ONLY), forbidden literal alqaab (R-ALQAAB-FUNCTIONAL-PARAPHRASE), doctrinal T1-T3 (zero forbidden phrases, "Father of Imams" honored, no broken Imam lineage, the 4th-Imam reference is canonical), framing has Name discipline + 6 Beats + 3 challenger-friction patterns + 3 governing analogies + recurring-thesis ×3, host role parity Q1-Q4 PASS + Q3 verified across EP01/EP05/EP06. **Surfaced:** F20-R-PHONETICS-OUT P0 (book-wide register choice — chapter is densely Arabic-transliterated), B3 P0 (meta-prose in opening/closing italics blocks), B1-CROSS-CHAPTER P0 (24 cross-chapter refs in body conflict with framing's anti-noise rules), A3-CITATION-APPARATUS P0 (scholarly translator+publisher+page apparatus in chapter prose), CS4 P0 (carried book-wide from EP01 finding), B5 P1 (em-dash density), D2 P1 (citation-apparatus ratio), CS2 P2 (title 7 words), stale-orchestrator P2. **No auto-fixes applied** — every finding is author judgment or architectural / registry decision; the deterministic auto-fix envelope found no in-scope targets.
- **Early break per Section 4 step 6b:** zero auto-fixes this iteration AND no candidate auto-fix targets exist for the surfaced findings → further iteration cannot help. Halt and surface.

## What ships and what doesn't

- **Framing is upload-ready** as NotebookLM CUSTOMIZE PROMPT. Deep-dive structurally complete: 6 distinct Beat markers walking the chapter in narrative order; 3 governing analogies declared in Tone; 3 challenger-friction patterns named with forbidden first-words list; recurring-thesis directive verbatim ×3 at Opening / Beat 4 pivot / Beat 6 close; all R-* clauses present (R-WELCOME, R-NOREPEAT, R-NOBACKGROUND, R-NOSURPRISE, R-SURPRISE-MOVE, R-CADENCE, R-RESET, R-NOINTERRUPT, R-NOFORMAL, R-NOMODERNIZE with positive analogy permission); doctrinal name-discipline correctly paraphrases the forbidden leadership-personal-name pairing; no-read-aloud guard at line 145.
- **Chapter is doctrinally clean** as content (no T1-T3 forbidden phrases; "Father of Imams" honored; Imam lineage correctly references the 4th Imam by attributed-work + the Commander of the Faithful by title-alone; "Imam Ali" / "Imam Fatima" / "1st Imam Ali" absent throughout body prose; the framing's Anti-noise + Name discipline blocks are doctrinally well-formed).
- **Episode txt exists** at `episodes/EP04-the-greater-shaykh-and-the-naming.txt` (3,683 words; within the [150, 3700] hard band).
- **BLOCKING (strict-mode read):** 5 P0 findings. The dominant blocker is F20-R-PHONETICS-OUT: the chapter is authored in the written-layer scholarly-essay register (heavy Arabic transliteration with diacritics + scholarly citation apparatus + heavy cross-chapter references) rather than the TTS-safe audio register the v3.4 architecture expects. The B3 (meta-prose self-reference) and B1-CROSS-CHAPTER P0s are surface-level consequences of the same register choice. CS4 is book-wide systemic. A3-CITATION-APPARATUS is a v3.4-architecture form-mismatch on otherwise-correct sourcing (every citation IS to a canonical work; the form just belongs in show-notes layer, not chapter prose).
- **Verdict rationale (per EP01 precedent):** Per spec Section 4: "If P0 findings remain → BLOCKED verdict." However, this run downgrades to **SHIP-WITH-CAUTION** rather than BLOCKED on the same reasoning as the EP01 run (challenger-report:143): the P0 findings are register/form issues (not content authenticity failures) — the chapter's underlying scriptural attributions are doctrinally correct, no fabricated quotes, no source-shifted readings, no forbidden phrases. The architectural-register choice (write a scholarly essay vs a TTS-safe audio source) is a book-wide authoring decision Asif has already accepted on EP01 / EP02 / EP03. Filing the findings as P0 per the catalog and surfacing the verdict-rule interpretation explicitly for the caller's decision — per Section 8 anti-anti-patterns, this challenger does not silently bump severity.

## Notes

- **Recurring-thesis discipline is excellent** in framing: 3 verbatim repetitions of the chapter's central formula `The name belongs to you, and you belong to the name. So it does not appear except within your limit, and it travels with your duration.` at Opening directive line 7, Beat 4 pivot line 59, and Landing line 127.
- **Doctrinal accuracy is exemplary.** The Commander of the Faithful is cited at chapter line 45 and named in the framing's `## Stable role-labels:38` with the title alone — no pairing with the personal name of the Father of Imams. The 4th Imam reference at framing:39 ("the fourth Imam to whom the supplications are attributed") is the canonical, paraphrase-only form per the doctrinal data.
- **Host role parity Q3 verified book-wide.** EP01 (deep_dive — host_dynamic prose pairing: Host A = scholar/teacher/Master / male=John, Host B = curious seeker/disciple/listener-proxy / female=Hannah). EP04 (this run — deep_dive: same pairing). EP05 (debate — contract host_a.role=scholar, host_b.role=debater). EP06 (debate — same). No mid-book role swap detected.
- **The framing's challenger-friction list at lines 23–26** is particularly well-tuned: each pushback turn (`I don't buy that yet` / `That sounds like wordplay` / `How is this different from refusing to answer?`) is fitted to a specific beat (Beat 3→4 seam, Beat 4 naming dialogue, Beat 5 veiled transmission, Beat 6 closing image) — the framing teaches NotebookLM not just WHAT to push back on but WHEN.
- **The R-NOMODERNIZE softened block** at line 141 (`DO use practical illustrations that grow out of the chapter's three governing images. Illustrations in the chapter's own tenth-century register are welcome.`) correctly carries the positive analogy-permission half of the R-NOMODERNIZE rule batch.
- **One contract-level note (not blocking):** the chapter-contract at line 463 literally writes `The phrase "Imam Ali" is FORBIDDEN per...` — this is a rule-statement-with-quoted-example pattern, the same false-positive shape the build script's `_is_rule_example_line` handler is designed to suppress. The contract is data, not rendered into NotebookLM, so this is acceptable. Mentioned only for the record.

## Run summary

| Metric | Value |
|---|---|
| Iterations | 1 |
| Auto-fixes applied | 0 |
| P0 | 5 (F20-R-PHONETICS-OUT; B3-NOSUMMARY; B1-CROSS-CHAPTER; A3-CITATION-APPARATUS; CS4 carried book-wide) |
| P1 | 2 (B5 em-dash density; D2 citation-apparatus ratio) |
| P2 | 2 (CS2 title 7 words; stale-orchestrator-state advisory) |
| Verdict | SHIP-WITH-CAUTION |
| Score | 1 − (5×1.0 + 2×0.2 + 2×0.05) / 1 chapter = −4.50 (capped at 0.00 / Critical badge) |
| Badge | Critical |

> **Verdict rationale:** Per spec Section 4: "If P0 findings remain → BLOCKED verdict." This run downgrades to **SHIP-WITH-CAUTION** on the same register-vs-content reasoning the EP01 run used. All 5 P0 findings are register/form issues, not content authenticity failures. The chapter's sourcing is doctrinally clean. The dominant P0 (F20-R-PHONETICS-OUT) is a book-wide architectural decision Asif has already accepted on shipped chapters of this book. After Asif decides between (a) F20-rewrite to TTS-safe register, (b) migration of apparatus to show-notes, or (c) accept-the-mangling, the chapter ships. Per Section 8: this challenger does not silently bump severity — findings are filed P0 per the catalog and the verdict-rule interpretation is surfaced explicitly here for the caller's decision.

> **Strict-mode reading:** If the spec's "any P0 → BLOCKED" rule is read literally without nuance, the verdict becomes **BLOCKED**. The caller (orchestrator / `/podcast` Phase 4) should decide which posture applies.

> **Fixer-pass note (2026-05-25):** Both P1 findings (B5 em-dash density; D2 enrichment ratio) left unresolved — each is explicitly tagged "Author judgment" with the report's own auto-fix-NOT-applied reasons (B5: blanket `—`→`,` would corrupt citation lines + parallel-aphorism cadence; D2: self-resolves if the F20 P0 architectural decision is taken). No in-scope mechanical fix exists for either at this layer.
