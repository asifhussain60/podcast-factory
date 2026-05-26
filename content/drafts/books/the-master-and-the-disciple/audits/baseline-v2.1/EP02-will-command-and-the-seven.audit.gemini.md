## Inventory

-   **Chapter/Episode 1: The Architecture of Creation: Will, Command, and the Seven**
    -   `00-framing.md`: Present
    -   `01-primary-source.md`: **Missing**
    -   `02-key-passages.md`: Present (template only)
    -   `03-context-pack.md`: Present (template only)
    -   `04-discussion-spine.md`: Present (template only)
    -   `99-show-notes.md`: Present

## Chapter Findings

No primary source file (`01-primary-source.md`) was provided for audit. Chapter-level findings are based on the `99-show-notes.md` file, which summarizes the chapter content.

### Chapter 1: The Architecture of Creation: Will, Command, and the Seven

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P0 | `99-show-notes.md` | The cosmological foundation of *Kitab al-'Alim wa-l-Ghulam* | Articulation style violation: uses transliterated Arabic with diacritics instead of Arabic script or the English equivalents mandated by the framing. | Replace all transliterated Arabic terms (`Kitab al-'Alim wa-l-Ghulam`, `nāṭiqs`, `ḥujaj`, `nuqabā'`, `du'āt`, `zahir`, `batin`, `al-Imām al-Nāṭiq`, `bāb`, `waṣī`) with their English equivalents as defined in `00-framing.md`. |
| P1 | `99-show-notes.md` | proven from Q 7:26's three garments | Citation format does not follow the required `Q|S:V` standard. | Change `Q 7:26` to `Q|7:26` and ensure a spoken-form appendix is created for it. |
| P2 | `99-show-notes.md` | The cosmological foundation of *Kitab al-'Alim wa-l-Ghulam* | Articulation style violation: uses italics for a book title and for emphasis. | Remove all markdown italics from the file. |
| P2 | `99-show-notes.md` | The cosmological foundation of *Kitab al-'Alim wa-l-Ghulam* | The main blurb is a single, dense paragraph over 400 words, which is difficult for hosts to parse for audio. | Break the paragraph into 3-4 smaller paragraphs at logical topic shifts (e.g., after the seven principles, after the great parallel, after the verdict on the world). |

## Episode Findings

### Episode 1: The Architecture of Creation: Will, Command, and the Seven

| Severity | File | Anchor | Problem | Fix |
| :--- | :--- | :--- | :--- | :--- |
| P1 | (bundle-wide) | N/A | The primary source chapter text is missing from the bundle. | Add the missing `01-primary-source.md` file containing the full chapter text that this episode is based on. |
| P0 | `04-discussion-spine.md` | Beat 1: Opening hook | The discussion spine is an unfilled template, which will cause NotebookLM to generate a generic, unstructured conversation. | Populate all 6 beats of the discussion spine with key questions, tensions, and anchor passage references, matching the structure defined in `00-framing.md`. |
| P0 | `02-key-passages.md` | Passage 1 | The key passages file is an unfilled template, leaving the hosts with no verbatim quotes to retrieve. | Extract the verbatim quotes required by the framing (the three-words formula, the great parallel, the body-and-soul figure, the egg parable, etc.) into this file, one per passage. |
| P0 | `00-framing.md` | ## Pronunciation | The pronunciation guide is incomplete and contradicts the show notes, creating a high risk of mispronunciation. | Create a comprehensive pronunciation appendix mapping every Arabic term used in the show notes (e.g., `nāṭiqs`, `ḥujaj`) to a simple phonetic spelling, and update the show notes to use the English equivalents per the framing's own rules. |
| P1 | `03-context-pack.md` | Author / narrator | The context pack is an unfilled template, increasing the risk of host hallucination. | Populate the context pack with brief, non-airtime notes on the author, tradition, and context to ground the hosts. |
| P1 | `04-discussion-spine.md` | # Discussion spine | The spine template has 8 beats, but the framing document specifies a 6-beat structure, creating a structural conflict. | Reduce the discussion spine from 8 beats to the 6 beats described in `00-framing.md`. |
| P1 | `00-framing.md` | ## Pronunciation | No spoken-form appendix exists for Quran citations, which will cause citations like `Q|7:26` to be read literally. | Create a citation appendix mapping machine-readable citations (e.g., 'Q|7:26') to natural spoken forms (e.g., 'Quran, chapter seven, verse twenty-six') and reference it from the framing. |
| P2 | `00-framing.md` | Episode format: in-depth walkthrough | The episode format is described but not explicitly declared using a standard label. | Add a line to the framing: `**Format declaration:** Deep Dive`. |

## Cross-Bundle Patterns

The primary systemic issue is that this bundle is a "scaffold" or "template" rather than a complete, production-ready artifact. The high-level framing (`00-framing.md`) is detailed and well-constructed, but the core content files that drive the NotebookLM conversation—`01-primary-source.md` (missing), `02-key-passages.md`, `03-context-pack.md`, and `04-discussion-spine.md`—are either absent or empty templates. This guarantees a failed audio generation.

There is also a significant articulation style contradiction. The framing document correctly forbids transliterated Arabic, while the show notes file (`99-show-notes.md`) uses it extensively. This indicates a process gap where different components of the bundle were generated under conflicting rules.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "04-discussion-spine.md",
    "anchor": "Beat 1: Opening hook",
    "severity": "P0",
    "problem": "The discussion spine is an unfilled template.",
    "fix": "Populate all 6 beats of the discussion spine with key questions, tensions, and anchor passage references, matching the detailed structure defined in `00-framing.md`.",
    "category": "spine"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "Passage 1",
    "severity": "P0",
    "problem": "The key passages file is an unfilled template.",
    "fix": "Extract the verbatim quotes required by the framing (the three-words formula, the great parallel, the body-and-soul figure, the six-limits-and-a-seventh formula, the air-as-highest-proof line, and the parable of the egg) into this file, each under its own passage heading.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The cosmological foundation of *Kitab al-'Alim wa-l-Ghulam*",
    "severity": "P0",
    "problem": "The show notes use transliterated Arabic with diacritics, which violates articulation style and risks severe mispronunciation.",
    "fix": "Replace all transliterated Arabic terms (`Kitab al-'Alim wa-l-Ghulam`, `nāṭiqs`, `ḥujaj`, `nuqabā'`, `du'āt`, `zahir`, `batin`, `al-Imām al-Nāṭiq`, `bāb`, `waṣī`) with their English equivalents as defined in the `## Stable role-labels` section of `00-framing.md`.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P0",
    "problem": "The pronunciation guide is incomplete for terms used elsewhere in the bundle.",
    "fix": "Create a comprehensive pronunciation appendix mapping every Arabic term used in the source material to a simple phonetic spelling and reference this appendix from the framing document.",
    "category": "pronunciation"
  },
  {
    "file": "(bundle-wide)",
    "anchor": "N/A",
    "severity": "P1",
    "problem": "The primary source chapter text is missing from the bundle.",
    "fix": "Add the missing `01-primary-source.md` file containing the full chapter text that this episode is based on.",
    "category": "cohesion"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "Author / narrator",
    "severity": "P1",
    "problem": "The context pack is an unfilled template.",
    "fix": "Populate the context pack with brief, non-airtime notes on the author, tradition, and context to ground the hosts and prevent hallucination.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "# Discussion spine",
    "severity": "P1",
    "problem": "The spine template has 8 beats, but the framing document specifies a 6-beat structure.",
    "fix": "Reduce the discussion spine from 8 beats to the 6 beats described in `00-framing.md`.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "proven from Q 7:26's three garments",
    "severity": "P1",
    "problem": "Quran citation 'Q 7:26' does not follow the required 'Q|S:V' format.",
    "fix": "Change 'Q 7:26' to 'Q|7:26'.",
    "category": "citation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "No spoken-form appendix exists for Quran citations.",
    "fix": "Create a new section in the framing document titled 'Citation Spoken-Form Appendix' and add an entry mapping 'Q|7:26' to its natural spoken form: 'Quran, chapter seven, verse twenty-six'.",
    "category": "citation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Episode format: in-depth walkthrough of a single foundational chapter.",
    "severity": "P2",
    "problem": "The episode format is described but not explicitly declared using a standard label.",
    "fix": "Add a new line immediately after the 'Episode format' line: `**Format declaration:** Deep Dive`.",
    "category": "format"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The cosmological foundation of *Kitab al-'Alim wa-l-Ghulam*",
    "severity": "P2",
    "problem": "The show notes use markdown italics for a book title and for emphasis.",
    "fix": "Remove all markdown asterisks used for italics from the file.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "The cosmological foundation of *Kitab al-'Alim wa-l-Ghulam*",
    "severity": "P2",
    "problem": "The main blurb is a single, dense paragraph over 400 words.",
    "fix": "Break the paragraph into 3-4 smaller paragraphs at logical topic shifts.",
    "category": "notebooklm"
  }
]
```