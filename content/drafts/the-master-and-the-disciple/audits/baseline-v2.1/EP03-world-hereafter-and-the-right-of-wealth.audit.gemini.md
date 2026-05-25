## Inventory

-   **Episode:** EP03-world-hereafter-and-the-right-of-wealth
    -   `00-framing.md`: Present
    -   `primary-source.md`: **Missing**
    -   `02-key-passages.md`: Present (unfilled template)
    -   `03-context-pack.md`: Present (unfilled template)
    -   `04-discussion-spine.md`: Present (unfilled template)
    -   `99-show-notes.md`: Present

## Chapter Findings

### Chapter: World, Hereafter, and the Right of Wealth

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `99-show-notes.md` | The ethical-practical bridge of Kitab al-'Alim wa-l-Ghulam... | The show notes blurb uses extensive transliterated Arabic, which violates the bundle's 'no transliteration' rule and will be mispronounced. | Replace all transliterated Arabic terms with their specified English equivalents from `00-framing.md`. |
| P1 | `99-show-notes.md` | The ethical-practical bridge of Kitab al-'Alim wa-l-Ghulam... | The entire blurb is a single, unbroken paragraph over 500 words long, which is unreadable and risks audio glitches. | Break the paragraph into 3-4 smaller paragraphs aligned with the chapter's major movements. |
| P1 | `99-show-notes.md` | The ethical-practical bridge of Kitab al-'Alim wa-l-Ghulam... | The tone is dense and academic, conflicting with the 'instructional-but-casual' tone required by the framing document. | Rewrite the blurb using more accessible language, removing overly technical vocabulary. |
| P2 | `99-show-notes.md` | ...with the Qur'anic warrant of Q 4:69... | The Quran citation `Q 4:69` does not use the required `Q\|Surah:Verse` format. | Change the citation to `Q\|4:69`. |
| P2 | `99-show-notes.md` | The ethical-practical bridge of *Kitab al-'Alim wa-l-Ghulam*... | The use of italics for titles and emphasis violates the prose-only articulation style. | Remove all markdown italics from the show notes blurb. |

## Episode Findings

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `02-key-passages.md` | # Key passages | The key passages file is an unfilled template containing no usable content for the hosts. | Populate this file with verbatim quotes from the primary source, corresponding to the beats described in `00-framing.md`. |
| P0 | `03-context-pack.md` | # Context pack | The context pack file is an unfilled template, providing no background for the hosts. | Populate this file with the author, historical context, and tradition details required to ground the conversation. |
| P0 | `04-discussion-spine.md` | # Discussion spine | The discussion spine is an unfilled template, providing no structure for the episode conversation. | Populate the spine with 6 distinct beats matching the structure in `00-framing.md`, each with a key question, tension, and anchor passage. |
| P1 | `00-framing.md` | ## Manifest (conceptual anchor) | The bundle is missing the primary source text for the chapter being discussed. | Add the primary source text as a new file, `01-primary-source.md`, to the bundle. |
| P1 | `00-framing.md` | ## Pronunciation | A Quran citation exists in the bundle, but there is no spoken-form appendix to guide NotebookLM's pronunciation. | Add a 'Citation Spoken Form' section mapping each citation to natural speech (e.g., 'Q\|4:69' -> 'Quran, chapter four, verse sixty-nine'). |
| P2 | `00-framing.md` | Episode format: in-depth walkthrough... | The episode format is described but does not use a standard NotebookLM format declaration. | Change the 'Episode format' line to 'Episode format: Deep Dive. An in-depth walkthrough of a single ethical-practical chapter.' |

## Cross-Bundle Patterns

This is a single-bundle audit. The most significant pattern is the use of unfilled templates (`[LLM-FILL]`) for critical artifacts like the discussion spine, key passages, and context pack. This suggests a systemic failure in the content generation pipeline, as the bundle is structurally present but functionally empty, making it impossible for NotebookLM to produce a coherent audio overview.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "02-key-passages.md",
    "anchor": "# Key passages",
    "severity": "P0",
    "problem": "The key passages file is an unfilled template and contains no content.",
    "fix": "Populate this file with verbatim quotes from the primary source, corresponding to the beats described in '00-framing.md'.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "# Context pack",
    "severity": "P0",
    "problem": "The context pack file is an unfilled template and contains no content.",
    "fix": "Populate this file with the author, historical context, and tradition details required to ground the hosts' conversation.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "# Discussion spine",
    "severity": "P0",
    "problem": "The discussion spine is an unfilled template and provides no structure for the episode.",
    "fix": "Populate the discussion spine with 6 distinct beats, matching the structure outlined in '00-framing.md', each with a key question, tension, and anchor passage reference.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The ethical-practical bridge of Kitab al-'Alim wa-l-Ghulam",
    "severity": "P0",
    "problem": "The show notes use extensive transliterated Arabic, which violates the 'Arabic script only' rule and will be mispronounced by NotebookLM.",
    "fix": "Replace all transliterated Arabic terms (e.g., 'Kitab al-'Alim wa-l-Ghulam', 'nāṭiqs', 'hujja', 'ta'wīl', 'batin', 'al-Khidr', 'awliyāʾ', 'zakat') with their English equivalents as specified in '00-framing.md'.",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "Episode format: in-depth walkthrough of a single ethical-practical chapter.",
    "severity": "P1",
    "problem": "The bundle is missing the primary source text for the chapter being discussed.",
    "fix": "Add the primary source text as a new file, '01-primary-source.md', to the bundle.",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "A Quran citation exists in the bundle ('Q 4:69' in show notes), but there is no spoken-form appendix to guide NotebookLM's pronunciation.",
    "fix": "Add a new section 'Citation Spoken Form' to this file with a mapping for each Quran citation, e.g., 'Q|4:69' -> 'Quran, chapter four, verse sixty-nine'.",
    "category": "citation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The ethical-practical bridge of Kitab al-'Alim wa-l-Ghulam",
    "severity": "P1",
    "problem": "The entire show notes blurb is a single, unbroken paragraph over 500 words long, which is difficult to read and process.",
    "fix": "Break the single paragraph into at least three smaller paragraphs, aligned with the major movements of the chapter (e.g., Pairs/Teaching, Interpretations/Verdicts, Enactment/Deferral).",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The ethical-practical bridge of Kitab al-'Alim wa-l-Ghulam",
    "severity": "P1",
    "problem": "The show notes' tone is dense and academic, which conflicts with the 'instructional-but-casual' tone specified in the framing.",
    "fix": "Rewrite the show notes blurb into 3-4 shorter paragraphs using a more accessible, instructional tone. Remove the overly technical vocabulary.",
    "category": "tone"
  },
  {
    "file": "00-framing.md",
    "anchor": "Episode format: in-depth walkthrough of a single ethical-practical",
    "severity": "P2",
    "problem": "The episode format is described but does not use one of the standard NotebookLM format declarations.",
    "fix": "Change the 'Episode format' line to 'Episode format: Deep Dive. An in-depth walkthrough of a single ethical-practical chapter.'",
    "category": "format"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "with the Qur'anic warrant of Q 4:69",
    "severity": "P2",
    "problem": "The Quran citation 'Q 4:69' does not use the required 'Q|Surah:Verse' format.",
    "fix": "Change the citation 'Q 4:69' to 'Q|4:69'.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The ethical-practical bridge of Kitab al-'Alim wa-l-Ghulam",
    "severity": "P2",
    "problem": "The show notes use italics for emphasis and titles, violating the prose-only articulation style.",
    "fix": "Remove all markdown italics from the show notes blurb.",
    "category": "articulation"
  }
]
```