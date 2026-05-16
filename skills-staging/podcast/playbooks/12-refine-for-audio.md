# Stage 12 — Refine For Audio

**Purpose:** Final pass that produces the audio-clean refined text in `01-refined/`. Preserves tone, improves flow and clarity for spoken delivery, replaces non-Latin script with the phonetic forms from `03-pronunciation.md`.

## Input

- `WORK_DIR/_analogized/section-NN-<slug>-analogized.md` (sections after enrichment + analogies)
- `WORK_DIR/_lexicon/detected-terms.yml` (the script-to-phonetic mapping)
- `WORK_DIR/_metadata.yml` (tone preferences from Stage 04)
- `traditions/<tradition>.yml` (tone preferences)

## Output

- `WORK_DIR/01-refined/section-NN-<slug>.md` — the final refined text for each section.

## Hard rules

1. **Tone preservation is non-negotiable.** If the source is reverent, the refinement is reverent. If conversational, conversational. Never flatten.
2. **No non-Latin script in the output.** Every non-Latin term is substituted with its phonetic form. No exceptions.
3. **No bracketed commentary.** Already enforced; verify nothing slipped in.
4. **Preserve dialogue structure.** Direct quotations stay direct. Speaker identification preserved.
5. **Preserve original meaning.** No rephrasing that changes what the source says, even subtly.

## Operations performed

### 1. Script substitution

For every non-Latin term identified in `_lexicon/detected-terms.yml`:

- Replace the original-script form with the phonetic form.
- Preserve surrounding punctuation and quotation marks.
- If the source includes the meaning inline (e.g., "Sharee-ah (the law)"), preserve the meaning gloss; just swap the script.
- If the source uses the term without a meaning gloss, decide:
  - First appearance in section: add brief meaning gloss if listener wouldn't know the term.
  - Subsequent appearances: phonetic only.

Example:

**Source:**
> "He said: 'Praise be to الله Who is eternally compassionate (الحمد للہ الذی لم یزل بالمؤمنین رحیما).'"

**Refined:**
> "He said, 'Praise be to Allaah, who has always been compassionate and merciful toward those who have faith: al-hamdu lil-laahil-ladhee lam yazal bil-mu'mineena raheemaa.'"

### 2. Sentence-level audio clarity

Apply these guidelines, but only where they don't change meaning:

- **Long sentences** (>40 words) → break into two sentences when natural break exists.
- **Heavy nominalization** ("the prevention of evil" → "preventing evil") only when the source's style admits the simpler form.
- **Dense pronoun chains** ("he told him that he..." with unclear antecedents) → restate the antecedent.
- **Archaic constructions** ("he doth" → "he does") only if the source isn't deliberately archaic. Most translated theological texts use archaic forms intentionally — preserve them.
- **Run-on prose without paragraph breaks** → add paragraph breaks at natural shift points.

### 3. Dialogue cleanup

For dialogues:

- Use straight quotation marks `"` for speech.
- Use a comma + quotation pattern (`He said, "..."`) rather than colon when natural.
- For long speeches, break into paragraphs but begin each new paragraph with an opening quotation mark, no closing mark, and a closing mark only at the end.

### 4. Pronunciation reminder integration

For terms that are easy to mispronounce, the source can include phonetic spelling parenthetically on first use:

> "He spoke of taa-weel — disciplined interpretation, as distinct from speculation."

The parenthetical is the meaning gloss; the phonetic spelling is already in the term itself. Only add the meaning gloss if the listener wouldn't follow without it.

### 5. Honorific preservation

Honorifics from `traditions/<tradition>.yml` tone preferences:

- Prophet Muhammad → "Prophet Muhammad, peace and blessings be upon him" (first mention per section; "the Prophet" or "Prophet Muhammad" thereafter).
- Imams → "Imam [Name], peace be upon him" (first mention; "the Imam" or "Imam [Name]" thereafter).
- Christian honorifics per christian.yml.
- Other traditions per their own tone preferences.

Use the honorific the tradition prefers in spoken English — do not invent new ones.

### 6. Tone-preserving examples

For each detected tone label (Stage 04), apply this guidance:

| Tone | Refinement guidance |
|---|---|
| `reverent` | No casual phrasing, no familiarity in address to divine or holy figures, preserve ceremonial language |
| `narrative` | Preserve scene, dialogue, character action; do not summarize away movement |
| `argumentative` | Preserve premises and conclusions; do not soften qualified claims |
| `conversational` | Preserve contractions, direct address, oral rhythm |
| `academic` | Preserve hedged language, technical vocabulary, citation style |
| `literary` | Preserve imagery, metaphor, distinctive sentence structure — these are the work |
| `instructional` | Preserve imperatives; do not soften "you must" to "you might" |
| `meditative` | Preserve pacing, repetition, slow tempo; do not compress |

### 7. Word count guard

After refinement, verify the section's word count is between 70% and 140% of the original section word count (this matches Quality Gate 5 in Stage 14).

If under 70%: the refinement is summarizing away content. Re-do with less compression.
If over 140%: enrichment + analogies + clarifications have run away. Re-do with less addition.

## Section file format

Each output `01-refined/section-NN-<slug>.md` contains:

```markdown
---
section_number: N
section_title: "[Title]"
source: "[Source Title]"
word_count: [N]
tone_preserved: [list of tone labels from Stage 04]
phonetic_substitutions: [N]
enrichments_added: [N]
analogies_added: [N]
---

# Section [N] — [Title]

[Refined audio-clean text, paragraph-formatted, phonetic substitutions
applied, tone preserved, no non-Latin script, no bracketed commentary,
suitable for direct ingestion into NotebookLM as source material.]
```

## What this stage does NOT do

- Does not generate the per-section instruction blocks (Stage 13).
- Does not run quality gates (Stage 14).
- Does not produce the ZIP (Stage 15).
- Does not modify the master lexicon or library files.
