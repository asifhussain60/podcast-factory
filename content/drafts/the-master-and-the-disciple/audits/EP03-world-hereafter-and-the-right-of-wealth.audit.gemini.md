## Inventory

-   **Chapter 3: World, Hereafter, and the Right of Wealth**
    -   `00-framing.md`: Present
    -   `01-source.md`: **Missing**
    -   `02-key-passages.md`: Present (empty template)
    -   `03-context-pack.md`: Present (empty template)
    -   `04-discussion-spine.md`: Present (empty template)
    -   `99-show-notes.md`: Present

## Chapter Findings

### Chapter 3: World, Hereafter, and the Right of Wealth

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `99-show-notes.md` | The ethical-practical bridge of *Kitab al-'Alim wa-l-Ghulam* | The prose contains numerous transliterated Arabic terms with diacritics (`nāṭiqs`, `hujja`, `ta'wīl`, `al-Khidr`, `awliyāʾ`, etc.) which violates the "Arabic script only" rule and will be mispronounced by TTS. | Replace all transliterated Arabic terms with their English equivalents as defined in `00-framing.md` under "Stable role-labels" and "Pronunciation". If an English equivalent is missing from the framing, add it there first. |
| P1 | `99-show-notes.md` | The ethical-practical bridge of *Kitab al-'Alim wa-l-Ghulam* | The entire blurb is a single, unbroken paragraph of over 500 words, which is unreadable for an audio host and risks TTS glitches. | Segment the paragraph into 5-7 smaller paragraphs, using the thematic shifts in the text (e.g., the pairs, the three houses, the rope, the two eyes, the question of passions, the five shares) as natural break points. |
| P1 | `99-show-notes.md` | *Kitab al-'Alim wa-l-Ghulam* (*The Book of the Master and the Boy*) | The text uses italics for book titles, which violates the "no italics" articulation style rule. | Remove all markdown italics. Per the framing document, wrap first mentions of book titles in quotes, e.g., `the book "The Master and the Disciple"`. |
| P1 | `99-show-notes.md` | ...with the Qur'anic warrant of Q 4:69 (*whoever obeys... | The Quran citation `Q 4:69` does not follow the required `Q|Surah:Verse` format and is not placed on a new line. | Reformat the citation to `Q|4:69` and place it on its own new line immediately following the quoted verse. |

## Episode Findings

### Episode 3: World, Hereafter, and the Right of Wealth

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `04-discussion-spine.md` | # Discussion spine | The discussion spine is an empty template containing only `[LLM-FILL]` placeholders. Without a spine, NotebookLM cannot generate a structured conversation. | Populate the discussion spine with 6 distinct beats as outlined in the `00-framing.md` file, including a key question, tension, and landing for each beat. |
| P0 | `02-key-passages.md` | # Key passages | The key passages file is an empty template containing only `[LLM-FILL]` placeholders. The hosts cannot quote source material that is not provided. | Populate this file with the verbatim quotes specified in the `00-framing.md` file's "Pronunciation" section under the "Quote verbatim for" list. |
| P0 | `03-context-pack.md` | # Context pack | The context pack is an empty template containing only `[LLM-FILL]` placeholders. The hosts lack necessary background for grounding, increasing hallucination risk. | Populate the context pack with the author, dates, tradition, and the core question the chapter is responding to, based on the "Background" section of `00-framing.md`. |
| P0 | `00-framing.md` | ## Pronunciation | The pronunciation guide is incomplete and contradicted by terms used in `99-show-notes.md`, creating a direct TTS failure risk. | Expand the pronunciation guide to include phonetic spellings for all required proper nouns. Ensure that `99-show-notes.md` is edited to use only English equivalents for concepts, removing the contradiction. |
| P1 | (Bundle-wide) | Manifest | The primary source file (`01-source.md`) is missing from the bundle. This is a required artifact. | Add the primary source text for the chapter to the bundle as `01-source.md`. |
| P1 | `00-framing.md` | (File-wide) | The bundle contains a Quran citation but lacks a spoken-form appendix for it, risking awkward TTS rendering of "Q pipe four colon sixty-nine". | Add a new section to `00-framing.md` titled "Citation Spoken Form" and add an entry mapping `Q|4:69` to "from the Quran, chapter four, verse sixty-nine". |

## Cross-Bundle Patterns

This audit covers a single bundle, but it exhibits a systemic pipeline failure: key artifacts (`02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`) were generated as empty templates rather than being populated with content derived from the framing document and source text. This suggests a failure in the generation step that needs to be addressed at the pipeline level.

Furthermore, there is a significant content drift between the strict articulation rules in `00-framing.md` (e.g., no transliteration) and the content of `99-show-notes.md` (which is filled with transliteration), indicating a lack of enforcement of the framing rules on downstream artifacts.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "04-discussion-spine.md",
    "anchor": "# Discussion spine",
    "severity": "P0",
    "problem": "The discussion spine is an empty template with '[LLM-FILL]' placeholders and is unusable.",
    "fix": "Delete the entire contents of the file. Populate the file with a complete 6-beat discussion spine based on the 'Three-part focus' section in '00-framing.md'. Each beat must have a key question, tension, and landing instruction.",
    "category": "spine"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "# Key passages",
    "severity": "P0",
    "problem": "The key passages file is an empty template with '[LLM-FILL]' placeholders.",
    "fix": "Delete the placeholder content. Populate this file with the verbatim quotes specified in the '00-framing.md' file's 'Pronunciation' section, under the list item beginning 'Quote verbatim for...'. Each quote should be a separate passage.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "# Context pack",
    "severity": "P0",
    "problem": "The context pack is an empty template with '[LLM-FILL]' placeholders.",
    "fix": "Delete the placeholder content. Populate the 'Author / narrator', 'What this chapter is responding to', and 'Tradition / lineage' sections using information from the 'Background' section of '00-framing.md'.",
    "category": "cohesion"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The ethical-practical bridge of *Kitab al-'Alim wa-l-Ghulam*",
    "severity": "P0",
    "problem": "The show notes contain numerous transliterated Arabic terms with diacritics (e.g., nāṭiqs, hujja, ta'wīl) that violate house style and will be mispronounced by TTS.",
    "fix": "Systematically replace every transliterated Arabic term with its corresponding English equivalent defined in '00-framing.md' under the 'Stable role-labels' section (e.g., replace 'nāṭiqs' with 'speaker-prophets', 'hujja' with 'argument', 'bāb' with 'door', 'ta'wīl' with 'inner interpretation', 'zakat' with 'purification-due').",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The ethical-practical bridge of *Kitab al-'Alim wa-l-Ghulam*",
    "severity": "P1",
    "problem": "The entire show notes blurb is a single, unbroken paragraph over 500 words long.",
    "fix": "Break the single paragraph into at least six smaller paragraphs. Use the thematic shifts corresponding to the six beats in '00-framing.md' as the paragraph breaks.",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "*Kitab al-'Alim wa-l-Ghulam*",
    "severity": "P1",
    "problem": "The text uses markdown italics for book titles, which violates the articulation style guide.",
    "fix": "Remove all instances of markdown italics (asterisks). For the first mention of a book title, enclose it in double quotes as per the 'Stable role-labels' section of '00-framing.md'.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "...with the Qur'anic warrant of Q 4:69",
    "severity": "P1",
    "problem": "The Quran citation 'Q 4:69' is not in the required 'Q|S:V' format and is not on its own line.",
    "fix": "Change the citation from 'Q 4:69' to 'Q|4:69' and move it to its own new line immediately after the verse it cites.",
    "category": "citation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Landing",
    "severity": "P1",
    "problem": "The bundle contains a Quran citation but lacks a required spoken-form appendix for TTS.",
    "fix": "Before the '## Do not (forbidden vocabulary and framings)' section, add a new section: '## Citation Spoken Form'. Under this new heading, add the mapping: 'Q|4:69 → from the Quran, chapter four, verse sixty-nine'.",
    "category": "citation"
  }
]
```