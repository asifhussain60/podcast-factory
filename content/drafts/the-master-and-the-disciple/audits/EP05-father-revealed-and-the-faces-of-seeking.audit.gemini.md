## Inventory

A single podcast bundle for one episode, "The Father Revealed and the Three Faces of Seeking," was detected.

*   **Chapter/Episode:** EP05-father-revealed-and-the-faces-of-seeking
    *   `00-framing.md`: Present and detailed.
    *   `01-primary-source.md`: **Missing.**
    *   `02-key-passages.md`: Present, but an empty template.
    *   `03-context-pack.md`: Present, but an empty template.
    *   `04-discussion-spine.md`: Present, but an empty template.
    *   `99-show-notes.md`: Present, but formatted as a single dense paragraph unsuitable for audio synthesis.

## Chapter Findings

This audit treats `99-show-notes.md` as the de-facto primary source prose for the chapter, as `01-primary-source.md` is missing.

### Chapter 5: The Father Revealed and the Three Faces of Seeking

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `99-show-notes.md` | (Entire file) | The entire text is a single, unbroken paragraph, which is unreadable for audio synthesis and will cause host pacing failures. | Restructure the entire file into short, distinct paragraphs with clear headings for each major narrative turn (e.g., The Father's Anger, The Debate, The Senior Scholar Arrives, etc.). |
| P0 | `99-show-notes.md` | `the boy's name was Salih (SAA-lih), and his father's name was al-Bakhtari (al-bakh-tah-REE)` | The file contains numerous inline parenthetical phonetic guides which will be read aloud literally by the TTS engine, creating broken audio. | Remove all inline parenthetical phonetic guides (e.g., `(SAA-lih)`, `(al-bakh-tah-REE)`) from this file. Add all unique terms to the pronunciation appendix in `00-framing.md` instead. |
| P1 | `99-show-notes.md` | `The boy — *re-born* into the chain on the *seventh day*` | The text uses italics for emphasis, which violates the 'prose only' articulation style and can be ignored or cause stumbles in audio synthesis. | Remove all instances of italics from the text. If emphasis is required, rephrase the sentence to create it naturally. |
| P1 | `99-show-notes.md` | `The boy's name was Salih` | The text uses transliterated Arabic names and terms, violating the house style which requires Arabic script only. | Replace all transliterated Arabic terms and names with their original Arabic script equivalents. For example, replace 'Salih' with 'صالح'. |
| P2 | `99-show-notes.md` | `Through them, God revived many of His creation` | The text uses 'God', which is inconsistent with the house style rule to use 'Allah'. | Replace all instances of 'God' with 'Allah' to maintain consistency. |

## Episode Findings

### Episode 5: The Father Revealed and the Three Faces of Seeking

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `04-discussion-spine.md` | `### Beat 1: Opening hook` | The discussion spine is an empty template with `[LLM-FILL]` placeholders. The episode cannot be generated without a populated spine. | Populate all beats of the discussion spine with key questions, tensions, and anchor passage references, following the six-beat structure outlined in `00-framing.md`. |
| P0 | `02-key-passages.md` | `# Key passages` | The key passages file is an empty template. The framing calls for verbatim quotes, but they are not provided in this structured file for retrieval. | Populate this file with the verbatim quotes stipulated in the `00-framing.md` file under the 'Anti-noise rules' section (e.g., the father's reproach, the divorce-oath ruling, etc.). |
| P0 | `03-context-pack.md` | `# Context pack` | The context pack is an empty template with `[LLM-FILL]` placeholders. | Populate the context pack with the author, dates, tradition, and the argument the chapter is responding to, based on the information in `00-framing.md` and `99-show-notes.md`. |
| P0 | `00-framing.md` | `## Pronunciation` | The pronunciation appendix is missing many proper names and terms used in the `99-show-notes.md` file (e.g., Salih, al-Bakhtari, Abu Malik, Ka'b al-Ahbar, Maqrub). | Add all proper names and technical terms from `99-show-notes.md` to this pronunciation list with their correct phonetic spellings. |
| P1 | `00-framing.md` | `## Manifest` | The bundle is missing the `01-primary-source.md` file, a standard and necessary artifact for grounding the conversation. | Create a new file named `01-primary-source.md` and populate it with the clean, segmented prose of the chapter, using the content from `99-show-notes.md` as a base after it has been reformatted. |
| P1 | `00-framing.md` | `Pronounce "Sharia" as "sha-REE-ah".` | The pronunciation guide is based on transliterated terms, but the house style requires Arabic script in the main prose. The guide should map from Arabic script to phonetics. | Change the pronunciation guide to map from Arabic script to phonetic spelling. For example, change `"Sharia" as "sha-REE-ah"` to `"شريعة" → "sha-REE-ah"` and ensure source files use the Arabic script. |

## Cross-Bundle Patterns

Only one bundle was provided; no cross-bundle patterns can be assessed.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "The discussion spine is an empty template with `[LLM-FILL]` placeholders.",
    "fix": "Populate all beats of the discussion spine with key questions, tensions, and anchor passage references, following the six-beat structure outlined in `00-framing.md`.",
    "category": "spine"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "# Key passages",
    "severity": "P0",
    "problem": "The key passages file is an empty template.",
    "fix": "Populate this file with the verbatim quotes stipulated in the `00-framing.md` file under the 'Anti-noise rules' section, such as the father's reproach, the divorce-oath ruling, and the senior scholar's confession.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "# Context pack",
    "severity": "P0",
    "problem": "The context pack is an empty template with `[LLM-FILL]` placeholders.",
    "fix": "Populate the context pack with the author, dates, tradition, and the argument the chapter is responding to, based on the information in `00-framing.md` and `99-show-notes.md`.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "# Show notes — EP05",
    "severity": "P0",
    "problem": "The entire file is a single, unbroken paragraph, which is unreadable for audio synthesis and will cause pacing failures.",
    "fix": "Restructure the entire file into short, distinct paragraphs, with clear headings for each major narrative turn (e.g., The Father's Anger, The Debate, The Senior Scholar Arrives, etc.).",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "the boy's name was Salih (SAA-lih), and his father's name was al-Bakhtari (al-bakh-tah-REE)",
    "severity": "P0",
    "problem": "The file contains numerous inline parenthetical phonetic guides which will be read aloud literally by the TTS engine, creating broken audio.",
    "fix": "Remove all inline parenthetical phonetic guides (e.g., `(SAA-lih)`, `(al-bakh-tah-REE)`, `(a-BOO MAA-lik)`) from this file. Add all unique terms to the pronunciation appendix in `00-framing.md` instead.",
    "category": "pronunciation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P0",
    "problem": "The pronunciation appendix is missing many proper names and terms used in the `99-show-notes.md` file (e.g., Salih, al-Bakhtari, Abu Malik, Ka'b al-Ahbar, Maqrub).",
    "fix": "Add all proper names and technical terms from `99-show-notes.md` to this pronunciation list with their correct phonetic spellings.",
    "category": "pronunciation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Manifest",
    "severity": "P1",
    "problem": "The bundle is missing the `01-primary-source.md` file, a standard and necessary artifact for grounding the conversation.",
    "fix": "Create a new file named `01-primary-source.md`. Populate it with the clean, segmented prose of the chapter, using the content from `99-show-notes.md` as a base after it has been reformatted into proper paragraphs and all other fixes have been applied to it.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The boy — *re-born* into the chain on the *seventh day*",
    "severity": "P1",
    "problem": "The text uses italics for emphasis, which violates the 'prose only' articulation style and can be ignored or cause stumbles in audio synthesis.",
    "fix": "Remove all instances of italics from the text. If emphasis is required, rephrase the sentence to create it naturally.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Pronounce \"Sharia\" as \"sha-REE-ah\".",
    "severity": "P1",
    "problem": "The pronunciation guide is based on transliterated terms, but the house style requires Arabic script in the main prose. The guide should map from Arabic script to phonetics.",
    "fix": "Change the pronunciation guide to map from Arabic script to phonetic spelling. For example, change `Pronounce \"Sharia\" as \"sha-REE-ah\"` to `شريعة → \"sha-REE-ah\"`. Ensure source files are updated to use the Arabic script.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The boy's name was Salih",
    "severity": "P1",
    "problem": "The text uses transliterated Arabic names and terms, violating the house style which requires Arabic script only.",
    "fix": "Replace all transliterated Arabic terms and names with their original Arabic script equivalents. For example, replace 'Salih' with 'صالح'.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Through them, God revived many of His creation",
    "severity": "P2",
    "problem": "The text uses 'God', which is inconsistent with the house style rule to use 'Allah'.",
    "fix": "Replace all instances of 'God' with 'Allah' to maintain consistency.",
    "category": "articulation"
  }
]
```