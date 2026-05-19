# Pre-Refined Source Mode — Adding NotebookLM Scaffolding Around Frozen Chapter Prose

**Purpose.** This handbook entry describes the **third pipeline mode** for the `/podcast` skill, distinct from:

1. **Full orchestrator pipeline** (PDF → Phase 0a–0e via `scripts/podcast/orchestrate_book.py`) — when the source is a PDF or other long-form raw input.
2. **Extract Mode** (single-chapter `.txt` → bundle via `extract_chapter.py`) — when one chapter is pre-prepared and the rest of the SKILL is bypassed.
3. **Pre-Refined Source Mode** (this entry) — when a *multi-chapter* book has already been refined into per-chapter Markdown/txt files by the user (or a prior pass), and the task is to **add podcast scaffolding around the frozen prose, not rewrite it**.

The canonical worked example is `content/podcast/library/books/the-master-and-the-disciple/`. Refer to its `_notebooklm/` directory for the concrete file pattern.

---

## When to use this mode

Trigger Pre-Refined Source Mode when the user uploads or points at a directory containing:

- **Multiple per-chapter source files** that are already refined to the prose quality the user wants (no orchestrator refinement pass needed).
- **Editorial commentary already authored inline** (modern analogies, clarifications, etc.) — frozen by the user.
- A request phrased as: "add podcast scaffolding," "prepare this for NotebookLM," "build the source bundle," "wrap these chapters for the audio overview" — **not** "ingest this book" or "extract this chapter."

If the user says any of:

- "Don't rewrite the prose"
- "These chapters are already refined"
- "Add scaffolding only"
- "Wrap this for NotebookLM"
- "Build the NotebookLM directory"

…the request is in **Pre-Refined Source Mode**. The orchestrator pipeline is the wrong tool; Extract Mode is too narrow (it handles one chapter); this mode is the right answer.

## What this mode adds (and what it does NOT touch)

**Adds:**

- A `_notebooklm/` subdirectory inside `BOOK_DIR/` containing **scaffolding files** (NEVER source text).
- A master source index (`00-NotebookLM-Source-Index.md`) — file-role table, series premise, upload order.
- A centralized pronunciation guide (`01-pronunciation-guide.md`) — with stress cues, do-not-pronounce-as table, and honorific protocol.
- A listener-facing glossary (`02-glossary.md`) — plain-English meaning per term, "why it matters in this series."
- Source integrity notes (`03-source-integrity-notes.md`) — every quotation, attribution, theological claim, hadith reference, and transliteration classified by source status with podcast-handling instruction.
- "Do Not Say" guardrails (`04-do-not-say-guardrails.md`) — book-specific anti-patterns.
- An episode arc map (`05-episode-arc.md`) — per-episode core question, tension, model.
- A human-review checklist (`06-human-review-checklist.md`) — pre-publication gate, P0/P1/P2 severity.
- Per-chapter scaffolding files (`chNN-scaffolding.md`) — Source Card, Episode Intelligence, Host Questions, Listener Difficulty, Review Lens, Listener Fit, Episode Opener/Closer, NotebookLM Instruction. Optional sub-blocks: Podcast Segment Map (dense chapters), Character Cards (drama-heavy chapters), Claim Map (argument-heavy chapters), Final Listener Examination (finales).

**Does NOT touch:**

- The refined chapter prose files in `BOOK_DIR/` parent. **Frozen.**
- Any editorial-clarification paragraphs the user already authored inline. Frozen — but they are flagged in `03-source-integrity-notes.md` §"Editorial-clarification paragraphs" so NotebookLM does not quote them as source text.

## Editorial separation contract (mandatory for all scaffolding files)

Every scaffolding file in `_notebooklm/` adheres to the four-layer label rule from the broader podcast-best-practices canon:

| Label | Meaning | Authority |
|---|---|---|
| `[Source Text]` | The work's own words (refined into English phonetic transcription where needed). | Original — uses the work's voice. |
| `[Editorial Clarification]` | Translator/editor explanation, modern analogy, or paraphrase. | Editorial — uses the editor's voice. |
| `[Podcast Host Cue]` | Question or instruction for the podcast host (NotebookLM). | Editorial — directed at the production layer. |
| `[NotebookLM Instruction]` | Direct instruction to NotebookLM about how to generate audio. | Editorial — directed at the AI. |

**NotebookLM must NEVER quote `[Editorial Clarification]`, `[Podcast Host Cue]`, or `[NotebookLM Instruction]` content as if it were `[Source Text]`.** When the refined chapter prose contains inline editorial paragraphs that were authored without these labels, the *source-integrity-notes file* tracks them so the host can flag them in delivery.

## Arabic pronunciation — pre-refined source mode protocol

This mode has a different pronunciation delivery channel than the orchestrator pipeline.

**Orchestrator pipeline (Phase 0c → Phase 3):** builds `_phonetics.md` from the book; populates the per-episode customize prompt's `## Pronunciation` block with R-PRONUNCIATION-IMPERATIVE directives (`Pronounce "Tasawwuf" as "ta-SAW-wuf"…`). The chapter file itself carries no inline phonetics (R-PHONETICS-OUT).

**Pre-refined source mode:** the chapter prose is frozen. Phonetic delivery happens through **two surfaces**:

1. **`_notebooklm/01-pronunciation-guide.md`** — the book-level pronunciation table. Uploaded to NotebookLM as one of the source files. Acts as a *standing reference* the model can cite.
2. **The per-episode customize prompt** — the operator pastes a `## Pronunciation` block (still R-PRONUNCIATION-IMPERATIVE form) into NotebookLM's Customize box, drawn from the entries in `01-pronunciation-guide.md` that appear in the current episode's chapter.

Why two surfaces? Because:
- The chapter prose is frozen and (per R-PHONETICS-OUT) does NOT carry inline phonetics — so NotebookLM cannot infer pronunciation from the chapter alone.
- A standing pronunciation source file alone is not enforced in the audio — NotebookLM may ignore it.
- The customize prompt is the *only* surface that reliably steers NotebookLM's pronunciation. The source file is the human-readable backup.

**Lookup order for every Arabic term in the pronunciation guide:**

1. `SHARED_ARABIC/03-arabic-english-manifest.md` — if the term is there, use the canonical phonetic verbatim.
2. `BOOK_DIR/_system/pronunciation.md` (book-specific overrides) — may add but not contradict.
3. Draft a new phonetic per `SHARED_ARABIC/01-tts-pronunciation-key.md` rules using the letter-level guide in `SHARED_ARABIC/02-quran-letter-phonetics.md`. Any new draft MUST also be proposed for inclusion in the shared manifest.

**The pronunciation guide must include:**

- Stress cues marked in CAPITAL LETTERS (e.g., **Sha-REE-ah**, **Wi-LAA-yah**).
- A "Do not pronounce as" anti-pattern table — failure modes specific to this book's terms.
- An honorific protocol section — when to apply "peace be upon him," "Imaam X, peace be upon him," etc., and explicitly the cadence rule (first mention with honorific; subsequent mentions name-only).
- A fallback rule: if a term is not in the guide and inference is unsafe, **stop and read it slowly letter-by-letter rather than guess**.

**This mode honors the same classical-Arabic pronunciation standard as the orchestrator pipeline.** The shared manifest is the source of truth for canonical phonetics; the per-book pronunciation guide is the user-facing aggregation of those phonetics for the current book.

## Per-chapter scaffolding file structure

Each `chNN-scaffolding.md` file follows this skeleton:

```md
# Ch NN — <Chapter Title>

**Episode role:** ...
**Source file:** <relative path>
**Best-practices model:** <one of: literary deep-dive | critical nonfiction review | teacher-disciple interview | structured listener-friendly review | dramatic book-club model | critical theological explainer>

## Source Card
- Work, Chapter, Episode role, Primary listener question, Main tension,
  Difficulty (Low | Medium | High | Very high), Spoiler level,
  Key terms, Key people, Pronunciation focus, Theological review needed.

## Episode Intelligence
- One-Sentence Premise
- Why a Listener Should Care
- What Changes in This Chapter
- Strongest Scene or Argument
- Most Confusing Point
- Host Questions (5–7)
- Listener Takeaway
- Bridge to Next Episode

## Listener Difficulty
- Difficulty: <level>
- Why <level>:
- How to make it listenable:

## Podcast Segment Map        # optional — for dense chapters
## Character Cards            # optional — for drama-heavy chapters
## Claim Map                  # optional — for argument-heavy chapters
## Listener Objection         # optional — when chapter triggers predictable modern resistance
## Final Listener Examination # optional — for series finales

## Review Lens
- What Works
- What May Challenge Listeners
- What Not to Do

## Listener Fit
- This episode is for listeners who:
- This episode may be difficult for listeners who:

## Episode Opener
## Episode Closer

## NotebookLM Instruction
- Specific imperatives for this episode's audio generation.
- Pronunciation references (point at `01-pronunciation-guide.md`).
- Honorific reminders.
- Anti-pattern reminders (from `04-do-not-say-guardrails.md`).
- Bridge to next episode.
```

Optional blocks are added only when the chapter merits them. Default skeleton is the seven required sections plus the optional ones as warranted.

## Upload bundle for NotebookLM

Standard upload bundle (all 17 files in a 7-chapter book):

| Order | File set |
|---|---|
| 1 | `_notebooklm/00-NotebookLM-Source-Index.md` (orientation) |
| 2 | `_notebooklm/01-pronunciation-guide.md` |
| 3 | `_notebooklm/02-glossary.md` |
| 4 | `_notebooklm/03-source-integrity-notes.md` |
| 5 | `_notebooklm/04-do-not-say-guardrails.md` |
| 6 | `_notebooklm/05-episode-arc.md` |
| 7 | Production metadata files (e.g., editorial notes) |
| 8–N | Chapter source files (`Ch-NN-*.md` / `.txt`) in order |
| N+1 | `_notebooklm/chNN-scaffolding.md` for the episode being produced this session |

For a single-episode session, the operator may upload a smaller subset: master index + that episode's chapter + that episode's scaffolding + pronunciation + glossary + Do Not Say + source-integrity.

## Customize prompt (per-episode)

The operator pastes the per-episode customize prompt into NotebookLM's Customize box. It is assembled from:

- The relevant `chNN-scaffolding.md`'s Episode Intelligence (one-sentence premise + listener stake) — paraphrased into the opening directive
- The host questions
- The NotebookLM Instruction block
- Relevant Do Not Say entries (from `04-do-not-say-guardrails.md`)
- Relevant pronunciation entries (from `01-pronunciation-guide.md`) — formatted as R-PRONUNCIATION-IMPERATIVE directives (`Pronounce "..." as "...". Do not spell. Do not pause.`)

Target word count: 500–1,200 words. Extended-tier episodes (30–45 min audio) may need 1,000–1,800 words.

## Pre-publication review

Every episode generated in this mode passes through `_notebooklm/06-human-review-checklist.md` before publication. The checklist is **the gate**, not an advisory. P0 findings block publication; P1 findings ship-with-caution; P2 findings note for the next episode.

## Why not just run the orchestrator pipeline?

The orchestrator pipeline assumes:
- The source is in a raw format (PDF / audio / Word / etc.) that requires extraction and refinement.
- Chapter boundaries are not yet determined.
- The user is willing to accept the pipeline's chapter re-segmentation.

Pre-refined sources fail all three assumptions. Forcing them through the orchestrator would:
- Re-extract text that is already clean (Phase 0a wasted).
- Re-refine prose the user has already finalized (Phase 0b destructive).
- Re-segment chapters the user has already designed (Phase 0d destructive).

This mode preserves the user's editorial work while adding the production scaffolding NotebookLM needs to generate a strong audio overview.

## Cross-reference

- Worked example: `content/podcast/library/books/the-master-and-the-disciple/_notebooklm/`
- General podcast best-practices (the cross-project distilled standard): `_workspace/plan/research/podcast-best-practices.md` (treat as historical reference; the operating canon is the SKILL + this handbook)
- Project-specific recommendation log that drove this mode's design: `_workspace/plan/research/master-disciple-recommendations.md`

## Failure modes to avoid

1. **Rewriting frozen prose.** The whole point of this mode is to *add* scaffolding, not to modify the source. If the user wants prose rewritten, that is a different request (Phase 0b or hand-edit).
2. **Skipping the pronunciation guide.** Without it, NotebookLM will mangle every Arabic name and term. The guide is mandatory, not optional.
3. **Letting `[Editorial Clarification]` content into the customize prompt unlabeled.** NotebookLM will then quote editor's-voice as if it were source-text-voice.
4. **Building scaffolding that summarizes instead of steers.** Scaffolding is *editorial guidance about how to present the work*, not a summary of the work. If a scaffolding file reads like a summary, it has failed.
5. **Forgetting the human review checklist.** This is a pre-publication gate. Skipping it is the failure mode that ships theological errors.

## Status

**Mode introduced:** 2026-05-19 from the *Master and the Disciple* worked example.
**Canonical worked example:** `content/podcast/library/books/the-master-and-the-disciple/_notebooklm/`.
**Skill reference:** Section 1.5 of `skills-staging/podcast/SKILL.md` (Bypass for pre-refined multi-chapter sources).
