## Inventory

-   **Chapter/Episode:** EP04: The Greater Shaykh and the Seventh-Day Naming
    -   `00-framing.md` (present)
    -   `primary-source.md` (missing)
    -   `02-key-passages.md` (present, but empty template)
    -   `03-context-pack.md` (present, but empty template)
    -   `04-discussion-spine.md` (present, but empty template)
    -   `99-show-notes.md` (present)

## Chapter Findings

The primary source file for the chapter is missing from the bundle. The following findings are based on `99-show-notes.md`, which contains a prose summary of the chapter and is the only available text for style and readability analysis.

### Chapter 4: The Greater Shaykh and the Seventh-Day Naming

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P1 | `99-show-notes.md` | The initiation chapter of *Kitab al-'Alim wa-l-Ghulam* | The text uses italics for emphasis and transliterated Arabic terms, violating the house articulation style. | Remove all italics. Replace transliterated Arabic (e.g., `Kitab al-'Alim wa-l-Ghulam`, `da'wa`, `batin`, `Shaykh`) with their English equivalents or the original Arabic script. |
| P1 | `99-show-notes.md` | The initiation chapter of *Kitab al-'Alim wa-l-Ghulam* | The entire body of the show notes is a single, unbroken paragraph over 400 words, posing a readability risk for NotebookLM hosts. | Segment the long paragraph into 5-7 smaller paragraphs, adding line breaks at natural thematic shifts (e.g., before the two discourses, the naming dialogue, the veiled transmission). |
| clean | clean | clean | clean | clean |

## Episode Findings

### Episode 4: The Greater Shaykh and the Seventh-Day Naming

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `04-discussion-spine.md` | `### Beat 1: Opening hook` | The discussion spine is an unfilled template and provides no structure for the hosts, which will cause NotebookLM to fail. | Populate all `[LLM-FILL]` placeholders with concrete questions, tensions, and passage references based on the six beats outlined in `00-framing.md`. |
| P1 | `02-key-passages.md` | `### Passage 1` | The key passages file is an unfilled template and contains no source text for the hosts to quote. | Populate the file with verbatim quotes from the primary source, corresponding to the anchor passages required by the six beats in `00-framing.md`. |
| P1 | `03-context-pack.md` | `## Author / narrator` | The context pack is an unfilled template, providing no background grounding for the hosts. | Populate all `[LLM-FILL]` placeholders with the relevant author, tradition, and contextual information. |
| P1 | `00-framing.md` | `## Pronunciation` | The pronunciation guide is missing entries for several transliterated terms used in `99-show-notes.md` (e.g., `Shaykh`, `da'wa`, `batin`). | Add phonetic spellings to the pronunciation guide for the terms 'Shaykh', 'da'wa', 'batin', and 'Kitab al-'Alim wa-l-Ghulam'. |
| P1 | `99-show-notes.md` | `**Title:** The Greater Shaykh and the Seventh-Day Naming` | The show notes file has a dense, academic tone that is misaligned with the instructional-but-casual tone specified in the framing document. | Rewrite the show notes summary to adopt a more conversational tone, breaking up complex sentences and using simpler language while retaining doctrinal accuracy. |
| clean | clean | clean | clean | clean |

## Cross-Bundle Patterns

As only one bundle was provided, no cross-bundle patterns can be identified. However, a significant pattern *within* this bundle is the use of placeholder templates (`[LLM-FILL]`) for critical artifacts like the discussion spine, key passages, and context pack. This suggests a systemic pipeline failure or that the bundle is a very early, incomplete draft. This is the root cause of the most severe (P0/P1) findings.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "The discussion spine is an unfilled template and provides no structure for the hosts, which will cause NotebookLM to fail.",
    "fix": "Populate all `[LLM-FILL]` placeholders in the discussion spine with concrete questions, tensions, and passage references based on the six beats outlined in `00-framing.md`.",
    "category": "spine"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "### Passage 1",
    "severity": "P1",
    "problem": "The key passages file is an unfilled template and contains no source text for the hosts to quote.",
    "fix": "Populate the file with verbatim quotes from the primary source, corresponding to the anchor passages required by the six beats in `00-framing.md`.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "## Author / narrator",
    "severity": "P1",
    "problem": "The context pack is an unfilled template, providing no background grounding for the hosts.",
    "fix": "Populate all `[LLM-FILL]` placeholders with the relevant author, tradition, and contextual information.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The initiation chapter of *Kitab al-'Alim wa-l-Ghulam*",
    "severity": "P1",
    "problem": "The text uses italics for emphasis and transliterated Arabic terms, violating the house articulation style.",
    "fix": "Remove all italics used for emphasis. Replace all transliterated Arabic terms (e.g., `Kitab al-'Alim wa-l-Ghulam`, `da'wa`, `batin`, `Shaykh`) with their English equivalents or, if necessary, the original Arabic script.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The initiation chapter of *Kitab al-'Alim wa-l-Ghulam*",
    "severity": "P1",
    "problem": "The entire body of the show notes is a single, unbroken paragraph over 400 words, which poses a readability risk for NotebookLM hosts.",
    "fix": "Segment the long paragraph into 5-7 smaller paragraphs, adding line breaks at natural thematic shifts (e.g., before the description of the two discourses, before the naming dialogue, before the veiled transmission).",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "The pronunciation guide is missing entries for several transliterated terms used in `99-show-notes.md`.",
    "fix": "Add phonetic spellings to the pronunciation guide for the terms 'Shaykh', 'da'wa', 'batin', and 'Kitab al-'Alim wa-l-Ghulam'.",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Title:** The Greater Shaykh and the Seventh-Day Naming",
    "severity": "P1",
    "problem": "The show notes file has a dense, academic tone that is misaligned with the instructional-but-casual tone specified in the framing document.",
    "fix": "Rewrite the show notes summary to adopt a more conversational tone, breaking up complex sentences and using simpler language while retaining doctrinal accuracy.",
    "category": "tone"
  }
]
```