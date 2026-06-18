# Podcast Challenger Report

**Book:** al-anwaar-al-lateefah / vol-01
**Run:** 2026-06-18 (challenger v2.5)
**Scope:** per-chapter `equal-but-not-infallible` (EP10 / ch10g)
**content_profile:** islamic_scholarly  ← defaulted (no _system/series-config.yaml; orchestrator-state confirms)
**source_tradition:** islam (doctrinal pack resolved)
**Iterations:** 1 (of 5 max) — converged; iteration 2 would reproduce identical findings with zero new auto-fixes (intelligent break)
**Verdict:** SHIP-WITH-CAUTION

> CHALLENGER_VERSION read from scripts/podcast/_rules.py at run time = 2.5.

## Pipeline note (P0 resolved during this run)

The orchestrator circuit-breaker that halted this chapter reported a "framing structural mismatch" P0.
Root cause confirmed and resolved during this pass:

- At pass start, `extract_chapter.py --force` was run for Category-G contract validation. The contract
  renderer regenerated `00-framing.md` into a **stub-shaped framing** carrying `[LLM-FILL ...]`
  placeholders, no Pronunciation anti-doubling instruction, no `## Name discipline` section, no 6-beat
  dramatic arc, no challenger-friction patterns, and no analogy-cap enumeration.
- `pipeline_lint.py` on that regenerated framing returned **BLOCKED (1 P0, 7 P1)** — this is exactly the
  "framing structural mismatch" the circuit-breaker saw: the deterministic contract renderer does not emit
  the rich framing structure the framing validators (`_validators_framing.py`) require.
- The correct ship artifact was the hand-authored framing already present in the working tree. It was
  restored. After restoration, `pipeline_lint.py` returns **SHIP-WITH-CAUTION (0 P0, 2 P1)** and all 10
  `_validators_framing.py` assertions PASS.

Lesson for the pipeline: for this book, `extract_chapter --force` must NOT be re-run against an
already-hand-authored framing — the renderer output is structurally inferior to the authored framing the
validators expect. Category G contract validation here should be read-only (parse + lint the contract),
not `--force` re-render.

## Gate results (post-restoration)

| Gate | Result |
|---|---|
| `build_episode_txt.py EP10` | EXIT 0 — chapter validated, episode txt emitted (714 words) |
| `pipeline_lint.py EP10` | SHIP-WITH-CAUTION (0 P0, 2 P1) |
| `_validators_framing.py` (10 assertions) | ALL PASS |
| Doctrinal T1–T5 (`_doctrinal.run_doctrinal_checks`) | CLEAN (0 findings) — T3 "Father of Imams, Ali ibn Abi Talib (peace be upon him)" construction holds |
| `extract_chapter.py --force` (G2) | EXIT 0 (contract validates) |
| Category U (AI-cliché / faux-profundity / deep-dive-self-ref) | CLEAN |
| Category V (interest) | V1–V5 all PASS |

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | framing-restore | EP10/00-framing.md | Restored hand-authored framing destroyed by extract --force; pipeline_lint P0 cleared (BLOCKED→SHIP-WITH-CAUTION) |
| 1 | build-sync | episodes/EP10-equal-but-not-infallible.txt | Re-ran build_episode_txt.py to re-emit the customize-prompt txt from the restored framing (714 words) |

No content auto-fixes were applied to the chapter SOURCE. The chapter carries 54 em-dashes (B5 in the
challenger catalog) but the canonical build gate (`build_episode_txt.py`) does NOT enforce B5 on the
NotebookLM SOURCE in the current architecture — code is authority, so these were left intact rather than
mass-rewritten (auto-stripping 54 author-woven em-dashes would risk corrupting voice). Honorific
discipline (O1) is clean: each expansion appears once.

## Findings requiring author resolution

### P0 (blocks ship)
None. (The framing-structural-mismatch P0 was resolved by restoring the authored framing — see Pipeline note.)

### P1 (ship-with-caution)

#### F20 / R-NO-ARABIC-TRANSLITERATION — Arabic transliterations in chapter SOURCE
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/chapters/ch10g-equal-but-not-infallible.txt (lines 3, 11, 61, and the four Quran citations)
- **Context:** 9 transliterations, concentrated in citation apparatus: `Al-Anwaar al-Lateefah` (line 3 episode-summary italic), `Hamid al-Din al-Kirmani` + `Rahat al-'Aql` + `al-Hakim` (line 11), `Nahj al-Balagha` (line 61), `Surat al-Nahl/al-Shams/al-Baqarah/al-Ma'idah` (Quran citation parentheticals).
- **Mitigation in place:** the framing's `## Name discipline` already instructs hosts to "never speak Arabic titles" and "Cite the Quran by verse content, not Arabic chapter names" — the steering layer keeps these out of the spoken audio. They remain in the written SOURCE as apparatus.
- **Suggested fix (author decision):** replace work titles with English audio labels in the source ("the book on the repose of the intellect"), or accept per the contract's own `tone_constraints` choice to keep citation apparatus. Not auto-fixed (not in the agent's deterministic auto-fix set; citation rendering is authoring judgment).

#### F29 / R-SURAH-ENGLISH-ONLY — Arabic surah names in chapter SOURCE
- **File:** same chapter, lines 17, 35, 47, 73 (the four Quran blockquote citations)
- **Context:** `(Surat al-Nahl)`, `(Surat al-Shams)`, `(Surat al-Baqarah)`, `(Surat al-Ma'idah)` trail the already-correct plain-English citation form (`Quran, chapter N, verse M`). The Arabic parenthetical is redundant on top of the English chapter-number and is a TTS-read risk.
- **Suggested fix (author decision):** drop the `(Surat al-X)` parenthetical or render it as the English meaning ("the chapter of the Bee", "the chapter of the Sun", etc.). The plain-English `Quran, chapter N, verse M` form already satisfies A1 / R-QURAN-CITATION-FORMAT.

#### F25-APPARATUS-TABLE — 99-show-notes.md missing the Name and Title Preservation Table
- **File:** content/Islamic/al-anwaar-al-lateefah/vol-01/_system/episode-drafts/EP10-equal-but-not-infallible/99-show-notes.md
- **Context:** no `## Name and Title Preservation Table` header. F25 expects the written-layer crosswalk (preserved Arabic / transliterations → audio labels) that the TTS-safe audio omits.
- **Note:** 99-show-notes.md is OUT OF SCOPE for this agent to edit (Section 8) and is a written-apparatus file that does not flow to NotebookLM audio. Flagged for the author/pipeline to add the table. Was regenerated by extract --force this pass.

#### CS8 / P8 — shared 12-word passages across chapters (cited scripture recurrence)
- **Files:** ch10g vs `the-ladder-of-tawhid` (12 passages); ch10g vs `the-unknowable-originator-and-the-first-intellect` (25 passages)
- **Context:** the overlap samples ("...the perfection of His purity is to deny Him attributes...", "that to which it is attributed and everything to which something is attributed...") are the **Nahj al-Balagha Sermon 1** blockquote on divesting attributes (tanzih), legitimately cited across multiple chapters whose shared spine is tawhid/tanzih. This is recurring *cited scripture*, not duplicated *teaching prose*.
- **Suggested fix (author decision):** acceptable for a book built on tanzih; if undesired, vary which Sermon-1 segment each chapter quotes, or cite the sermon in full in one chapter and reference by paraphrase elsewhere. Challenger judgment: this is a soft P1, not a teaching-duplication failure.

#### CS10 / P10 — chapter over-dense (6 concept sections, target ≤3)
- **File:** ch10g (H2 movements: No obstacle / Potential and actual / Equal but not infallible / Slipping / The first to declare / Seeking the means)
- **Context:** advisory in CS10; `density_standard` is null for this book so it does not halt. The six movements form a coherent single arc (the chapter is `length_target: longer`), but the density standard prefers ≤3 concepts per chapter.
- **Suggested fix (author decision):** accept for a `longer`-tier chapter, or re-split via Phase 0d if a tighter density is desired book-wide.

### P2 (advisory)

#### B3 — soft file self-reference
- **File:** ch10g line 85: "...the very error **this chapter has been tracing**..."
- **Context:** "this chapter has been tracing" is a soft meta-prose tell (B3 family: "this chapter has..."). In context it means the teaching's argument thread, and the canonical build gate (`build_episode_txt.py` META_PROSE_TELLS) does NOT flag it. Surfaced P2 (not P0) because the authority gate passes it.
- **Suggested fix (author decision):** reword to "the very error the teaching has been tracing" to remove the file-self-reference smell.

## Health metrics

| Chapter | Words | Enrichment tiers | Citations | Honorific repeats | Doctrinal | Arabic-translit (F20) | Surah-names (F29) |
|---|---|---|---|---|---|---|---|
| ch10g equal-but-not-infallible | 3,783 | 5 (Quran / Imam / Ismaili / Sufi / academic) | Quran ×4, Nahj al-Balagha S.1, Rahat al-'Aql, Mathnawi, Walker | 0 (each ×1) | CLEAN | 9 | 4 |

Framing: 714 words · all 10 framing validators PASS · pipeline_lint SHIP-WITH-CAUTION (0 P0, 2 P1).
