## Inventory

-   **Chapter/Episode:** EP01: The Master's Call and the Disciple's Covenant
    -   **Framing:** `00-framing.md` (present)
    -   **Primary Source:** (missing)
    -   **Key Passages:** `02-key-passages.md` (present, but empty template)
    -   **Context Pack:** `03-context-pack.md` (present, but empty template)
    -   **Discussion Spine:** `04-discussion-spine.md` (present, but empty template)
    -   **Show Notes:** `99-show-notes.md` (present)

## Chapter Findings

### Chapter 1: The Master's Call and the Disciple's Covenant

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | n/a | Manifest | The primary source text for the chapter is missing from the bundle. | Add the primary source file (e.g., `01-primary-source.md`) to the bundle and update the manifest. |
| P2 | `00-framing.md` | ## Host dynamic | The framing document uses bold markdown for emphasis on role-labels like **the Master**. | Remove all bold markdown formatting from the file; use plain text only. |
| P2 | `00-framing.md` | ## Audience | The text inconsistently uses 'God' and 'Allah'; house style requires 'Allah'. | Replace all instances of 'God' with 'Allah' (e.g., 'Party of Allah', 'Allah was waiting at the mirage'). |

## Episode Findings

### Episode 1: The Master's Call and the Disciple's Covenant

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `02-key-passages.md` | # Key passages | The key passages file is an empty template with `[LLM-FILL]` placeholders. | Populate the file with verbatim quotes from the primary source, one for each beat in the discussion spine. |
| P0 | `03-context-pack.md` | # Context pack | The context pack file is an empty template with `[LLM-FILL]` placeholders. | Populate the file with the required author, lineage, and background context to ground the hosts. |
| P0 | `04-discussion-spine.md` | # Discussion spine | The discussion spine is an empty template with `[LLM-FILL]` placeholders. | Populate all beats with a key question, tension, and anchor passage reference, following the 6-beat structure from `00-framing.md`. |
| P1 | `04-discussion-spine.md` | # Discussion spine | The spine template has 8 beats, but the framing document specifies a 6-beat structure. | Remove 'Beat 7' and 'Beat 8' sections and ensure the remaining six beats align with the narrative flow in `00-framing.md`. |
| P1 | `00-framing.md` | ## Length | The target length is 50-60 minutes, but the source volume cannot be verified as the primary source is missing. | This finding is blocked by the missing primary source. Once added, re-evaluate if the source text volume can support a 50-60 minute discussion. |
| P1 | `00-framing.md` | ## Pronunciation | Pronunciation guidance is embedded in the framing file, not in a separate, referenced appendix as required for the pipeline. | Create a separate `05-pronunciation-appendix.md` file with all required terms and replace the current `## Pronunciation` section with a reference to it. |
| P2 | `00-framing.md` | ## Pronunciation | No spoken-form appendix for Quran citations is present or referenced. | Add a directive to generate a `06-citation-spoken-form.md` file and reference it from the framing, to be used if the primary source contains Q\|S:V citations. |
| P2 | `99-show-notes.md` | ## Related episodes | The 'Related episodes' section uses a bulleted list, which can be read awkwardly by NotebookLM hosts. | Convert the bulleted list of related episodes into a single prose sentence, e.g., "Related episodes include 'will-command-and-the-seven', 'world-hereafter-and-the-right-of-wealth', and others." |

## Cross-Bundle Patterns

The bundle is critically incomplete. While the `00-framing.md` file provides an exceptionally detailed and well-structured plan, it is a plan for a house that has not been built. The primary source text is entirely missing, and the core content artifacts (`02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`) are empty templates. This indicates a systemic failure in the content generation stage of the pipeline; the template was scaffolded, but the content-fill step failed or was skipped. The bundle is non-functional in its current state.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "02-key-passages.md",
    "anchor": "# Key passages",
    "severity": "P0",
    "problem": "The key passages file is an empty template.",
    "fix": "Based on the 6-beat structure in `00-framing.md` and the (currently missing) primary source text, populate this file with at least six distinct, verbatim passages, each under a `### Passage N` heading.",
    "category": "notebooklm"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "# Context pack",
    "severity": "P0",
    "problem": "The context pack file is an empty template.",
    "fix": "Populate the 'Author / narrator', 'What this chapter is responding to', 'Tradition / lineage', and 'Related works' sections with concise, factual background information based on the source text's context.",
    "category": "notebooklm"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "# Discussion spine",
    "severity": "P0",
    "problem": "The discussion spine is an empty template.",
    "fix": "Populate all six beats of the discussion spine. For each beat, define the 'Key question', 'Tension', and 'Anchor passage' by referencing the corresponding passage number from `02-key-passages.md`.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 7: [LLM-FILL] Beat 7",
    "severity": "P1",
    "problem": "The discussion spine template contains 8 beats, but the episode framing specifies a 6-beat structure.",
    "fix": "Delete the entire sections for '### Beat 7' and '### Beat 8' from the file.",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "Pronunciation guidance is embedded directly in the framing file instead of being in a separate, required appendix.",
    "fix": "Replace the entire '## Pronunciation' section and its contents with a single line: 'See `05-pronunciation-appendix.md` for all pronunciation guidance.' The pipeline must then generate this file.",
    "category": "pronunciation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Host dynamic",
    "severity": "P2",
    "problem": "The file uses bold markdown for emphasis on role-labels, which violates the 'prose only' articulation style.",
    "fix": "Remove all double-asterisk (bold) markdown characters from the file. For example, change '**the Master**' to 'the Master'.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Audience",
    "severity": "P2",
    "problem": "The text uses 'God' in several places, which is inconsistent with the house style requirement to use 'Allah'.",
    "fix": "Perform a case-sensitive search and replace for the word 'God' and replace all instances with 'Allah'.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## Related episodes",
    "severity": "P2",
    "problem": "The 'Related episodes' section uses a bulleted list, which can cause awkward phrasing when read by the audio model.",
    "fix": "Rewrite the bulleted list under '## Related episodes' as a single prose sentence. For example: 'Related episodes include will-command-and-the-seven, world-hereafter-and-the-right-of-wealth, the-greater-shaykh-and-the-naming, father-revealed-and-the-faces-of-seeking, and justice-monotheism-and-the-guardians.'",
    "category": "notebooklm"
  }
]
```