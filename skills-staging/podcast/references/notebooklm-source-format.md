# NotebookLM Source Format Spec

This is the format spec for files in an episode bundle. Each file has a specific job; do not blur the boundaries.

## Why coordinated multi-file bundles work better than one monolithic source

NotebookLM treats every uploaded source as a chunk in its retrieval index. When the Audio Overview is generated, the hosts paraphrase what the retrieval surfaces. If we give it ONE giant file, the model has to pick what matters. If we give it COORDINATED files where each file has a job, the retrieval naturally pulls the right material at the right moment.

  - Hosts need a quote → retrieval pulls from `02-key-passages.md`
  - Hosts need context → retrieval pulls from `03-context-pack.md`
  - Hosts need a thematic beat → retrieval pulls from `04-discussion-spine.md`
  - Hosts need the primary material → retrieval pulls from `01-source-primary.md`

The framing file is uploaded as a source AND its content is pasted into the "Customize" prompt for the Audio Overview generation. Belt and suspenders.

## File-by-file spec

### `00-framing.md`

  - 150–300 words
  - First line: `# Framing — Episode ##: [Title]`
  - Sections (H2):
    - `## Audience` — concrete, one or two sentences
    - `## Angle` — faithful / critical / personal / comparative / lived-reaction
    - `## Host Dynamic` — default or override (name the personas and behaviors)
    - `## Central Tensions` — 2–4 specific tensions, each one sentence
    - `## Tone Constraints` — what to avoid (filler, false enthusiasm, lecturing)
    - `## Steering Instructions` — direct instructions to the hosts using patterns from `two-host-framing.md`
  - Final paragraph: the UPLOAD CHECKLIST (added in Phase 4)

### `01-source-primary.md`

  - First line: `# [Source Title] — [Author/Origin]`
  - Attribution block (H2 `## Source`) with: author, work title, edition/translator, year, section/chapter, source path on disk
  - The distilled source content with consistent H2/H3 hierarchy
  - For book chapters: include short context (~50 words) at the top so the source is self-contained
  - For full books or long sources: stay above 1,500 words and below 8,000 words. Split into multiple episodes if needed.

### `02-key-passages.md`

  - First line: `# Key Passages — [Source Short Title]`
  - Each passage as a blockquote, attribution line beneath:
    ```
    > Verbatim text of the passage.
    — [Author], [Work], [Section/Page]
    ```
  - Order matches source order
  - 6–15 passages typical. Cap at 20.
  - Skip passages that are pure connective tissue. We want passages that turn something, contradict, surprise, or anchor.

### `03-context-pack.md`

  - First line: `# Context Pack — [Source Short Title]`
  - Sections (H2):
    - `## Author` — bio in 100–200 words, dates, intellectual lineage, primary works
    - `## Tradition` — the tradition / school / school-of-thought this work sits within
    - `## Historical Moment` — when was this written, what was the author responding to
    - `## Related Works` — 3–7 works in conversation with this one
    - `## Why Now` — why this conversation matters in 2026 (or whatever the framing audience needs)
  - All facts cited or marked `[CONTEXT NEEDED]` if missing

### `04-discussion-spine.md`

  - First line: `# Discussion Spine — Episode ##: [Title]`
  - 6–12 numbered beats. Each beat:
    ```
    ### Beat N: [Title]
    - **Key question:** What is the host asking here?
    - **Tension:** What's the friction or unresolved point?
    - **Anchor passage:** Reference to a passage from `02-key-passages.md`
    - **Landing:** What state does this beat leave the listener in?
    ```
  - Beats build pressure. Don't start at maximum intensity.
  - The last beat lands the episode. Often a question, not a conclusion.

### `99-show-notes.md` (optional but recommended)

  - First line: `# Show Notes — Episode ##: [Title]`
  - `## Blurb` — 50–80 words, what the episode covers and why
  - `## Listening Time` — estimate from NotebookLM after generation
  - `## Sources` — full citations
  - `## References Mentioned` — anything cited inside the episode
  - `## Related Episodes` — links to other episodes in registry

## Heading hierarchy rules

  - H1 once per file (the title)
  - H2 for major sections
  - H3 for sub-beats within an H2
  - Never skip levels
  - Never use H4 or deeper

## What NotebookLM ignores

  - Front matter (YAML)
  - HTML tags
  - Comments
  - Tables of contents
  - Filename — but it uses filenames to order sources in the UI, hence our `00-`, `01-`, etc.

## What NotebookLM responds to strongly

  - Blockquotes with attribution → high quote-inclusion rate
  - Clear H2 sections → hosts naturally segment around them
  - Direct instructions in the framing file → noticeable behavior change
  - Repetition of a tension across multiple files → hosts return to it
  - Short, declarative beat descriptions in `04-discussion-spine.md`
