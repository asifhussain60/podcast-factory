# Podcast Challenger Report

**Book:** kitab-al-riyad
**Run:** 2026-05-21 (challenger v2.0)
**Scope:** per-chapter motion-stillness-hyle-and-form
**Iterations:** 2 (of 5 max; intelligent-break at iteration 2 — identical P0/P1 counts, zero auto-fixes)
**Verdict:** BLOCKED

---

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | J2 | chapters/ch10-motion-stillness-hyle-and-form.txt:195 | Replaced second full-name occurrence "Imam Ali ibn Abi Talib" with alias "Imam Ali" per name-alias policy |

---

## Findings requiring author resolution

### P0 (blocks ship)

#### A3: Translation provenance — first Quranic translation unnamed

- **File:** content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt:99
- **Context:** Blockquote `*His command, when He intends a thing, is only that He says to it, "Be," and it is.* (Quran 36:82)` — translation used without naming the translator. Subsequent quotes (lines 106, 152, 167) explicitly name Pickthall. The first Quranic translation in the chapter must name its translator on first occurrence per enrichment-sources.md §2 and check A3.
- **Suggested fix:** Identify the translation (likely Sahih International, which renders the verse as "He only says to it, 'Be,' and it is" or similar). Add the translator attribution: `(Quran 36:82; translation rendered after Sahih International)` — or use Pickthall's rendering and name Pickthall consistently from the first verse. The Pickthall rendering of 36:82 reads "But His command, when He intendeth a thing, is only that He saith unto it: Be! and it is." — choose one translation and name it.

#### B5: Em-dashes in chapter prose — 77 occurrences

- **File:** content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt (throughout)
- **Context:** The chapter contains 77 em-dash (`—`) characters. Per check B5, em-dashes confuse NotebookLM's TTS prosody and must be replaced with commas, semicolons, or restructured. This is an auto-fixable check (Section 3) but the tool environment does not support regex-based batch replacement with clean spacing in the current invocation. The agent recommends the author apply: `sed -i '' 's/ — /, /g' chapters/ch10-motion-stillness-hyle-and-form.txt` (macOS) or equivalent, then review for any sentence that reads awkwardly with a comma substitution and restructure those manually.
- **Suggested fix:** Script-assisted batch replacement of ` — ` (space em-dash space) with `, ` (comma space) across all 77 occurrences. Then manual review of ~10–15 sentences where the em-dash marks a strong structural pause (e.g., "They are *opposites* — a single body cannot be simultaneously moving...") and restructure those into two separate sentences. After applying, re-run `build_episode_txt.py` to validate the chapter passes the B5 gate.

---

### P1 (ship-with-caution)

#### N3: Three Arabic transliterated terms in chapter lack Pronunciation directives

- **File:** content/podcast/library/books/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt:87, 112
- **Context:** Three terms appear in italics in the chapter body but have no corresponding `Pronounce "..."` directive in the framing's `## Pronunciation` block. None of the three terms is in the shared Arabic manifest (`content/_shared/arabic/03-arabic-english-manifest.md`) or the book lexicon (`_system/source/text/_phonetics.md`). Cannot auto-fix; author must supply phonetics.
  - `*mawhumiya*` (line 87) — Arabic: "imaginary", the term al-Kirmani uses to characterize the ontological status of al-hayula
  - `*takhayyuliya*` (line 87) — Arabic: "imaginary/fantastical", paired with mawhumiya
  - `*nisbas*` (line 112) — Arabic: "proportions/relations", the plural of nisba; al-Kirmani's term for the two honorable proportions
- **Suggested fix:** Add three `Pronounce "..."` lines to the framing's `## Pronunciation` section (before the `Name discipline` block) with the correct phonetics. Suggested forms (author to verify against scholarly sources):
  - `Pronounce "mawhumiya" as "maw-hoo-mee-yah". Say it as one fluent word.`
  - `Pronounce "takhayyuliya" as "ta-khai-yu-lee-yah". Say it as one fluent word.`
  - `Pronounce "nisbas" as "nis-bahs". Say it as one fluent word.`
  - After adding, re-run `build_episode_txt.py` to regenerate `episodes/EP10-motion-stillness-hyle-and-form.txt`.

---

### P2 (advisory)

#### F6: Steering phrases from two-host-framing.md not explicitly present

- **File:** content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP10-motion-stillness-hyle-and-form/00-framing.md
- **Context:** The framing does not contain the canonical steering phrase forms ("Slow down on...", "Treat X as the central tension...", "End on a question...") from `notebooklm-best-practices.md` and `two-host-framing.md`. The framing's steering content is excellent and detailed but uses prose form rather than canonical directives.
- **Agent note:** This is advisory only. The framing's Three-part focus and Landing sections contain equivalent steering content in prose form. NotebookLM will receive adequate guidance. Consider adding one or two canonical steering lines to give the phrasing a sharper anchor.

---

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Blockquotes | Phonetic gaps | Em-dashes | Verdict |
|---|---|---|---|---|---|---|---|
| ch10-motion-stillness-hyle-and-form | 9,431 | ~1% | 3+ tiers (Quran, Sunni hadith, Ismaili source) | 6 | 3 terms (mawhumiya, takhayyuliya, nisbas) | 77 | BLOCKED |

**Chapter tier breakdown:**
- Tier 1 (Quran): 4 verses cited (36:82, 16:40, 112:1-4, 42:11) — all with surah:verse format
- Tier 3 (Sunni hadith): 1 hadith (Sahih al-Bukhari, Book 59, Hadith 3191) — correctly cited with collection, book, number, narrator
- Tier 4 (Shia hadith/sayings): 1 (Nahj al-Balagha, Sermon 1) — correctly cited

**Framing word count:** 3,321 of 3,500 hard cap (94.9% capacity — approaching ceiling)

**Checks that passed cleanly:** B1 (no HTML comments), B2 (no cross-episode refs in chapter), B3 (no file-length self-refs), B4 (no translator-apparatus prefixes), B6 (no invented dialogue), C3/O1 (honorifics — peace be upon him once per figure), C4 (substitution policy — al-nafs, al-ruh, tawhid, da'wa all correctly handled), D1 (enrichment multi-tier), D2 (enrichment ratio ~1%, well under 60%), D4 (no quote-stacking), D5 (no CONTEXT NEEDED markers), F1 (framing exists), F2 (four-part structure), F3 (audience named concretely), F4 (5 tensions named), F5 (8 discussion beats, within 6-12 band), H1 (welcome clause), H2 (summary clause), H3 (closing-landing clause), I1 (anti-repetition clause), I2 (no-irrelevant-background clause), I3 (no adjacent-movement thesis repetition), I4 (biographical material bounded), J1 (name discipline block in framing), K1 (interruption-avoidance clause — conversation discipline block), K2 (filler vocabulary named), M1 (DENY-modernize block present), M2 (DENY-surprise block present), N2 (Pronunciation block uses imperative form), N4 (no-read-aloud guard present), O2 (no abbreviated work titles), R1 (separate-prep illusion clause — conversation choreography block), R2 (reset clause present, spine >5 beats), R3 (cadence directive in Tone), R4 (formal-transition DENY in Do not section), R5 (analogy-permission paragraph present), S1 (no concurrent orchestrator active — stale running state, no live process), S2 (no boundary violations), S5 (no scope-out write violations)

**Checks skipped (no transcript):** M3, M4, N5, O3, R6, R7 — all empirical/transcript checks

**Category G:** No chapter-contracts directory check triggered for per-chapter scope (contracts directory exists and `motion-stillness-hyle-and-form.yml` is present and well-formed; G1 and G3 pass; G4 N/A for non-derivative chapter)

**Category P:** `episode_format: deep_dive` — Category P (debate checks) skipped.

---

## S1 async-safety note

`orchestrator-state.json` shows `phase_status: "running"` for `per-chapter` phase, `ts_updated: 2026-05-21T11:24:27Z`. No live orchestrator process was found via pgrep. This is a stale running state consistent with the known orchestrator resume bug (documented in MEMORY.md). The challenger proceeded; if a live orchestrator resumes, it should NOT touch this chapter file during challenger review.

