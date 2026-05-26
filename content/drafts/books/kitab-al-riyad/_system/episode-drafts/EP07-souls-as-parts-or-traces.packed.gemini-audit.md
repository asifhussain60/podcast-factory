## Inventory

-   **EP07-souls-as-parts-or-traces**
    -   **Files Found:** `00-framing.md`
    -   **Artifacts Missing:** `primary-source.md`, `key-passages.md`, `context-pack.md`, `discussion-spine.md`, `show-notes.md`. The absence of the primary source material makes a full audit of content cohesion, duplication, and NotebookLM readability impossible.

## Chapter Findings

### Chapter: Souls As Parts Or Traces

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P1 | n/a | n/a | The primary source file for the chapter is missing from the bundle. | Add the chapter's primary source text to the bundle as `primary-source.md`. |

## Episode Findings

### Episode: Souls As Parts Or Traces

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `00-framing.md` | `## Stable role-labels` | Host roles are assigned as Advocate A/B, which deviates from the required male=scholar/teacher and female=student/learner dynamic. | Rewrite the 'Stable role-labels' and 'Host dynamic' sections to assign the male host the scholar/teacher role and the female host the student/learner role. |
| P0 | `00-framing.md` | `## Host dynamic` | The first paragraph is a verbatim duplicate of the last paragraph of the preceding 'Stable role-labels' section. | Delete the duplicated first paragraph under 'Host dynamic'. |
| P0 | `00-framing.md` | `eceivership. The soul's continuity with what stands above` | The final paragraph "Do not read this prompt aloud..." is duplicated at the very end of the file. | Delete the final, duplicated instance of the "Do not read this prompt aloud..." paragraph. |
| P1 | `00-framing.md` | `## Opening directive` | The framing is missing the required instruction for the hosts to 'skip the intro'. | Add a new H2 section titled '## Host Instructions' after the 'Opening directive' and add the bullet point: '- Skip the intro. Begin directly with the opening hook.' |
| P1 | `00-framing.md` | `## Opening directive` | The framing does not state a target episode length or explicitly declare the episode format. | Add a new H2 section titled '## Format and Length' after the 'Opening directive' and add the lines: 'Format: Debate' and 'Target length: 12-15 minutes'. |
| P1 | `00-framing.md` | `## Pronunciation` | The document uses transliterated Arabic terms (e.g., 'walaya', 'sharia'), which violates the 'Arabic script only' house style. | Replace all transliterated Arabic terms with their Arabic script equivalents and update the pronunciation guide to map from script to phonetics. |
| P1 | `00-framing.md` | `eceivership. The soul's continuity with what stands above` | The file ends with a truncated, malformed paragraph that starts mid-sentence. | Delete the entire malformed paragraph beginning with 'eceivership.'. |
| P2 | `00-framing.md` | `## Stable role-labels` | The document uses bolding and bulleted lists, which deviates from the 'prose only' house style. | Convert the bulleted list under 'Stable role-labels' to simple prose paragraphs and remove all bold markdown. |

## Cross-Bundle Patterns

The most significant issue is the bundle's incompleteness. It contains only a framing document, omitting the primary source text, key passages, and other essential artifacts. This prevents a comprehensive audit and guarantees failure in the production pipeline. The framing document itself, while detailed, contains several P0-level structural errors like verbatim duplication and deviation from core host role requirements, suggesting a need to review the template or generation process that produced it.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "00-framing.md",
    "anchor": "## Stable role-labels",
    "severity": "P0",
    "problem": "Host roles are assigned as Advocate A/B, which deviates from the required male=scholar/teacher and female=student/learner dynamic.",
    "fix": "Rewrite the 'Stable role-labels' and 'Host dynamic' sections to assign the male host the scholar/teacher role and the female host the student/learner role, seeding the pattern with an example exchange.",
    "category": "host-role"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Host dynamic",
    "severity": "P0",
    "problem": "The 'Host dynamic' section begins with a paragraph that is a verbatim duplicate of the last paragraph of the 'Stable role-labels' section.",
    "fix": "Delete the first paragraph of the 'Host dynamic' section, which reads: 'The female host is Advocate A (protagonist + verdict). The male host is Advocate B (challenger). Roles are locked at episode start; no swap mid-episode.'",
    "category": "duplication"
  },
  {
    "file": "00-framing.md",
    "anchor": "eceivership. The soul's continuity with what stands above",
    "severity": "P0",
    "problem": "The final paragraph 'Do not read this prompt aloud...' is duplicated at the end of the file.",
    "fix": "Delete the final duplicated paragraph that begins with 'Do not read this prompt aloud...' and follows the malformed 'eceivership...' paragraph.",
    "category": "duplication"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Opening directive",
    "severity": "P1",
    "problem": "The framing is missing the required instruction for the hosts to 'skip the intro'.",
    "fix": "Add a new H2 section titled '## Host Instructions' after the 'Opening directive' and add the bullet point: '- Skip the intro. Begin directly with the opening hook.'",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Opening directive",
    "severity": "P1",
    "problem": "The framing is missing the required target episode length and an explicit format declaration.",
    "fix": "Add a new H2 section titled '## Format and Length' after the 'Opening directive' and add the lines: 'Format: Debate' and 'Target length: 12-15 minutes'.",
    "category": "length"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "The document uses transliterated Arabic terms (e.g., 'walaya', 'sharia') which violates the 'Arabic script only' house style.",
    "fix": "Replace all transliterated Arabic terms throughout the document with their Arabic script equivalents. For example, change 'walaya' to 'ولاية', 'sharia' to 'شريعة', etc. Update the pronunciation guide to map from the Arabic script to the phonetic spelling.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "eceivership. The soul's continuity with what stands above",
    "severity": "P1",
    "problem": "The file ends with a truncated, malformed paragraph that starts mid-sentence with 'eceivership.'.",
    "fix": "Delete the entire malformed paragraph beginning with 'eceivership.' and ending with '...where bodies cannot reach.'",
    "category": "cohesion"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Stable role-labels",
    "severity": "P2",
    "problem": "The document uses bolding and bulleted lists, which deviates from the 'prose only' house style.",
    "fix": "Convert the bulleted list under 'Stable role-labels' to simple prose paragraphs, one for each figure, and remove all bold markdown.",
    "category": "articulation"
  }
]
```