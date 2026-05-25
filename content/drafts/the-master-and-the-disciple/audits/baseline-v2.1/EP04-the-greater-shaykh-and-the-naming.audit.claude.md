## Inventory

- **Bundle**: `EP04-the-greater-shaykh-and-the-naming` (single bundle, single chapter, single episode).
- **Chapter / Episode**: EP04 — "The Greater Shaykh and the Seventh-Day Naming".
- **Artifacts present (with content)**: `00-framing.md` (complete), `99-show-notes.md` (complete blurb).
- **Artifacts present as stubs (no usable content)**: `02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`.
- **Artifacts missing entirely**: primary-source chapter file (no `01-*.md` or equivalent). NotebookLM has no source body to ingest.

---

## Chapter Findings

### Chapter 1: The Greater Shaykh and the Seventh-Day Naming

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | (bundle root) | (no primary-source file) | The bundle ships no chapter prose — NotebookLM has nothing to upload as the source corpus. Framing references "the chapter file is the entire source" but that file is absent. | Author or restore `01-primary-source.md` (or the project's standard primary-source filename) containing the full chapter prose in articulation style. Without it, the episode cannot be generated. |
| P0 | 02-key-passages.md | Passage 1 | File contains a single empty blockquote (`> >`) and `[LLM-FILL]`. The framing demands ~14 verbatim quotes (announcement, brotherly recognition, doxology, chain of rights, naming dialogue, veiled transmission, Hajj figure, eight-clause blessing, five negatives, six qualities, interpretation key, closing line). None are present. | Populate each numbered passage with the verbatim quote referenced in the framing's "Quote verbatim for" list. Each passage gets its English text, source location, and a one-sentence "Why this matters" tied to the beat it serves. |
| P0 | 04-discussion-spine.md | Beat 1: Opening hook | Every beat 1–8 is `[LLM-FILL]`. The spine is the hidden steering layer; an empty spine produces a free-associating episode regardless of framing quality. | Write all 8 beats. Map them to the framing's 6 narrative beats (Yellowing, Council, Two discourses, Naming dialogue, Veiled transmission, Farewell) plus an opening-hook beat and the silent-landing beat. Each beat states its key question, the tension drawn from a specific passage in `02-key-passages.md`, an anchor-passage reference, and a one-line landing. |
| P0 | 04-discussion-spine.md | Beat 1: Opening hook | Host-role assignment (male=scholar/elder, female=seeker) is declared only in `00-framing.md` and not seeded inside the spine itself. NotebookLM follows the spine more reliably than the framing for turn-by-turn role inheritance. | At Beat 1, add a seed exchange that explicitly labels Host A as the elder/scholar voice and Host B as the seeker voice, with one example pushback Host B will use (drawn from the framing's three pushback turns). Re-affirm the role at Beat 4 (naming dialogue) where the framing requires the second pushback. |
| P0 | 03-context-pack.md | Author / narrator | Every retrieval slot (author/dates, what the chapter answers, tradition/lineage, related works) is `[LLM-FILL]`. Hosts have no grounded background to retrieve when a beat asks "why this chapter matters". This invites hallucination on origin, tradition, and lineage. | Populate the four required sections from the framing's `## Background` paragraph and the chapter's known attribution (tenth-century Fatimid Yemen, attributed to a son of one of the founding Yemeni callers, fourteen-section dialogue treatise ending in the testament of the dying Master). Leave "Why this lands now" empty per the comment. |
| P1 | 00-framing.md | Pronunciation | Pronunciation directives sit INLINE in the framing rather than in a separate appendix referenced from the framing. The spec requires the appendix to be a discrete artifact, not woven into the steering prose. | Extract every "Pronounce X as Y" line into a new file `05-pronunciation.md` formatted as a two-column appendix (term → phonetic). Replace the inline block in `00-framing.md` with a single sentence pointing NotebookLM to `05-pronunciation.md`. |
| P1 | 99-show-notes.md | Blurb | The blurb is one ~800-word unbroken paragraph — well past the ~400-word breath-limit. Even though show notes are not voiced, they get scraped into NotebookLM's context as a high-weight summary; a wall-of-text blurb forces the hosts to over-compress in the opening. | Segment the blurb into 4–6 short paragraphs at natural seams (announcement → council → two discourses → naming dialogue → veiled transmission + Hajj figure → farewell + close). No bullets — keep prose. |
| P1 | 99-show-notes.md | Blurb | Arabic terms are transliterated throughout (*Kitab al-'Alim wa-l-Ghulam*, *batin*, *da'wa*, *Ubayd Allah, son of Abd Allah*, *ihram*, *Sa'd*, *Imam's permission*). Articulation style mandates Arabic script with parenthesized English meaning, never transliteration. | Replace every transliterated Arabic term with its Arabic-script form preceded by the English gloss, e.g., "the inner (الباطن)", "the call (الدعوة)", "the consecrated state (الإحرام)". For the book title, follow the framing's role-label rule: *the book "The Master and the Boy"*. Strip the Arabic personal name *Ubayd Allah, son of Abd Allah* from the blurb entirely — the framing restricts that name to the Beat-4 verbatim quote only. |
| P1 | 99-show-notes.md | Blurb | The blurb uses heavy italic emphasis on almost every key phrase, plus em-dash chains and parenthetical stacking. Italics confuse retrieval weighting and the dash chains will produce voice glitches if any of this gets read aloud. | Remove all italics. Convert em-dash chains to short sentences. Keep parentheticals to one per sentence. |
| P1 | 99-show-notes.md | References | The References block contains a single empty `>` blockquote. Either it should list grounded references in plain prose, or the section should be removed. | Either populate with the chapter's grounded inter-text references (the Treatise on Rights, the Psalms of Islam, the Path of Eloquence — already named in the framing's role-labels) in prose form, or delete the heading and the empty blockquote. |
| P2 | 00-framing.md | Stable role-labels | The Commander of the Faithful's "*peace be upon him* spoken IN FULL at first mention only" rule and the forbidden-pairing prohibition are clearly stated, but the spine has no enforcement hook. If the spine populates and a beat-author re-introduces the title at a later beat, the honorific will be repeated. | When authoring `04-discussion-spine.md`, mark in Beat 3 (the two opening discourses) that the title's full honorific is voiced exactly once and add a note to NotebookLM: subsequent mentions use the title alone. |
| P2 | 00-framing.md | Host dynamic | The three required pushback turns are listed by beat-seam but none specify a NotebookLM-style prompt the female host can reach for if she defaults to assent. They risk being soft-pedalled or skipped. | Strengthen each pushback with a verbatim opener that is permitted (not on the forbidden first-word list), e.g., "I don't follow yet — …" or "Let me push on that — …". Keep them in `00-framing.md` under `## Host dynamic`. |
| P2 | 00-framing.md | Pronunciation | The Quran is listed but the framing also instructs hosts to "refer to surahs by their English meaning". There are no Quran citations in `Q|S:V` form to spoken-form-map, so no citation appendix is required for this episode. | Add a single line under `## Pronunciation` stating that no Q|S:V citations appear in this chapter and the spoken-form appendix is therefore not needed (so a downstream check does not flag it as missing). |
| P2 | 00-framing.md | (whole file) | Cohesion: clean. Single-thesis discipline: clean. Format declaration (`deep_dive`): clean. Skip-the-intro instruction: clean. Banter suppression / anti-noise rules: clean. Length target (50–60 min): stated but cannot be calibrated until the primary-source file exists. | Re-verify length calibration once `01-primary-source.md` is populated: chapter word count divided by ~140 wpm should land in the 50–60 min band; if short, trim the spine to five beats. |

---

## Episode Findings

### Episode EP04: The Greater Shaykh and the Seventh-Day Naming

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | 04-discussion-spine.md | Beat 1: Opening hook | Spine is entirely `[LLM-FILL]` — none of the required beats exist (opening hook, 3–5 discussion beats, bridging tension, closing reflection that returns to the hook). Without a populated spine the episode has no steering layer and the framing alone cannot hold a 50–60 min conversation. | Author all eight beats per the framing's six narrative beats plus opening-hook and silent-landing. Bridge tension lives at the seam between Beat 3 (chain of rights) and Beat 4 (naming dialogue) — this is also the R-RESET site the framing names. |
| P0 | 04-discussion-spine.md | Beat 1: Opening hook | Host roles not seeded in the spine. | See Chapter Findings row above. |
| P0 | 04-discussion-spine.md | Beat 4: [LLM-FILL] Beat 4 | The veiled-transmission discipline (HONOR THE VEIL — never invent content) lives only in the framing. NotebookLM will improvise transmission content unless the spine repeats the constraint at the Beat-5 anchor. | At Beat 5 (the veiled transmission), write the landing as "Name what kind of matters these are (innermost inward; what the source guards under pious dissimulation) and why the source veils. Do not invent specifics. Hold the silence." |
| P0 | 02-key-passages.md | Passage 1 | The framing requires verbatim quotation for ~14 distinct passages including the recurring thesis (spoken three times). With zero passages provided, the hosts cannot quote verbatim and will paraphrase — collapsing the chapter's settled formula and the R-NOREPEAT verbatim-thrice rule. | Populate at minimum: the announcement, the brotherly recognition, the doxology on justice, the chain of rights, the naming dialogue, the recurring thesis ("The name belongs to you…"), the veiled-transmission disclosure, the Hajj-by-the-great-sign figure, the eight-clause blessing, the five negatives, the six qualities, the interpretation key, and the closing line ("then his father came to him, angry"). |
| P0 | 00-framing.md | Pronunciation | Pronunciation appendix is inline, not a separate referenced artifact. Arabic terms exist in the source. Per spec, inline-only equals "absent appendix" → P0. | See Chapter Findings — extract to `05-pronunciation.md`. |
| P1 | 99-show-notes.md | Related episodes | The related-episodes list points to neighboring chapter slugs in the same book, which is the correct pattern. Clean as a structure — but the framing's `R-NOBACKGROUND` and "Treat this chapter as self-contained" rules mean hosts should not be primed to cross-reference. The show-notes-driven related-episodes block is not voiced; it is a NotebookLM retrieval surface that will leak into context. | Add a one-line preamble to `## Related episodes` stating these slugs are publication-only metadata and must not be referenced in spoken dialogue. |
| P1 | 00-framing.md | Length | 50–60 min target is declared, but source volume cannot be verified — primary-source file is missing. If the source is thinner than the framing's six-beat density implies, the hosts will pad with repetition. | Re-calibrate after `01-primary-source.md` exists. If word count is below ~6,000, drop to a 35–45 min target and collapse Beat 6's eight-clause blessing + five negatives + six qualities into one landing rather than three. |
| P1 | 00-framing.md | Host dynamic | The single-name discipline forbids voicing the seeker's birth-name *Ubayd Allah, son of Abd Allah* outside the Beat-4 verbatim quote. The pronunciation appendix teaches the pronunciation. NotebookLM will read the appendix and then statistically reuse the name elsewhere. | In `05-pronunciation.md` (once created), gate the two birth-name entries with an explicit constraint: "These names appear ONLY inside the Beat-4 naming-dialogue verbatim quote. Do not speak them at any other moment of the episode. Refer to the figure as the seeker before and after." |
| P2 | 00-framing.md | Anti-noise rules | Format-suitability: clean (deep_dive matches a six-beat narrative walkthrough). Single-thesis: clean. Cliffhanger discipline: clean (chapter ending is explicit, no "we'll explore later"). Forbidden first-words enumerated. | No fix required for this row. |
| P2 | 00-framing.md | Pronunciation | "Surah names spoken in English meaning" is correct but does not name which surahs are touched. If the chapter cites verses (e.g., "Allah does not burden a soul beyond its capacity" — the framing already gestures here), the hosts may not know which surah they are paraphrasing. | Add a short table under `## Pronunciation` mapping each verse paraphrase the chapter uses to its surah's English meaning (e.g., "the chapter on the cow" for Q 2:286). |

---

## Cross-Bundle Patterns

Only one bundle is present, so cross-bundle pattern analysis is limited. The single dominant pattern is that the bundle is half-built: `00-framing.md` and `99-show-notes.md` are mature, while the three retrieval artifacts (`02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`) and the primary source file are either stubs or absent. NotebookLM weighs the framing as instruction and the source/key-passages as retrieval ground; with the retrieval ground empty, the framing's careful discipline (the recurring thesis spoken three times verbatim, the eight-clause blessing voiced in order, the veiled-transmission held under doctrine rather than improvised) cannot be enforced. The episode cannot generate cleanly until those four files are populated.

A second pattern: the framing exhibits very high articulation discipline (script-script Arabic, role-label substitutions, R-rule citations, forbidden-vocabulary lists), but the show-notes blurb does not inherit it — it freely transliterates Arabic, italicizes for emphasis, and stacks dashes. The tone gap between `00-framing.md` and `99-show-notes.md` is the single largest articulation drift in the bundle and should be closed before generation.

A third pattern: pronunciation guidance is inline-in-framing rather than appendix-as-artifact. If the project ships multiple episodes this way, the audit should treat the pattern as a project-wide template issue, not a per-episode one.

---

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "02-key-passages.md",
    "anchor": "Passage 1",
    "severity": "P0",
    "problem": "File is an empty stub containing only an empty blockquote and an [LLM-FILL] tag; the framing requires fourteen verbatim quotes that NotebookLM has nothing to retrieve.",
    "fix": "Populate the file with numbered verbatim passages for: the announcement, the brotherly recognition, the doxology on justice as the middle between two extremes (with the spread-out-hands figure), the chain of rights (thought to obedience), the full naming dialogue, the recurring thesis 'The name belongs to you, and you belong to the name. So it does not appear except within your limit, and it travels with your duration.', the veiled-transmission disclosure, the Hajj-by-the-great-sign figure, the eight-clause blessing, the five negatives on safeguarding the father, the six qualities, the interpretation key, and the closing line 'then his father came to him, angry.' Each passage gets the verbatim English text and a one-sentence 'Why this matters' tying it to the beat it anchors.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "Beat 1: Opening hook",
    "severity": "P0",
    "problem": "Every beat from 1 through 8 is [LLM-FILL]; the spine has no key questions, tensions, anchor passages, or landings, so the episode has no steering layer.",
    "fix": "Author all eight beats. Map them to the framing's six narrative beats (Yellowing/announcement, Council/brotherly recognition, Two discourses, Naming dialogue, Veiled transmission/Hajj figure, Farewell/interpretation key) plus Beat 1 as the opening hook in the middle of the question and Beat 8 as the silent landing. For each beat write: key question (one line), tension (one line, drawn from a specific passage in 02-key-passages.md), anchor passage (reference passage N from 02-key-passages.md), landing (one line naming what residue this beat leaves).",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "Beat 1: Opening hook",
    "severity": "P0",
    "problem": "Host-role assignment (Host A male = elder/scholar voice, Host B female = seeker/questioner voice) is declared only in 00-framing.md and not seeded in the spine; NotebookLM follows the spine more reliably than the framing for turn-by-turn role inheritance.",
    "fix": "At Beat 1 add a seed exchange labeling Host A as the elder/scholar voice and Host B as the seeker voice, with one example pushback Host B will use (draw verbatim from the framing's three pushback turns under '## Host dynamic'). Re-affirm the role at Beat 4 where the naming dialogue lands.",
    "category": "host-role"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "Beat 4: [LLM-FILL] Beat 4",
    "severity": "P0",
    "problem": "The 'HONOR THE VEIL — never invent content' discipline lives only in 00-framing.md; without it repeated at the Beat-5 anchor, NotebookLM will improvise transmission content.",
    "fix": "Write Beat 5's landing as: 'Name what kind of matters these are — the innermost inward, what the source guards under pious dissimulation — and name why the source veils. Do not invent specifics. Both hosts hold the silence before moving to the Hajj-by-the-great-sign figure.'",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "Author / narrator",
    "severity": "P0",
    "problem": "Author/narrator, what-this-chapter-is-responding-to, tradition/lineage, and related-works are all [LLM-FILL]; hosts have no retrieval-grounded background and will hallucinate origin and lineage.",
    "fix": "Populate the four required sections from 00-framing.md's '## Background' paragraph: a tenth-century dialogue treatise composed in early Fatimid Yemen, attributed by long tradition to a son of one of the founding-generation Yemeni callers, fourteen sections of dialogue ending in the testament of the dying Master; the chapter is the chapter of initiation following the chapter-three deferral on the elder's permission. Use prose, no bullets. Leave 'Why this lands now' empty per its comment.",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "Pronunciation",
    "severity": "P0",
    "problem": "Pronunciation directives sit inline in 00-framing.md instead of as a separate appendix referenced from the framing; per the audit spec, an inline-only pronunciation block counts as an absent appendix when the source contains Arabic terms.",
    "fix": "Create a new file 05-pronunciation.md as a two-column appendix (Arabic term in Arabic script — phonetic spelling), one row per term currently in the inline block (Quran, Sinai, Hajj, ihram, Sa'd, Ubayd Allah, Abd Allah). In 00-framing.md, replace the inline pronunciation paragraph with a single sentence: 'NotebookLM should consult 05-pronunciation.md for every Arabic term before voicing it.' Inside 05-pronunciation.md, gate the two birth-name rows with the constraint that those names are voiced only inside the Beat-4 naming-dialogue verbatim quote.",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb",
    "severity": "P1",
    "problem": "The blurb is a single ~800-word unbroken paragraph that exceeds the ~400-word breath limit and forces oversimplification when retrieved into NotebookLM's opening context.",
    "fix": "Split the blurb into 4 to 6 short prose paragraphs at natural narrative seams (announcement; council and brotherly recognition; the two discourses; the seventh-day naming dialogue; the veiled transmission and Hajj-by-the-great-sign; farewell, interpretation key, and the father's anger). Keep prose only; no bullets, no headings inside the blurb.",
    "category": "length"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb",
    "severity": "P1",
    "problem": "Arabic terms throughout the blurb are transliterated (Kitab al-'Alim wa-l-Ghulam, batin, da'wa, ihram, Sa'd, Ubayd Allah son of Abd Allah, Imam's permission) instead of appearing in Arabic script with a parenthesized English gloss, violating articulation style.",
    "fix": "Replace each transliterated term with its English gloss followed by the Arabic-script form in parentheses, e.g., 'the inner (الباطن)', 'the call (الدعوة)', 'the consecrated state (الإحرام)'. For the book title use the framing's role-label form: the book 'The Master and the Boy'. Remove the personal name 'Ubayd Allah, son of Abd Allah' from the blurb entirely; the framing restricts that name to the Beat-4 verbatim quote only.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb",
    "severity": "P1",
    "problem": "The blurb uses italic emphasis on most key phrases, stacked em-dashes, and dense parentheticals, which fragment retrieval weighting and break audio cadence if scraped into context.",
    "fix": "Remove every italic span. Convert em-dash chains to short sentences. Keep at most one parenthetical per sentence.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "References",
    "severity": "P1",
    "problem": "The References section contains only an empty blockquote (`>`), so the heading promises grounded references and delivers none.",
    "fix": "Either populate the References section in prose with the chapter's grounded inter-text references (the book 'The Treatise on Rights', the book 'The Psalms of Islam', the book 'The Path of Eloquence' as already named in the framing's stable-role-labels), or remove the '## References' heading and the empty blockquote line together.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Related episodes",
    "severity": "P1",
    "problem": "The related-episodes list is correct structurally but, because the framing's R-NOBACKGROUND rule forbids cross-chapter references in spoken dialogue, the list will leak into NotebookLM's context and prime the hosts to cross-reference.",
    "fix": "Add a one-line preamble directly under '## Related episodes' stating: 'These slugs are publication-only metadata. They must not be referenced in spoken dialogue. The chapter is self-contained per R-NOBACKGROUND.'",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "Length",
    "severity": "P1",
    "problem": "The 50–60 minute length target cannot be calibrated because the primary-source chapter file is missing from the bundle; if the source is thinner than the framing's six-beat density implies, the hosts will pad with repetition.",
    "fix": "After the primary-source file is restored (see the separate primary-source fix), recompute word count divided by ~140 wpm. If the result falls below 50 minutes, drop the target to 35–45 minutes and collapse Beat 6's eight-clause blessing, five negatives, and six qualities into a single landing rather than three sequential ones. Update the '## Length' paragraph in 00-framing.md to match.",
    "category": "length"
  },
  {
    "file": "00-framing.md",
    "anchor": "Host dynamic",
    "severity": "P2",
    "problem": "The three required pushback turns are listed by beat-seam but each opens mid-stream without a permitted opener; the female host's default-assent tendency may soft-pedal them.",
    "fix": "Prefix each of the three pushback turns under '## Host dynamic' with a permitted opener that is not on the forbidden-first-words list, for example 'I don't follow yet — …' or 'Let me push on that — …'. Keep the bullet-list structure of the section as is.",
    "category": "host-role"
  },
  {
    "file": "00-framing.md",
    "anchor": "Pronunciation",
    "severity": "P2",
    "problem": "The framing instructs hosts to refer to surahs by their English meaning but does not enumerate which surahs the chapter touches, so the hosts may not know which surah a paraphrase points to.",
    "fix": "Under '## Pronunciation' add a short prose paragraph listing the surahs the chapter draws from (at minimum the chapter on the cow for the verse 'Allah does not burden a soul beyond its capacity') and the English-meaning form to use for each. Also state explicitly that no Q|S:V citations appear in the chapter, so the spoken-form-citation appendix is not required for this episode.",
    "category": "citation"
  }
]
```
