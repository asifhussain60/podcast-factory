# Quality Gates Report — Ayyuhal Walad

Run: dry-run 2026-05-16
Source: Ayyuhal Walad by Imam Al-Ghazali (trans. Irfan Hasan)
Sections audited in this run: 3 of 22 (dry-run sample — Introduction, Reality of Tasawwuf, Admonition 1)

## Per-section results

| # | section | src wc | ref wc | ratio | G1 | G2 | G3 | G4 | G5 | G6 | G7 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | section-01-introduction.md | 368 | 323 | 0.88 | PASS | PASS | PASS | PASS | PASS | PASS | DEF |
| 08 | section-08-reality-of-tasawwuf.md | 233 | 287 | 1.23 | PASS | PASS | PASS | PASS | PASS | PASS | DEF |
| 13 | section-13-admonition-1-debate.md | 1113 | 1044 | 0.94 | PASS | PASS | PASS | PASS | PASS | PASS | DEF |

## Gate-level verdicts (sample set)

- **Gate 1** — No non-Latin script: **PASS**
- **Gate 2** — No bracketed commentary: **PASS**
- **Gate 3** — Citation provenance: **PASS**
- **Gate 4** — Section order preserved: **PASS**
- **Gate 5** — Word count 70-140%: **PASS**
- **Gate 6** — Implicit citation detection: **PASS**
- **Gate 7** — Per-section determinism: **DEFERRED**

## Overall: PASS (Gate 7 deferred)

All gates that can be evaluated in a single-run dry-run pass on the 3 sample sections. Gate 7 (per-section determinism) requires a second run for comparison and is deferred until the full pipeline executes.

The new Stage 12 Hard Rule 5 (paraphrase for articulation, preserve propositional content) operates safely within the Gate 5 word-count envelope (70-140%). Section 8 was initially trimmed after coming in at ratio 1.41 — the paraphrasing latitude prompted slightly over-articulation, which the gate caught and the trim corrected. This is the gate doing its job.