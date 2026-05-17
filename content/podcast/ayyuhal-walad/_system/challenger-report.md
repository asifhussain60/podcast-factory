# Podcast Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-05-17 (fresh re-run under v3.5; producer-side self-audit)
**Scope:** per-book sweep (5 chapters + 5 framings)
**Iterations:** producer-side self-audit only; the `/podcast-challenger` agent run is **deferred to Asif** post-review (Phase 4 step 1a)
**Verdict (self-audit):** SHIP-READY-FOR-CHALLENGER

This report records the structural pass and the self-audit against the 30-check catalog in `.github/agents/podcast-challenger.agent.md`. The agent run itself (the convergence loop) is the gate Asif controls — he invokes `/podcast-challenger ayyuhal-walad` when ready to converge.

---

## Iteration history

| Date | Iter | Action | Notes |
|---|---|---|---|
| 2026-05-17 | producer | Phase 0a–0g | Fresh PDF extraction, normalized text folded into chapter authoring, phonetics index built, 5-chapter plan carried over from prior workspace and re-authored from scratch under v3.5 |
| 2026-05-17 | producer | Phase 4 step 2 first pass | 4/5 episodes built clean; EP02 caught on R-HONORIFIC-ONCE (2x `(may Allah have mercy upon him)` and 2x `Imam Ali (AS)` in ch02); EP05 caught on B2 (META_PROSE "previous episode") |
| 2026-05-17 | producer | Phase 4 step 2 fix pass | ch02 honorifics + EP05 framing patched; all 5 build clean |
| 2026-05-17 | producer | em-dash sweep (R-NOEMDASH, B5) | 133 em-dashes across chapters + framings replaced with commas via deterministic regex |
| 2026-05-17 | producer | Pronounce-line gap fill (N3) | EP01 added Pronounce lines for Minhaj al-Abidin, bid'a, Kimiya al-Sa'ada, Arba'in. EP03 added Pronounce line for Riyad al-Salihin |
| 2026-05-17 | producer | rebuild + verify | all 5 episodes build clean; word counts in band; episode txts 1,580–1,896 words; chapters 2,579–3,090 words |

---

## Catalog pass (self-audit against challenger v1.3, 30 checks)

### Category A: Authenticity (P0)

| Check | Status | Notes |
|---|---|---|
| A1 (Citation discipline) | ✓ PASS | Every Quranic verse cites surah:verse. Translator (Yusuf Ali) named on first per-chapter use. Hadith citations carry collection where canonically available; source-internal hadith without published numbers are left unsuffixed rather than fabricated (preserves A2). |
| A2 (Citation authenticity) | ✓ PASS | Zero `[VERIFY CITATION]` markers. No fabricated hadith numbers. |
| A3 (Translation provenance) | ✓ PASS | Yusuf Ali named on first Quranic citation in every chapter that quotes the Quran (ch01:40, ch02:22, ch03:9, ch04:23, ch05 has no direct Quranic blockquote and so the rule is moot). |
| A4 (Verbatim quote integrity) | ✓ PASS | All scripture and hadith blockquotes are verbatim from the Yusuf Ali rendering or the source's hadith citation. |
| A5 (No source-shifting) | ✓ PASS | Self-audit; no obvious source-shifting flagged. Agent run will catch semantic drift. |
| A6 (No cross-tradition collision) | ✓ PASS | Sunni and Tier 4/5 sources are kept distinct in attribution; ch05 explicitly names the Ismaili tradition's *Holy Du'a* alongside the Sunni hadith in a way that names both, not collapses them. |

### Category B: NotebookLM literalness (P0)

| Check | Status | Notes |
|---|---|---|
| B1 (No meta-prose) | ✓ PASS | Build script passed all 5 chapters and all 5 framings post-strip. |
| B2 (No cross-episode refs) | ✓ PASS | EP05 caught initially; rewritten to "the letter's preceding section". No `EP##` regex hits in chapter bodies. The EP## references in Upload Checklists are stripped before emission by `build_episode_txt.py`. |
| B3 (No file-length self-refs) | ✓ PASS | No "in a few thousand words" / "this chapter has" / etc. |
| B4 (No translator-apparatus prefixes) | ✓ PASS | No "the translator notes" / "the square brackets are" / etc. The translator's-note material from the source PDF page 2 is summarized in `_system/editorial-notes.md`, not in chapter bodies. |
| B5 (No em-dashes) | ✓ PASS | All em-dashes replaced with commas. Final scan: 0 em-dashes in any chapter or framing. One en-dash residue in EP01 upload-checklist fixed. |
| B6 (No invented dialogue) | ✓ PASS | All dialogue (Haatim and Shaqeeq, the angel and the worshipper, etc.) is from the source. No fabrication. |

### Category C: Pronunciation discipline (P1)

| Check | Status | Notes |
|---|---|---|
| C1 (Phonetic coverage) | ✓ PASS (post-N3 fill) | Every transliterated Arabic term in every chapter has a matching imperative `Pronounce "..."` line in the matching framing. |
| C2 (Lexicon parity) | ✓ PASS | All phonetics match the SHARED_ARABIC manifest. `_phonetics.md` is the per-book index. |
| C3 / O1 (Honorific discipline) | ✓ PASS | Each honorific phrase form ≤1 per chapter (the build script enforces this; passes for all 5). |
| C4 (Substitution policy) | ✓ PASS | `nafs` kept where the source explicitly defines it as a technical term (ch02 second-benefit beat); elsewhere substituted to "lower soul" / "the soul". `shaytan` → "Satan". `ruh` → "spirit". `dunya` → "this world". `akhirah` → "the Hereafter". etc. Editorial notes record the substitution decisions. |

### Category D: Enrichment & depth (P1)

| Check | Status | Notes |
|---|---|---|
| D1 (Multi-tier enrichment) | ✓ PASS | Every chapter draws on ≥4 tiers. Tier mix across the series: Tier 1 + 2 + 3 + 4 + 5 + 6. |
| D2 (Enrichment ratio ≤ 60%) | ✓ PASS | All chapters estimated at 25–32% enrichment, well below the 60% cap. The source's own argument remains the spine. |
| D3 (Tradition-coherence over breadth) | ✓ PASS | Citations cluster around named tensions (e.g., the "knowledge without action" tension in ch01 anchors Quran + hadith + Imam Ali + Hasan al-Basri together). |
| D4 (No quote stacking) | ⚠ ADVISORY | ch01:39-46 stacks three Quranic verses back-to-back (99:7-8, 18:110, 18:107). The chapter intentionally preserves this stacking as Ghazali's rhetorical move: he piles them so no single verse can be argued away. The chapter explicitly names this on the next sentence ("The pattern is unmistakable"). The stacking is the structure. Carry-over from prior workspace; previously marked as P2 ADVISORY by challenger v1.0. |
| D5 (No `[CONTEXT NEEDED]`) | ✓ PASS | None. |

### Category E: Articulation & shape (P1)

| Check | Status | Notes |
|---|---|---|
| E1 (Word-count band) | ✓ PASS | All chapters 2,579–3,090 (above the 1,800–2,800 sweet spot, well within 1,500–4,500 acceptable). Variance across chapters: 3,090 vs 2,579 = 20% — within the ±30% balance target. |
| E2 (One-sentence summarizability) | ✓ PASS | Each chapter has a clear one-sentence summary in the opening contextual paragraph. |
| E3 (Beginning/middle/end arc) | ✓ PASS | Each chapter opens with a contextual frame, develops through movements, lands. |
| E4 (No verbal filler) | ✓ PASS | The chapter prose is built. No "well, you know" / "wow" / etc. |
| E5 (No translation-residue calques) | ✓ PASS | The chapters are rewritten in clean modern English, not preserving the Urdu→English calque rhythm of the source. |

### Category F: Framing integrity (P1)

| Check | Status | Notes |
|---|---|---|
| F1 (Framing exists per chapter) | ✓ PASS | 5/5 framings present and slug-matched. |
| F2 (Four-part structure) | ✓ PASS | All framings carry Opening directive, Background, Audience, Angle, Central tensions, Host dynamic, Tone constraints, Permission to disagree, Three-part focus, Pronunciation, Do not, Upload checklist. |
| F3 (Audience named concretely) | ✓ PASS | "Thoughtful seekers, Muslim and otherwise, drawn to the Islamic and Sufi spiritual tradition." Concrete; not generic. |
| F4 (2–4 specific tensions) | ✓ PASS | Each framing names exactly four specific tensions in the *Central tensions to reach* section. Not generic themes. |
| F5 (Discussion-spine 6–12 beats) | n/a | Architecture v3.5 does not require a separate `04-discussion-spine.md` file. The framing's Three-part focus + Central tensions block serves the steering function. |
| F6 (Steering phrases present) | ✓ PASS | "Slow down on…", "Close on the unresolved tension", "Quote X directly", "End on … no host commentary after" all appear. |

### Category G: Extract Mode contracts

n/a — this is a Series Mode book; no `chapter-contracts/` directory.

### Category H: Welcome opening + closing landing (P1)

| Check | Status | Notes |
|---|---|---|
| H1 (Welcome clause) | ✓ PASS | Every framing's Opening directive instructs a one-sentence welcome. |
| H2 (Summary clause) | ✓ PASS | Every framing's Opening directive instructs a 2–3 sentence summary naming source + tension + landing. |
| H3 (Closing landing) | ✓ PASS | Every framing's Three-part focus → Landing section instructs the close on an unresolved tension / question / sharp line, with explicit "do not recap" language. |

### Category I: Anti-repetition + no-irrelevant-background (P1)

| Check | Status | Notes |
|---|---|---|
| I1 (Anti-repetition clause) | ✓ PASS | Every framing's Do not section forbids restating thesis more than twice, re-citing quotes, summarizing what was just said. |
| I2 (No-irrelevant-background clause) | ✓ PASS | Every framing's Do not section bounds biographical/historical context to one mention, pertinent only, never returned to. |
| I3 (Chapter respects no-repetition) | ✓ PASS | Self-audit; agent will catch any drift. |
| I4 (Chapter background bounded) | ✓ PASS | Biographical content (Ghazali's autobiographical exit from Baghdad, the Nizamiyya, etc.) appears at most once and only where it serves an argument. |

### Category J: Name aliasing (P1)

| Check | Status | Notes |
|---|---|---|
| J1 (Name discipline block in framing) | ✓ PASS | Every framing's Pronunciation block has a Name discipline sub-block listing each long name → alias. |
| J2 (Chapter applies alias) | ✓ PASS | After first mention, each chapter uses the alias for every long name (Ghazali, Junaid, Sufyan, Shaqeeq, Haatim, Dhu'l-Nun, Imam Ali, etc.). |
| J3 (Alias matches canonical phonetic) | ✓ PASS | Every alias matches `content/_shared/arabic/05-name-alias-policy.md`. |

### Category K: Interruption avoidance + host dynamic (P1)

| Check | Status | Notes |
|---|---|---|
| K1 (Interruption-avoidance clause) | ✓ PASS | Every framing's Host dynamic section names "Conversation discipline" with explicit no-interjections language. |
| K2 (Filler-injection words named) | ✓ PASS | "yeah", "right", "exactly" named in every framing's Host dynamic. |

### Category M: Modernization + surprise-noise audit (P0/P1)

| Check | Status | Notes |
|---|---|---|
| M1 (DENY-modernize block) | ✓ PASS | Every framing's Do not section carries the full canonical DENY-modernize list (Twitter, X, social media, algorithm, etc.). |
| M2 (DENY-surprise block) | ✓ PASS | Every framing's Do not section carries the full canonical DENY-surprise list (wow, right?, exactly, it's chilling, etc.). |
| M3 (Transcript modernizations) | DEFERRED | No transcripts yet (this is the fresh re-run; nothing has been generated). Loop M re-runs after audio is generated and transcribed. |
| M4 (Transcript surprise density) | DEFERRED | Same. |

### Category N: Phonetic-as-content audit (P0)

| Check | Status | Notes |
|---|---|---|
| N1 (Zero inline phonetic parens in chapter) | ✓ PASS | Build script's `INLINE_PHONETIC_PATTERNS` regex passes for all 5 chapters. Author-side discipline: chapters were written under v3.5 from scratch, no phonetic parens ever inserted. |
| N2 (Framing Pronunciation uses imperative) | ✓ PASS | Every Pronunciation line in every framing begins `Pronounce "..."` or `Do not`. |
| N3 (Every Arabic term has a Pronounce line) | ✓ PASS (post-fill) | Initial audit found 4 minor gaps (Minhaj al-Abidin, bid'a, Riyad al-Salihin, Kimiya al-Sa'ada in framings); all 4 filled. |
| N4 (No-read-aloud guard at end) | ✓ PASS | Every framing ends with `Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.` |
| N5 (Transcript doublings) | DEFERRED | No transcripts yet. |

### Category O: Honorific repetition + abbreviation audit (P0)

| Check | Status | Notes |
|---|---|---|
| O1 (Honorific ≤1 per chapter per form) | ✓ PASS | Build script enforces; passes for all 5 chapters. |
| O2 (No abbreviated work titles) | ✓ PASS | "Ihya Ulum al-Din" written in full every time across all 5 chapters. "Nahj al-Balagha" written in full. "Sahih Bukhari" + "Sahih Muslim" written in full. |
| O3 (Transcript honorific repetition) | DEFERRED | No transcripts yet. |

---

## Health metrics

| Chapter | Words | Episode words | Enrichment % (est.) | Tiers | Citations | Phonetic gaps | Honorific repeats | Em-dashes |
|---|---|---|---|---|---|---|---|---|
| ch01 | 3,090 | 1,896 | ~28% | 5 (T1,2,3,4,6) | 17 | 0 | 0 | 0 |
| ch02 | 2,579 | 1,580 | ~32% | 4 (T2,3,4,6+T5 ref) | 17 | 0 | 0 | 0 |
| ch03 | 3,076 | 1,736 | ~25% | 5 (T1,2,3,4,6) | 8 | 0 | 0 | 0 |
| ch04 | 2,752 | 1,640 | ~26% | 5 (T1,2,3,4,6) | 6 | 0 | 0 | 0 |
| ch05 | 2,718 | 1,724 | ~28% | 5 (T1,3,4,5,T2 lite) | 10 | 0 | 0 | 0 |

Cross-chapter variance: ~20% (3,090 vs 2,579), within the ±30% balance target.

---

## Findings requiring author / challenger resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

None at the structural / self-audit level. The convergence loop run by `/podcast-challenger ayyuhal-walad` will surface any semantic findings the producer self-audit missed (host-dynamic feel, citation authenticity, source-shifting, etc.).

### P2 (advisory)

- **D4 quote stack in ch01:39-46** — three Quranic verses stacked back-to-back. Intentional rhetorical move; explicitly named in the next sentence. The prior challenger v1.0 also marked this P2 ADVISORY and accepted it. The author may revisit if reading audio shows the stack overwhelming the rhythm.

---

## Next action for Asif

1. Invoke `/podcast-challenger ayyuhal-walad` to run the agent's full convergence loop. Auto-fixes will land in chapters + framings; any P0 / P1 findings will be surfaced for resolution.
2. After challenger says `SHIP-READY`, upload episode 1 to NotebookLM per the Upload checklist in EP01's framing. Use it as a spot-test before queueing the rest.
3. Once audio is generated and transcribed via TurboScribe, drop the transcripts into `turboscribe/` and re-run the challenger for Loop M (empirical-transcript audit).
