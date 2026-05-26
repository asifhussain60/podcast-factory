## Inventory

-   **Chapter/Episode:** EP05: The Father Revealed and the Three Faces of Seeking
    -   `00-framing.md`: Present
    -   `01-primary-source.md`: **Missing**
    -   `02-key-passages.md`: Present, but empty template
    -   `03-context-pack.md`: Present, but empty template
    -   `04-discussion-spine.md`: Present, but empty template
    -   `99-show-notes.md`: Present, but serving as a malformed primary source

## Chapter Findings

### Chapter 5: The Father Revealed and the Three Faces of Seeking

*Note: The file `99-show-notes.md` is serving as a de-facto primary source and has been audited as such. This is a structural violation flagged as a P1 finding below.*

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `99-show-notes.md` | Entire file | The entire text is a single, unbroken paragraph, making it unreadable for the audio hosts and causing severe pacing and segmentation failures. | Restructure the content into a proper chapter format with headings for major narrative turns and break the text into paragraphs of no more than 200 words each. |
| P0 | `99-show-notes.md` | `Salih (SAA-lih)` | Inline parenthetical phonetic spellings will be read aloud literally by the audio hosts, creating broken speech. | Remove all inline parenthetical phonetic spellings (e.g., `(SAA-lih)`, `(al-bakh-tah-REE)`). Rely exclusively on the pronunciation guide in `00-framing.md`. |
| P1 | `99-show-notes.md` | Entire file | The bundle is missing a primary source file (`01-primary-source.md`), and this show notes file is being used as a dense, unformatted substitute. | Create a new file `01-primary-source.md`. Move the narrative content from this file into the new file after applying the formatting fixes. Rewrite this show notes file to be a concise, public-facing summary. |
| P1 | `99-show-notes.md` | `Salih`, `al-Bakhtari`, `taqiyya` | The text uses transliterated Arabic terms, violating the house style which requires Arabic script to avoid ambiguity and ensure correct host pronunciation. | Replace all transliterated Arabic names and terms with their Arabic script equivalents. Update the pronunciation guide in `00-framing.md` to map from the new Arabic script terms to their phonetic spellings. |
| P2 | `99-show-notes.md` | `*re-born*`, `*answer*`, `*seventh day*` | The use of italics for emphasis is a style violation and can introduce minor voice artifacts. | Remove all italic markdown (`*...*`) from the text. |
| P2 | `99-show-notes.md` | `Through them, God revived...` | The text uses 'God' instead of the required 'Allah', violating house style. | Replace all instances of 'God' with 'Allah'. |
| clean | `99-show-notes.md` | n/a | Cohesion | The narrative follows a clear arc despite the formatting issues. |
| clean | `99-show-notes.md` | n/a | Duplication | No significant intra-file duplication was found. |

## Episode Findings

### Episode 5: The Father Revealed and the Three Faces of Seeking

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `04-discussion-spine.md` | Entire file | The discussion spine is an empty template containing only `[LLM-FILL]` placeholders, which will cause the hosts to hallucinate a conversation structure. | Populate the discussion spine with the 6 distinct beats described in `00-framing.md` under 'Three-part focus'. For each beat, define the key question, central tension, and landing point. Remove the unused beats 7 and 8. |
| P0 | `02-key-passages.md` | Entire file | The key passages file is an empty template, depriving the hosts of specific text to ground their discussion. | Extract at least three key verbatim quotes from the narrative in `99-show-notes.md` to serve as anchor passages for the discussion spine. Populate this file with those passages. |
| P0 | `00-framing.md` | `the cause that connects heaven to earth...` | The recurring thesis sentence is present verbatim in this file and also in `99-show-notes.md`, creating a P0 risk of the hosts looping on the phrase. | Remove the verbatim sentence 'the cause that connects heaven to earth...' from `99-show-notes.md`. The framing document must be the sole source for this specific instruction. |
| P1 | `03-context-pack.md` | Entire file | The context pack is an empty template, increasing the risk of hosts hallucinating background information. | Populate the context pack with brief, factual details for 'Author / narrator', 'What this chapter is responding to', and 'Tradition / lineage' to ground the hosts. |
| P1 | `99-show-notes.md` | Entire file | The dense, summary tone of this file clashes with the instructional-but-casual tone required for source material, which will disrupt host pacing. | After moving the content to a new `01-primary-source.md` file, rewrite it as proper prose in the house style. |
| clean | `00-framing.md` | n/a | Host-role consistency, format declaration, length calibration, banter suppression, single-thesis discipline, cliffhanger handling. | All episode directives are clear, consistent, and well-defined. |

## Cross-Bundle Patterns

The primary issue is a structural failure: the bundle relies on empty templates (`discussion-spine.md`, `key-passages.md`, `context-pack.md`) and misuses the `show-notes.md` file as a single, massive, unformatted data dump instead of a proper `primary-source.md`. This makes the bundle unusable for NotebookLM as-is.

There is also a systemic violation of the articulation style for Arabic terms. The bundle uses transliteration with inline phonetic hints, whereas the house style requires Arabic script in the source prose and a separate pronunciation appendix mapping script-to-phonetics.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "99-show-notes.md",
    "anchor": "Entire file",
    "severity": "P0",
    "problem": "The entire text is a single, unbroken paragraph, which is unreadable by NotebookLM's audio hosts.",
    "fix": "Restructure the entire file into a proper chapter format with headings for major narrative turns (e.g., 'The Father's Anger', 'The Senior Scholar Arrives', 'The Debate', 'The Concession') and break the content into paragraphs of no more than 200 words each.",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Salih (SAA-lih), and his father's name was al-Bakhtari (al-bakh-tah-REE)",
    "severity": "P0",
    "problem": "Inline parenthetical phonetic spellings will be read aloud literally by the audio hosts, creating broken speech.",
    "fix": "Remove all inline parenthetical phonetic spellings such as `(SAA-lih)` and `(al-bakh-tah-REE)`. Rely exclusively on the pronunciation guide in `00-framing.md`.",
    "category": "notebooklm"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "Entire file",
    "severity": "P0",
    "problem": "The discussion spine is an empty template containing only `[LLM-FILL]` placeholders.",
    "fix": "Populate the discussion spine with 6 distinct beats as described in `00-framing.md` under 'Three-part focus'. For each beat, define the key question, the central tension, and the landing point. Remove the unused beats 7 and 8.",
    "category": "spine"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "Entire file",
    "severity": "P0",
    "problem": "The key passages file is an empty template, depriving the hosts of specific text to ground their discussion.",
    "fix": "Extract at least three key verbatim quotes from the narrative in `99-show-notes.md` to serve as anchor passages for the discussion spine and populate this file with them.",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "the cause that connects heaven to earth, unbroken",
    "severity": "P0",
    "problem": "The recurring thesis sentence is present verbatim in this file and also in `99-show-notes.md`, creating a high risk of audio looping.",
    "fix": "Search for the sentence 'the cause that connects heaven to earth, unbroken...' in `99-show-notes.md` and remove it. The framing document must be the sole source for this specific instruction.",
    "category": "duplication"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Title: The Father Revealed and the Three Faces of Seeking",
    "severity": "P1",
    "problem": "The bundle is missing a primary source file and this show notes file is being used as a dense, unformatted substitute.",
    "fix": "Create a new file `01-primary-source.md`. Move the narrative content from this file into the new file, applying all other formatting fixes to it. Then, rewrite this show notes file to be a concise, public-facing summary.",
    "category": "cohesion"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "Entire file",
    "severity": "P1",
    "problem": "The context pack is an empty template, increasing the risk of hosts hallucinating background information.",
    "fix": "Populate the context pack with brief, factual details for 'Author / narrator', 'What this chapter is responding to', and 'Tradition / lineage' to ground the hosts.",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Salih",
    "severity": "P1",
    "problem": "The text uses transliterated Arabic terms, violating the house style which requires Arabic script.",
    "fix": "Replace all transliterated Arabic names and terms with their Arabic script equivalents (e.g., 'Salih' -> 'صالح', 'taqiyya' -> 'تقية'). Update the pronunciation guide in `00-framing.md` to map from the new Arabic script terms to their phonetic spellings.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "*re-born*",
    "severity": "P2",
    "problem": "The use of italics for emphasis is a style violation.",
    "fix": "Remove all italic markdown (`*...*`) from the text.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Through them, God revived many of His creation",
    "severity": "P2",
    "problem": "The text uses 'God' instead of the required 'Allah', violating house style.",
    "fix": "Replace all instances of 'God' with 'Allah'.",
    "category": "articulation"
  }
]
```