## Inventory

- **EP03 — World, Hereafter, and the Right of Wealth** (bundle: `EP03-world-hereafter-and-the-right-of-wealth`)
  - `00-framing.md` — present, dense (22 KB)
  - `01-primary-source.md` — **MISSING** (no primary source file in manifest)
  - `02-key-passages.md` — present but **functionally empty** (single `>` quote stub, all `[LLM-FILL]`)
  - `03-context-pack.md` — present but **all `[LLM-FILL]` placeholders**
  - `04-discussion-spine.md` — present but **all 8 beats are `[LLM-FILL]` placeholders**
  - `99-show-notes.md` — present with full blurb prose

Net: 1 of 6 standard artifacts is fully authored. The hosts have a fully-specified framing and a fully-written show-notes blurb, but **zero retrieval substrate** (no primary source, no key passages, no context, no spine).

## Chapter Findings

### Chapter EP03: World, Hereafter, and the Right of Wealth ⚠

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `02-key-passages.md` | `### Passage 1` | The file contains only `> >` and `*Why this matters:* [LLM-FILL]`. NotebookLM has no verbatim source quotes to retrieve when the spine names a beat. The framing's verbatim-quote contract (pair-question, three-houses, sower, rope, dropped inner interpretations, two verdicts, two-eyes, archer-figure, golden rule, wealth-rule, five-share enactment, generous-one description, deferral) cannot be honored. | Author 12–15 numbered passages, each a verbatim quote from the chapter, exactly matching the list in `00-framing.md` § Pronunciation ("Quote verbatim for…"). Each passage must include a 1–2 sentence `*Why this matters:*` line tied to a specific Beat (1–6). |
| P0 | `03-context-pack.md` | `## Author / narrator` | All four sections (Author/narrator, What this chapter is responding to, Tradition/lineage, Related works) are `[LLM-FILL]`. Hosts have no grounding for the tenth-century Yemeni / Fatimid tradition the chapter sits in. | Author each section in 2–4 sentences. Constraint: do not voice author's Arabic name; use "the tenth-century author." Use English labels for the tradition (the surrounding schools of law; the speakers; the captains). Restate the chapter's hinge-function: ethical-practical bridge between cosmology and the journey-and-naming arc. |
| P0 | `04-discussion-spine.md` | `### Beat 1: Opening hook` | All 8 beats are `[LLM-FILL]`. The discussion spine — the "hidden steering layer NotebookLM hosts follow when it is well-built" — has zero content. Without it the hosts will improvise; the framing's six-beat narrative architecture will not survive contact with NotebookLM. | Replace the 8-beat scaffold with a **6-beat** spine matching `00-framing.md` § "Three-part focus" (Pairs that point; Three houses + limit of teaching; Rope + two dropped inner interpretations; Two eyes + Master's tears; One creation, many passions + classes/degrees + body and wealth; Five shares + Imam named + deferral). For each beat, fill key-question, tension, anchor-passage (reference passage N from the rewritten `02-key-passages.md`), and landing — and seed at least one role-pattern exchange (Host A = scholar voicing the Master; Host B = student voicing the Boy pressing back). |
| P0 | `04-discussion-spine.md` | `### Beat 7 / Beat 8` | The spine template has **8 beats**; the framing prescribes **6 beats walking the chapter in narrative order, each landing once and only once**. The two extra slots will either be padded (force repetition) or left empty (hosts drift). | Delete Beats 7 and 8. The spine must be six beats, matching the framing exactly. |
| P1 | (bundle root) | (missing file) | The bundle has **no `01-primary-source.md`** (or equivalent chapter-text file). NotebookLM needs the full source text to anchor retrieval; show-notes prose and key-passages snippets are not a substitute. | Add `01-primary-source.md` containing the full chapter text (or a clearly-marked excerpt of the ethical-practical chapter from `The Master and the Disciple`), formatted as paragraph prose. |
| P1 | `99-show-notes.md` | `**Blurb:**` | The blurb is a single ~600-word unbroken paragraph mixing English narration with transliterated Arabic terms (nāṭiqs, ta'wīl, hujja, bāb, hawl, quwwa, ʿuṣba, batin, awliyāʾ, al-Khidr, zakat, Kitab al-'Alim wa-l-Ghulam). Violates the articulation rule: Arabic terms must appear in Arabic script with a parenthesized English gloss, never as Latin-letter transliterations with diacritics. NotebookLM will mispronounce every one. | Rewrite blurb in plain English using the framing's stable labels: "the seven speakers" (not nāṭiqs), "inner interpretation" (not ta'wīl), "argument" (not hujja), "door" (not bāb), "year-turning figure" (not hawl), "power" (not quwwa), "the band" (not ʿuṣba), "the inward" (not batin), "guardians" (not awliyāʾ), "the immortal green-clad guide" (not al-Khidr), "purification-due" (not zakat), and "the book 'The Master and the Disciple'" (not Kitab al-'Alim wa-l-Ghulam). Break into 3–4 paragraphs. |
| P1 | `99-show-notes.md` | `**Blurb:**` second sentence | Quran citation appears as `Q 4:69`. Articulation contract requires the exact form `Q|4:69` placed on a new line immediately following the verse. | Replace `Q 4:69` with the verse content on one line, then `Q|4:69` on the following line. |
| P1 | `99-show-notes.md` | `**Blurb:**` | The Boy is referenced in lowercase ("the boy") throughout the show-notes blurb; the framing's stable role-label is capitalized ("the Boy"). Drift in the published metadata will leak into NotebookLM's reading. | Capitalize "Boy" everywhere in the blurb to match `00-framing.md` § "Stable role-labels". |
| P1 | `99-show-notes.md` | `## References` | The references list contains a single literal `>` line — a broken markdown stub, not a reference. | Either populate with real references in the same English-labels style as the rest of the bundle, or remove the section. |
| P2 | `99-show-notes.md` | `**Title:** / **Blurb:** / **Length estimate:**` | Show notes use bold labels and italicized terms throughout. House style is paragraph prose without bold or italics. Acceptable for metadata fields the hosts never read, but inconsistent with the chapter style. | Acceptable to retain bold metadata labels (Title, Blurb, Length). Strip italics from quoted phrases in the blurb body — they will not survive audio rendering and clutter the visible style. |
| P2 | `00-framing.md` | `## Three-part focus` | The section title says "Three-part focus" but the body contains six beats. Cosmetic mismatch — does not affect audio but is confusing for downstream parsers and human reviewers. | Rename the heading to `## Six beats` or `## Narrative spine`. |
| — | `00-framing.md` | (cohesion) | clean — single thesis (the two-eyes formula), six beats walking the chapter in narrative order, opening / middle / closing turn clear, three governing analogies named and gated. | clean |
| — | `00-framing.md` | (duplication, intra-file) | clean — the recurring thesis is deliberately repeated three times verbatim per the framing's own anti-repetition rule. Not excessive; structurally load-bearing. | clean |

## Episode Findings

### Episode EP03: World, Hereafter, and the Right of Wealth ⚠

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `04-discussion-spine.md` | (all beats) | Host-role pattern is declared in `00-framing.md` (Host A male = scholar / Master's voice; Host B female = curious-seeker / Boy's voice) but **the spine seeds zero example exchanges**. Without at least one in-spine exchange that demonstrates the role assignment, NotebookLM's voices will not lock onto the pattern and may invert mid-episode. | In the rewritten spine, every beat must contain at least one explicit role-tagged exchange. Beat 1 must include a seed example showing Host A delivering the structural reading and Host B pressing with the framing's pre-written pushback (`I don't buy that yet…`). Beats 3, 5 must surface the other two scripted pushbacks verbatim. |
| P0 | `99-show-notes.md` | `**Blurb:**` (transliterations) | Show-notes contains ~13 transliterated Arabic terms with diacritics (nāṭiqs, ta'wīl, hujja, bāb, hawl, quwwa, ʿuṣba, batin, awliyāʾ, al-Khidr, zakat, ʿAlim, Ghulam). NotebookLM will read these literally and butcher every one. The framing's pronunciation list does not cover them because the framing already converts them to English. | Strip all transliterated Arabic from show-notes per the chapter-level fix above. The framing's "Concept words convert to English" table is the canonical mapping; show-notes must conform. |
| P1 | `02-key-passages.md` `03-context-pack.md` `04-discussion-spine.md` | (whole files) | Spine completeness fails on every required beat. The required beat structure (opening hook, 3–5 discussion beats, bridging tension, closing reflection returning to hook) cannot be evaluated because the spine is empty. Same applies to passages and context. | Author all three files. See P0 fixes above. |
| P1 | `00-framing.md` | `## Pronunciation` | Pronunciation guidance is present and well-formed (Quran, imam, Allah, Adam, Joseph, Sinai, Islam, hadith) but **the show-notes file introduces ~13 Arabic terms not on the list** (nāṭiqs, ta'wīl, etc.). Either the source is bleeding terms the framing forbids, or the pronunciation appendix is incomplete. The fix is to remove the terms from show-notes (preferred — matches framing's English-equivalents policy), not to extend the pronunciation list. | After show-notes is de-transliterated, audit `01-primary-source.md` (once authored) for any Arabic token the framing has not pre-converted. Remove or replace. Pronunciation appendix stays as-is. |
| P2 | `00-framing.md` | `**Episode format:** in-depth walkthrough` | The format is declared as "in-depth walkthrough" — not one of the four canonical NotebookLM Audio Overview formats (Deep Dive, Brief, Critique, Debate). NotebookLM will pick its own default. | Declare `Deep Dive` explicitly. Justification: 50–60 minute target + single-chapter, single-thesis architecture + scholar/student dynamic with structured pushback maps directly to Deep Dive. |
| P2 | `00-framing.md` | (citation spoken-form) | No spoken-form citation appendix exists. The framing avoids voicing `Q|Surah:Verse` literally by referring to surahs by English meaning ("the chapter on the family of Imran"). For Q 4:69 in show-notes, no spoken form is provided. | If `Q|4:69` will be voiced in audio, add a one-line mapping: "Q|4:69 → 'Quran, chapter four, verse sixty-nine.'" If the framing's strategy is to never voice the citation literally (current intent), explicitly state that in the framing and ensure the spine never directs hosts to a verse by number. |
| — | `00-framing.md` | (length) | clean — 50–60 min target, source volume (six beats, dense doctrinal moves) supports it without padding. | clean |
| — | `00-framing.md` | (cliffhanger) | clean — the episode ends OPEN on the deferral at the door, which the framing explicitly designs as intra-episode resolution ("door reached but not yet entered"), not a hallucination-bait cliffhanger. | clean |
| — | `00-framing.md` | (single thesis) | clean — one thesis named in one sentence (the two-eyes aphorism), spoken three times verbatim. | clean |
| — | `00-framing.md` | (banter suppression) | clean — forbidden first-words list present, anti-noise rules present, anti-repetition rule (R-NOREPEAT) present, welcome-opening rule (R-WELCOME) present, formal-essay-transition ban (R-NOFORMAL) present. | clean |
| — | `00-framing.md` | (tone alignment within framing) | clean — instructional but casual, third person, paragraph prose, no bold/italics/footnotes in chapter prose. | clean |

## Cross-Bundle Patterns

Only one bundle is in the consolidated input, so there are no cross-bundle duplications to flag. However, the bundle exhibits a **single systemic pattern worth surfacing**: the framing is exhaustively authored (22 KB of beat-by-beat steering, role labels, pronunciation, governing analogies, forbidden vocabulary) while the four downstream files that NotebookLM actually retrieves from (primary source, key passages, context pack, spine) are missing or stubbed. The framing is the *instruction* — the spine and passages are the *substrate*. NotebookLM does not read the framing the way Claude Code does; it reads the source documents. A pristine framing over an empty substrate produces an episode that ignores the framing.

A second pattern: the show-notes blurb appears to have been authored against an earlier pipeline standard that allowed transliterated Arabic with diacritics, while the framing has moved to a stricter English-equivalents policy ("Concept words convert to English"). Either the blurb pre-dates the framing's policy lock or it was authored outside the policy. Going forward, the show-notes blurb should be regenerated from the framing's English-labels table, not from the source chapter directly.

A third, structural drift: `04-discussion-spine.md` ships an 8-beat template, but the framing prescribes six. This suggests the spine template is the pipeline default and was not adapted to this chapter's narrative architecture. Either the template should be parameterized (`N` beats), or the framing should override the template at scaffold time.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "02-key-passages.md",
    "anchor": "### Passage 1",
    "severity": "P0",
    "problem": "Key-passages file contains only an empty blockquote and an LLM-FILL stub; NotebookLM has no verbatim source quotes to retrieve when the spine names a beat, breaking the framing's verbatim-quote contract for the pair-question, three-houses, sower, rope, dropped inner interpretations, two verdicts, two-eyes, archer-figure, golden rule, wealth-rule, five-share enactment, generous-one description, and deferral.",
    "fix": "Replace the file body with 12 to 15 numbered passages (### Passage 1 through ### Passage N), each containing a verbatim blockquote from the chapter matching the list in 00-framing.md section Pronunciation under 'Quote verbatim for', followed by a one-to-two-sentence '*Why this matters:*' line that names which Beat (1 through 6) the passage anchors.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "## Author / narrator",
    "severity": "P0",
    "problem": "All four sections (Author/narrator, What this chapter is responding to, Tradition/lineage, Related works) contain only [LLM-FILL] placeholders; hosts have zero grounding in the tenth-century Yemeni Fatimid tradition the chapter sits in.",
    "fix": "Author each of the four sections in 2 to 4 sentences. Use 'the tenth-century author' (never the author's Arabic name). Use the framing's English labels: 'the surrounding schools of law', 'the seven speakers', 'the twelve captains', 'the ten arguments'. Explicitly restate the chapter's hinge-function as the ethical-practical bridge between the cosmology arc and the journey-and-naming arc.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "All 8 beat slots are [LLM-FILL] placeholders; the discussion spine — the hidden steering layer NotebookLM hosts follow — has zero content, so the framing's six-beat narrative architecture will not survive contact with NotebookLM.",
    "fix": "Delete the 8-beat scaffold and replace with exactly 6 beats matching 00-framing.md section 'Three-part focus': Beat 1 'Pairs that point', Beat 2 'Three houses + limit of teaching', Beat 3 'Rope + two dropped inner interpretations', Beat 4 'Two eyes + Master's tears', Beat 5 'One creation, many passions + classes/degrees + body and wealth', Beat 6 'Five shares + Imam named + deferral'. For each beat fill Key question, Tension, Anchor passage (reference passage N from the rewritten 02-key-passages.md), and Landing.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 7: [LLM-FILL] Beat 7",
    "severity": "P0",
    "problem": "Spine template has 8 beats; framing prescribes 6 beats walking the chapter in narrative order, each landing once and only once. The two extra slots will either pad (force repetition) or stay empty (hosts drift).",
    "fix": "Delete the entire Beat 7 and Beat 8 sections. The spine must contain exactly six beats matching the framing.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "Host-role pattern (Host A male = scholar/Master, Host B female = student/Boy) is declared in the framing but the spine seeds zero example exchanges, so NotebookLM voices will not lock onto the pattern and may invert mid-episode.",
    "fix": "In the rewritten Beat 1, embed one explicit role-tagged exchange: Host A delivers the structural reading ('the outward is a name, the inward is an attribute…'), then Host B presses with the framing's pre-written pushback verbatim ('I don't buy that yet. If the Master says the great station cannot be GIVEN by another, what is he doing for the Boy?'). In Beats 3 and 5 embed the other two scripted pushbacks verbatim from 00-framing.md section 'Host dynamic'.",
    "category": "host-role"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P0",
    "problem": "Blurb contains roughly 13 transliterated Arabic terms with diacritics (nāṭiqs, ta'wīl, hujja, bāb, hawl, quwwa, ʿuṣba, batin, awliyāʾ, al-Khidr, zakat, ʿAlim, Ghulam) plus the transliterated book title Kitab al-'Alim wa-l-Ghulam; NotebookLM will mispronounce every one and these violate the framing's 'Concept words convert to English' table.",
    "fix": "Replace transliterations with the framing's stable English labels throughout the blurb: nāṭiqs → 'the seven speakers'; ta'wīl → 'inner interpretation'; hujja → 'argument'; bāb → 'door'; hawl → 'year-turning figure'; quwwa → 'power'; ʿuṣba → 'the band'; batin → 'the inward'; awliyāʾ → 'guardians'; al-Khidr → 'the immortal green-clad guide'; zakat → 'purification-due'; Kitab al-'Alim wa-l-Ghulam → 'the book \"The Master and the Disciple\"'. Use 'Maulana Ali' if the Commander of the Faithful is named in any future blurb expansion (never 'Imam Ali').",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb is a single unbroken paragraph of roughly 600 words, well over the 400-word audio-readability threshold, and mixes summary prose with embedded source quotations in italics.",
    "fix": "Break the blurb into 3 or 4 paragraphs along the framing's beat boundaries: Pairs and three houses; Rope and the two dropped inner interpretations; Two eyes, brethren, and the Master's tears; Five shares, Imam named, deferral at the door.",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Quran citation appears as 'Q 4:69' which violates the articulation contract requiring exact form 'Q|Surah:Verse' on a new line immediately following the verse content.",
    "fix": "Replace 'with the Qur'anic warrant of Q 4:69 (whoever obeys Allah…)' with the verse content on one line followed by 'Q|4:69' on the next line, with no parenthetical wrapping of the citation.",
    "category": "citation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "The Boy is referenced as lowercase 'the boy' throughout the blurb; the framing's stable role-label is capitalized 'the Boy'.",
    "fix": "Replace every occurrence of 'the boy' with 'the Boy' in the blurb text. Leave the slug 'the boy' untouched if it appears in any URL or filename context (none in this file).",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## References",
    "severity": "P1",
    "problem": "References section contains only a literal '>' line — a broken markdown stub, not a reference.",
    "fix": "Either populate the references list with concrete references in the framing's English-labels style, or remove the entire '## References' heading and its body from the file.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P2",
    "problem": "Blurb uses italics on roughly 30 quoted phrases; articulation policy is paragraph prose without italics.",
    "fix": "Remove italic markers (asterisks) from every quoted phrase inside the blurb body. Retain bold only on the metadata labels at the top of the file (Title, Blurb, Length estimate).",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "**Episode format:**",
    "severity": "P2",
    "problem": "Episode format is declared as 'in-depth walkthrough', not one of the four canonical NotebookLM Audio Overview formats (Deep Dive, Brief, Critique, Debate), so NotebookLM picks its own default.",
    "fix": "Change 'Episode format: in-depth walkthrough of a single ethical-practical chapter.' to 'Episode format: Deep Dive — an in-depth walkthrough of a single ethical-practical chapter.' The 50 to 60 minute target plus single-chapter single-thesis architecture plus scholar/student dynamic with structured pushback maps to Deep Dive.",
    "category": "format"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Three-part focus",
    "severity": "P2",
    "problem": "Heading reads 'Three-part focus' but body contains six beats; cosmetic mismatch confuses downstream parsers and human reviewers.",
    "fix": "Rename the heading from '## Three-part focus' to '## Six beats'.",
    "category": "cohesion"
  }
]
```
