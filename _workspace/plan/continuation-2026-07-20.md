# Continuation prompt — 2026-07-20

Paste everything below the rule into a new session, from the repo root.

---

We are on branch `Islamic/the-master-and-the-disciple-augmented`, clean and pushed
through `9b3d609`. All gates were green at that commit: pytest 1575, ruff check +
format clean, astro check 0 errors, lint:views clean, smoke 32/32.

## What just shipped (six commits, read `git log` for detail)

The book `content/Islamic/the-master-and-the-disciple` was fully recomposed and
the pipeline gained a narrative-frame contract.

- **Narrative frame is a SOURCE property.** `narrative_frame: transmitted_report`
  is declared in `_system/series-config.yaml` (the Arabic opens `بلغنا`, "it has
  reached us" — an anonymous transmitter, so third person; first person only
  inside quoted speech). Registry + resolver in `_rules.py`
  (`NARRATIVE_FRAMES`, `narrative_frame_for`), read via `_pipeline_flags.py`.
  Deliberately independent of `book_voice` and `deliverable_mode`.
- **`scripts/podcast/_narrative.py`** holds the deterministic guards shared by all
  three prose routes (re-voice, fluency de-calque, translation compose): person,
  speech-tag integrity, Arabic retention, supplied diacritics, enumeration
  survival. Same module supplies the prompt directives, so instruction and gate
  cannot drift.
- **`book-challenger` gained Pass 3 (BK-N1..BK-N7)** as its CLOSING gate, synced
  across all four spec files (`.github/agents/*.agent.md` master, `.claude/`,
  `infra/claude-agents/`, `.codex/agents/*.toml`).
- **`book_voice` switched `author_companion` → `faithful`.** With the frame
  enforcing third person the companion prompt had nothing left to do (six of nine
  chapters came back 92-100% identical to base, chapter 3 byte-identical). The
  de-calque pass is the one written for the job.
- **The Book Composer is the singular path** for PDF-bound chapter edits:
  `_book_edits.py` + `plan-dashboard/src/lib/reader/composer-edits.ts` write and
  replay `_system/composer-edits.json` as the final compose step, so an edit
  survives a re-compose. Conflicts and orphans reported, never guessed.
- **Canonical mushaf wired in.** `content/knowledge-base/mirror.db` (tracked in
  git) holds all 6,236 vowelled ayat in `fts_quran`; `_mushaf.py::is_quranic` is
  the discriminator and the Arabic audit ladder is now canonical-mushaf → ocr →
  knowledge-base → honorific → unverified.

Current book state, verified: **0 person violations and 0 findings on every
deterministic guard, book-wide.** PDF renders at 121 pages, render verdict
RENDER-CAUTION with 3 pre-existing front-matter findings.

## Task 1 — re-run the book challenger (it died mid-run)

A `book-challenger` whole-book sweep was running when the previous session's
process exited; its state was lost. `book/book-challenger-report.md` on disk is
from the EARLIER (pre-repair) run — treat it as stale.

Re-run it over `the-master-and-the-disciple`, whole book, and ask it to confirm
three repairs plus hunt for anything new:

1. **Chapter 8 Arabic, line ~1266.** The earlier run reported two defects:
   fabricated vowelling AND the divine name `الله` dropped for a pronoun. The
   vowelling finding was right and is fixed. **The divine-name finding was
   WRONG** — the scan contains BOTH forms, `وإن الله كل يوم هو في شأن` in one
   passage and `وإنه كل يوم هو في شأن` in another, and the book renders each at
   its own site, matched by its English gloss ("Indeed…" vs "And truly…"). I
   briefly applied that "fix" and reverted it before commit. **Have the
   challenger verify this independently against
   `_system/source/ocr/raw-extract.md` and contradict me if I am wrong.**
2. Six Arabic runs at the end of chapter 8 now carry the `>` blockquote the other
   37 have. Confirm consistency book-wide.
3. `sunna` in chapter 4 is now consistent (the de-calque had rendered it "way"
   twice). Sweep for the same elegant-variation defect on OTHER technical terms.

Also run Pass 3 in full, teaching/citation fidelity against the base chunks in
`book/_chunks/translation/`, and seam integrity at chapter 7's two and chapter 8's
five window boundaries.

**Do NOT let it re-report the two `Editorial note (source-grounded)` blocks as an
augmenter violation.** `book_augmentation: source_only` means augmentation is ON
and source-grounded; `none` means off. The earlier run read that backwards.

## Task 2 — the one open editorial question

The chapter 5 editorial note (around line 460) imports a cosmology of celestial
spheres generating minerals and plants, and a spiritual world produced "in a
single instantaneous emanation from absolute non-existence". Chapter 4 of this
book teaches creation from light through will, command, and saying. The note was
drawn from OTHER books in `content/knowledge-base/`. Asif has not yet ruled on
whether to keep or strip it — **ask him, do not decide it unilaterally.**

## Known gap, do not re-attempt blindly

`supplied_diacritics_findings` compares a rewrite against its own base, so it is
blind to vowelling fabricated at TRANSLATION time and baked into the base. Four
attempts at a scan-grounded guard are recorded in the `_narrative.py` docstring —
the working version needs `_mushaf.is_quranic` to exclude canonical verses, and
ships ADVISORY only (`vowelling_review` in `_system/book-arabic-audit.json`),
never in `frame_findings`, because a wrong revert costs real authored text.

## Task 3 — cleanup, merge, audit (run AFTER tasks 1 and 2)

1. **Clean `content/Islamic/the-master-and-the-disciple/`.** Delete any folder or
   file left over from legacy processes or that is not a production artifact —
   e.g. `book/book.md.bak`, `_system/scratchpad/`, `_system/drafts/`,
   `_system/probe/`, `chapters/_curator-archive/`, stray `.DS_Store`, empty dirs,
   superseded reports. **Propose the delete list and get approval before
   removing anything** (Tier 2 — `rm` of tracked files). Do NOT delete
   `book/_chunks/translation/` (the compose cache the pipeline reads),
   `_system/composer-edits.json`, `_system/series-config.yaml`, or any `m4a/`
   audio. Prefer the `vacuum` agent, which is built for exactly this.
2. **Merge to `develop`** with `--no-ff`, then switch to `develop`.
3. **Full repo audit** — `repo-surgeon --scope podcast` (the mandatory post-merge
   holistic sweep). Verify every piece of the work above survived the merge:
   `_narrative.py`, `_mushaf.py`, `_book_edits.py`, `_book_voice_prompts.py`,
   `_translation_prompts.py`, the four `book-challenger` spec mirrors, the
   `composer-edits.ts` mirror, and the `narrative_frame` key in the book's
   series-config. Re-run the full gate set and report.
