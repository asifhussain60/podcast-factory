## At a glance — 🔴 bundle blocked from NotebookLM upload

1. Three of five bundle files — [02-key-passages.md](02-key-passages.md), [03-context-pack.md](03-context-pack.md), [04-discussion-spine.md](04-discussion-spine.md) — are unfilled LLM scaffold; NotebookLM has no source or spine to work with.
2. No primary chapter file exists in the bundle even though [00-framing.md](00-framing.md) presupposes one ("the chapter file is the entire source NotebookLM sees").
3. Beat-count contradiction: framing prescribes six beats; spine template has eight slots.
4. [99-show-notes.md](99-show-notes.md) is a single ~1,500-word paragraph saturated with italicized inline phonetic transliterations — audio-toxic if NotebookLM ingests it.
5. Host-role assignment in framing aligns with the rule (male=teacher, female=student-by-concession) but is not seeded in the empty spine.

---

## Inventory

- **Chapter / Episode EP06 — Justice, Monotheism, and the Guardians of Allah**
  - framing: [00-framing.md](00-framing.md) — present (21,389 B, complete)
  - primary source: **missing** (no chapter prose file in bundle)
  - key passages: [02-key-passages.md](02-key-passages.md) — present but empty (one `>` blockquote stub + `[LLM-FILL]`)
  - context pack: [03-context-pack.md](03-context-pack.md) — present but empty (all sections `[LLM-FILL]`)
  - discussion spine: [04-discussion-spine.md](04-discussion-spine.md) — present but empty (all 8 beats `[LLM-FILL]`)
  - show notes: [99-show-notes.md](99-show-notes.md) — present (~1,500-word mono-paragraph)

## Chapter Findings

### Chapter EP06: Justice, Monotheism, and the Guardians of Allah

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | 00-framing.md | Anti-noise rules ("the chapter file is the entire source") | The framing tells hosts the chapter file is the only source NotebookLM will see, but no chapter prose file exists in the bundle. NotebookLM will hallucinate or default to whatever it can scrape from show notes. | Add a `01-source.md` containing the verbatim Arabic-translated chapter prose, including the fire-is-hot figure, four-letters exchange, four-nations indictment, prophets count, *Moses fleeing Pharaoh* paradigm, recurring thesis verbatim, jurists-and-tyrants indictment, and closing doxology. |
| P0 | 99-show-notes.md | "Blurb:" | Show notes is one unbroken ~1,500-word paragraph; if NotebookLM falls back to it as source, hosts cannot segment for breath and will collapse into summary. | Split into prose paragraphs of 80–150 words each, breaking at the doctrinal turns the framing already names (fire-is-hot, four-letters, four-nations, three qualities, prophets count, *Moses fleeing*, jurists-indictment, repentance, doxology). |
| P0 | 99-show-notes.md | "Abu Malik (a-BOO MAA-lik)" / "*Taqiyya* (ta-KEE-yah, …)" | Inline phonetic transliterations (e.g., "ta-KEE-yah", "moo-haa-jih-ROON", "shoo-AYB") are sprinkled through the prose. If this file is ingested as source, NotebookLM will voice the phonetic guides literally. | Strip every inline phonetic gloss from the prose. Keep pronunciation in the framing's dedicated `## Pronunciation` appendix only. Arabic terms that survive in the prose should appear in Arabic script with English in apposition where needed, e.g., *protective concealment (تقية)*. |
| P1 | 99-show-notes.md | "Blurb:" | Show notes uses italicized terms (*Sharia*, *Taqiyya*, *waṣī*, *ḥawl*) extensively; the house-style rule bans italics. | Remove all italics. Where emphasis was structural (chapter quotes), restate as a quoted phrase introduced by attribution; where italics marked Arabic, use Arabic script in parentheses after an English gloss. |
| P1 | 99-show-notes.md | "Chapter five ended on Abu Malik" / "Related episodes" | The show notes recaps chapter five extensively and lists five sibling chapters — both contradict the framing's `R-NOBACKGROUND` and self-contained-episode rule. | Cut the chapter-five recap. Replace the opening sentence with a single line of in-chapter framing ("This is the chapter answering the seam-question from the previous turn"). Remove or hide the "Related episodes" list from the source NotebookLM ingests. |
| P1 | 99-show-notes.md | "Abu Malik" / "Salih" / "Al-Bakhtari" | Personal Arabic names of figures appear repeatedly even though the framing's `## Stable role-labels` directive forbids voicing them and assigns English-only labels. If this is the source, NotebookLM will voice the Arabic names. | Replace every "Abu Malik" with "the senior scholar"; every "Salih" with "the young teacher"; every "Al-Bakhtari" with "the scholar-father", using the exact stable labels listed in framing. |
| P1 | 00-framing.md | "Use 'Maulana Ali' instead of 'Imam Ali'" (house style) vs framing's "Commander of the Faithful" | The framing's doctrinal discipline (forbid pairing the leadership-title with the personal name of the Father of Imams) is correct for this chapter but diverges from the global house rule that prescribes "Maulana Ali". Note for downstream consistency. | Leave the framing as-is for EP06 — the chapter's own naming-by-attribute discipline supersedes here. Add a one-line comment in framing's `## Name discipline` block citing the chapter-internal reason, so downstream auditors do not re-flag. |
| P2 | 99-show-notes.md | "**Length estimate:** see contract.length_target (extended)" | Length-target placeholder is not a concrete minute count. Listeners and pipeline tooling cannot parse "extended". | Replace with explicit "50–60 minutes" to match framing's `## Length`. |

## Episode Findings

### Episode EP06: Justice, Monotheism, and the Guardians of Allah

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | 04-discussion-spine.md | Beat 1 through Beat 8 | The entire spine is `[LLM-FILL]`. No hidden steering layer exists. NotebookLM has no beat anchors, no key-question per beat, no passage references. | Fill every beat with key-question, tension, anchor-passage reference, and landing. Either match the framing's six-beat plan (recommended) by deleting Beats 7 and 8, or revise framing to align with the eight-beat template. |
| P0 | 04-discussion-spine.md | "8 beats" header | Spine template prescribes 8 beats; framing's `## Three-part focus` prescribes 6 beats with exact ordering. NotebookLM receives contradictory architecture. | Reduce spine to six beats matching framing's Beat 1–6 names (crisis / first failed answer / second failed answer / pivot / non-bodily correction / human stakes). Update the file's intro from "8 beats" to "6 beats". |
| P0 | 02-key-passages.md | "Passage 1" | Key passages file contains only a `>` blockquote stub and `[LLM-FILL]`. The framing stipulates verbatim quotation of nine specific passages; none of them are retrievable here. | Populate with the nine framing-stipulated verbatim passages: fire-is-hot figure, four-letters exchange, *causes between Him and His creation* derivation, four-nations indictment, the *three qualities*, the prophets count, *Moses fleeing Pharaoh*, *they show mercy to the slain*, *were it not for the narrations of the jurists*, plus the recurring thesis and the closing doxology. Each as a separate numbered passage with a one-line *Why this matters*. |
| P0 | 04-discussion-spine.md | Beat 1 — "Opening hook" | Framing assigns Host A (male) = young teacher and Host B (female) = senior scholar; the spine must seed this with at least one example exchange so NotebookLM locks the roles. Empty spine = no seed = role drift risk. | In Beat 1's landing, write one explicit exchange that voices Host A naming the recurring thesis and Host B opening the proposition-under-debate; tag the speakers `Host A (male)` and `Host B (female)` inline. |
| P1 | 03-context-pack.md | "Author / narrator" through "Why this lands now" | Context pack is all `[LLM-FILL]`. Hosts lose grounding. | Populate: tenth-century author label (no Arabic personal name); the seam-question the chapter is answering; the tradition (a tenth-century da'wa dialogue book); one or two related chapters by stable label only; leave "Why this lands now" empty per its bracketed note. |
| P1 | 00-framing.md | "## Length" | Target length 50–60 min, but no primary source exists and key passages and context pack are empty. Source volume cannot sustain the target without padding or hallucination. | Either restore the source files (preferred) or cut the target to a length the surviving source supports. Do not ship a 50-min target against an effectively empty source set. |
| P1 | 00-framing.md | "## Three-part focus" header text | The section is titled "Three-part focus" but contains six beats. The label confuses any downstream beat-counter. | Rename to "## Beat structure" or "## Six-beat arc". |
| P2 | 00-framing.md | "**Episode format:** Debate with concession" | Format is declared, but NotebookLM's UI exposes only "Deep Dive / Debate / Brief / Critique" and a Length setting. The framing does not name the NotebookLM-facing setting pair. | Add a one-line operator note: "NotebookLM Format: Debate. Length: Long." |
| P2 | 00-framing.md | "## Pronunciation" | Pronunciation appendix is present and complete, but the framing does not contain a Quran citation spoken-form appendix. The chapter has no `Q|N:M` citations to voice, so this is forward-compat only. | If any future revision adds Quran citations, append a `## Citation spoken-form` block mapping each `Q|N:M` to natural speech ("Quran, chapter N, verse M"). |
| clean | — | host-role assignment in framing | clean | clean |
| clean | — | "Skip the intro" instruction | clean | clean |
| clean | — | banter suppression directive | clean | clean |
| clean | — | single-thesis discipline | clean | clean |
| clean | — | banned-vocabulary deny list | clean | clean |

## Cross-Bundle Patterns

Only one bundle is in scope so cross-bundle observations are limited to internal cross-file patterns. The dominant pattern is **scaffold collapse**: three of five files are LLM-fill skeletons that were never authored. The framing is fully written and disciplined; the show notes is fully written but tonally and structurally mismatched against the framing's own rules (transliteration, italics, mono-paragraph, cross-chapter references); and the connective tissue (source, key passages, context pack, spine) is absent. The bundle is therefore a framing-and-blurb pair, not a NotebookLM-ready package.

A second pattern: the show notes file is doing two incompatible jobs — listener-facing blurb and de facto source — and is failing both. As a blurb it is too long and dense; as a source it is too italicized, transliterated, and unsegmented. Splitting it into a true source file (clean prose, Arabic script where needed) and a true blurb (one paragraph for the reader) would resolve a large fraction of the P0 and P1 findings simultaneously.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "00-framing.md",
    "anchor": "Anti-noise rules",
    "severity": "P0",
    "problem": "Framing states 'the chapter file is the entire source NotebookLM sees' but no chapter prose file exists in the bundle.",
    "fix": "Create 01-source.md containing the chapter prose verbatim, including every framing-stipulated quotation (fire-is-hot figure, four-letters exchange, four-nations indictment, three qualities, prophets count, Moses-fleeing-Pharaoh paradigm, jurists-and-tyrants line, recurring thesis verbatim, closing doxology). Add it to the bundle and to manifest.",
    "category": "spine"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "Passage 1",
    "severity": "P0",
    "problem": "Key passages file contains only a '>' stub and [LLM-FILL]; NotebookLM has no retrievable verbatim anchors for any of the nine framing-stipulated quotations.",
    "fix": "Replace stub with nine numbered Passage blocks containing the framing's stipulated verbatim quotes (fire-is-hot, four-letters, causes-between-Him-and-creation, four-nations, three qualities, prophets count, Moses-fleeing-Pharaoh, mercy-to-slain, narrations-of-the-jurists), plus the recurring thesis and the closing doxology. Add a one-line 'Why this matters' under each.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "Author / narrator",
    "severity": "P1",
    "problem": "Every context-pack section is [LLM-FILL]; hosts have no grounding for author, lineage, or the question the chapter is answering.",
    "fix": "Populate with: tenth-century author label (do not voice Arabic personal name); the seam-question from chapter five ('the attribute is preferable to him; so how is it described?'); tradition as a tenth-century da'wa dialogue book; one or two sibling chapter references by stable label only. Leave 'Why this lands now' bracketed as Not required per its existing note.",
    "category": "cohesion"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "8 beats",
    "severity": "P0",
    "problem": "Spine template prescribes 8 beats while framing prescribes 6, creating contradictory architecture for NotebookLM.",
    "fix": "Reduce spine to six beats matching framing's Beat 1 through Beat 6 (crisis; first failed answer; second failed answer; pivot with recurring-thesis-2; non-bodily correction; human stakes with recurring-thesis-3). Update header from '8 beats' to '6 beats'.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "Beat 1 through Beat 8",
    "severity": "P0",
    "problem": "Every beat is [LLM-FILL]; NotebookLM has no hidden steering layer.",
    "fix": "Fill each retained beat with key-question, tension drawn from the verbatim passages in 02-key-passages.md, anchor-passage reference by number, and a landing line. In Beat 1 seed a Host A / Host B exchange explicitly tagged '(male)' and '(female)' to lock host roles.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "Beat 1: Opening hook",
    "severity": "P0",
    "problem": "Host roles (male=young teacher, female=senior scholar) are assigned in framing but never seeded in spine, risking mid-episode drift.",
    "fix": "In Beat 1 landing write one example exchange: Host A (male) names the recurring thesis verbatim, then Host B (female) states the proposition under debate verbatim. Tag both speakers inline.",
    "category": "host-role"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb:",
    "severity": "P0",
    "problem": "Single ~1,500-word unbroken paragraph; if ingested by NotebookLM as source the hosts cannot segment for breath and will summarize.",
    "fix": "Split into prose paragraphs of 80 to 150 words each, breaking at the doctrinal turns: fire-is-hot, four-letters, four-nations, three qualities, prophets count, Moses-fleeing-Pharaoh, jurists indictment, repentance, doxology.",
    "category": "length"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Abu Malik (a-BOO MAA-lik)",
    "severity": "P0",
    "problem": "Inline phonetic transliterations are sprinkled throughout (a-BOO MAA-lik, ta-KEE-yah, moo-haa-jih-ROON, shoo-AYB); NotebookLM will voice the phonetic guides literally if this file is the source.",
    "fix": "Strip every inline phonetic gloss. Keep pronunciation only in 00-framing.md's ## Pronunciation section. Where Arabic terms remain in prose, render in Arabic script with English in apposition (e.g., 'protective concealment (تقية)').",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb:",
    "severity": "P1",
    "problem": "Italicized terms (Sharia, Taqiyya, wasi, hawl, quwwa) appear throughout; the house style bans italics.",
    "fix": "Remove every italics marker. Where italics marked a chapter quote, convert to a quoted phrase introduced by attribution. Where italics marked an Arabic term, render the Arabic in Arabic script after an English gloss in parentheses.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Chapter five ended on Abu Malik",
    "severity": "P1",
    "problem": "Show notes opens with an extended chapter-five recap and ends with a Related-episodes list, both contradicting framing's R-NOBACKGROUND and self-contained-episode directives.",
    "fix": "Replace the chapter-five recap with one sentence of in-chapter framing ('This chapter answers the seam-question from the previous turn — if religion is the cause that connects heaven to earth, how is that cause described?'). Remove the 'Related episodes' list from any version NotebookLM ingests; keep it only in a listener-facing variant outside the source set.",
    "category": "cohesion"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Abu Malik / Salih / Al-Bakhtari",
    "severity": "P1",
    "problem": "Personal Arabic names of figures appear repeatedly even though framing's ## Stable role-labels forbids voicing them and assigns English-only labels.",
    "fix": "Replace every 'Abu Malik' with 'the senior scholar'; every 'Salih' with 'the young teacher'; every 'Al-Bakhtari' with 'the scholar-father'. Use the exact stable labels from framing's ## Stable role-labels.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Length estimate: see contract.length_target (extended)",
    "severity": "P2",
    "problem": "Length placeholder 'extended' is not a concrete minute count; pipeline tooling and listeners cannot parse it.",
    "fix": "Replace with '50 to 60 minutes' to match framing's ## Length.",
    "category": "length"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Three-part focus",
    "severity": "P1",
    "problem": "Section title 'Three-part focus' contains six beats, confusing downstream beat-counters and human readers.",
    "fix": "Rename the section header from '## Three-part focus' to '## Six-beat arc'. Update any internal cross-reference accordingly.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Length",
    "severity": "P1",
    "problem": "Target length is 50 to 60 minutes against an effectively empty source set (no primary source, empty key-passages, empty context-pack, empty spine).",
    "fix": "Either restore the source files first (preferred — see other findings) or temporarily reduce the target to a length the surviving source supports (e.g., 25 to 35 minutes). Do not ship a 50-minute target against an empty source.",
    "category": "length"
  },
  {
    "file": "00-framing.md",
    "anchor": "Episode format: Debate with concession",
    "severity": "P2",
    "problem": "Format is declared in prose but the framing does not name the NotebookLM-facing Format + Length settings pair.",
    "fix": "Append a single operator-facing line after the Episode-format declaration: 'NotebookLM Format setting: Debate. NotebookLM Length setting: Long.'",
    "category": "format"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Name discipline",
    "severity": "P1",
    "problem": "The chapter's name-by-attribute discipline (forbidding pairing of the leadership-title with the personal name of the Father of Imams) supersedes the global house rule 'Use Maulana Ali'. Downstream auditors may re-flag this without context.",
    "fix": "Add one explanatory sentence at the end of ## Name discipline: 'The forbidden-pairing rule above is a chapter-internal doctrinal discipline that overrides the global Maulana-Ali default for this episode only.'",
    "category": "articulation"
  }
]
```

---

## Next: 👤 Asif
A. (Recommended) Do all of the below in the order shown (B → C → D) — the bundle is structurally hollow; running the fix list end-to-end is cheaper than half-shipping.

B. Run the Claude-Code fix list above in P0-then-P1 order against the bundle directory `content/drafts/the-master-and-the-disciple/_system/episode-drafts/EP06-justice-monotheism-and-the-guardians/` — the four P0s (missing source, empty key passages, empty spine + beat-count contradiction, show-notes audio-toxicity) all block NotebookLM upload.

C. After P0 + P1 are clean, re-run this auditor on the patched bundle to confirm host-role seeding, pronunciation appendix, and length-vs-source balance all read clean.

D. If a per-chapter regeneration would be cheaper than hand-fixing the show notes and spine, retry phase 0e or the per-chapter authoring step for EP06 only (do not retry the whole book) — the framing is already authored and should be preserved.
