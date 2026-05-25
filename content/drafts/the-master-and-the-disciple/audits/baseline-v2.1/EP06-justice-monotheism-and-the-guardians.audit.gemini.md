## Inventory

-   **Chapter/Episode 1:** `Justice, Monotheism, and the Guardians of Allah`
    -   **Bundle Artifacts Detected:**
        -   `00-framing.md` (present)
        -   `02-key-passages.md` (present, but empty template)
        -   `03-context-pack.md` (present, but empty template)
        -   `04-discussion-spine.md` (present, but empty template)
        -   `99-show-notes.md` (present, used as chapter content proxy)
    -   **Bundle Artifacts Missing:**
        -   `01-primary-source.md`

## Chapter Findings

### Chapter 6: Justice, Monotheism, and the Guardians of Allah

*Note: As no `primary-source.md` was provided, these findings are based on an audit of `99-show-notes.md` as the chapter content proxy.*

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `99-show-notes.md` | The book's doctrinal climax and final chapter. | Inline parenthetical phonetic guides (e.g., `(a-BOO MAA-lik)`) will be read aloud by the audio host, causing severe audio glitches. | Remove all inline parenthetical and slash-delimited phonetic guides from the prose. All pronunciation guidance must live exclusively in the framing file's pronunciation appendix. |
| P0 | `99-show-notes.md` | the *waṣī*, /waˈsˤiː/, the successor, bearer of | IPA-style phonetic guides (e.g., `/waˈsˤiː/`) are unreadable by the text-to-speech engine and will produce broken audio. | Remove all IPA-style phonetic guides. Use the simplified phonetic style from the framing file and place it in the pronunciation appendix. |
| P1 | `99-show-notes.md` | The book's doctrinal climax and final chapter. | The entire body of the show notes is a single, unbroken paragraph of over 800 words, which is too long for the audio hosts to parse effectively. | Break the single paragraph into multiple smaller paragraphs, each no more than 400 words, using thematic breaks in the narrative as segmentation points. |
| P1 | `99-show-notes.md` | The book's doctrinal climax and final chapter. | Arabic terms are transliterated (e.g., 'Sharia', 'Salih') instead of being written in Arabic script as required by the articulation style guide. | Replace all transliterated Arabic terms with their original Arabic script (e.g., 'Sharia' becomes 'شريعة'). Ensure each term is added to the pronunciation appendix in the framing file. |
| P2 | `99-show-notes.md` | The book's doctrinal climax and final chapter. | The text uses italics for emphasis (e.g., *zero point*), which violates the prose-only articulation style. | Remove all italic formatting from the text. Rephrase sentences for emphasis if necessary. |
| P2 | `99-show-notes.md` | The book's doctrinal climax and final chapter. | The tone is a dense, academic summary rather than the required "instructional-but-casual" style suitable for audio. | Rewrite the content to adopt a more conversational and instructional tone, as if explaining the concepts to a learner rather than summarizing for a peer. |
| clean | `99-show-notes.md` | n/a | Cohesion | clean |
| clean | `99-show-notes.md` | n/a | Duplication | clean |

## Episode Findings

### Episode 6: Justice, Monotheism, and the Guardians of Allah

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `02-key-passages.md` | `# Key passages` | The key passages file is an unfilled template containing only placeholders, leaving the hosts with no source material to quote. | Populate this file with verbatim quotes from the primary source that correspond to the beats in the discussion spine. |
| P0 | `03-context-pack.md` | `# Context pack` | The context pack file is an unfilled template, depriving the hosts of necessary background information. | Populate this file with the specified background context on the author, tradition, and related works to ground the hosts. |
| P0 | `04-discussion-spine.md` | `# Discussion spine` | The discussion spine is an unfilled template, providing no structure for the episode and no example of host role interaction. | Populate all beats with a key question, tension, and anchor passage reference, and add at least one example exchange demonstrating the host roles. |
| P1 | `00-framing.md` | `# Justice, Monotheism, and the Guardians of Allah` | The bundle is missing the primary source text artifact, relying only on a dense summary in the show notes. | Add a new file `01-primary-source.md` containing the full, clean prose of the chapter being discussed. |
| P1 | `04-discussion-spine.md` | `# Discussion spine` | The spine template has 8 beats, which contradicts the 6-beat arc detailed in `00-framing.md`. | Revise the spine to have exactly six beats matching the arc described in the framing file: crisis, first failed answer, second failed answer, pivot, non-bodily correction, human stakes. |
| P2 | `00-framing.md` | `## Pronunciation` | Pronunciation guides are inconsistent between files (e.g., `waṣī` is `wa-SEE` here but `/waˈsˤiː/` in show notes). | Consolidate all pronunciation guidance into this section, remove it from all other files, and ensure a single, consistent phonetic spelling for each term. |
| clean | `00-framing.md` | n/a | Host-role consistency | clean |
| clean | `00-framing.md` | n/a | Length calibration | clean |
| clean | `00-framing.md` | n/a | Format declaration | clean |
| clean | `00-framing.md` | n/a | Banter suppression | clean |
| clean | n/a | n/a | Source file count | clean |

## Cross-Bundle Patterns

Only one bundle was provided for audit. No cross-bundle patterns can be identified.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "02-key-passages.md",
    "anchor": "# Key passages",
    "severity": "P0",
    "problem": "The key passages file is an unfilled template containing only placeholders.",
    "fix": "Populate this file with verbatim quotes from the primary source that correspond to the beats in the discussion spine.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "# Context pack",
    "severity": "P0",
    "problem": "The context pack file is an unfilled template containing only placeholders.",
    "fix": "Populate this file with the specified background context on the author, tradition, and related works to ground the hosts.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "# Discussion spine",
    "severity": "P0",
    "problem": "The discussion spine is an unfilled template, providing no structure for the episode.",
    "fix": "Populate all beats with a key question, tension, and anchor passage reference, and add at least one example exchange demonstrating the host roles.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The book's doctrinal climax and final chapter.",
    "severity": "P0",
    "problem": "The show notes contain inline parenthetical phonetic spellings (e.g., `(a-BOO MAA-lik)`) which the audio host will read aloud literally.",
    "fix": "Remove all inline parenthetical and slash-delimited phonetic guides from the prose. All pronunciation guidance must live exclusively in the framing file's pronunciation appendix.",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "the *waṣī*, /waˈsˤiː/, the successor, bearer of",
    "severity": "P0",
    "problem": "The show notes contain IPA-style phonetic guides (e.g., `/waˈsˤiː/`) that are unreadable by the text-to-speech engine.",
    "fix": "Remove all IPA-style phonetic guides from the prose. Use the simplified phonetic style from the framing file and place it in the pronunciation appendix.",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "# Justice, Monotheism, and the Guardians of Allah",
    "severity": "P1",
    "problem": "The bundle is missing the primary source text artifact, relying only on a dense summary in the show notes.",
    "fix": "Add a new file `01-primary-source.md` containing the full, clean prose of the chapter being discussed.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "# Discussion spine",
    "severity": "P1",
    "problem": "The spine template has 8 beats, which contradicts the 6-beat arc detailed in `00-framing.md`.",
    "fix": "Revise the spine to have exactly six beats matching the arc described in the framing file: crisis, first failed answer, second failed answer, pivot, non-bodily correction, human stakes.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The book's doctrinal climax and final chapter.",
    "severity": "P1",
    "problem": "The entire body of the show notes is a single, unbroken paragraph of over 800 words, which is too long for the audio hosts to parse effectively.",
    "fix": "Break the single paragraph into multiple smaller paragraphs, each no more than 400 words, using thematic breaks in the narrative as segmentation points.",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The book's doctrinal climax and final chapter.",
    "severity": "P1",
    "problem": "Arabic terms are transliterated (e.g., 'Sharia', 'Salih') instead of being written in Arabic script as required by the articulation style guide.",
    "fix": "Replace all transliterated Arabic terms with their original Arabic script, e.g., 'Sharia' becomes 'شريعة'. Ensure each term is added to the pronunciation appendix in the framing file.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P2",
    "problem": "Pronunciation guides are inconsistent between files (e.g., `waṣī` is `wa-SEE` here but `/waˈsˤiː/` in show notes).",
    "fix": "Consolidate all pronunciation guidance into this section, remove it from all other files, and ensure a single, consistent phonetic spelling for each term.",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The book's doctrinal climax and final chapter.",
    "severity": "P2",
    "problem": "The text uses italics for emphasis (e.g., *zero point*), which violates the prose-only articulation style.",
    "fix": "Remove all italic formatting from the text. Rephrase sentences for emphasis if necessary.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The book's doctrinal climax and final chapter.",
    "severity": "P2",
    "problem": "The tone is a dense, academic summary rather than the required \"instructional-but-casual\" style suitable for audio.",
    "fix": "Rewrite the content to adopt a more conversational and instructional tone, as if explaining the concepts to a learner rather than summarizing for a peer.",
    "category": "tone"
  }
]
```