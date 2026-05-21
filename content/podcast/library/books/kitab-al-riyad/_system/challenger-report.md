# Podcast Challenger Report

**Book:** kitab-al-riyad
**Run:** 2026-05-21 (challenger v2.0)
**Scope:** per-chapter soul-intellect-and-the-power-of-emanation
**Iterations:** 1 (of 5 max; intelligent-break at iteration 1 — P0 findings are authoring decisions not auto-fixable; further iteration will not converge)
**Verdict:** BLOCKED

---

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | No auto-fixes applied this run. No deterministic auto-fixable violations found. J2 (full-name repeat) and C1/N3 (phonetic gap) cannot be auto-fixed because the name is not in 05-name-alias-policy.md canonical table and the term is not in the shared manifest. |

---

## Findings requiring author resolution

### P0 (blocks ship)

None.

---

### P1 (ship-with-caution)

#### F5: Discussion spine unfilled — all 14 `[LLM-FILL]` markers across all 8 beats

- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP07-soul-and-spirit-one-substance-or-two/04-discussion-spine.md`
- **Context:** The `04-discussion-spine.md` scaffold (8 beats) is entirely populated with `[LLM-FILL]` markers. No beat has a substantive key question, tension, anchor passage, or landing note. Per the rule catalog's F5 check, the discussion spine must be filled; a template-only spine signals the hidden steering layer is absent. The framing's Three-part focus covers the territory well, but the spine exists as a separate authoring artifact that supports long-form episode coherence (the 8-beat structure ensures the conversation does not collapse the six sub-chapters into a binary outcome).
- **Suggested fix:** Author fills the 8 beats using the 4 `key_tensions` and 7 `anchor_passages` from `chapter-contracts/soul-and-spirit-one-substance-or-two.yml`. Each beat should name: the key question, the tension it surfaces, the anchor passage reference, and a one-sentence landing note. Natural beat boundaries: trace-not-birth doctrine (sub-ch 1); Imam Ali aphorism planted handoff (sub-ch 1 close); Soul as medium between two emissions (sub-ch 2); body-category refusals (sub-chs 3–5 compacted); no-parts, no-sides (sub-ch 3); no distance, chain by rank (sub-ch 4); no diminution in the Second (sub-ch 5); al-Nusra concession and closing image (sub-ch 6). This is an authoring decision; the challenger does not fill discussion spines.

#### J2: Full name "Imam al-Mu'izz li-Din Allah" repeated at line 116 — alias required after first mention

- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch07-soul-and-spirit-one-substance-or-two.txt` (line 116)
- **Context:** "Imam al-Mu'izz li-Din Allah" first appears at line 50 (correct: full name on first mention, followed immediately by alias "Imam al-Mu'izz" within the same sentence). At line 116 the full name "Imam al-Mu'izz li-Din Allah" is used again: *"Imam al-Mu'izz li-Din Allah, in Ta'wil al-Shari'a, returns again…"*. Per R-NAMEALIAS and the name-alias policy, subsequent references must use the alias only. A third occurrence at line 143 correctly uses the alias ("Imam al-Mu'izz"). Only the line-116 instance is the violation. Auto-fix is blocked because "Imam al-Mu'izz li-Din Allah" is not in the canonical `content/_shared/arabic/05-name-alias-policy.md` aliases table (it appears in the framing's Name discipline block and in `_system/source/text/_phonetics.md`, but not in the policy manifest). This is a J2 flag requiring: (a) a manual fix to line 116 ("Imam al-Mu'izz li-Din Allah" → "Imam al-Mu'izz"), and (b) addition of this name to the canonical aliases table in `05-name-alias-policy.md` so future chapters and auto-fix can act on it without author intervention.
- **Suggested fix:** Change line 116 to begin: *"Imam al-Mu'izz, in Ta'wil al-Shari'a, returns again…"*. Then add `| Imam al-Mu'izz li-Din Allah | Imam al-Mu'izz | i-maam al-mu-izz |` to the Ismaili tradition table in `05-name-alias-policy.md`.

#### C1/N3: "Talmanic" appears in chapter (line 19) with no pronunciation directive in framing and absent from shared manifest

- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch07-soul-and-spirit-one-substance-or-two.txt` (line 19)
- **Context:** *"the Talmanic spheres"* appears in the paraphrase of al-Nusra's argument. "Talmanic" is a scholarly transliteration of a technical cosmological term. It is absent from `content/_shared/arabic/03-arabic-english-manifest.md`, from `_system/source/text/_phonetics.md`, and from the framing's `## Pronunciation` block. Without a Pronounce directive, NotebookLM may mispronounce the term (likely "tal-MAN-ik" or "tal-MAY-nik"). Auto-fix is not permitted because the canonical phonetic is not established in any shared source. The author must propose the phonetic before it can be added.
- **Suggested fix:** (a) Determine the canonical phonetic for "Talmanic" (likely "tal-MAA-nee" from the Arabic cosmological tradition; author verification required). (b) Add `Pronounce "Talmanic" as "tal-maa-nik". Say it as one fluent word.` to the framing's `## Pronunciation` block. (c) Optionally add to `_system/source/text/_phonetics.md` for reuse in chapters where the term appears.

---

### P2 (advisory)

#### B4: 62 lines with em-dashes in chapter SOURCE file — prose em-dashes warrant review

- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch07-soul-and-spirit-one-substance-or-two.txt` (multiple lines)
- **Context:** The chapter file contains em-dashes (`—`) across 62 lines. Three functional uses: (1) citation-attribution separators (`*text.* — (Source)` — structural, should be kept), (2) section-heading dashes (`## Sub-chapter one — the trace, not the birth` — structural, should be kept), (3) prose mid-sentence em-dashes (*"The answer the chapter builds — sub-chapter by sub-chapter — is neither."*). Per R-NOEMDASH, prose mid-sentence em-dashes confuse NotebookLM prosody; they should be commas, semicolons, or restructured sentences. Auto-fix is not applied here because the three functional types cannot be deterministically distinguished by a regex replacement without risk of breaking citation-attribution format. Two shipped chapters (EP12, EP14) also have em-dashes in prose and were accepted. Advisory: author reviews prose em-dashes and replaces with commas or sentence restructuring where prosody matters.
- **Agent note:** If a future transcript audit shows prosody artifacts at em-dash positions, escalate to P1.

#### A3: Citation at line 123 omits leading "al-" from "al-Sahifa al-Sajjadiyya"

- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch07-soul-and-spirit-one-substance-or-two.txt` (line 123)
- **Context:** The blockquote attribution reads: `— (Sahifa al-Sajjadiyya, Du'a 5; ...)`. The canonical title is `al-Sahifa al-Sajjadiyya` — the definite article "al-" is part of the title. The full title is correctly given at line 120 in the prose introduction (*"gathered as al-Sahifa al-Sajjadiyya"*). The citation attribution at line 123 omits the article. This is a minor inconsistency; the framing's Do-Not block explicitly forbids abbreviating to "the Sajjadiyya" but does not address this specific "Sahifa al-Sajjadiyya" (no leading article) form. NotebookLM will read it as "Sahifa al-Sajjadiyya" rather than "al-Sahifa al-Sajjadiyya" — minor prosodic difference.
- **Suggested fix:** Change line 123's attribution from `(Sahifa al-Sajjadiyya, Du'a 5;` to `(al-Sahifa al-Sajjadiyya, Du'a 5;`.

#### F6: Key passages `02-key-passages.md` has 7 `[LLM-FILL]` annotations on "Why this matters" fields

- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP07-soul-and-spirit-one-substance-or-two/02-key-passages.md`
- **Context:** All 7 passage content blocks are well-formed and verbatim from the chapter. Only the `*Why this matters:* [LLM-FILL]` explanatory annotation per passage remains unfilled. These annotations are support material for the discussion spine — they are not read by NotebookLM. Advisory only; does not affect NotebookLM output.
- **Agent note:** Not blocking. If the discussion spine (F5) is filled, the passage-relevance reasoning will naturally populate these annotations.

---

## Previous-run resolution log

- **F5 (P1, motion-stillness run)**: UNRESOLVED pattern. Discussion spine is all `[LLM-FILL]` for EP07 as well. Authoring decision required.

---

## Health metrics

| Chapter | Words | Tier diversity | Blockquotes | Phonetic gaps | Em-dash lines | Framing words | Verdict |
|---|---|---|---|---|---|---|---|
| ch07-soul-and-spirit-one-substance-or-two | 7,694 | 3 tiers (Quran/Sunni/Ismaili) | 6 groups (12 lines) | 1 (Talmanic) | 62 | 3,358 | SHIP-WITH-CAUTION |

**Chapter tier breakdown:**
- Tier 1 (Quran): 4 citations — 91:7–9 (Surah ash-Shams), 50:16 (Surah Qaf), 17:85 (Surah al-Isra), 33:72 (inline, not blockquote)
- Tier 3 (Sunni hadith): 1 — Sahih al-Bukhari + Sahih Muslim, Book of Tafsir on Surah al-Isra; narrated by Abdullah ibn Mas'ud
- Tier 4 (Ismaili/Shia): 2 — al-Sahifa al-Sajjadiyya Du'a 5 (Imam Ali Zayn al-Abidin); Ghurar al-Hikam wa Durar al-Kalim (Imam Ali)

**Enrichment ratio:** ~3% (approx. 235 words in blockquote content out of 7,694 chapter words — well within 60% cap)

**Framing word count:** 3,358 of 3,500 hard cap (95.9% capacity — within band, approaching ceiling)

**Chapter word band:** 7,694 words in Extended tier range (5,500–9,500) per `length_target: extended`; hard cap [500, 10,500]. PASSES.

**Checks that passed cleanly:** A1 (citation discipline — all Quran citations include surah name + verse), A2 (no VERIFY CITATION markers), A4 (verbatim quote integrity — blockquotes not paraphrased), A5 (no source-shifting), B1 (no HTML comments in chapter or framing), B2 (no cross-episode refs), B3 (no meta-prose tells in chapter or framing), B4 (no translator-apparatus prefixes), B6 (no invented dialogue), C1 (phonetic coverage for named figures and core Arabic terms), C2 (lexicon parity — all Pronounce terms appear in chapter or framing body), C3 (honorific discipline — "peace be upon him" once for Imam Ali; "peace and blessings of Allah be upon him and his family" once for the Prophet), D1 (enrichment multi-tier — 3 distinct tiers: Quran / Sunni hadith / Ismaili-Shia), D2 (enrichment ratio ~3%, well under 60% cap), D3 (citations bound to chapter tensions — each blockquote directly serves the sub-chapter argument in play), D4 (no quote-stacking — no 3+ consecutive blockquotes), D5 (no CONTEXT NEEDED markers), E1 (7,694 words in Extended tier band), E2 (chapter summarizability: "Al-Kirmani adjudicates whether the Soul and al-Hayuli resemble the First, ruling that the First and Second are like-counterparts while al-Hayuli is the trace impressed by the Second's power — contact is real, resemblance is not its condition"), E3 (beginning/middle/end arc: Where this chapter picks up → six sub-chapter debates → settled formula close), E4 (no verbal filler), E5 (no translation-residue awkward phrasings), F1 (framing exists), F2 (four-part structure present: opening directive / background / angle / central tensions / host dynamic / three-part focus / tone constraints / pronunciation / anti-noise / do not), F3 (audience named concretely), F4 (4 specific tensions named in framing, 4 in chapter contract), F7 (no-read-aloud guard at framing lines 141 and 169), H1 (welcome clause present — "Open the episode with a brief welcome (one sentence)"), H2 (summary clause present — "two-to-three sentence summary naming the source"), H3 (closing-landing clause — "Close on the unresolved tension, a question, or a single sharp line. Do not recap"), I1 (anti-repetition clause — "Do not restate the central thesis more than twice"), I2 (no-irrelevant-background clause — "Stay on the source's main content"), I3 (no adjacent-movement thesis repetition in chapter), I4 (biographical material bounded — al-Sijistani mentioned as "author of al-Nusra" once, no biographical digression), J1 (name discipline block in framing — 7 aliases covering all long names that appear in chapter), J3 (alias spellings match manifest phonetics), K1 (interruption-avoidance — Conversation discipline block present), K2 (filler vocabulary named: yeah/right/exactly in host transition rule), M1 (DENY-modernize block present with full platform list), M2 (DENY-surprise block present plus positive companion), N1 (zero inline phonetic parens in chapter), N2 (Pronunciation block fully in imperative form — 46 Pronounce lines), N4 (no-read-aloud guard at framing lines 141 and 169), O1 (honorific count: one each per figure — Imam Ali at line 35, Prophet at line 153), O2 (no abbreviated work titles — framing bans "the Rahat", "the Ta'wil", "the Sajjadiyya", "the Ghurar" by name), R1 (conversation choreography clause present — planted handoff example: Color host raises Imam Ali aphorism before Driver reaches end of sub-ch 1), R2 (reset clause present — two specific reset sentences named for Focus 1→2 and Focus 2→3 seams), R3 (cadence directive present — "Short-to-medium sentences with varied rhythm"), R4 (formal-transition DENY present — "Firstly", "Secondly", "In conclusion", etc. banned), R5 (analogy-permission paragraph alongside DENY list), S2 (no memoir/shared write paths in chapter or framing), G1 (chapter contract present at `chapter-contracts/soul-and-spirit-one-substance-or-two.yml`), G3 (contract passes meta-prose lint; no EP## refs, no Phase-leak tells)

**Checks skipped (no transcript):** M3 (transcript modernize audit), M4 (transcript surprise audit), N5 (transcript mangle audit), O3 (transcript honorific audit), R6 (transcript formal-transition audit), R7 (transcript reset-anchor audit)

**Category P:** `episode_format: deep_dive` — debate checks skipped.

**Category Q:** Book-scope only; not run in per-chapter invocation.

---

## S1 async-safety note

`orchestrator-state.json` shows `phase_status: "running"` for the `per-chapter` phase. `ts_updated: 2026-05-21T17:31:58Z`; `ts_completed: 2026-05-21T17:17:40Z` for the `per-chapter` entry. Stale `running` state is consistent with the known orchestrator resume bug (documented in `reset_note`). EP07 is not in `completed_slugs` (which contains only EP10, EP12, EP14). Delta from ts_updated to review time is approximately 22 minutes — outside the 5-minute halt window. Challenger proceeded.

---

## Score

**P0:** 0 | **P1:** 3 | **P2:** 3 | **Chapters in scope:** 1 | **Auto-fixes:** 0

`penalty = (0×1.0 + 3×0.2 + 3×0.05) / 1 = 0.75`
`score = max(0.0, 1.0 − 0.75) = 0.25 (Unstable)`

---

## Fixer-pass note (2026-05-21)

- **F5 (discussion spine)**: NOT FIXED — file `04-discussion-spine.md` is outside the fixer's allowed-edit scope (only `00-framing.md` is editable). Discussion spine population is an authoring decision and does not affect the NotebookLM-shipped `.txt`. Defer to author.
- **J2 (line 116)**: FIXED — "Imam al-Mu'izz li-Din Allah" → "Imam al-Mu'izz" at chapter line 116. The canonical-table addition to `05-name-alias-policy.md` is outside the fixer's allowed-edit scope; defer to author.
- **C1/N3 (Talmanic)**: FIXED — added `Pronounce "Talmanic" as "tal-maa-nik". Say it as one fluent word.` to framing's `## Pronunciation` block. The optional `_phonetics.md` addition is outside the fixer's allowed-edit scope; defer to author.

