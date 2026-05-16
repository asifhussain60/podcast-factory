# Per-Section Instruction Block — Canonical Format

This is the canonical format for each section's NotebookLM instructions. Every section in `02-instructions/podcast-instructions.md` follows this template exactly.

## Template

```
[Section N] — [Title] [Format Tag]
Opening: "Welcome to this episode on [SOURCE], where today we [VERB] [SECTION]."

Focus on three things only:
  Key concepts:
    – <concept 1, extracted from the section text>
    – <concept 2>
    – <concept 3, optional, max 4>
  Teachings:
    – <what source figures explicitly instruct in this section>
    – <teaching 2, if multiple>
  Practical modern applications:
    – <concrete modern situation 1 where the teaching applies>
    – <application 2>
    – <application 3, optional, max 3>

Stay on these three. Do not introduce trivial background, biographical
filler, or contextual padding unless the section directly demands it.

[Optional: format-specific notes]
[Optional: pronunciation reminders for terms in this section]
```

## Field rules

**Section header line:**
- `[Section N]` becomes "Chapter N", "Part N", "Section N", or the type-appropriate word per content type.
- `[Title]` is the detected or user-supplied section title.
- `[Format Tag]` is `[Deep Dive]` or `[Debate]` — auto-assigned by the skill, user-overridable.

**Opening line:**
- Single sentence per `opening-templates.md`. No exceptions.
- The verb follows position-aware rotation for multi-section sources.

**Key concepts (2–4 items):**
- Each item is a noun phrase or short sentence naming a concept the section teaches.
- Extracted from the actual section text — not invented, not paraphrased from training knowledge.
- Listed in the order they appear in the section.

**Teachings (1–3 items):**
- Each item is what the source figures explicitly instruct.
- Must be attributable to a named figure or to the source itself.
- Distinguished from concepts: concepts are *ideas*; teachings are *instructions*.

**Practical modern applications (2–3 items):**
- Each item is a concrete contemporary situation where the teaching applies.
- Must be practical and recognizable, not theoretical extension.
- Period-aware: applications make sense for a 2026 listener.

**The "Stay on these three" line is mandatory.** Do not omit, do not paraphrase.

## Format-specific optional notes

If `[Deep Dive]`:
```
Format: Deep Dive — single trajectory. One host leads the unfolding of the
chapter's argument; the other interrupts only to clarify, challenge,
summarize, or introduce a useful analogy.
```

If `[Debate]`:
```
Format: Debate — opposing positions. One host defends [position A from the
section]; the other defends [position B]. Both bring the chapter's
higher principle into view: [the synthesis the section reaches].
```

## Pronunciation reminders (when applicable)

If the section contains any term from the master lexicon or proposed for the master lexicon:

```
Pronunciation reminders for this section:
  – [Term 1]: [Phonetic spelling]
  – [Term 2]: [Phonetic spelling]
```

Only include terms that appear in this section. The complete guide lives in `03-pronunciation.md`.

## Format tag assignment logic

The skill auto-assigns `[Deep Dive]` or `[Debate]`:

- `[Debate]` — when the section contains explicit dialogue between figures with opposing positions, OR when the section text presents a question and works through competing answers.
- `[Deep Dive]` — when the section follows a single trajectory of insight, OR when one figure is teaching another without sustained opposition.

User can override per section via post-generation edit. The skill does not silently change a user override on rerun.
