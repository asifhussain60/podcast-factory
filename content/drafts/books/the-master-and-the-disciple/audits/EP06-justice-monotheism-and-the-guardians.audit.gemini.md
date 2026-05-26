## Inventory

One podcast bundle, "EP06-justice-monotheism-and-the-guardians", was detected.

-   **Chapter/Episode:** Justice, Monotheism, and the Guardians of Allah
    -   `00-framing.md`: **Present**
    -   `01-source.md`: **Missing**
    -   `02-key-passages.md`: **Present (but empty template)**
    -   `03-context-pack.md`: **Present (but empty template)**
    -   `04-discussion-spine.md`: **Present (but empty template)**
    -   `99-show-notes.md`: **Present**

## Chapter Findings

The file `99-show-notes.md` is treated as the de-facto chapter source due to the absence of `01-source.md`.

### Chapter: Justice, Monotheism, and the Guardians of Allah

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `99-show-notes.md` | (Entire file) | The entire text is a single, unbroken paragraph, which is unreadable for audio hosts and will cause pacing failure. | Segment the text into multiple paragraphs with markdown headings that align with the six-beat structure from `00-framing.md`. |
| P0 | `99-show-notes.md` | `Abu Malik (a-BOO MAA-lik)` | Phonetic pronunciations are included inline in parentheses, which will be read aloud literally and cause voice glitches. | Remove all inline parenthetical phonetic spellings. The pronunciation guide in `00-framing.md` is the single source of truth. |
| P0 | `99-show-notes.md` | `had you supported the friends of Allah...` | The recurring thesis is present verbatim, creating a duplication risk with `00-framing.md` that will cause host looping. | Remove the verbatim sentence from this file. The framing document already instructs Host A to speak it three times. |
| P1 | `99-show-notes.md` | `Sharia (sha-REE-ah)` | Arabic terms are transliterated, violating the house style which requires Arabic script. | Replace all transliterated Arabic terms with their original Arabic script. The pronunciation guide in `00-framing.md` must then be updated to map from script to phonetics. |
| P1 | `99-show-notes.md` | `*zero point*` | Italics are used for emphasis, which violates the plain-prose articulation style. | Remove all markdown italics. Rephrase for emphasis if necessary. |
| P1 | `99-show-notes.md` | (Entire file) | The tone is a dense academic summary, not the required instructional-but-casual prose for hosts to read. | Rewrite the content as direct, instructional prose suitable for being spoken aloud, following the segmentation fix above. |

## Episode Findings

### Episode: Justice, Monotheism, and the Guardians of Allah

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `04-discussion-spine.md` | (Entire file) | The file is an empty template containing only `[LLM-FILL]` placeholders, making episode generation impossible. | Populate all beats of the discussion spine based on the six-beat structure defined in `00-framing.md`. |
| P0 | `02-key-passages.md` | (Entire file) | The file is an empty template, preventing hosts from quoting required passages and risking hallucination. | Extract all verbatim quotes stipulated in `00-framing.md` from the primary source and add them as numbered passages. |
| P0 | `03-context-pack.md` | (Entire file) | The file is an empty template, leaving hosts without necessary background context and increasing hallucination risk. | Populate the 'Author / narrator', 'What this chapter is responding to', and 'Tradition / lineage' sections. |
| P1 | (Bundle-wide) | (Manifest) | The primary source file (`01-source.md`) is missing from the bundle, leaving the episode ungrounded. | Add the primary source text for this chapter to the bundle as `01-source.md`. |
| clean | `00-framing.md` | (Entire file) | Host roles, format, length, tone, and anti-patterns are exceptionally well-defined. | No action needed. |

## Cross-Bundle Patterns

The single bundle exhibits a systemic failure pattern: an exceptionally detailed and well-architected `00-framing.md` document is paired with completely empty, non-functional support files (`02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`). The bundle is a blueprint for an episode, not an executable set of artifacts. Furthermore, the primary source text is missing entirely, and the `99-show-notes.md` file, which serves as a poor substitute, violates multiple critical rules for NotebookLM audio-readability (single paragraph, inline phonetics, prohibited formatting).

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "04-discussion-spine.md",
    "anchor": "(Entire file)",
    "severity": "P0",
    "problem": "File is an empty template with '[LLM-FILL]' placeholders.",
    "fix": "Populate all beats of the discussion spine based on the six-beat structure defined in '00-framing.md', ensuring each beat has a key question, tension, and anchor passage reference.",
    "category": "spine"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "(Entire file)",
    "severity": "P0",
    "problem": "File is an empty template, preventing hosts from quoting required passages.",
    "fix": "Extract all verbatim quotes stipulated in '00-framing.md' (e.g., the fire-is-hot figure, the four-nations indictment) from the primary source and add them to this file as numbered passages.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "(Entire file)",
    "severity": "P0",
    "problem": "File is an empty template, leaving hosts without necessary background context.",
    "fix": "Populate the 'Author / narrator', 'What this chapter is responding to', and 'Tradition / lineage' sections with concise, factual background information to ground the hosts.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "(Entire file)",
    "severity": "P0",
    "problem": "The entire text is a single, unbroken paragraph over 400 words.",
    "fix": "Segment the text into multiple paragraphs with markdown headings that align with the six-beat structure from '00-framing.md' to improve readability for the hosts.",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Abu Malik (a-BOO MAA-lik)",
    "severity": "P0",
    "problem": "Phonetic pronunciations are included inline in parentheses, which will cause voice glitches.",
    "fix": "Remove all inline parenthetical phonetic spellings. The pronunciation guide in '00-framing.md' is the single source of truth for pronunciation.",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "had you supported the friends of Allah, they would have appeared; had you failed His enemies, they would not have prevailed.",
    "severity": "P0",
    "problem": "The recurring thesis is present verbatim, creating a duplication risk with '00-framing.md' that will cause host looping.",
    "fix": "Remove the verbatim sentence 'had you supported the friends of Allah, they would have appeared; had you failed His enemies, they would not have prevailed' from this file. The framing document already instructs Host A to speak it three times.",
    "category": "duplication"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Manifest",
    "severity": "P1",
    "problem": "A primary source file (e.g., '01-source.md') is missing from the bundle.",
    "fix": "Add the primary source text for this chapter to the bundle as '01-source.md'. This is required for grounding all other artifacts.",
    "category": "cohesion"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Sharia (sha-REE-ah)",
    "severity": "P1",
    "problem": "Arabic terms are transliterated instead of using Arabic script as required by the articulation style guide.",
    "fix": "Replace all transliterated Arabic terms (e.g., 'Sharia', 'Salih', 'ta'wil') with their original Arabic script. The pronunciation guide in '00-framing.md' must then be updated to map from script to phonetics.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "*zero point*",
    "severity": "P1",
    "problem": "Italics are used for emphasis, which violates the articulation style.",
    "fix": "Remove all markdown italics (e.g., '*zero point*', '*Sharia*'). Rephrase for emphasis if necessary.",
    "category": "articulation"
  }
]
```