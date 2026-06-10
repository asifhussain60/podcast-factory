# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-10 (challenger v2.5)
**Scope:** per-chapter abu-malik-arrives-and-the-fair-inquiry
**Iterations:** 2 (of 5 max)
**Verdict:** SHIP-WITH-CAUTION
**Content profile:** islamic_scholarly

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | No deterministic auto-fixes triggered this run. Prior-iteration V4 fix on line 21 ("two faster routes that bypass the inquiry") confirmed landed. |

Em-dash count (B5): 13 in chapter, 21 in framing. Policy defer per memory `feedback_systemic_fixes_from_chapter_archetype.md` — root cause is upstream normalizer behavior; mechanical `—` → `,` substitution would degrade parenthetical-clause cadence in the chapter's dense citation prose.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### V4 (residual) — "cheap moves" recurs in Closing
- **File:** content/Islamic/the-master-and-the-disciple/chapters/ch14c-abu-malik-arrives-and-the-fair-inquiry.txt:65
- **Context:** Opening paragraph (line 21) was softened from "cheap ways" to "two faster routes that bypass the inquiry" in the prior pass. The Closing recap (line 65) still reads "Abu Malik refuses both cheap moves on which his clients had been counting." The narrator-pejorative the V4 fix removed at the open returns at the close, undoing the discipline.
- **Suggested fix:** Reword line 65 to "Abu Malik refuses both faster routes on which his clients had been counting" or "both bypass moves" to keep the inversion landed by Abu Malik's reasoning rather than the narrator's verdict.

#### CS / book-scope cross-chapter content overlap (carried)
- **File:** content/Islamic/the-master-and-the-disciple/chapters/ch14c-abu-malik-arrives-and-the-fair-inquiry.txt
- **Context:** Shares 5 distinct 12-word passages with `homecoming-and-the-forty-year-syllogism` (the prior chapter). Sample: "allah gave life to a great number of people in that country."
- **Suggested fix:** This chapter opens by reaching back to the prior chapter's landing sentence as the priced cost of homecoming. Either reword by function ("the largest sentence the book had let itself") without re-quoting, OR accept as deliberate bridging. Author decision; not a new finding this pass.

### P2 (advisory)

#### B5: Em-dash density (chapter 13, framing 21)
- **File:** chapter + framing
- **Context:** Em-dashes carry parenthetical clauses dense with attribution. The systemic preferred fix is normalizer-side (book-wide), not per-chapter mechanical substitution.
- **Suggested fix:** Defer to systemic fix. No per-chapter action.

#### U1 false-positive: "today's episode" inside DENY context
- **File:** content/Islamic/the-master-and-the-disciple/_system/episode-drafts/EP14-abu-malik-arrives-and-the-fair-inquiry/00-framing.md:4
- **Context:** Substring appears inside the deny clause ("No vehicle-talk, no 'today's episode.'") instructing hosts not to use it.
- **Suggested fix:** None. Recorded for ledger continuity.

## Health metrics

| File | Words | Em-dashes | Notes |
|---|---|---|---|
| ch14c-abu-malik-arrives-and-the-fair-inquiry.txt | 2,620 | 13 | Inside Default Deep Dive band (1,800–2,800) |
| EP14-…/00-framing.md | 725 | 21 | Comfortably inside framing soft band |

| Check family | Status |
|---|---|
| A (Authenticity / citations) | Clean — every blockquote and verse carries inline source attribution with translator + edition + page |
| B (NotebookLM literalness) | Clean (em-dashes deferred per systemic policy) |
| C / N (Phonetic discipline) | Clean — framing uses imperative "Say each term ONCE" form; no inline phonetic guides in chapter |
| D (Enrichment depth) | Clean — 4+ tiers cited (Quran, Tabari, Ghurar al-Hikam, Peak of Eloquence, Tirmidhi, Daftary); enrichment ratio ~30% |
| E (Articulation & shape) | Clean — three-movement arc (summons → three readings → inversion of signs → same-day departure) |
| F (Framing integrity) | Clean — 4-part structure plus Name discipline / Pronunciation / Tone / Do-not |
| H (Welcome + landing) | Clean — Welcome present, landing closes on a modern question |
| I (Anti-repetition + bounded background) | Clean — R-RECURRING-THESIS deliberately repeats spine 3× by design |
| J (Name aliasing) | Clean — Name discipline names Abu Malik, al-Bakhtari, Salih, Commander of the Faithful, Prophet, sixth Imam |
| K (Host dynamic) | Clean — scholar/seeker pairing with 3 friction beats + 1 concession |
| M (Modernize + surprise) | Clean — Do-not block names Twitter, social media, algorithm, "wow", "right?" |
| O (Honorific + abbreviation) | Clean — honorifics introduced once per phrase form |
| Q (Host role parity) | Clean — Host A (male, scholar) + Host B (female, seeker), consistent with book-wide pattern |
| R (Conversation choreography) | Clean — Tone + Host dynamic + Do-not block carry the choreography clauses |
| T (Doctrinal accuracy) | Clean — no forbidden-phrase pairings; sixth Imam by ordinal, not Father-of-Imams collision |
| U (Scholarly-conversation rubric) | One U1 false-positive (deny-context "today's episode") — no real findings |
| V (Interest & engagement) | V1 satisfied (line 7 rhetorical question hook); V3 present (relevance); V4 residual in line 65 (P1 above) |

## PEQ Score

Estimated PEQ: ~82 (WARN-band, single V4 residual prevents PASS ≥85).
- Fidelity (30%): ~28 — citations dense, translations attributed, no source-shifting.
- Voice (20%): ~17 — scholar/seeker register intact.
- Structure (18%): ~16 — clean three-movement arc.
- Enrichment (17%): ~15 — multi-tier citations, well-bounded.
- Interest (15%): ~10 — V1 hook present, V4 residual narrator-pejorative pulls this down ~3 points.

Single P1 fix to line 65 would lift PEQ into PASS band.
