## Inventory

-   **Chapter/Episode:** EP01: The Master's Call and the Disciple's Covenant
    -   `00-framing.md` (present)
    -   `01-source.md` (**MISSING**)
    -   `02-key-passages.md` (present, but empty)
    -   `03-context-pack.md` (present, but empty)
    -   `04-discussion-spine.md` (present, but empty)
    -   `99-show-notes.md` (present)

## Chapter Findings

### Chapter 1: The Master's Call and the Disciple's Covenant

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | (missing) | Bundle Manifest | The primary source file `01-source.md` is missing. The bundle is non-functional without the chapter text. | This is a fatal error requiring human intervention. The full text of the chapter must be added to the bundle as `01-source.md`. |
| P2 | 99-show-notes.md | Blurb | The blurb uses transliterated Arabic (`Kitab al-'Alim wa-l-Ghulam`, `da'wa`, `sheikh`) instead of Arabic script as required by the articulation style guide. | Replace transliterated terms with their Arabic script equivalents, or remove them if the script is unavailable. |

## Episode Findings

### Episode 1: The Master's Call and the Disciple's Covenant

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | 04-discussion-spine.md | File-level | The discussion spine is an empty template filled with `[LLM-FILL]` placeholders. NotebookLM cannot generate a conversation without it. | Populate the discussion spine with content for each beat, following the detailed six-beat structure laid out in `00-framing.md`. |
| P0 | 02-key-passages.md | File-level | The key passages file is an empty template. There are no verbatim quotes for the hosts to retrieve and discuss. | Populate this file with key verbatim quotes from the primary source, corresponding to the beats in the discussion spine. |
| P0 | 03-context-pack.md | File-level | The context pack is an empty template. No background information is available for retrieval grounding. | Populate this file with the author, lineage, and context details as prompted by the template headers. |
| P1 | 04-discussion-spine.md | File-level | The discussion spine template contains 8 beats, which contradicts the explicit six-beat structure detailed in `00-framing.md`. | Replace the 8-beat template with a 6-beat structure that directly maps to the "Three-part focus" section in `00-framing.md`. |
| P1 | 00-framing.md | ## Pronunciation | The pronunciation guide is incomplete. Terms used in `99-show-notes.md` (`da'wa`, `sheikh`) are not included, risking mispronunciation. | Add pronunciation guidance for `da'wa` and `sheikh` to the pronunciation list. |
| P2 | 00-framing.md | ## Stable role-labels | The file uses bolding for emphasis on role labels, which violates the "no bold" articulation style rule. | Remove all bold markdown (`**`) from the file. |
| P2 | 00-framing.md | Throughout | The text inconsistently uses "God" (e.g., "Party of God") and "Allah" (in an honorific). The house style prefers "Allah". | Standardize all instances of "God" to "Allah" where it does not alter the meaning of a direct quote or established term from the source text. |

## Cross-Bundle Patterns

The bundle is a well-designed but incomplete skeleton. The `00-framing.md` file is exceptionally detailed, providing a robust blueprint for a high-quality scholarly conversation that avoids common AI-driven failure modes. However, all content-bearing artifacts (`01-source.md`, `02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`) are either missing or empty templates. The immediate priority is to populate these files with the actual source material and derived content as specified in the framing document. Without this, the bundle is entirely non-functional.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "04-discussion-spine.md",
    "anchor": "File-level",
    "severity": "P0",
    "problem": "The discussion spine is an empty template filled with '[LLM-FILL]' placeholders.",
    "fix": "Replace the entire file content with a populated six-beat discussion spine, deriving the key question, tension, and landing for each beat from the 'Three-part focus' section in '00-framing.md'.",
    "category": "spine"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "File-level",
    "severity": "P0",
    "problem": "The key passages file is an empty template.",
    "fix": "This file cannot be populated without the primary source. Replace the entire file content with a single comment: '# ERROR: Primary source (01-source.md) is missing. Cannot populate key passages.'",
    "category": "notebooklm"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "File-level",
    "severity": "P0",
    "problem": "The context pack is an empty template.",
    "fix": "This file cannot be populated without the primary source. Replace the entire file content with a single comment: '# ERROR: Primary source (01-source.md) is missing. Cannot populate context pack.'",
    "category": "notebooklm"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "File-level",
    "severity": "P1",
    "problem": "The discussion spine template contains 8 beats, which contradicts the explicit six-beat structure detailed in '00-framing.md'.",
    "fix": "Ensure the populated discussion spine (per the P0 fix) has exactly six beats, mapping directly to the structure in the 'Three-part focus' section of '00-framing.md'.",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "The pronunciation guide is incomplete and does not cover terms used in the show notes.",
    "fix": "Add the following lines to the pronunciation list under the '## Pronunciation' heading: 'Pronounce \"da'wa\" as \"DAH-wah\".' and 'Pronounce \"sheikh\" as \"SHAYKH\".'",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The opening chapter of Kitab al-'Alim wa-l-Ghulam",
    "severity": "P2",
    "problem": "The blurb uses transliterated Arabic instead of Arabic script.",
    "fix": "In the blurb, replace 'Kitab al-'Alim wa-l-Ghulam' with 'كتاب العالم والغلام', replace 'da'wa' with 'دعوة', and replace 'sheikh' with 'شيخ'.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Stable role-labels",
    "severity": "P2",
    "problem": "The file uses bold markdown for emphasis, violating the house style.",
    "fix": "Remove all bold markdown markers (`**`) from the entire file.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Party of God",
    "severity": "P2",
    "problem": "The text inconsistently uses 'God' and 'Allah'.",
    "fix": "Throughout the file, replace instances of 'God' with 'Allah', except where it is part of a proper noun or direct title from the source text like 'Party of God' or 'religion of God's friends'. Apply this change to 'servant of God' -> 'servant of Allah'.",
    "category": "articulation"
  }
]
```