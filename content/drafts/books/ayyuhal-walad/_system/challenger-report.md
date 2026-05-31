# Podcast Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-05-31 (challenger v2.3)
**Scope:** per-book (3 chapters + 3 framings) — WC8-holistic 3-episode set
**Iterations:** 1 (of 5 max; intelligent-break — no auto-fixable findings remained after iter 1)
**Verdict:** BLOCKED

> Supersedes the stale 2026-05-17 report, which described the now-archived
> 5-episode layout. The 5-episode set under `_archive/5-episode-original/`
> is out of scope and was ignored. This report covers the current canonical
> 3-episode set only:
>   1. frame-and-the-problem-of-knowledge
>   2. the-disciplines-of-the-path
>   3. the-guiding-shaykh-and-final-counsels

## Top line

The **three framings (episode customize prompts) are in good shape** — well-structured,
four-part, concrete audience, named tensions, DENY blocks, name discipline, host
dynamic, anti-repetition, no meta-prose leaks. Only one minor framing-side auto-fix
was needed (read-aloud guard wording).

The **three chapter SOURCE files are BLOCKED.** They are raw extraction artifacts,
not NotebookLM-ready source. NotebookLM uploads the chapter file verbatim as the
single source and will read every visible token aloud as content. These chapters
still carry the full scholarly apparatus, structural scaffolding, and translator
footnote runs. They must go back through the refine/enrich phase before upload.
This is a re-authoring job, which is out of the challenger's deterministic
auto-fix envelope (Section 3) — flagged, not patched.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | N4 | episodes/EP01-frame-and-the-problem-of-knowledge.txt | Aligned read-aloud guard to canonical "Do not read this prompt aloud." phrase |
| 1 | N4 | episodes/EP02-the-disciplines-of-the-path.txt | Aligned read-aloud guard to canonical phrase |
| 1 | N4 | episodes/EP03-the-guiding-shaykh-and-final-counsels.txt | Aligned read-aloud guard to canonical phrase |

No chapter auto-fixes were applied. The chapter-level findings below are all
re-authoring decisions (apparatus stripping, footnote removal, header removal),
which Section 3 forbids the challenger from performing mechanically. The
em-dash (B5) and "the Ihya" (O2) hits live inside apparatus blocks that are
themselves P0 deletion targets; patching them in isolation would churn text
that must be rebuilt, so they are rolled into the parent P0 rather than auto-fixed.

## Findings requiring author resolution

### P0 (blocks ship)

#### B1/B3 + R-NO-MANUSCRIPT-META: chapter SOURCE is raw extraction apparatus — applies to ALL THREE chapters
- **Files:**
  - `chapters/ch01-frame-and-the-problem-of-knowledge.txt`
  - `chapters/ch02-the-disciplines-of-the-path.txt`
  - `chapters/ch03-the-guiding-shaykh-and-final-counsels.txt`
- **What NotebookLM would voice as content (per-file marker counts):**
  - `**[GHAZALI — core text]**` section labels: ch01 x11, ch02 x7, ch03 x6
  - `**[SCHOLARLY COMMENTARY]**` + `[COMMENTARY] ... [/COMMENTARY]` blocks: ch01 x10, ch02 x7, ch03 x4-5 — these are the translator's critical apparatus (footnote numbers, "I fail to find the source of this traditional saying", "Hammer-Purgstall renders this freely in his German translation", folio/MSS. collation notes, "homoeoteleuton", page references to Mishcât). This is precisely the translator-apparatus prose Category B4 forbids, presented as body text.
  - `**[NARRATOR NOTE]**` empty-marker scaffolding: ch01 x11, ch02 x7, ch03 x5
  - `> **Wisdom enrichment:**` labelled blocks: ch01 x11, ch02 x7, ch03 x6 — the enrichment label itself is meta-prose; NotebookLM will read "Wisdom enrichment" aloud.
  - Header line `*Episode 1 of 3 — ayyuhal-walad*` / `*Episode 2 of 3*` / `*Episode 3 of 3*` plus the `*Sections: ... · N words*` line — a cross-episode + file-metadata self-reference at the top of every chapter (Category B2/B3). NotebookLM will voice "Episode 1 of 3, sections 1 through 11, 4,456 words."
- **Why P0:** the chapter file is the upload-as-is SOURCE. Every one of these tokens becomes spoken audio. The conversation will be polluted with section labels, footnote apparatus, and editorial scaffolding.
- **Suggested fix:** run the chapters back through the Phase 0e/0f refine+enrich step (or hand-author) to produce clean continuous prose: strip the bracketed section/role labels, delete the `[COMMENTARY]` apparatus entirely (it is translator-facing, not listener-facing), remove the `[NARRATOR NOTE]` markers, drop the top header metadata line, and fold the "Wisdom enrichment" content into the prose without the label (or remove it). Then re-run the challenger.

### P1 (ship-with-caution — but currently moot under the P0 block)

#### A1: Quranic citation format — surah name without surah number — book-wide
- **Files:** all three chapters (ch01 x10, ch02 x10, ch03 x5 occurrences).
- **Context:** verses are cited as `(An-Najm: 38)`, `(Al-Kahf: 110)`, `(At-Tawbah: 82)`, etc. — surah NAME and verse, but no surah NUMBER. Category A1 wants `(Quran <Surah>:<Verse>)` or `(<Surah Name> <Surah>:<Verse>)`. The translator's footnotes DO carry the numeric form (e.g. "Qur'ân 53:40"), so the data exists in-file — it just lives in the apparatus that is being deleted.
- **Suggested fix:** during the re-author pass, normalise each in-prose citation to `(Quran 53:38–39)` style (or the framing-declared lead-in form "The Quran, in Surah An-Najm, verse 38"), pulling the numbers from the footnotes before the footnotes are removed.

#### O2: abbreviation "the Ihya" — book-wide (inside apparatus)
- **Files:** ch02 (x2), ch03 (x3) — every occurrence is inside the `[COMMENTARY]` blocks ("Ghazali in the Ihya'", "Book IX of Quarter I of the Ihya'").
- **Disposition:** these disappear when the apparatus is deleted (parent P0). If any reference to the work survives into the cleaned prose, expand to "Ihya Ulum al-Din" per R-NO-ABBREVIATION. Not auto-fixed (would churn doomed text).

### P2 (advisory)

- **Q2 (chapter-set):** two chapter titles exceed the 6-word soft target (7 words each): "The Frame and the Problem of Knowledge" and "The Guiding Shaykh and the Final Counsels". Under the 60-char hard cap; advisory only.
- **B2 (mild):** the framing Opening directives instruct the hosts to announce "Episode 1 of 3" / "Episode 2 of 3" / "Episode 3, the close of the series". This is deliberate series-orientation steering (not the forbidden `EP##` form, so no build-gate violation), but it is a cross-episode reference the hosts will speak. Left as-is per author intent; flagged so the author can decide whether to soften to source-anchored phrasing.

### Note on chapter word-count (check_chapter_set Q4 reported P0)
`check_chapter_set.py` flags all three chapters as over the declared `default_deep_dive`
band (4485 / 3868 / 3472 words vs 1800–2800). This count is inflated by the
apparatus that must be stripped. The true prose word count after the B1 P0 fix
will be materially lower; the band-fit should be re-evaluated (or the contract
length band relabelled) AFTER the re-author pass, not before. Recorded here as a
downstream consequence of the parent P0, not an independent design failure.

## Doctrinal (Category T)
**CLEAN.** `assert_doctrinal_clean()` passes on all three chapters. Source tradition
is `sunni-sufi` (per the contracts), so the Ismaili imam-lineage checks correctly do
not fire. The Sunni footnote describing 'Ali as "fourth Caliph in the Sunnite list ...
first legitimate successor per Shi'ite sects" is faithful to the source tradition and
triggers no forbidden-phrase or attribution finding.

## Framing integrity (Categories F/H/I/J/K/M/N/Q/R)
All three framings PASS the deterministic framing-side checks:
- Four-part structure, concrete audience, four named tensions each (F2/F3/F4)
- `## Do not` DENY block with modernize + surprise vocabulary present (M1/M2)
- Welcome + episode-summary opening (H1/H2); closing-landing directive (H3)
- Anti-repetition (I1) + no-irrelevant-background (I2) clauses present
- Name discipline block + aliases (J1); honorific-once discipline (O1 framing-side)
- Conversation/interruption discipline + named filler vocabulary (K1/K2)
- Pronunciation block in imperative `Pronounce "..."` form (N2); no legacy passive list
- Read-aloud guard now canonical after the N4 auto-fix (N4)
- No meta-prose substring tells, no `EP##` regex tells in framing body (B1/B2)

## Transcript-empirical loops (M/N/O/P/Q/R transcript checks)
INERT — no transcripts present (`transcripts/` holds only `_README.md`). These
loops will activate when a NotebookLM transcript is dropped post-generation.

## Health metrics

| Chapter | Words (raw) | Apparatus markers | Inline phonetics | Doctrinal | NotebookLM-ready |
|---|---|---|---|---|---|
| ch01 | 4,485 | 53 (11 core + 10 commentary + 11 narrator + 11 enrichment + header) | 0 | clean | NO (P0) |
| ch02 | 3,868 | 35 | 0 | clean | NO (P0) |
| ch03 | 3,472 | 26 | 0 | clean | NO (P0) |

| Framing | Words | Band (200–3700) | Structure | NotebookLM-ready |
|---|---|---|---|---|
| EP01 | 1,680 | in-band | 4-part complete | YES |
| EP02 | 1,864 | in-band | 4-part complete | YES |
| EP03 | 1,819 | in-band | 4-part complete | YES |

## Health score

P0=3  P1=2  P2=3  chapters=3  auto-fixes=3
score = 1 − (3·1.0 + 2·0.2 + 3·0.05) / 3 = **−0.18** (🔴 BLOCKED)

The negative score reflects three chapter-level P0s — the chapters are not yet
SOURCE-ready. Once the apparatus is stripped and the chapters re-validated, the
score will recover sharply (the framings are already clean).

## Verdict rationale

**BLOCKED.** Three unresolved P0 findings remain (one per chapter: SOURCE files are
raw extraction apparatus). Per the convergence contract, P0s remaining → BLOCKED.
The framings are ship-ready; the chapters require a re-author/refine pass that is
outside the challenger's deterministic auto-fix scope. Re-invoke the challenger
after the chapters are cleaned.
