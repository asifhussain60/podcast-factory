## Inventory

- **Bundle:** EP05 — The Father Revealed and the Three Faces of Seeking (one episode, single chapter)
  - `00-framing.md` — present, fully authored
  - `02-key-passages.md` — present but **empty stub** (single `> >` line + one `[LLM-FILL]`)
  - `03-context-pack.md` — present but **all five sections are `[LLM-FILL]`**
  - `04-discussion-spine.md` — present but **all 8 beats are `[LLM-FILL]`** including key question, tension, anchor passage
  - `99-show-notes.md` — present, fully authored

## Chapter Findings

### Chapter EP05: The Father Revealed and the Three Faces of Seeking

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `02-key-passages.md` | `### Passage 1` | File is an unfilled scaffold — single `> >` blockquote and one `[LLM-FILL]`. NotebookLM will retrieve nothing when the spine references passage anchors. | Populate with at least 6–8 verbatim quotes drawn from the chapter (the father's reproach, the boy's bind, the divorce-oath ruling, the breach-in-medicine figure, the three-states reasoning, the testing-forge parable, the zero-point confession, the closing seam-question), each followed by a `*Why this matters:*` one-sentence ground line. |
| P0 | `03-context-pack.md` | `## Author / narrator` | All five subsections are `[LLM-FILL]`. Hosts have no grounding for author, chapter-question, lineage, or related works. | Fill all five sections with the tenth-century Yemeni dialogue-book context already implicit in the framing's `## Background` and `## Audience` blocks — author identification, the father-reproach inheritance from chapter four, the Ismā'īlī da'wa-pedagogy lineage, and the four prior chapters as related works. Mark `## Why this lands now` `Not required` per the existing template note. |
| P1 | `99-show-notes.md` | `**Blurb:**` | Blurb is a single ~900-word unbroken paragraph with stacked parentheticals (`(SHAYKH)`, `(SAA-lih)`, `(al-bakh-tah-REE)`, `(KAB al-AH-bar)`, etc.) — exceeds the ~400-word breath limit and saturates with parenthetical phonetics that read as voice-glitch fuel if NotebookLM ingests it. | Split blurb into 3–4 paragraphs at the natural beat-boundaries (father-and-boy / senior-scholar-arrives / Salih–Abu-Malik dialogue / closing seam-question). Strip the inline phonetic parens — pronunciation belongs in the framing's `## Pronunciation` block, not the blurb. |
| P2 | `00-framing.md` | `## Stable role-labels` | Bulleted list of nine label rules — articulation rule says "bulleted lists in the prose are deviations." Framing is meta-instruction (not spoken), so this is acceptable, but flag for stylistic consistency. | Acceptable as a framing directive; no fix required unless the house-style enforcement extends to framing prose itself. If it does, convert the nine bullets to a numbered prose paragraph keyed by figure. |
| Cohesion | — | — | clean |
| Duplication | — | — | clean (the three-times thesis repetition is intentional, governed, and within R-NOREPEAT) |

## Episode Findings

### Episode EP05: The Father Revealed and the Three Faces of Seeking

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `04-discussion-spine.md` | `### Beat 1: Opening hook` through `### Beat 8: Landing` | All 8 beats unfilled (`[LLM-FILL]` for key question, tension, anchor passage). The spine is the hidden steering layer — without it the framing's six-beat arc has no retrievable counterpart, and NotebookLM will improvise structure. | Author all 8 beats. Map to the framing's six narrative beats: Beat 1 → divorce-oath crisis; Beat 2 → breach-in-medicine + three-states; Beat 3 → historical-temporal objection (revelation cut off); Beat 4 → pivot + first verbatim thesis recurrence; Beat 5 → testing-forge + three faces of seeking; Beat 6 → zero-point + third thesis recurrence; Beat 7 → senior scholar's concession; Beat 8 → closing seam-question. Each beat's anchor passage must reference a real entry from a populated `02-key-passages.md`. |
| P0 | `04-discussion-spine.md` | `### Beat 1: Opening hook` Tension line | Tension fields all read `[LLM-FILL — must draw from: >]` — the source-extract pointer is also empty, so the build pipeline had nothing to inject. Indicates an upstream extraction failure, not just authoring drift. | Re-run `extract_chapter.py` for this bundle so the tension-extract injector has source text to draw from, then re-template the spine. Verify the chapter contract's `length_target` and `key_quotes` are populated in `_system/chapter-contracts/`. |
| P1 | `00-framing.md` | `## Pronunciation` | Pronunciation guidance is embedded inline in the framing rather than carried in a dedicated appendix file referenced from the framing. Audit rule §3f requires a separate referenced appendix. | Either accept the framing-embedded form as the bundle's convention (no fix), or extract `## Pronunciation` into `05-pronunciation-appendix.md` and replace the framing block with a one-line reference. Recommend keeping inline — the appendix-file split adds an upload artifact for marginal NotebookLM benefit. |
| P1 | bundle | citation spoken-form | Chapter's source body invokes multiple surahs (the Cow, Family of Imran, Light, Poets) but no Q\|Surah:Verse citations and no spoken-form appendix exist. Framing handles this by instructing English surah-naming, which is functionally equivalent but does not satisfy the house Quran-citation format. | If verbatim verses are quoted in the source, add a `06-citation-spoken-form.md` appendix mapping each `Q\|S:V` to its natural-speech form. If no verbatim citations appear (only surah-by-theme references), document the exemption in framing under `## Pronunciation` as a one-sentence note. |
| Host-role | `00-framing.md` | `## Roles + positions` | clean — male=scholar, female=senior-scholar-of-old-creed conceding; explicit seed exchange in Beat 1 |
| Length | `00-framing.md` | `## Length` | clean — 50–60 min stated; source supports it |
| Format | `00-framing.md` | `**Episode format:**` | clean — "Debate with concession" declared on line 1 |
| Banter suppression | `00-framing.md` | `## Tone constraints` + `## Do not` | clean — explicit R-NOINTERRUPT, forbidden first-words list, surprise-noise DENY |
| Cliffhanger | `00-framing.md` | `## Anti-noise rules` | clean — explicit prohibition on cross-chapter references and pre-announcement |
| Single-thesis | `00-framing.md` | `## Opening directive` | clean — one settled formula, spoken three times verbatim |
| Skip-the-intro | `00-framing.md` | `## Opening directive` | clean — "Do not open with formulaic show-intro phrasing" is the functional equivalent |

## Cross-Bundle Patterns

Three of the five bundle files are unfilled scaffolds (`02`, `03`, `04`), while the two narrative-authored files (`00`, `99`) are exhaustively rich. This is the signature of a partial pipeline run — the LLM-authoring phase completed framing and show-notes but never executed against the spine, key-passages, and context-pack templates. The fix is upstream (re-run the spine/passages/context-pack authoring phase for this bundle), not file-by-file remediation.

The framing's pronunciation block, the show-notes blurb's inline phonetics, and an absent dedicated pronunciation appendix together suggest the bundle treats pronunciation as a framing concern only. That is a defensible convention provided it is consistent across the book — but if other bundles in `the-master-and-the-disciple/` use a separate appendix file, EP05 drifts from the series shape.

The framing is exceptionally disciplined on host-role, anti-noise, anti-repetition, forbidden-vocabulary, and the verbatim-thesis-three-times mechanic. None of those need touching. The audit weight is entirely on the unfilled scaffolds and the show-notes blurb-segmentation.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "02-key-passages.md",
    "anchor": "### Passage 1",
    "severity": "P0",
    "problem": "File is an unfilled scaffold containing a single empty blockquote and one [LLM-FILL] marker; NotebookLM has no verbatim passages to retrieve when the spine references anchor passages.",
    "fix": "Populate the file with 6 to 8 verbatim quotes from the chapter: the father's reproach (is this the reward of sons to their fathers?), the boy's bind (either you are a scholar or you are ignorant), the divorce-oath ruling (act on whichever of the two you wish), the breach-in-medicine figure, the three-states reasoning, the testing-forge / glass-in-camouflage parable, the zero-point confession (I do not see that anything is left with me), and the closing seam-question (the attribute is preferable to him — so how is it described?). After each passage add a one-sentence 'Why this matters:' ground line.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "## Author / narrator",
    "severity": "P0",
    "problem": "All five context-pack sections are [LLM-FILL] placeholders, leaving hosts with no grounding for author, chapter question, lineage, or related works.",
    "fix": "Fill Author/narrator with the tenth-century Yemeni dialogue-book author identification. Fill 'What this chapter is responding to' with the father-reproach inheritance from chapter four. Fill Tradition/lineage with the Ismaili da'wa pedagogical chain context. Fill Related works with the four prior chapters (the-call-and-the-covenant, will-command-and-the-seven, world-hereafter-and-the-right-of-wealth, the-greater-shaykh-and-the-naming) already listed in 99-show-notes.md Related episodes. Leave 'Why this lands now' as 'Not required for this adaptation mode.' per the existing template note.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "All 8 spine beats are unfilled — key question, tension, and anchor passage are [LLM-FILL] in every beat, leaving NotebookLM's hidden steering layer empty.",
    "fix": "Author all 8 beats mapped to the framing's six-beat arc: Beat 1 = divorce-oath crisis; Beat 2 = breach-in-medicine plus three-states; Beat 3 = historical-temporal objection that revelation was cut off by the books; Beat 4 = pivot plus first verbatim recurrence of the cause-that-connects-heaven-to-earth thesis; Beat 5 = testing-forge parable plus three-faces-of-seeking; Beat 6 = zero-point confession plus third verbatim recurrence of the thesis; Beat 7 = senior scholar's doctrinal concession; Beat 8 = closing seam-question 'how is it described?' held unresolved. Each beat must cite a real anchor passage from the populated 02-key-passages.md by passage number.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "Tension fields across all beats",
    "severity": "P0",
    "problem": "Every Tension line ends 'must draw from: >' — the source-extract injection is empty, indicating the upstream extract_chapter pipeline did not deliver source text into the templating step.",
    "fix": "Re-run scripts/podcast/extract_chapter.py for this bundle so the tension-extract injector has source text available, then re-template 04-discussion-spine.md. Before authoring beats by hand, verify _system/chapter-contracts/ for this chapter has populated key_quotes and length_target fields; if not, regenerate the contract first.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb is a single unbroken paragraph of roughly 900 words with stacked inline phonetic parentheticals ((SHAYKH), (SAA-lih), (al-bakh-tah-REE), (KAB al-AH-bar), (mak-ROOB), (a-BOO MAA-lik)) that exceed the ~400-word breath limit and create parenthetical-stacking voice-glitch risk.",
    "fix": "Split the blurb into 4 paragraphs at natural beat boundaries: paragraph 1 = the father-and-boy reconciliation and naming; paragraph 2 = the senior scholar (Abu Malik) arriving with the breach-and-three-states answer; paragraph 3 = the Salih-and-Abu-Malik dialogue (three faces of seeking, essence-traders parable, divorce-oath case); paragraph 4 = the zero-point confession and closing seam-question. Strip every inline phonetic parenthetical from the blurb body — pronunciation guidance already lives in 00-framing.md ## Pronunciation and does not belong duplicated in the show-notes prose.",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P2",
    "problem": "Pronunciation directives live inline in the framing rather than in a dedicated appendix file referenced from the framing — defensible as a bundle convention, but a drift if other bundles in this book use a separate appendix.",
    "fix": "Check sibling bundles under content/drafts/the-master-and-the-disciple/_system/episode-drafts/ for whether they use a separate pronunciation appendix or inline ## Pronunciation in framing. If sibling bundles use a separate file, extract this block into 05-pronunciation-appendix.md and replace the framing block with a one-line cross-reference. If sibling bundles are also inline, leave as-is.",
    "category": "pronunciation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "No citation spoken-form appendix exists, even though the chapter's source body invokes multiple surahs. Framing handles surahs by English-meaning naming, which is functionally equivalent but does not document the citation policy for the bundle.",
    "fix": "If any verbatim Quran verses are quoted in the source body, add a 06-citation-spoken-form.md appendix mapping each Q|Surah:Verse to its natural-speech form. If only English-meaning surah references appear (no verbatim verses), add one sentence to the ## Pronunciation block stating that surahs are spoken by English-meaning name and no Q|S:V citations appear in this chapter.",
    "category": "citation"
  }
]
```
