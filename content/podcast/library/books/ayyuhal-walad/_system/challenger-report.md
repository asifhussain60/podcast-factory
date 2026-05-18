# Podcast Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-05-17 17:23 (challenger v1.4)
**Scope:** per-book (5 chapters + 5 framings)
**Iterations:** 1 (of 5 max)
**Verdict:** SHIP-READY

This is the third outer-loop invocation. The caller resolved the three residual P1 items from pass #2 via three protocol-level edits, not via content changes:

1. **R-HONORIFIC-ONCE clarified to per-form semantics with a verbatim-quote (A4) exception** in `content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md`. The two contested lines (`chapters/ch03-the-path.txt:33` and `chapters/ch05-method-and-closing-prayer.txt:107`) are inside verbatim Ghazali blockquotes (line 33 is a verbatim Ghazali sentence about the perfected guide; line 107 is the closing supplication quoted in full). Both now exempt by rule.
2. **E1 framing soft band raised from 200–1,000 to 200–2,000** in the challenger contract itself (`.github/agents/podcast-challenger.agent.md`), with the v3.5 ~600-word steering baseline named as the reason the prior cap predated current architecture. All five framings (1,639–1,966 words) fall well inside the new band.
3. **`_system/editorial-notes.md` updated** with the per-form + verbatim-quote semantics, and with explicit acknowledgement that ch03:33 and ch05:107 are protected exceptions, not bugs.

This pass re-read the two normative rule files and the agent contract first, then ran the full 30-check catalog against all 10 in-scope files. **Zero auto-fixes applied. Zero findings remain.** Build-script re-run on all 5 episodes confirms continued upload-readiness.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | (none — file set is already clean under the clarified contract) |

Convergence note (Section 4 step 6a): iteration 1 produced zero auto-fixes and zero new findings vs the post-edit baseline. Loop terminated after one iteration.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

None.

### P2 (advisory)

#### D4-adjacent: ch01:39–46 three consecutive Quranic blockquotes with minimal bridge prose

- **File:** `content/podcast/library/books/ayyuhal-walad/chapters/ch01-frame-and-first-counsel.txt:39-46`
- **Context:** Three Quranic blockquotes (Az-Zalzalah 99:7-8, Al-Kahf 18:110, Al-Kahf 18:107) appear in sequence with only blank-line separation between them, no intervening commentary of 30+ words.
- **Why not P1:** The chapter prose at line 37 ("He stacks the verses on each other so that none of them can be argued away") names this as Ghazali's deliberate rhetorical move. The stacking IS the argument. Bridge prose between the verses would dilute exactly the effect Ghazali is producing in his source. The framing's Focus 1 also instructs hosts to "walk the listener through the stacking of verses; do not flatten the rhetoric."
- **Recommendation:** No change. Carried forward as P2 advisory; surfaced for completeness so the outer loop has a record that the stacking was noticed and accepted.

## Health metrics

### Chapter file (SOURCE) — uploaded as-is to NotebookLM

| Chapter | Words | Enrichment ratio (blockquote/total) | Tier diversity | Citation density | Phonetic gaps (inline) |
|---|---|---|---|---|---|
| ch01-frame-and-first-counsel | 3,042 | 21% | 4 tiers (Quran, hadith, Nahj al-Balagha, Sufi quote) | 11 cited | 0 |
| ch02-hatim-eight-benefits | 2,561 | 40% | 4 tiers (Quran, hadith, Nahj al-Balagha + Ghurar al-Hikam, Ismaili farman) | 14 cited | 0 |
| ch03-the-path | 3,049 | 14% | 4 tiers (Quran, hadith, Nahj al-Balagha + Ghurar al-Hikam, Ibn Ata Allah/Dhu'l-Nun Sufi) | 7 cited | 0 |
| ch04-four-cautions | 2,738 | 13% | 4 tiers (Quran, hadith, Nahj al-Balagha + Ghurar al-Hikam, Hasan al-Basri) | 7 cited | 0 |
| ch05-method-and-closing-prayer | 2,680 | 24% | 4 tiers (Quran, hadith, Nahj al-Balagha, Ismaili du'a tradition) | 9 cited | 0 |

All five chapters are within the soft band (1,500–4,500) and inside the sweet spot envelope. All enrichment ratios are well below the 60% cap.

### Framing file → episode txt (CUSTOMIZE PROMPT) — pasted into NotebookLM Customize box

| Episode | Framing words | Episode-txt words | Inside 200–2,000 soft band | Required v3.5 blocks |
|---|---|---|---|---|
| EP01-frame-and-first-counsel | 1,966 | 1,908 | yes | all 9 present |
| EP02-hatim-eight-benefits | 1,639 | 1,590 | yes | all 9 present |
| EP03-the-path | 1,785 | 1,736 | yes | all 9 present |
| EP04-four-cautions | 1,689 | 1,640 | yes | all 9 present |
| EP05-method-and-closing-prayer | 1,816 | 1,767 | yes | all 9 present |

Required v3.5 blocks audited per episode: (1) Opening directive with welcome + 2-3 sentence summary (R-WELCOME / H1+H2); (2) Pronunciation block in imperative form ending with "Do not read this guidance aloud" (R-PRONUNCIATION-IMPERATIVE / N2+N4); (3) Name discipline block (R-NAMEALIAS / J1); (4) Honorific discipline block; (5) `## Do not` DENY-modernize block (R-NOMODERNIZE / M1); (6) DENY-surprise block (R-NOSURPRISE / M2); (7) Anti-repetition clause (R-NOREPEAT / I1); (8) No-irrelevant-background clause (R-NOBACKGROUND / I2); (9) Conversation-discipline clause + final "Do not read this prompt aloud" line (R-NOINTERRUPT / K1 + R-NO-READ-PROMPT / F7).

### Honorific audit per chapter (R-HONORIFIC-ONCE per-form semantics, A4 exception)

| Chapter | "peace and blessings be upon him" | "peace be upon him/her" | "may Allah have mercy upon him" | "may Allah be pleased with him/her" | (AS) inside attribution lines |
|---|---|---|---|---|---|
| ch01 | 1 (line 9, outside) | 1 (line 89, outside) | 1 (line 7, outside) | 0 | 1 (line 92, inside source attribution) |
| ch02 | 1 (line 44, outside) | 1 (line 66, outside) | 1 (line 9, outside) | 0 | 1 (line 69, inside source attribution) |
| ch03 | 1 outside (line 19) + **1 A4-exempt (line 33, inside verbatim Ghazali blockquote)** | 1 (line 79, outside) | 0 | 0 | 1 (line 82, inside source attribution) |
| ch04 | 1 (line 25, outside) | 1 (line 47, outside) | 0 | 0 | 1 (line 107, inside source attribution) |
| ch05 | 1 outside (line 21) + **1 A4-exempt (line 107, inside verbatim closing supplication)** | 1 (line 43, outside) | 0 | 1 (line 80, outside, for Aisha) | 1 (line 46, inside source attribution) |

Every chapter: each honorific phrase form expanded at most once outside verbatim blockquotes. A4 exceptions documented in editorial-notes.md. (AS) occurrences appear only inside `> Source:` attribution lines, which are part of the structural citation format required by R-ATTRIBUTION/A1 for Imam Ali sayings.

### Cross-cutting structural checks

- HTML comments in chapters: 0
- Cross-episode refs (`EP\d\d`, "previous episode", "earlier episode"): 0 in chapters
- Em-dashes in chapter prose: 0 (one em-dash in `EP05-method-and-closing-prayer/00-framing.md:77`, inside an instructional line about the term `qudsi`; framings are processed silently by NotebookLM under R-NO-READ-PROMPT and Loop B5 scopes to chapter prose, so not flagged)
- Inline phonetic parens (R-PHONETICS-OUT / N1): 0 in all chapters
- Abbreviated work titles (`the Ihya`, `the Nahj`, `EI`, etc. — R-NO-ABBREVIATION / O2): 0 in chapters; all framings carry the canonical DENY clause
- `[CONTEXT NEEDED]` / `[VERIFY CITATION]` markers: 0 across all files
- Build-script structural validation: passes on all 5 episode builds

### Extract Mode (Category G) and empirical-transcript audit (Category M/N/O)

`chapter-contracts/` directory not present (book is authored, not Extract Mode) → Category G N/A.
`transcripts/` contains only `_README.md`, no transcripts → Category M/N/O empirical-audit branches N/A. Loops M1, M2, N1, N2, N3, N4, O1, O2 (framing-side + chapter-side static checks) all pass independently.

## Verdict rationale

The three residual P1 items from pass #2 (P1-1 honorific-in-verbatim-blockquote on ch03:33 + ch05:107, P1-2 framings outside 200–1,000 soft band, P1-5 per-form vs per-figure ambiguity) were all rule-level disagreements about how to interpret content that was structurally and authorially sound. The caller's three edits resolved the disagreements at the rule level: per-form is canonical, the verbatim-quote A4 exception is named explicitly, and the framing soft band was reset to match v3.5 architectural reality. Under the clarified contract, every check in the 30-item catalog passes. Zero P0, zero P1, one P2 advisory carried forward for transparency.

All 5 episode bundles are upload-ready. Each episode's pair (chapter SOURCE + episode-txt CUSTOMIZE PROMPT) is byte-aligned with its framing via the most recent `build_episode_txt.py` run.

## Upload steps (per episode)

1. Upload `content/podcast/library/books/ayyuhal-walad/chapters/chNN-<slug>.txt` to NotebookLM as the single source for the notebook.
2. Paste the contents of `content/podcast/library/books/ayyuhal-walad/episodes/EP##-<slug>.txt` into NotebookLM's *Customize* prompt box.
3. Choose *Deep Dive* format, *Default* length, click *Generate*.

| # | Chapter source | Episode customize-prompt |
|---|---|---|
| 1 | `chapters/ch01-frame-and-first-counsel.txt` | `episodes/EP01-frame-and-first-counsel.txt` |
| 2 | `chapters/ch02-hatim-eight-benefits.txt` | `episodes/EP02-hatim-eight-benefits.txt` |
| 3 | `chapters/ch03-the-path.txt` | `episodes/EP03-the-path.txt` |
| 4 | `chapters/ch04-four-cautions.txt` | `episodes/EP04-four-cautions.txt` |
| 5 | `chapters/ch05-method-and-closing-prayer.txt` | `episodes/EP05-method-and-closing-prayer.txt` |
