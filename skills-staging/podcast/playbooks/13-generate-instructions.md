# Stage 13 — Generate NotebookLM Instructions

**Purpose:** Produce the canonical `02-instructions/podcast-instructions.md` file: one block per section per `templates/instruction-block.md`, plus the eight-rule anti-noise block per `templates/anti-noise-block.md` appended once at the end.

## Input

- `WORK_DIR/_segments/segments.yml`
- `WORK_DIR/01-refined/section-NN-<slug>.md` (each refined section)
- `WORK_DIR/_metadata.yml` (content type, author, title)
- `WORK_DIR/03-pronunciation.md` (terms used per section)
- `templates/opening-templates.md`
- `templates/instruction-block.md`
- `templates/anti-noise-block.md`

## Output

- `WORK_DIR/02-instructions/podcast-instructions.md` — the canonical NotebookLM instructions file, ready to paste into NotebookLM's prompt.

## File structure

```
# Podcast Instructions — [Source Title]

[brief preamble, 2-3 lines — see "Preamble" below]

---

[Section 1 block]

---

[Section 2 block]

---

...

---

[Global anti-noise block — verbatim per template]
```

## Preamble

```
Source: [Source Title] by [Author / Speaker]
Format: [Per-content-type description]
Sections: [N]

These instructions cover [N] episodes — one per section. Each episode
has its own opening, focus directive, and format tag. The global
behavior rules at the end of this file apply to every episode.
```

For multi-section sources, the preamble names the count. For single-section sources, the preamble notes "Single-section source — one episode below."

## Per-section block generation

For each section in `segments.yml`, generate the block per `templates/instruction-block.md`:

### Step 1: Header line

```
[Section N] — [Title] [Format Tag]
```

- `[Section N]` is the type-appropriate word from the content type:
  - Book / memoir → `Chapter N`
  - Academic paper → `Section: [Section Name]` (no number — section names are the identifier)
  - Lecture series → `Part N`
  - Article (multi-section) → `Section N`
  - Anthology → `Piece N`
  - Otherwise → `Section N`

- `[Title]` is the section title from segments.yml.

- `[Format Tag]` is `[Deep Dive]` or `[Debate]` from auto-detection.

### Step 2: Opening line

Generate from `templates/opening-templates.md` using:

- Content type → template selection.
- Verb rotation → position-aware for multi-section sources; tonal for single-piece sources.

Verify:
- Single sentence.
- Contains source identity AND section identity.
- Title italicized for books / memoirs / collections; quoted for articles / papers / lectures / sermons / documents / pieces.

### Step 3: Three-part Focus directive

Extract from the refined section content:

**Key concepts (2–4):**
- Identify the conceptual ideas the section teaches.
- Noun phrases or short sentences.
- Listed in source order.
- Must be present in the section text — not invented.

**Teachings (1–3):**
- What the source figures explicitly instruct.
- Attributable to a named figure or to the source itself.
- Must be present as instructions/teachings in the section, not extracted as concepts.

**Practical modern applications (2–3):**
- Concrete contemporary situations where the teaching applies.
- Use the analogies already woven into the section (Stage 11) when relevant — those analogies become the "application" list.
- Period-appropriate for 2026 listeners.

Write the directive with the exact format from `templates/instruction-block.md`:

```
Focus on three things only:
  Key concepts:
    – <concept 1>
    – <concept 2>
    – <concept 3, optional>
  Teachings:
    – <teaching 1>
    – <teaching 2, if multiple>
  Practical modern applications:
    – <application 1>
    – <application 2>
    – <application 3, optional>

Stay on these three. Do not introduce trivial background, biographical
filler, or contextual padding unless the section directly demands it.
```

### Step 4: Format-specific note (optional)

If `[Deep Dive]`:
```
Format: Deep Dive — single trajectory. One host leads the unfolding of the
section's argument; the other interrupts only to clarify, challenge,
summarize, or introduce a useful analogy.
```

If `[Debate]`:
```
Format: Debate — opposing positions. One host defends [position A from
section]; the other defends [position B]. Both bring the section's
higher principle into view: [the synthesis the section reaches].
```

The skill fills `[position A]`, `[position B]`, and `[synthesis]` from the actual section content.

### Step 5: Pronunciation reminders (optional)

If the section contains terms from the master lexicon, list them:

```
Pronunciation reminders for this section:
  – [Term 1]: [Phonetic spelling]
  – [Term 2]: [Phonetic spelling]
```

Only include terms that appear in this specific section. Sort alphabetically by phonetic.

## Format tag auto-assignment

For each section, decide Deep Dive vs Debate using these signals:

**Signals favoring [Debate]:**
- Section contains 2+ named speakers in active disagreement.
- Section text uses "but", "however", "on the other hand", "objection" frequently.
- Section presents a question and works through competing answers.
- Section ends in a synthesis that named both positions explicitly.

**Signals favoring [Deep Dive]:**
- Section has a single trajectory of insight.
- Section has one figure teaching another without sustained opposition.
- Section is reflective or meditative without explicit dialectic.
- Section is a sermon, lecture passage, or single-author argument.

Score each signal. Pick the format with higher score. Default to `[Deep Dive]` if scores are equal.

## Position-aware verb rotation (multi-section sources)

| Section position | Verb |
|---|---|
| 1 (first) | `begin with` |
| 2 | `explore` |
| 3 | `enter` |
| 4 | `continue with` |
| 5 to N-1 (cycle) | `discuss`, then `explore` again, then `continue with` |
| N (last) | `conclude with` |

For 2-section sources: first = `begin with`, last = `conclude with`.
For 3-section sources: first = `begin with`, middle = `explore`, last = `conclude with`.
Single-piece sources use single-piece verbs (`examine`, `explore`, `consider`, `unpack`).

## Anti-noise block

Append once at the end of the file, verbatim from `templates/anti-noise-block.md`. Do not paraphrase, do not omit any of the eight rules, do not change the order, do not change the pronunciation reminder line at the end.

## Validation before writing

Before writing `02-instructions/podcast-instructions.md`, verify:

- Every section has an opening that is exactly one sentence.
- Every opening contains both source identity and section identity.
- Every section's three-part Focus directive has at least 2 key concepts, 1 teaching, 2 applications.
- Every section has a format tag.
- Every section header uses the type-appropriate word.
- The anti-noise block appears exactly once at the end.
- No non-Latin script anywhere in the file (regex check).
- No bracketed commentary headings (`[Note]`, `[Commentary]`, etc.) anywhere except `[Section N]` headers, `[Deep Dive]`/`[Debate]` format tags, and the canonical block headers.

If any check fails, fix and re-run. If a fix is not possible (e.g., section title is missing), stop and write `WORK_DIR/INSTRUCTION-GENERATION-ERROR.md`.

## What this stage does NOT do

- Does not run the five quality gates (Stage 14).
- Does not produce the ZIP (Stage 15).
- Does not write library proposals (Library Cross-Pollination stage).
