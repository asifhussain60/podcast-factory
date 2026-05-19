# Podcast Best Practices for Claude Code AI

## Purpose

Use this file to improve the podcast-building intelligence of Claude Code when transforming books, transcripts, PDFs, notes, or chapter drafts into high-quality podcast source material.

The goal is not to produce a plain summary. The goal is to produce source material that helps a podcast system or host create a strong episode: clear premise, structured discussion, memorable scenes, tension, takeaways, host questions, and listener guidance.

## Core Rule

For every source file, Claude Code must answer four questions before generating or revising podcast material:

1. What is this source really about?
2. Why would a listener care?
3. What tension, question, argument, or transformation should drive the episode?
4. What must be clarified so the listener does not get lost?

Do not treat podcast preparation as formatting only. Treat it as editorial intelligence.

## Recommended Podcast Models

### 1. Literary Deep-Dive Model

Use this when the source is a novel, sacred text, philosophical work, memoir, or story-driven work.

Best practices:
- Begin with the central question of the work.
- Track character movement, not only plot.
- Discuss theme through scenes, dialogue, and turning points.
- Make the listener feel the progression of discovery.
- Use spoiler warnings where needed.
- Distinguish what the text says from what the host is interpreting.

Avoid:
- Reducing the work to a chapter-by-chapter summary.
- Explaining every symbol at once.
- Treating dense material as if it is self-explanatory.
- Letting admiration replace analysis.

### 2. Critical Nonfiction Review Model

Use this when the source makes claims, arguments, theological positions, historical assertions, or practical recommendations.

Best practices:
- State the main claim early.
- Ask what evidence supports it.
- Identify assumptions.
- Separate strong claims from weak claims.
- Include fair criticism without hostile tone.
- Ask what a skeptical listener would challenge.

Avoid:
- Snark without evidence.
- Treating the author as the target instead of the argument.
- Accepting claims only because the language sounds impressive.
- Ignoring contradictions, unsupported quotations, or source gaps.

### 3. Author or Teacher Interview Model

Use this when the episode should feel like a guided conversation with a thinker, scholar, author, teacher, or narrator.

Best practices:
- Prepare questions that reveal craft, context, and meaning.
- Ask why a passage matters, not only what it says.
- Use follow-up questions that deepen an answer.
- Let biographical or historical context serve the main idea.
- Keep a clear thread so the episode does not sprawl.

Avoid:
- Overloading the episode with biography.
- Asking vague admiration questions.
- Losing the source text inside general inspiration.
- Letting long answers go without a recap.

### 4. Recommendation and Discovery Model

Use this when the goal is to help listeners decide whether to read the book, continue the series, or understand its value.

Best practices:
- Identify who the work is for.
- Identify who may struggle with it.
- Give a short premise before analysis.
- Explain the difficulty level honestly.
- Name the strongest reason to engage with the work.
- Name the main barrier to engagement.

Avoid:
- Turning every source into praise.
- Hiding the hard parts.
- Using generic phrases like "important", "deep", or "timeless" without saying why.
- Making recommendations without listener fit.

### 5. Structured Listener-Friendly Review Model

Use this when the source is complex and needs a repeatable podcast format.

Recommended structure:
1. Spoiler or context warning
2. One-sentence premise
3. Why this episode matters
4. Three to five key beats
5. Best passage or strongest idea
6. Hardest or most confusing idea
7. Host questions
8. Listener takeaway
9. Next episode bridge

Avoid:
- Starting with housekeeping for too long.
- Giving ratings without reasons.
- Letting personal chatter bury the review.
- Ending without a clear takeaway or next step.

## Required NotebookLM Source Improvements

When preparing material for Google NotebookLM or similar podcast-generation tools, the source must be explicit. Do not assume the model will infer what matters.

Each source file should include:

### Source Card

Add this near the top of each chapter or source:

```md
## Source Card

- Work:
- Chapter / section:
- Source type:
- Intended episode role:
- Spoiler level:
- Primary listener question:
- Main tension:
- Key people:
- Key terms:
- Pronunciation notes:
- Theological or factual review needed:
```

### Episode Intelligence Block

Add this after the source card:

```md
## Episode Intelligence

### One-Sentence Premise

### Why a Listener Should Care

### What Changes in This Chapter

### Strongest Scene or Argument

### Most Confusing Point

### Host Questions

### Listener Takeaway

### Bridge to Next Episode
```

### Glossary

For specialized terms, include:

```md
## Glossary for Listeners

- Term:
  - Plain-English meaning:
  - How to pronounce:
  - Why it matters in this episode:
```

### Pronunciation Guide

For names and non-English terms, include:

```md
## Pronunciation Guide

- Name or term:
  - Pronunciation:
  - Keep consistent as:
  - Do not pronounce as:
```

### Source Integrity Notes

For quotations, teachings, historical claims, theological claims, or contested material, include:

```md
## Source Integrity Notes

- Claim or quotation:
- Source status:
  - Directly sourced
  - Traditional attribution
  - Editorial explanation
  - Needs verification before publication
- Use in podcast:
  - Safe to mention
  - Mention with caution
  - Do not present as settled fact
```

## Required Editorial Separation

Podcast source files must distinguish between four kinds of material:

1. Original source text
2. Translation or paraphrase
3. Editorial clarification
4. Host-facing podcast guidance

Use labels. Do not blend them silently.

Recommended labels:

```md
[Source Text]

[Translator / Editor Clarification]

[Podcast Host Cue]

[NotebookLM Instruction]
```

This matters because NotebookLM may treat everything in a source file as equally authoritative. If commentary is not labeled, the generated podcast may confuse explanation with original text.

## Episode Design Checklist

Before finalizing any podcast source, Claude Code must verify:

- The episode has a clear central question.
- The listener knows why the material matters.
- Dense concepts are introduced before they are used.
- Names and terms are pronounced consistently.
- Long paragraphs are broken into listenable units.
- Interpretive commentary is clearly labeled.
- The host has discussion questions.
- There is at least one tension point or critique.
- The episode does not merely praise the source.
- The episode names what may confuse or challenge listeners.
- The conclusion gives a clear takeaway.
- The next episode bridge is explicit.

## Concrete Source Rewrite Pattern

Use this pattern when a passage is dense.

### Before

A long explanatory paragraph that mixes story, symbolism, terms, and interpretation.

### After

```md
[Source Text]
Preserve the original or refined source passage here.

[Translator / Editor Clarification]
Explain the difficult idea in plain language.

[Podcast Host Cue]
Ask:
- What is the passage asking the listener to notice?
- What would a modern listener misunderstand?
- What tension should the host surface?

[Listener Takeaway]
One direct sentence explaining what the listener should carry forward.
```

## Dos

- Start with the listener's problem, not the source's complexity.
- Identify the episode's central question.
- Preserve nuance while making the path clear.
- Use concrete examples, but do not overuse analogies.
- Add spoiler guidance when the episode reveals major turns.
- Create host questions that invite real discussion.
- Include objections or points of confusion.
- Make the end of each episode feel earned.
- Use chapter transitions so the series feels designed.

## Don'ts

- Do not produce generic summaries.
- Do not flatten spiritual, literary, or philosophical material into self-help.
- Do not over-explain every symbol immediately.
- Do not mix source text and editorial interpretation without labels.
- Do not treat all quotations as equally verified.
- Do not use modern analogies that overpower the original work.
- Do not let the host sound like a lecturer reading notes.
- Do not bury the strongest idea in the middle of a dense paragraph.
- Do not rely on vibes. Use structure, evidence, and listener fit.

## Claude Code Workflow

When asked to improve podcast source files, Claude Code should follow this workflow:

1. Inventory all files.
2. Identify each file's role in the podcast project.
3. Detect inconsistencies in numbering, scope, terminology, and source status.
4. For each chapter, create or improve:
   - Source Card
   - Episode Intelligence
   - Glossary
   - Pronunciation Guide
   - Source Integrity Notes
   - Host Questions
   - Listener Takeaways
   - Next Episode Bridge
5. Flag theological, historical, or quotation claims that need review.
6. Keep original source material intact unless explicitly asked to rewrite it.
7. Put all new podcast scaffolding in clearly labeled sections.
8. Run the quality gate before finalizing.

## Quality Gate

Before completing the task, Claude Code must answer:

- Would a first-time listener understand the episode premise within one minute?
- Would a host know what to ask and where to focus?
- Are the hard parts named directly?
- Is the strongest material easy to find?
- Are source text, commentary, and host instructions separated?
- Are claims and quotations handled responsibly?
- Does the source support a real podcast conversation rather than a monotone narration?
