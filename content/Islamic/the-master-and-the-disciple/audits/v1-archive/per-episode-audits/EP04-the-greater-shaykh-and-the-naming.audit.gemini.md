## Inventory

One podcast bundle, "EP04-the-greater-shaykh-and-the-naming", was detected.

*   **Chapter/Episode:** The Greater Shaykh and the Seventh-Day Naming
    *   `00-framing.md`: Present and detailed.
    *   `01-source.md` (Primary Source): **Missing.**
    *   `02-key-passages.md`: Present, but an empty template.
    *   `03-context-pack.md`: Present, but an empty template.
    *   `04-discussion-spine.md`: Present, but an empty template.
    *   `99-show-notes.md`: Present.

## Chapter Findings

### Implied Chapter: The Greater Shaykh and the Seventh-Day Naming

This audit is based on descriptions in `00-framing.md` and `99-show-notes.md`, as the primary source file itself is missing.

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | (missing) | n/a | The primary source file for the chapter (`01-source.md`) is missing from the bundle. | Add the full, clean prose of the chapter to a new file named `01-source.md` and include it in the bundle. |
| P1 | 99-show-notes.md | Title: The Greater Shaykh and the Seventh-Day Naming | The file uses transliterated Arabic (`Kitab al-'Alim wa-l-Ghulam`, `da'wa`, `batin`) instead of Arabic script. | Replace all transliterated Arabic terms with their Arabic script equivalents, enclosed in parentheses after the English translation, per house style. |
| P1 | 99-show-notes.md | Blurb: The initiation chapter of... | The entire blurb is a single, unbroken paragraph of over 600 words, making it unreadable for audio hosts. | Segment the blurb into 5-7 smaller paragraphs, each corresponding to a major narrative beat described in `00-framing.md`. |

## Episode Findings

### Episode: The Greater Shaykh and the Seventh-Day Naming

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | 04-discussion-spine.md | # Discussion spine | The discussion spine is an empty template filled with `[LLM-FILL]` placeholders. | Populate the discussion spine with 6 distinct beats matching the narrative structure outlined in `00-framing.md`, including key questions, tensions, and anchor passage references for each. |
| P0 | 02-key-passages.md | # Key passages | The key passages file is an empty template. | Extract the verbatim quotes specified in `00-framing.md` (the announcement, brotherly recognition, naming dialogue, etc.) from the primary source and add them to this file as distinct, numbered passages. |
| P0 | 03-context-pack.md | # Context pack | The context pack is an empty template. | Populate the context pack with the author, dates, tradition, and intellectual context of the source text as outlined in the `## Background` section of `00-framing.md`. |
| P0 | 00-framing.md | ## Pronunciation | The pronunciation guide is incomplete; it omits Arabic terms used in `99-show-notes.md` (`Kitab al-'Alim wa-l-Ghulam`, `da'wa`, `batin`). | Add phonetic spellings for `Kitab al-'Alim wa-l-Ghulam`, `da'wa`, and `batin` to the pronunciation list to prevent host mispronunciation. |
| P2 | 99-show-notes.md | Blurb: The initiation chapter of... | The blurb uses extensive italics for emphasis, which can cause awkward vocal delivery if the text is used as a source. | Remove all italics from the blurb. Use prose structure to create emphasis instead. |

## Cross-Bundle Patterns

The primary pattern is **scaffolding without substance**. The `00-framing.md` file is exceptionally detailed and well-structured, providing a clear blueprint for a high-quality episode. However, all the core content files that this blueprint depends on (`01-source.md`, `02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`) are either missing or empty templates. The bundle is a plan for an episode, not a producible episode itself.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "04-discussion-spine.md",
    "anchor": "# Discussion spine",
    "severity": "P0",
    "problem": "The discussion spine is an empty template with '[LLM-FILL]' placeholders and cannot guide the hosts.",
    "fix": "Delete the entire file content and replace it by populating the 8 beats (6 main beats, 1 opening, 1 landing) with specific key questions, tensions, and anchor passage references based on the detailed narrative structure provided in '00-framing.md'.",
    "category": "spine"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "# Key passages",
    "severity": "P0",
    "problem": "The key passages file is an empty template, leaving hosts with no source text to quote.",
    "fix": "Delete the placeholder content. Populate this file with the verbatim quotes required by the 'Quote verbatim for...' list in '00-framing.md'. Each quote should be a separate passage with a heading (e.g., '### Passage 1: The Announcement').",
    "category": "notebooklm"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "# Context pack",
    "severity": "P0",
    "problem": "The context pack is an empty template, providing no background for the hosts.",
    "fix": "Delete the placeholder content. Populate the 'Author / narrator', 'What this chapter is responding to', and 'Tradition / lineage' sections using the information from the '## Background' section of '00-framing.md'.",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P0",
    "problem": "The pronunciation guide is incomplete, omitting terms used in '99-show-notes.md' which will cause mispronunciation.",
    "fix": "Add the following items to the pronunciation list: 'Pronounce \"Kitab al-'Alim wa-l-Ghulam\" as \"ki-TAAB al-AA-lim wal-ghu-LAAM\".', 'Pronounce \"da'wa\" as \"DAH-wah\".', 'Pronounce \"batin\" as \"BAA-tin\".'",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb: The initiation chapter of Kitab al-'Alim wa-l-Ghulam...",
    "severity": "P1",
    "problem": "The file uses transliterated Arabic instead of Arabic script, violating house style.",
    "fix": "Replace 'Kitab al-'Alim wa-l-Ghulam' with 'The Book of the Master and the Boy (كتاب العالم والغلام)'. Replace 'da'wa' with 'call (دعوة)'. Replace 'batin' with 'inner (باطن)'.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb: The initiation chapter of...",
    "severity": "P1",
    "problem": "The entire blurb is a single, massive paragraph over 600 words long, which is an audio-readability pitfall.",
    "fix": "Break the single large paragraph into at least six smaller paragraphs. Use the six narrative beats from '00-framing.md' (announcement, council, discourses, naming, transmission, farewell) as logical separation points for the new paragraphs.",
    "category": "notebooklm"
  }
]
```