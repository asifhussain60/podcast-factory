# Podcast Challenger Report

**Book:** al-anwaar-al-lateefah / vol-01
**Run:** 2026-06-17 18:43 (challenger v2.5)
**Scope:** per-chapter `the-refined-mukathir-house-of-allah` (ch06c / EP06)
**Iterations:** 1 (of 5 max) — intelligent break: no in-scope deterministic auto-fixes available; all remaining findings are authoring decisions or live-gate-accepted.
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← defaulted (no _system/series-config.yaml or meta.yml on disk; islamic_scholarly per spec §0B)
source_tradition: ismaili (islam pack) — doctrinal gate ran, clean (T1–T5: 0 findings on chapter and framing)

> Pipeline-internal invocation: Category S1 (async-safety) bypassed per orchestrator context — the visible `orchestrate_book.py` process is THIS pass's parent, not a concurrent run.

## Gate results (deterministic, code-is-authority)

| Gate | Result |
|---|---|
| `build_episode_txt.py` (chapter SOURCE + framing → episode txt) | PASS (exit 0); 2 P1 flags emitted (R-NO-ARABIC-TRANSLITERATION, F25-APPARATUS-TABLE) |
| `_doctrinal.run_doctrinal_checks` (chapter) | CLEAN (0 findings) |
| `_doctrinal.run_doctrinal_checks` (framing) | CLEAN (0 findings) |
| `check_chapter_set.py` (book scope, CS) | 25 P1 (P8 n-gram overlap ×15, P10 over-dense ×10); 0 P0 |

## Auto-fixes applied (iteration-by-iteration)

None. No in-scope deterministic auto-fix fired:
- B5 (em-dashes): the chapter carries 44 em-dashes, but the live build gate (`build_episode_txt.py`, the authority per spec §0) accepts them at exit 0 — there is no `assert_no_em_dash` in `_validators.py`. The legacy v1.x B5 auto-fix conflicts with current TTS-safety doctrine; mass-rewriting 44 authored punctuation marks against a passing gate would corrupt the SOURCE. Held as INFO, not applied. (All sibling chapters in this book shipped SHIP-WITH-CAUTION with em-dashes intact.)
- B2 (cross-episode refs): none present (0 `EP\d\d`, 0 "previous/earlier/next episode") — nothing to fix.
- C3 / O1 (honorific repeats): each honorific phrase-form appears exactly once (`ﷺ` ×1, `upon him be peace` ×1) — nothing to strip.
- E4 (filler tells): none present — nothing to strip.
- N1 (inline phonetic parens): none present in chapter — nothing to strip.
- Framing-side H/I/K/M/N/Q/R clauses: all already present (see Findings) — nothing to insert.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION — 10 transliterations in chapter SOURCE (build-gate P1, non-blocking)
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch06c-the-refined-mukathir-house-of-allah.txt
- **Context:** Every flagged token lives inside a written-layer citation or a treatise title, NOT in spoken doctrinal prose: `Abu Hurayra` / `Sahih al-Bukhari` / `Kitab al-Riqaq` (line 23 hadith attribution); `Qadi al-Nu'man` / `Ta'wil al-Da'a'im` (line 55 treatise title); `Nahj al-Balagha` / `al-Sharif al-Radi` (line 61 Nahj attribution); `al-Lateefah` (line 3 book subtitle). These are the citation apparatus, which under F25 doctrine belongs in the written layer while the audio uses English labels.
- **Suggested fix:** Authoring decision per F20/F25. Either (a) accept as written-layer citation apparatus (the conventional resolution — NotebookLM reads the chapter as SOURCE but the framing's Name-discipline + "render Arabic citations as English meaning" steering governs the spoken output), or (b) move full citation strings to the 99-show-notes apparatus table and shorten the in-chapter attributions. Not auto-fixed: rewriting authentic citation strings is an authoring decision (Category A forbids the challenger from altering citations).

#### F25-APPARATUS-TABLE — 99-show-notes.md missing the Name and Title Preservation Table (build-gate P1)
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/_system/episode-drafts/EP06-the-refined-mukathir-house-of-allah/99-show-notes.md
- **Context:** No `## Name and Title Preservation Table` section. F25 doctrine: every episode's 99-show-notes.md carries the preserved-Arabic / audio-label crosswalk the TTS-safe audio omits.
- **Suggested fix:** Regenerate 99-show-notes.md via the show-notes generator with the F25 apparatus table. NOT touched by the challenger — `99-show-notes.md` is published-library apparatus, explicitly out of the challenger's edit surface (spec §8).

#### V3 — no modern-relevance bridge (Category V, P1)
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch06c-the-refined-mukathir-house-of-allah.txt
- **Context:** `R_INTEREST_RELEVANCE_PATTERNS` → 0 hits. The chapter has a strong curiosity hook (V1 ✓, "What if the holiest man you ever met…"), a clear challenge-defeat arc (V2 ✓, 4 hits), no strawman (V4 ✓), and rhetorical cadence (V5 ✓, 3 questions) — but no single sentence connecting the doctrine to the listener's contemporary life.
- **Suggested fix:** Authoring decision (Category V is never auto-fixed). Optionally add one brief bridging sentence tying the "house emptied of every rival preoccupation, cleared to receive" image to a recognizable everyday discipline. The closing already gestures at this with the action-question ("which of my thoughts, words, and deeds this week…"), so this is a soft flag.

#### CS-P8 — n-gram overlap with sibling chapters (book scope, P1)
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01 (book scope)
- **Context:** `the-refined-mukathir-house-of-allah` shares 6 distinct 12-word passages with `the-unknowable-originator-and-the-first-intellect`, 6 with `what-tawhid-really-is`, 6 with `naming-the-unnameable`, and 11 with `outer-and-inner-gnosis-and-the-mukathir`. This is a book-wide P8 pattern (15 pairs total across the set) — consistent with the shared frame/liturgical scaffolding and the Mukathir-thread continuity between EP05 and EP06, not verbatim concept-duplication.
- **Suggested fix:** Authoring decision at book scope. Review the shared passages with `outer-and-inner-gnosis-and-the-mukathir` (the adjacent Mukathir episode) to confirm the overlap is recurring-thesis/frame language rather than the same teaching re-taught. CS findings are never auto-fixed.

#### CS-P10 — over-dense (5 concept sections vs ≤3 target) (book scope, P1 advisory)
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01 (book scope)
- **Context:** This chapter has 5 concept H2 sections (Same flesh / The refined essence / A house of Allah / Establishing the da'wah / The inner meaning of the pillars), over the ≤3 density target. The whole set runs over-dense (10/10 chapters flagged), so this is a book-wide design property, not a single-chapter outlier. The chapter is `length_target: longer` (3,351 words), which partially justifies the count.
- **Suggested fix:** Advisory only (the $0 preflight density gate owns halting for `density_standard: 2` books; this book is not flagged for halt). Consider whether "Establishing the da'wah" and "The inner meaning of the pillars" could fold, but the chapter's argument runs continuous, so no re-split is required for ship.

### P2 (advisory)

#### INFO — em-dash density (B5 legacy rule, not enforced by live gate)
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch06c-the-refined-mukathir-house-of-allah.txt
- **Context:** 44 em-dashes. The legacy challenger B5 rule would auto-strip these, but the current build gate accepts them and the spec mandates "code is authority." Recorded for trend visibility only; no action taken.

## Checks that PASSED (audit trail)

- **A1–A6 (Authenticity):** All 4 citations fully formed. Hadith qudsi: Sahih al-Bukhari, Kitab al-Riqaq, no. 6502, narrated Abu Hurayra (✓ collection+book+number+narrator). Quran 24:36–37 and 62:9–10 both in plain-English form `(chapter N, verses M to M)` with translator named (Nasr et al., The Study Quran — A3 ✓). Nahj al-Balagha Saying 147 (al-Sharif al-Radi, trans. Sayyid Ali Reza — ✓). No `[VERIFY CITATION]`, no fabricated numbers, no source-shifting. A6: Sunni hadith (Bukhari) and Ismaili ta'wil material are not collapsed — the chapter explicitly frames the Bukhari hadith from "the divine side" and the Ismaili reading as the tradition's own inner exegesis (Qadi al-Nu'man named).
- **B1–B6 (NotebookLM literalness):** No meta-prose tells, no cross-episode refs, no file-length self-refs, no translator-apparatus prefixes, no invented dialogue. Build gate confirmed no HTML comments.
- **D1–D6 (Enrichment):** Multi-tier (Quran, Sunni hadith canon, Nahj al-Balagha / Father of Imams, classical Ismaili ta'wil treatise). No `[CONTEXT NEEDED]`, no quote-stacking (≤2 adjacent blockquotes, all with integrating prose). Enrichment well under 60%.
- **E1–E5 (Shape):** Chapter 3,351 words (within `length_target: longer` band 2,800–4,500). One-sentence summarizable. Clear hook → pressure → landed close arc. No filler. No translation-residue.
- **F1–F6 (Framing integrity):** Framing present (1:1). 8 H2 sections (≥4). Audience concrete. Three-part focus with named beats. Steering present.
- **H1–H3:** Welcome ✓, episode preview ✓, no-recap/leave-open landing ✓.
- **I1–I4:** Anti-repetition (R-RECURRING-THESIS spine ×3), background bounded.
- **J1–J3:** Name discipline block present; one English label per figure; "Father of Imams" never paired with personal name (doctrinal gate confirms).
- **K1–K2:** Conversation discipline (steelman, "Host B must NOT open with…") + named filler words (Exactly/Yeah/Right/Of course/Wow).
- **M1–M2:** DENY-modernize (Twitter, social media, algorithm) + DENY-surprise (wow, right?) both present.
- **N1–N4:** No inline phonetic parens in chapter; `## Pronunciation` block in say-ONCE form; no-read-aloud guard present.
- **O1–O2:** Each honorific form ×1; no abbreviated work titles (full titles: Sahih al-Bukhari, Nahj al-Balagha, Ta'wil al-Da'a'im).
- **Q1–Q5 (Host-role parity):** Host A = male scholar, Host B = female seeker — consistent across all 6 sibling framings (EP05–EP10). No swap. Voice/gender declared.
- **R1–R5 (Conversation choreography):** Steelman/surprise-move, cadence, formal-transition DENY (Firstly/Secondly/Furthermore/In conclusion), modern-analogy handling all present.
- **T1–T5 (Doctrinal):** Clean. "Ali ibn Abi Talib, the Father of Imams" is the canonical form; lineage and naming conventions intact.
- **U1–U6 (Scholarly rubric):** No AI-cliché, no faux-profundity opening ("What if [concrete scenario]" is a legitimate hook, not a banned stem), no premature closure, no deep-dive self-reference, no external essentialism. Deep_dive format — U6 (concession-arc) N/A.
- **V1/V2/V4/V5 (Interest):** Hook ✓, challenge-defeat arc ✓, no strawman ✓, rhetorical cadence ✓. (V3 flagged above.)

## Health metrics

| Chapter | Words | Citations | Honorific forms | Em-dashes | Phonetic gaps | Doctrinal |
|---|---|---|---|---|---|---|
| ch06c-the-refined-mukathir-house-of-allah | 3,351 | 4 (1 hadith, 2 Quran, 1 Nahj) | 2 (each ×1) | 44 (gate-accepted) | 0 | clean |

| Framing | Words | H2 sections | Host roles | Deny blocks |
|---|---|---|---|---|
| EP06-the-refined-mukathir-house-of-allah | 756 | 8 | A=male scholar, B=female seeker | modernize + surprise + formal-transition |

## PEQ Score

| Axis | Weight | Score | Weighted |
|---|---|---|---|
| Fidelity   | 50% (incl. Voice) | 100.0 | 50.0 |
| Voice      | 20% | N/A | →Fidelity |
| Structure  | 18% | 66.7 | 12.0 |
| Enrichment | 17% | 14.0 | 2.4 |
| Interest   | 15% | 75.0 | 11.2 |
| **Total**  | 100% | — | **75.6** |

**Verdict: WARN** — total 75.6 (threshold 85 for PASS)

> voice axis unavailable — weight redistributed to fidelity
