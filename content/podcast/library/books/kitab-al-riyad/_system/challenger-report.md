# Podcast Challenger Report

**Book:** kitab-al-riyad
**Run:** 2026-05-21 (challenger v2.0)
**Scope:** per-chapter souls-as-parts-or-traces
**Iterations:** 1 (of 5 max; intelligent-break after iteration 1: two A3 P0 findings are author-resolvable citation omissions; further iteration cannot auto-fix them; breaking early and surfacing to caller)
**Verdict:** BLOCKED

---

## Auto-fixes applied (iteration 1)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | B5 | content/podcast/library/books/kitab-al-riyad/chapters/ch08-souls-as-parts-or-traces.txt | Replaced 59 lines of em-dashes with commas/semicolons throughout chapter prose and translated-speech sections. Zero em-dashes remain. |
| 1 | O1 | content/podcast/library/books/kitab-al-riyad/chapters/ch08-souls-as-parts-or-traces.txt:145 | Restored ﷺ glyph on "Prophet Muhammad ﷺ seeing" (double-space gap indicated stripped glyph). |
| 1 | O1 | content/podcast/library/books/kitab-al-riyad/chapters/ch08-souls-as-parts-or-traces.txt:175 | Restored ﷺ glyph on "where the Prophet ﷺ saw at the boundary" (same strip pattern). |
| 1 | N3 | content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP08-souls-as-parts-or-traces/00-framing.md | Inserted `Pronounce "dar al-Ibda'" as "daar al-ib-daa"` directive in Pronunciation block (term in chapter line 73; phonetic sourced from _phonetics.md). |

---

## Findings requiring author resolution

### P0 (blocks ship)

#### A3: Quranic translations at Quran 91:7-10 and 53:7-11 have no named translator [BLOCKS SHIP]

- **File:** content/podcast/library/books/kitab-al-riyad/chapters/ch08-souls-as-parts-or-traces.txt, lines 79 and 143
- **Context:** The first Quranic blockquote in the chapter (Quran 17:85) correctly names the translator as Pickthall. Two subsequent Quranic blockquotes — Quran 91:7-10 (Surat al-Shams, line 79) and Quran 53:7-11 (the Prophet's vision at the highest horizon, line 143) — carry no translator identification. Cross-referencing Pickthall's known text: Pickthall renders Quran 91:7-8 as "And a soul and Him Who perfected it" (not "By the soul, and Him Who fashioned it" as in the chapter). Pickthall renders Quran 53:7 as "And he was on the uppermost horizon" (not "And he was at the highest horizon"). These are not Pickthall's renderings. The chapter is therefore silently blending translations from an unnamed second translator. Per check A3, every Quranic quotation must name its translator; when a subsequent translation is from a different translator than the one named first, that is a separate P0 A3 finding for each occurrence.
- **Required fix (not auto-fixable):** (1) Identify which translation is used for Quran 91:7-10 and Quran 53:7-11. Leading candidates: Yusuf Ali ("He who purifies it succeeds, and he who corrupts it fails" matches the chapter's sense), Sahih International, or Arberry. (2) Add the translator name to each citation line: `(Quran 91:7-10, [Translator])` and `(Quran 53:7-11, [Translator])`. (3) If the author prefers a single-translator chapter, replace all three blockquotes with consistently Pickthall-sourced text. This is a citation accuracy fix — auto-fix is not permitted for Quranic source attribution.

---

### P1 (ship-with-caution)

#### A1: Imam Ali aphorism has no specific collection citation

- **File:** content/podcast/library/books/kitab-al-riyad/chapters/ch08-souls-as-parts-or-traces.txt, line 39
- **Context:** "Imam Ali ibn Abi Talib (peace be upon him) is reported in the aphorisms of his tradition as having said that your soul is a precious jewel; whoever guards it has elevated it, and whoever lets it slip has lowered it." Per A1, every Imam Ali saying must cite either `(Nahj al-Balagha, Aphorism N)` or `(Ghurar al-Hikam, N)`. The loose form "aphorisms of his tradition" does not satisfy this citation discipline. The framing mirrors this loose attribution ("aphoristic tradition"), which is consistent, but the chapter-level source text is what NotebookLM hosts will read and cite back.
- **Suggested fix:** Locate this aphorism in Ghurar al-Hikam (a common source for soul-jewel aphorisms attributed to Imam Ali) or Nahj al-Balagha and add the specific number. If the aphorism is not traceable to either canonical collection, the framing's note "Attribute your soul is a precious jewel to Imam Ali ibn Abi Talib from the aphoristic tradition" documents the attribution approach — update the chapter citation to read `(attributed in the Ismaili aphoristic tradition)` so the qualified attribution is explicit, not implied.

#### B2-variant: "What comes next" section in the chapter SOURCE names Chapter Five content

- **File:** content/podcast/library/books/kitab-al-riyad/chapters/ch08-souls-as-parts-or-traces.txt, lines 179-183 (the "## What comes next" section)
- **Context:** The chapter ends with a "## What comes next" section that tells the reader what "Chapter Five of al-Riyad will take the next step..." and describes the seven sub-chapters that follow. This section is present in the chapter SOURCE file, which NotebookLM ingests verbatim. NotebookLM has no context of other episodes. The hosts reading this section will narrate content about a future chapter that is not in the source, producing bridging language to a chapter the listener has not heard and will not hear in this session. The framing at line 146 explicitly instructs: "Treat this as a standalone Audio Overview — do not reference other Audio Overviews in this series." The section's cross-chapter forward reference contradicts the standalone contract.
- **Suggested fix:** Author decision required. Two options: (a) Remove the "## What comes next" section from the chapter SOURCE file entirely (the content is pipeline metadata for the author, not source content for NotebookLM). (b) Keep the section but note it as author context only by converting it to an HTML comment `<!-- What comes next: ... -->`. The build script will then strip it before NotebookLM sees it, if the chapter is run through the pipeline. Option (a) is cleaner for direct upload. The challenger cannot auto-remove this section (content authoring decision).

#### F5: Discussion spine (04-discussion-spine.md) has beats 2-8 as unfilled [LLM-FILL] stubs

- **File:** content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP08-souls-as-parts-or-traces/04-discussion-spine.md
- **Context:** The discussion spine declares "8 beats" but only beat 1 (opening hook) has a structural shell; beats 2-8 show only `[LLM-FILL]` markers for every field (Key question, Tension, Anchor passage, Landing). The framing's Three-part focus is well-developed and covers the territory adequately for NotebookLM steering, so the unfilled spine does not block the episode, but it leaves the hidden steering layer absent. The eight sub-chapters of Chapter Four are demanding to navigate; a filled spine with explicit beat boundaries would materially improve host coherence across the 30-45 minute runtime.
- **Suggested fix:** Author fills beats using the 4 key_tensions and 8 anchor_passages from the chapter contract. Natural beat seams: (1) opening hook/vocabulary dispute setup, (2) al-Islah traces vs al-Nusra parts sub-ch 1, (3) al-Nusra positive proposal sub-ch 2, (4) dilemma refusal sub-ch 3, (5) second emanation doctrine sub-ch 4, (6) unlimited-capacity proof sub-chs 5-6, (7) prophethood stake sub-ch 7, (8) Intellect-is-Word deepest move sub-ch 8. This is an authoring decision; challenger does not fill spines.

---

### P2 (advisory)

#### O2-advisory: "God's prayers be upon them" — non-standard honorific form in translated text

- **File:** content/podcast/library/books/kitab-al-riyad/chapters/ch08-souls-as-parts-or-traces.txt, line 65
- **Context:** The phrase "God's prayers be upon them" appears twice in the italicized translation of al-Kirmani's text (within `*...*` markers). This is a literal rendering of the Arabic `Allahumma salli `alayhim` formula and is not in the standard English honorific forms (`peace be upon him`, `peace and blessings of Allah be upon him`, etc.). NotebookLM hosts will read it aloud as "God's prayers be upon them" — unusual phrasing that may sound awkward in audio. The framing's Tone constraints specify "Every honorific is spoken in full English" but do not address this translation-register formula.
- **Agent recommendation:** Advisory only. The phrasing is inside a translated quotation, not in the author's narrative voice. If the author prefers standard English form, replace with "peace be upon them" at both occurrences. If the translation-register form is intentional (preserving al-Kirmani's register), no change needed.

---

## Health metrics

| Chapter | Words | Tier diversity | Blockquotes | Phonetic gaps (post-fix) | Em-dash lines (post-fix) | Framing words | Verdict |
|---|---|---|---|---|---|---|---|
| ch08-souls-as-parts-or-traces | 7,316 | 4 tiers | 5 | 0 | 0 | 3,349 | SHIP-WITH-CAUTION |

**Chapter tier breakdown:**
- Tier 1 (Quran): 3 citations — 17:85 (Surah al-Isra), 91:7-10 (Surat al-Shams), 53:7-11 and 53:17-18 (Surat al-Najm)
- Tier 3 (Sunni hadith): 1 — Sahih al-Bukhari, Book 81, Hadith 38, narrated by Abu Hurayrah (Hadith Qudsi on voluntary works)
- Tier 5 (Ismaili source): 2 — Imam al-Mu'izz li-Din Allah, Ta'wil al-Shari'a (cited in sub-chapter eight); al-Kirmani's Asrar al-Ma'ad and Rahat al-'Aql (author's own treatises cited as cross-references)
- Tier 6 (Sufi tradition): 1 — Ibn Ata Allah al-Iskandari, Hikam, Aphorism 96

**Enrichment ratio:** ~8% (approximately 590 words in blockquote content out of 7,316 total — well within the 60% cap)

**Framing word count:** 3,349 of 3,500 hard cap (95.7% capacity — within band, approaching ceiling)

**Chapter word band:** 7,316 words; contract length_target: extended (band 5,500-9,500). PASSES.

**Auto-fixes this run:** 3 items (B5 em-dash replacement: 59 occurrences across 59 lines; O1 ﷺ restoration: 2 occurrences; N3 Pronounce directive: 1 insertion)

**Checks that passed cleanly:** A2 (no VERIFY CITATION or CONTEXT NEEDED markers), A4 (verbatim quote integrity — all 5 blockquotes match cited sources without paraphrase), A5 (no source-shifting — quotations framed consistently with scholarly context), A6 (cross-tradition adjacency acknowledged — Sahih al-Bukhari Hadith Qudsi and Ibn Ata Allah al-Iskandari Hikam introduced with explicit tradition labels), B1 (no HTML comments), B3 (no file-length self-references), B4 (no translator-apparatus prefixes), B6 (no invented dialogue or fictionalized scenes), C1 (phonetic coverage — all named persons have Pronounce directives; core Arabic terms covered), C2 (lexicon parity — all Pronounce terms match chapter usage), C3 (honorific discipline — peace be upon him once for Imam Ali, ﷺ once for Prophet in author prose), D1 (4 distinct tiers present — Quran, Sunni hadith, Ismaili authority, Sufi tradition), D2 (enrichment ~8%, well under 60%), D3 (all citations bound to sub-chapter tensions in play), D4 (no quote-stacking — blockquotes separated by commentary), D5 (no CONTEXT NEEDED markers), E1 (7,316 words in Extended band), E2 (chapter summarizable: al-Kirmani adjudicates eight sub-chapters on whether speaking souls are parts or traces of the universal Soul, landing on second emanation as the third and correct term), E3 (hook-middle-end arc: preamble + Where this chapter picks up → eight sub-chapters → settled formula close), E4 (no verbal filler), E5 (no translation-residue phrasings), F1 (framing exists), F2 (framing has Opening directive/Background/Audience/Angle/Central tensions/Host dynamic/Three-part focus/Tone constraints/Pronunciation/Anti-noise/Do not — full four-part structure plus extensions), F3 (audience named concretely: thoughtful adults who followed Chapters One-Three), F4 (four tensions named in framing and contract), F6 (steering phrases present: "Do not collapse the eight into a single thesis", "Half-credit is al-Kirmani's signature"), G1 (chapter contract present at chapter-contracts/souls-as-parts-or-traces.yml), G3 (contract passes meta-prose lint — no EP## refs, no Phase-leak tells in title/audience/key_tensions/tone_constraints/anchor_passages), H1 (welcome clause present), H2 (episode summary clause present: 2-3 sentence summary naming source, tension, landing question), H3 (closing-landing clause present: "End on the chapter's closing image and the bridge"), I1 (anti-repetition clause present: "Do not restate the central thesis more than twice"), I2 (no-irrelevant-background clause present), I3 (no adjacent-movement thesis repetition in chapter), I4 (biographical material bounded — Ibn Ata Allah context given once, concisely), J1 (name discipline block present — 6 aliases for all long names), J2 (alias application in chapter — Imam al-Mu'izz alias used after first mention), J3 (alias spellings match Pronunciation block), K1 (interruption-avoidance clause present: Conversation discipline block), K2 (filler vocabulary named: yeah/right/exactly), M1 (DENY-modernize block present with full canonical list), M2 (DENY-surprise block present), N1 (zero inline phonetic parens — all stripped in prior pipeline pass), N2 (Pronunciation block in imperative form — all Pronounce lines), N4 (no-read-aloud guard present at framing line 138 and line 166), O1 (after fix: ﷺ used correctly in author prose, once at line 141 intro, restored at 145 and 175), O2 (no abbreviated work titles — framing bans "the Rahat"/"the Asrar"/"the Ta'wil"/"the Hikam-set" explicitly), R1 (conversation choreography clause present — planted Hadith Qudsi handoff example detailed), R2 (reset clause present — two specific single-sentence reset directives at Focus 1→2 and Focus 2→3 seams), R3 (cadence directive present in Tone section), R4 (formal-transition DENY present — full list including Firstly/Secondly/Furthermore/In conclusion/Lastly), R5 (analogy-permission paragraph present alongside DENY list), S2 (no memoir/shared write paths in chapter or framing), S5 (no scope-out files modified)

**Checks skipped (no transcript):** M3, M4, N5, O3, R6, R7

**Category P:** episode_format: deep_dive — debate checks (P1-P13) skipped.

**Category Q:** Book-scope only; run separately. ch08 contract shows title "Souls — Parts of the First Truths, or Only Traces?" (41 chars, 8 words — over 6-word soft target; advisory Q2). No P0 Q-findings for this chapter.

---

## S1 async-safety note

`orchestrator-state.json` shows `phase_status: "running"` for the `per-chapter` phase with `ts_updated: 2026-05-21T18:56:44Z`. No actual orchestrate_book.py or build_episode.py processes found via pgrep. Stale `running` state is consistent with the known orchestrator resume bug. souls-as-parts-or-traces is not in `completed_slugs`. Delta from ts_updated exceeds 5-minute halt window. Challenger proceeded.

---

## Score

**P0:** 2 | **P1:** 3 | **P2:** 1 | **Chapters in scope:** 1 | **Auto-fixes:** 3

`penalty = (2×1.0 + 3×0.2 + 1×0.05) / 1 = 2.65`
`score = max(0.0, 1.0 − 2.65) = 0.00 (Blocked)`

Note: Two P0 A3 findings block ship. Both are author-resolvable: identify the translator(s) used for Quran 91:7-10 and 53:7-11 and add attribution lines. Once the A3 findings are resolved, the remaining P1/P2 findings (A1 collection citation, B2-variant forward-ref, F5 spine stubs, O2 honorific register) are authoring choices, not blockers. Resolving only the A3 findings will shift verdict to SHIP-WITH-CAUTION; resolving A1 and B2 as well would approach SHIP-READY.

